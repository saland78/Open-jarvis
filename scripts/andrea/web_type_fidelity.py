"""Finite technical equivalence and selected CSV conversion result-type guards.

No model text is repaired. These guards check known lexical relationships, not
general entailment, and do not decide whether a source itself is true.
"""
from __future__ import annotations

import re


def io_identifier_text(text):
    """The exact standard input/output expansion, not arbitrary paraphrases.

    This is a temporary lexical scan representation. The original claim, quote,
    source bank and returned text stay byte-for-byte unchanged. Both the claim
    and its own quote are scanned; another passage cannot license an I/O fact.
    """
    return re.sub(r'(?<![\w/])input/output(?![\w/])', 'I/O', text, flags=re.I)


def csv_converted_source_types(quote):
    """float belongs to the explicit QUOTE_NONNUMERIC/unquoted-fields rule.

    The source's plural floats names the singular Python result type float.
    An unrelated mention of float or a page-level glossary does not suffice.
    """
    field_type = (r'\b(?:unquoted|non[- ]quoted)\s+fields\s+(?:are\s+)?'
                  r'(?:transformed|converted)\s+(?:into|to)\s+floats?\b')
    signature = re.search(r'\bQUOTE_NONNUMERIC\b', quote) and re.search(field_type, quote, re.I)
    return {'float'} if signature else set()


def float_terms(text):
    """Finite same-concept forms; numeri decimali/Decimal are not aliases."""
    forms = r'\b(?:floats?|floating[- ]point|a\s+virgola\s+mobile)\b'
    return {'float'} if re.search(forms, text, re.I) else set()


def converted_field_targets(text):
    """Known conversion predicates with a stated target, scoped to a field clause.

    This finite lexical detector is deliberately not a complete parser. A default
    rule without a stated conversion target is not forced to restate another fact.
    Common explicit negated-conversion forms are not positive target assertions.
    """
    targets = []
    predicate = (r'\b(?:(?:convert(?:a|ano|e|ono|s)?|convertit[oi]|converted|trasformat[oi]|'
                 r'trasform(?:a|ano)|transformed)\b[^.!?;]*?\b(?:in|into|to|as)\s+'
                 r'|(?:divent(?:a|ano)|becomes?)\s+)([^.!?;]+)')
    for clause in re.split(r'[.!?;]', text):
        if not re.search(r'\b(?:camp[oi]|fields?)\b', clause, re.I):
            continue
        for match in re.finditer(predicate, clause, re.I):
            prefix = clause[:match.start()]
            negated = (re.search(r'\b(?:non|not)\s+(?:(?:vengono|viene|sono|è|is|are|be)\s+)?$', prefix, re.I)
                       or re.search(r'\b(?:do|does)n[\'’]t\s+$', prefix, re.I))
            if not negated:
                targets.append(match.group(1))
    return targets


def converted_field_type_error(text, quote):
    required = csv_converted_source_types(quote)
    if not required:
        return None
    for target in converted_field_targets(text):
        # An explicit alternative target (including float or Decimal) is not
        # licensed by this source rule. The whole target must still be reviewed.
        alternatives = re.search(r'\b(?:decimali?|decimal|integers?|int|strings?|stringhe|booleans?|bool)\b', target, re.I)
        if alternatives or not required.issubset(float_terms(target)):
            return 'converted_field_type_not_preserved'
    return None
