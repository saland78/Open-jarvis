"""Keep execution predicates and examples inside their own operation evidence.

This finite vocabulary guard is active for capability questions only. It does
not infer command execution from subprocess control or certify entailment.
Existing source, schema and raw model text remain unchanged, without repair.
"""
from __future__ import annotations

import copy
import json
import re


OPERATION_FORMS = {
    'execution': r'\b(?:run|runs|running|perform|performs|performing|execute|executes|executing|execution|'
                 r'launch|launches|launching|spawn|spawns|spawning|esegu\w*|esecuzion[ei]|avvi\w*)\b',
    'commands': r'\b(?:commands?|comand[oi])\b',
    'external_commands': r'\b(?:external\s+commands?|comand[oi]\s+estern[oi])\b',
    'shell': r'\b(?:shells?|bash|powershell)\b',
}
INSTRUCTION = (
    ' For capability questions, paraphrase only the operation stated in the chosen passage. '
    'Do not expand control into execution or add examples and use cases. '
    'Execution, command or shell terms require sourceOperationTerms for that SAME passage; '
    'an unlisted passage licenses none. Preserve one complete supported fact per claim.'
)


def operation_terms(text):
    return {name for name, expression in OPERATION_FORMS.items()
            if re.search(expression, text, re.I)}


def operation_scope_error(text, quote):
    added = operation_terms(text) - operation_terms(quote)
    if added:
        return {'reason': 'operation_example_not_in_own_passage',
                'unsupportedOperationTerms': sorted(added)}
    return None


def apply(bank, messages, schema, selection, *, contract):
    payload = json.loads(messages[1]['content'], object_pairs_hook=contract.unique_pairs)
    if payload['passages'] != [[ref, bank[ref-1]] for ref in selection['selectedRefs']]:
        raise ValueError('operation_predicate_source_alignment_failed')
    if 'sourceOperationTerms' in payload or 'sourceOperationScopePolicy' in selection:
        raise ValueError('operation_predicate_already_applied')
    active = selection['sourceCapabilityScopePolicy']['active']
    policy = {'mode': 'finite_execution_command_shell_vocabulary_in_own_operation', 'active': active,
              'nativeSchemaChanged': False, 'sourceBytesOrNumbersChanged': False,
              'wholeAnswerRefusal': True, 'freeModelPredicatePreserved': True,
              'semanticEntailmentCertified': False, 'noOutputRepair': True}
    if not active:
        return bank, copy.deepcopy(messages), copy.deepcopy(schema), {**selection, 'sourceOperationScopePolicy': policy}
    if (len(messages) != 2 or [message['role'] for message in messages] != ['system', 'user']
            or list(payload)[-1] != 'question'):
        raise ValueError('operation_predicate_question_focus_not_compatible')
    refs = selection['sourceCapabilityScopePolicy']['eligibleOperationRefs']
    terms = {str(ref): sorted(operation_terms(bank[ref-1])) for ref in refs if operation_terms(bank[ref-1])}
    question = payload.pop('question')
    payload['sourceOperationTerms'] = terms
    payload['question'] = question
    revised = copy.deepcopy(messages)
    revised[0]['content'] += INSTRUCTION
    revised[1]['content'] = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    return bank, revised, copy.deepcopy(schema), {**selection, 'sourceOperationScopePolicy': {**policy, 'sourceOperationTerms': terms}}


def validate_generation(result, selection):
    if result['outcome'] != 'accepted_pending_semantic_review':
        return result
    policy = selection['sourceOperationScopePolicy']
    if not policy['active']:
        return result
    for index, claim in enumerate(result['claims'], 1):
        error = operation_scope_error(claim['text'], claim['quote'])
        if error:
            return {'outcome': 'rejected', 'reason': error['reason'], 'claims': [],
                    'details': {'claimIndex': index, **claim,
                                'unsupportedOperationTerms': error['unsupportedOperationTerms'],
                                'diagnosticOnly': True}}
    return result
