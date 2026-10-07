"""Keep HTML heading roles without changing the extracted source text.

Headings are retained as context. Their character ranges are produced by the
reader, never by the model. This does not determine whether prose is true or
whether a paraphrase is semantically entailed.
"""
from __future__ import annotations

import re

HEADINGS = frozenset({'h1', 'h2', 'h3', 'h4', 'h5', 'h6'})


def parser_with_heading_roles(base_parser):
    class HeadingParser(base_parser):
        def __init__(self):
            super().__init__()
            self.role_parts = []
            self.main_role_parts = []

        def append(self, data, main):
            heading = any(entry[0] in HEADINGS for entry in self.stack)
            super().append(data, main)
            self.role_parts.append((data, heading))
            if main:
                self.main_role_parts.append((data, heading))

    return HeadingParser


def normalized_heading_ranges(parser, expected_text, limit):
    """Match the installed extractor's normalization, including its final cap.

Only a line entirely from heading elements is excluded as stand-alone evidence.
A mixed heading/prose line stays selectable; its full context needs review.
No punctuation, language, topic or hard-coded page title is used as a proxy.
"""
    parts = parser.main_role_parts if parser.has_main else parser.role_parts
    raw = ''.join(data for data, _ in parts)
    flags = bytearray()
    for data, heading in parts:
        flags.extend(bytes([int(heading)]) * len(data))
    lines = []
    ranges = []
    raw_offset = 0
    text_offset = 0
    for line in raw.splitlines(keepends=True):
        meaningful = [i for i, char in enumerate(line) if not char.isspace()]
        if meaningful:
            normalized = ' '.join(line.split())
            start = text_offset
            end = start + len(normalized)
            if all(flags[raw_offset + i] for i in meaningful) and start < limit:
                ranges.append([start, min(end, limit)])
            lines.append(normalized)
            text_offset = end + 1
        raw_offset += len(line)
    if '\n'.join(lines)[:limit] != expected_text:
        raise ValueError('heading_source_alignment_failed')
    return ranges


def context_only_refs(bank, heading_ranges):
    """Resolve reader ranges against exact, unchanged bank offsets.

Missing or malformed reader metadata fails closed. An empty list is a valid
reader result (for example for a plain-text page or an HTML page with no h tags).
"""
    page = ''.join(bank)
    if not isinstance(heading_ranges, list) or len(heading_ranges) > len(page):
        raise ValueError('invalid_heading_metadata')
    previous_end = -1
    for span in heading_ranges:
        if (not isinstance(span, list) or len(span) != 2
                or any(type(value) is not int for value in span)):
            raise ValueError('invalid_heading_metadata')
        start, end = span
        if (not 0 <= start < end <= len(page) or start < previous_end
                or (start and page[start - 1] != '\n')
                or (end < len(page) and page[end] != '\n')):
            raise ValueError('invalid_heading_metadata')
        previous_end = end
    refs = []
    offset = 0
    cursor = 0
    for ref, passage in enumerate(bank, 1):
        nonspace = re.search(r'\S(?:[\s\S]*\S)?', passage)
        if nonspace:
            start, end = offset + nonspace.start(), offset + nonspace.end()
            while cursor < len(heading_ranges) and heading_ranges[cursor][1] < end:
                cursor += 1
            if cursor < len(heading_ranges):
                first, last = heading_ranges[cursor]
                if first <= start and end <= last:
                    refs.append(ref)
        offset += len(passage)
    return refs
