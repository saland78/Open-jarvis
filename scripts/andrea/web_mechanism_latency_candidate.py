"""Isolated correction for an added mechanism in a bare source capability.

This finite scope check is not general entailment. It does not repair answers,
change a historical verdict or install itself in the running application.
"""
from __future__ import annotations

import copy
import re

import web_type_latency_candidate as preceding

MECHANISM_INSTRUCTION = (' Do not add a mechanism or interface unless the selected passage explicitly states it.')


def bare_subprocess_scope_error(text, quote):
    # The actual cited unit says only "control subprocesses;". The surrounding
    # API introduction belongs to another unit under the selected-passage rule.
    if not re.fullmatch(r'control\s+subprocesses[.;]?', quote.strip(), re.I):
        return None
    means = (r'\b(?:attraverso|tramite|mediante|usando|utilizzando|through|via|using|'
             r'interfacci[ae]|interfaces?|protocoll[oi]|protocols?)\b|\bper\s+mezzo\s+di\b')
    if re.search(means, text, re.I):
        return 'subprocess_mechanism_not_in_passage'
    return None


def prepare(page, question, *, heading_ranges):
    bank, messages, schema = preceding.prepare(page, question, heading_ranges=heading_ranges)
    messages = copy.deepcopy(messages)
    messages[0]['content'] += MECHANISM_INSTRUCTION
    return bank, messages, schema


def validate(raw, bank, complete, *, heading_ranges):
    result = preceding.validate(raw, bank, complete, heading_ranges=heading_ranges)
    if result['outcome'] != 'accepted_pending_semantic_review':
        return result
    for index, claim in enumerate(result['claims'], 1):
        error = bare_subprocess_scope_error(claim['text'], claim['quote'])
        if error:
            return {'outcome': 'rejected', 'reason': error, 'claims': [],
                    'details': {'claimIndex': index, 'passage': claim['passage'],
                                'text': claim['text'], 'quote': claim['quote'],
                                'diagnosticOnly': True}}
    return result
