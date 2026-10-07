"""Conservative source-scope fallback, not a semantic model validator.

Only two explicit, dated conventions are recognized. Do not infer freshness
from file timestamps, rank conflicting sources, or certify external facts.
"""
from __future__ import annotations

import re

LABEL = re.compile(r"\bDATO (?:NON VERIFICATO|ASSENTE)\b")
DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def scoped_labels(sources):
    rows = []
    for source in sources:
        context = None
        for line in source["text"].splitlines():
            clean = line.strip().lstrip("> ").strip()
            if DATE.search(clean) and re.search(r"\bAggiornamento\b", clean, re.I):
                context = ("update", line)
            elif DATE.search(clean) and re.search(r"\bFotografia\b", clean, re.I):
                context = ("snapshot", line)
            elif re.match(r"^#{1,6}\s", clean):
                context = None
            if context:
                for match in LABEL.finditer(line):
                    rows.append({"source": source["id"], "kind": context[0],
                                 "heading": context[1], "label": match.group()})
    return rows


def status_scope_answer(sources):
    """Decline free synthesis for recognized mixed status contexts.

Labels can mention different quantities: this rule deliberately declines
without asserting that they conflict. Even a cut line may contain a complete
label: quote only that label and its preceding explicit dated heading.
"""
    rows = scoped_labels(sources)
    if not (any(r["kind"] == "update" and r["label"] == "DATO NON VERIFICATO" for r in rows)
            and any(r["kind"] == "snapshot" and r["label"] == "DATO ASSENTE" for r in rows)):
        return None
    if any(re.search(r"\[N\d+\]", s["text"]) for s in sources):
        return ("Sintesi libera non generata: gli estratti contengono qualifiche datate "
                "differenti e riferimenti ambigui. Apri le note per confrontarli. "
                "Nessuna verifica su sistemi esterni è stata effettuata.")
    passages = []
    seen = set()
    for row in rows:
        key = (row["source"], row["heading"], row["label"])
        if key in seen:
            continue
        seen.add(key)
        # Bounded literal fragments; never truncate a heading into a new fact.
        if len(row["heading"]) > 300:
            passages.append(f"[{row['source']}] Intestazione troppo lunga: apri la nota.")
        else:
            passages.append(f"«{row['heading']}»\nEtichetta presente in questo contesto: «{row['label']}». [{row['source']}]")
    return (
        "Sintesi libera non generata: negli estratti sono presenti un aggiornamento "
        "con DATO NON VERIFICATO e una fotografia con DATO ASSENTE. Per evitare "
        "di fondere le qualifiche, mostro separatamente intestazioni ed etichette "
        "copiate dalle fonti. Non stabilisco se riguardino lo stesso valore.\n\n"
        + "\n\n".join(passages[:6])
        + "\n\nSelezione parziale: queste etichette non significano zero, non descrivono "
        "il contenuto di dashboard esterne e non verificano la situazione attuale. "
        "Apri le note per leggere le qualifiche complete."
    )
