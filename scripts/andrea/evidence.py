"""Conservative lookup of explicit count fields; no semantic truth certification.

Only a small, declared set of Italian quantity questions is handled. Values
remain statements in excerpts, not independently verified facts. Other questions
return None and retain the separately labelled model synthesis path.
"""
from __future__ import annotations

import re
import unicodedata


def normalized(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)).lower()


FIELDS = {
    "published": ("titoli pubblicati", r"(?:libri|titoli)[ _]+pubblicati", r"\b(?:libri|titoli)\b"),
    "copies": ("copie vendute", r"copie[ _]+vendute(?:[ _]+totali)?", r"\b(?:vendite|copie)\b"),
}


def supplied_sources(value):
    """Bounded excerpts supplied by a local caller, never labelled as vault reads."""
    if not isinstance(value, list) or not 1 <= len(value) <= 3:
        raise ValueError("Fornisci da uno a tre estratti locali.")
    result, seen = [], set()
    for source in value:
        if not isinstance(source, dict) or set(source) - {"id", "title", "text", "modifiedAt"}:
            raise ValueError("Formato degli estratti forniti non valido.")
        sid = source.get("id")
        if not isinstance(sid, str) or sid not in {"N1", "N2", "N3"} or sid in seen:
            raise ValueError("Identificativi delle fonti non validi.")
        if not isinstance(source.get("text"), str) or not source["text"].strip() or len(source["text"]) > 900:
            raise ValueError("Estratto vuoto o troppo lungo.")
        if not isinstance(source.get("title"), str) or len(source["title"]) > 160:
            raise ValueError("Titolo della fonte non valido.")
        if "modifiedAt" in source and (not isinstance(source["modifiedAt"], str) or len(source["modifiedAt"]) > 80):
            raise ValueError("Data del file non valida.")
        seen.add(sid)
        result.append(dict(source))
    return result


def explicit_count_answer(query, sources):
    """Quote counts verbatim for simple lookup questions; abstain outside scope.

    Numeric fields need an explicit value. Missing values, decimals, estimates,
    causal/operational questions and unrecognised metrics are not converted into
    an answer. Separate files or modifiedAt never resolve different counts.
    """
    query_norm = normalized(query)
    if not re.search(r"\b(?:quanti|quante|quali|numero|conteggio)\b", query_norm):
        return None
    if re.search(r"\b(?:non|nessun|nessuno|come|perche|consigli|strategia|strategie|previsioni|confronta|confrontare|trend|crescita|migliorare|scaricare|devo|royalty|ricavi)\b", query_norm) or query.count("?") > 1:
        return None
    wanted = {key for key, (_, _, intent) in FIELDS.items() if re.search(intent, query_norm)}
    if "published" in wanted and not re.search(r"\bpubblicat[ioae]\b", query_norm):
        wanted.remove("published")
    if "copies" in wanted and not re.search(r"\b(?:vendite|vendute)\b", query_norm):
        wanted.remove("copies")
    if not wanted:
        return None
    rows = []
    for source in sources:
        for line in source["text"].splitlines():
            # This path copies the entire original field line. Do not introduce
            # a second citation namespace or treat a qualified estimate as fact.
            line_norm = normalized(line)
            if re.search(r"\[N\d+\]", line) or re.search(r"\b(?:stima|stimato|stimata|stimati|stimate|circa|ipotetico|ipotetica|ipotetici|ipotetiche)\b", line_norm):
                continue
            for key in wanted:
                _, label, _ = FIELDS[key]
                pattern = r"(?<!\w)" + label + r"(?:\s+sono)?(?:\s+(?:nel|per|a|al)\s+[^:\n|]{1,45})?[\s*:=|]+(\d{1,9})(?!\w|[.,]\d)"
                matches = list(re.finditer(pattern, line_norm))
                for match in matches:
                    # Negated statements cannot be reduced to a positive field.
                    if re.search(r"\b(?:non|nessun|nessuno)\b", line_norm[:match.start()]):
                        continue
                    tail = line_norm[match.end():].lstrip("*_`")
                    if re.match(r"\s*(?:[-–—/+]|(?:o|oppure|mila|k|euro)\b|milion\w*\b|miliard\w*\b|%|€|dollar\w*\b)", tail):
                        continue
                    rows.append({"field": key, "value": int(match.group(1)), "id": source["id"], "quote": line})
    if {row["field"] for row in rows} != wanted:
        return None
    conflicts = []
    for key in sorted(wanted):
        related = [row for row in rows if row["field"] == key]
        if len({row["value"] for row in related}) > 1:
            values = list(dict.fromkeys(f"{row['value']} [{row['id']}]" for row in related))
            conflicts.append(f"Valori discordanti per «{FIELDS[key][0]}»: " + " e ".join(values) + ".")
    quotes = list(dict.fromkeys(f"«{row['quote']}» [{row['id']}]" for row in rows))
    if conflicts:
        heading = " ".join(conflicts) + " Non scelgo un conteggio unico: occorre chiarire periodo e ambito delle fonti. La separazione delle schede e la data del file non risolvono questa discrepanza."
    else:
        heading = "Dati espliciti negli estratti; le fonti non sono state verificate su sistemi esterni."
    return heading + "\n\n" + "\n\n".join(quotes)
