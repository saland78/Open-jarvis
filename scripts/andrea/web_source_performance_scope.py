"""Keep generated performance vocabulary anchored to its own evidence unit.

Supporting an operation does not establish that it is efficient, faster or
low-latency. This finite lexical guard detects unsupported additions; it does
not prove entailment, resolve negations or replace review of the whole answer.
The original source, native schema and model answer are never repaired here.
"""
from __future__ import annotations

import copy
import json
import re


# These are separate attributes. A high-performance server, for example, does
# not establish faster execution or efficient connections in a different unit.
PERFORMANCE_FORMS = {
    'efficiency': r'\b(?:efficient(?:ly)?|efficiency|efficiencies|efficient[ei]|efficienza)\b',
    'speed': r'\b(?:fast(?:er|est)?|quick(?:er|est|ly)?|speed(?:up|ups)?|'
             r'veloc[ei]|velocemente|velocit\u00e0|rapid[oaie]|rapidamente|'
             r'accelerat\w*|accelerazion[ei])\b',
    'high_performance': r'\b(?:high[- ]performance|high[- ]performing|'
                        r'alt[ea]\s+prestazioni|prestazioni\s+elevate|performant[ei])\b',
    'low_latency': r'\b(?:(?:low|lower|reduced|zero|no)[- ]latency|'
                   r'(?:bass[ae]|minim[ae]|ridott[ae]|zero)\s+latenz[ae]|'
                   r'senza\s+latenza|latenz[ae]\s+(?:ridott[ae]|minim[ae]))\b',
}

INSTRUCTION = (
    ' Describe capabilities with neutral verbs, without adding benefits. '
    'Performance vocabulary is allowed only by sourcePerformanceTerms for the SAME selected passage; '
    'an unlisted passage licenses none. Efficiency, speed, high performance and low latency '
    'are different attributes. Operation support alone does not establish efficiency. '
    'Labels do not support the predicate; use only that passage, never its neighbors.'
)


def performance_terms(text):
    """Finite English/Italian vocabulary presence, never a truth classifier."""
    return {name for name, expression in PERFORMANCE_FORMS.items()
            if re.search(expression, text, re.I)}


def performance_scope_error(text, quote):
    added = performance_terms(text) - performance_terms(quote)
    if added:
        return {'reason': 'performance_attribute_not_in_own_passage',
                'unsupportedPerformanceTerms': sorted(added)}
    return None


def apply(bank, messages, schema, selection, *, contract):
    payload = json.loads(messages[1]['content'], object_pairs_hook=contract.unique_pairs)
    if payload['passages'] != [[ref, bank[ref-1]] for ref in selection['selectedRefs']]:
        raise ValueError('performance_scope_source_alignment_failed')
    vocabulary = {str(ref): sorted(performance_terms(bank[ref-1]))
                  for ref in selection['selectedRefs'] if performance_terms(bank[ref-1])}
    if 'sourcePerformanceTerms' in payload:
        raise ValueError('performance_scope_already_applied')
    payload['sourcePerformanceTerms'] = vocabulary
    revised_messages = copy.deepcopy(messages)
    revised_messages[0]['content'] += INSTRUCTION
    revised_messages[1]['content'] = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    revised_selection = {**selection, 'sourcePerformanceScopePolicy': {
        'mode': 'finite_performance_vocabulary_from_own_passage',
        'sourcePerformanceTerms': vocabulary, 'nativeSchemaChanged': False,
        'freeModelPredicatePreserved': True, 'sourceBytesOrNumbersChanged': False,
        'postGenerationCheckAddedExplicitly': True, 'wholeAnswerRefusal': True,
        'semanticEntailmentCertified': False, 'noOutputRepair': True}}
    return bank, revised_messages, copy.deepcopy(schema), revised_selection


def validate_generation(result, selection):
    # Preserve all preceding refusals, missing values and abstention exactly.
    if result['outcome'] != 'accepted_pending_semantic_review':
        return result
    if 'sourcePerformanceScopePolicy' not in selection:
        raise ValueError('performance_scope_policy_missing')
    for index, claim in enumerate(result['claims'], 1):
        error = performance_scope_error(claim['text'], claim['quote'])
        if error:
            return {'outcome': 'rejected', 'reason': error['reason'], 'claims': [],
                    'details': {'claimIndex': index, **claim,
                                'unsupportedPerformanceTerms': error['unsupportedPerformanceTerms'],
                                'diagnosticOnly': True}}
    return result
