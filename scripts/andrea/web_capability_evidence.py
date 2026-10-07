"""Use operation statements as evidence when a question asks for capabilities.

This finite recognizer covers action-led documentation units. It does not
infer an operation from suitability, performance, a heading or nearby text.
Source bytes and numbering stay unchanged; evidence eligibility is explicit.
"""
from __future__ import annotations

import copy
import json
import re


CAPABILITY_QUESTION = r'\b(?:funzionalit[\u00e0a]|functionalit(?:y|ies)|capabilities)\b'
ACTION_START = r'^(?:run|perform|control|distribute|synchroni[sz]e|inspect(?:ing)?|create|manage|implement|bridge)\s+'
INSTRUCTION = (' For a capability question with capabilityEvidenceRefs, select ONLY those operation '
               'statements as evidence. Suitability and performance descriptions are not additional '
               'functionalities. Answer the requested number with distinct supported operations; '
               'never invent a missing operation. All other passages remain context only for this question.')


def action_statement(quote):
    # Deliberately narrow: prose that merely mentions an operation, a heading,
    # uppercase prompt instructions and incomplete fragments are not promoted.
    return (20 <= len(quote) <= 600
            and bool(re.search(ACTION_START, quote.lstrip()))
            and bool(re.search(r'[.;]\s*$', quote)))


def apply(bank, messages, schema, selection, *, contract):
    payload = json.loads(messages[1]['content'], object_pairs_hook=contract.unique_pairs)
    if payload['passages'] != [[ref, bank[ref-1]] for ref in selection['selectedRefs']]:
        raise ValueError('capability_evidence_source_alignment_failed')
    capability_question = bool(re.search(CAPABILITY_QUESTION, payload['question'], re.I))
    statements = [ref for ref in selection['selectedRefs'] if action_statement(bank[ref-1])]
    # Do not turn an unrelated or insufficient page into a forced two-point
    # answer. Existing abstention, source checks and manual review still apply.
    active = capability_question and len(statements) >= 2
    policy = {'mode': 'action_led_source_units_for_capability_question', 'active': active,
              'capabilityQuestionRecognized': capability_question,
              'eligibleOperationRefs': statements if active else [],
              'sourceBytesOrNumbersChanged': False, 'sourceStillSuppliedAsContext': True,
              'nativeEvidenceEligibilityChangedExplicitly': active,
              'nativeArrayMinimumChanged': False, 'freeModelPredicatePreserved': True,
              'semanticEntailmentCertified': False, 'noOutputRepair': True}
    if not active:
        return bank, copy.deepcopy(messages), copy.deepcopy(schema), {**selection, 'sourceCapabilityScopePolicy': policy}
    revised_schema = copy.deepcopy(schema)
    items = revised_schema['properties']['claims']['items']
    branches = items.get('oneOf', [items])
    revised_branches, represented = [], set()
    for branch in branches:
        revised = copy.deepcopy(branch)
        references = revised['properties']['passage']['enum']
        references = [ref for ref in references if ref in statements]
        if references:
            revised['properties']['passage']['enum'] = references
            revised_branches.append(revised)
            represented.update(references)
    if represented != set(statements):
        raise ValueError('capability_evidence_native_references_not_aligned')
    revised_schema['properties']['claims']['items'] = {'oneOf': revised_branches}
    revised_messages = copy.deepcopy(messages)
    revised_messages[0]['content'] += INSTRUCTION
    payload['capabilityEvidenceRefs'] = statements
    # Labels on non-operation descriptions are no longer generation branches.
    for name in ('requiredStarts', 'sourceFrequencyQualifiers'):
        if name in payload:
            payload[name] = {key: value for key, value in payload[name].items() if int(key) in represented}
    revised_messages[1]['content'] = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    revised_selection = copy.deepcopy(selection)
    if 'nativeIdentifierPolicy' in revised_selection:
        revised_selection['nativeIdentifierPolicy']['rules'] = [rule for rule in revised_selection['nativeIdentifierPolicy']['rules']
                                                               if rule['passage'] in represented]
    labels = revised_selection.get('sourceLabelScopePolicy')
    if labels:
        for key in ('sourceFrequencyRefs', 'sourceCsvFileAliasRefs'):
            labels[key] = [ref for ref in labels[key] if ref in represented]
        revised_guards = []
        for guard in labels['guardBranches']:
            guard['passages'] = [ref for ref in guard['passages'] if ref in represented]
            if guard['passages']:
                revised_guards.append(guard)
        labels['guardBranches'] = revised_guards
    revised_selection['sourceCapabilityScopePolicy'] = policy
    return bank, revised_messages, revised_schema, revised_selection


def validate_generation(result, selection):
    if result['outcome'] != 'accepted_pending_semantic_review':
        return result
    policy = selection['sourceCapabilityScopePolicy']
    if policy['active']:
        for index, claim in enumerate(result['claims'], 1):
            if claim['passage'] not in policy['eligibleOperationRefs']:
                return {'outcome': 'rejected', 'reason': 'capability_not_supported_by_operation_statement',
                        'claims': [], 'details': {'claimIndex': index, **claim, 'diagnosticOnly': True}}
    return result
