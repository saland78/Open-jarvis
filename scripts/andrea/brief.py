"""Bounded extractive replies: copy source blocks, never paraphrase facts.

This is a separate mode, not a validator for arbitrary model prose. Paragraphs
and their preceding headings stay together; modifiedAt never supplies a date.
The selected passages are partial and do not certify the source's truth.
"""
from __future__ import annotations

import re

MAX_WORDS_PER_SOURCE = 140


def selected_passage(text):
    """Return one complete-looking paragraph with its literal heading context.

Do not shorten a long block by deleting qualifiers, negation or dates. An
excerpt's final block can itself be cut by retrieval: refuse visibly unfinished
text. This cannot prove the note or the excerpt has no omitted qualification.
"""
    if re.search(r"\[N\d+\]", text):
        return None
    headings = []
    blocks = re.split(r"\n[ \t]*\n", text)
    for index, raw in enumerate(blocks):
        block = raw.strip()
        if not block:
            continue
        lines = block.splitlines()
        while lines and re.match(r"^#{1,6}\s", lines[0]):
            heading = lines.pop(0)
            level = len(heading) - len(heading.lstrip("#"))
            headings = [(depth, value) for depth, value in headings if depth < level]
            headings.append((level, heading))
        if not lines:
            continue
        body = "\n".join(lines)
        # Reusing source-owned [N...] would introduce an ambiguous namespace.
        if re.search(r"\[N\d+\]", body):
            return None
        if index == len(blocks) - 1 and not re.search(r"[.!?。！？][\s*`\"'»)]*$", body):
            return None
        passage = "\n".join([value for _, value in headings] + [body])
        if len(passage.split()) > MAX_WORDS_PER_SOURCE:
            return None
        return passage
    return None


def brief_answer(sources):
    """Copy at most one bounded passage per source, retaining all source IDs.

No relevance/completeness/truth claim is inferred from selection. Conflicting
sources are displayed separately instead of resolving them by file timestamp.
"""
    rows = []
    for source in sources:
        passage = selected_passage(source["text"])
        if passage is None:
            rows.append(f"[{source['id']}] Nessun passaggio breve selezionabile senza tagliare il testo: apri la nota.")
        else:
            rows.append(f"«{passage}» [{source['id']}]")
    return (
        "Passaggi originali, senza parafrasi. Selezione parziale: non è una risposta esaustiva "
        "e non verifica i dati su sistemi esterni.\n\n" + "\n\n".join(rows)
    )
