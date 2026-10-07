"""Keep the verified fetcher and source bytes; add reader-owned HTML roles."""
from __future__ import annotations
import json
import sys
import web_page_fetch as fetch
import web_heading_evidence as headings
import web_definition_context as definitions


def read_request(raw):
    original_parser, original_extract = fetch.TextParser, fetch.extract
    instrumented = definitions.parser_with_definition_roles(headings.parser_with_heading_roles(original_parser))
    instances, heading_ranges, definition_ranges = [], [], []
    class Captured(instrumented):
        def __init__(self):
            super().__init__()
            instances.append(self)
    def extract(body, content_type):
        nonlocal heading_ranges, definition_ranges
        title, text, partial = original_extract(body, content_type)
        if content_type.split(';')[0].strip().lower() == 'text/html':
            parser = instances[-1]
            heading_ranges = headings.normalized_heading_ranges(parser, text, fetch.MAX_TEXT)
            definition_ranges = definitions.normalized_definition_ranges(parser, text, fetch.MAX_TEXT)
        return title, text, partial
    try:
        fetch.TextParser, fetch.extract = Captured, extract
        page = fetch.read_request(raw)
        if 'error' not in page:
            page['headingRanges'], page['definitionRanges'] = heading_ranges, definition_ranges
        return page
    finally:
        fetch.TextParser, fetch.extract = original_parser, original_extract


if __name__ == '__main__':
    try:
        result = read_request(sys.stdin.buffer.read(4097))
    except Exception:
        result = {'error': 'unexpected_worker_error'}
    print(json.dumps(result, ensure_ascii=False))
