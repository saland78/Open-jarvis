"""A native one-claim budget for a proven, single CSV conversion-rule question.

This is a small, closed-domain Italian intent route, not a general classifier.
Unknown wording, multiple requested facts/APIs or multiple source rules retain
the two-claim contract. Every case still uses inference and source validation.
No generated claim is removed, repaired, merged or chosen after generation.
"""
from __future__ import annotations

import copy
import re
import unicodedata


FOCUS_PATTERNS = (
    r'come si comporta csv\.reader (?:rispetto alla|riguardo alla|con la) conversione automatica dei (?:tipi|campi)',
    r'csv\.reader (?:converte|trasforma) automaticamente (?:i tipi|i campi|i valori)',
    r'(?:quando|in quali condizioni) csv\.reader (?:converte|trasforma) (?:i tipi|i campi|i valori)',
    r'(?:spiega|descrivi) la regola di conversione automatica (?:dei tipi )?di csv\.reader',
)
CONDITION_TAIL = (r"(?:[?.]\s*(?:conserva|mantieni|indica) "
                  r"(?:l'(?:eventuale )?condizione|la condizione|le condizioni))?[?.]?")
SINGLE_RULE_QUESTION = re.compile(r'(?:'+'|'.join(FOCUS_PATTERNS)+')'+CONDITION_TAIL)
OLD_COUNT_INSTRUCTION = 'up to two distinct relevant paraphrases'
ONE_COUNT_INSTRUCTION = 'at most one complete paraphrase of the rule'


def ordinary_policy(reason):
    return {'mode': 'ordinary_two_claims', 'maxClaims': 2, 'reason': reason,
            'sourceRuleRefs': [], 'nativeArrayLimitChanged': False}


def plan(question, bank, selection, *, contract):
    if (selection['mode'] != 'complete_api_entries'
            or selection['matchedAnchors'] != ['csv.reader']):
        return ordinary_policy('no_complete_single_reader_entry')
    normalized = ' '.join(unicodedata.normalize('NFKC', question).casefold().replace('’', "'").split())
    if SINGLE_RULE_QUESTION.fullmatch(normalized) is None:
        return ordinary_policy('single_conversion_question_not_proven')
    refs = [ref for ref in selection['selectedRefs']
            if contract.csv_converted_source_types(bank[ref-1])
            and re.search(r'\bNo automatic data type conversion\b.*?\bunless\b', bank[ref-1], re.I | re.S)]
    if len(refs) != 1:
        return ordinary_policy('one_complete_own_source_rule_not_proven')
    return {'mode': 'single_csv_conversion_rule', 'maxClaims': 1,
            'reason': 'recognized_single_rule_question_and_one_complete_source_rule',
            'sourceRuleRefs': refs, 'nativeArrayLimitChanged': True}


def apply(messages, schema, policy):
    """Change only the upfront count instruction and native array cardinality."""
    if policy['maxClaims'] == 2:
        return messages, schema
    if (policy['maxClaims'] != 1
            or messages[0]['content'].count(OLD_COUNT_INSTRUCTION) != 1
            or schema['properties']['claims'].get('maxItems') != 2):
        raise ValueError('single_rule_contract_not_compatible')
    messages, schema = copy.deepcopy(messages), copy.deepcopy(schema)
    messages[0]['content'] = messages[0]['content'].replace(OLD_COUNT_INSTRUCTION, ONE_COUNT_INSTRUCTION, 1)
    schema['properties']['claims']['maxItems'] = 1
    return messages, schema


def validate_cardinality(result, policy):
    """Refuse a violated budget even if an engine fails to honor its schema."""
    maximum = policy['maxClaims']
    if type(maximum) is not int or maximum not in (1, 2):
        raise ValueError('invalid_rule_claim_budget')
    if result['outcome'] == 'accepted_pending_semantic_review' and len(result['claims']) > maximum:
        return {'outcome': 'rejected', 'reason': 'single_rule_cardinality_exceeded', 'claims': [],
                'details': {'maximumClaims': maximum, 'actualClaims': len(result['claims']),
                            'originalClaims': copy.deepcopy(result['claims']), 'diagnosticOnly': True}}
    return result
