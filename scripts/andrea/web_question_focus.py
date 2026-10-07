"""Keep the unchanged user question after source-format metadata, without repair.

An unrelated source fact is not an answer. Named-subject absence is a narrow
lexical relevance guard, not a complete answerability or entailment classifier.
The model must still produce its own empty claims array; its schema stays open.
"""
from __future__ import annotations

import copy
import json
import re


NEUTRAL_PERFORMANCE_START = ' Answer the user question without adding benefits. '
OLD_CAPABILITY_START = ' Describe capabilities with neutral verbs, without adding benefits. '
INSTRUCTION = (
    ' The final question field is the actual task; source metadata is not another task. '
    'Answer ONLY that question. A true but unrelated page fact is not an answer. '
    'requestedSubjects are names from the question, not evidence. '
    'If the passages do not support the requested information about that subject, return {"claims":[]}; '
    'do not replace a missing answer with a general page summary.'
)
SUBJECT_PATTERN = (r'\b(?:servizio|progetto|prodotto|azienda|service|project|product|company)\s+'
                   r'([A-Z\u00c0-\u00d6\u00d8-\u00de][\w-]{1,59}'
                   r'(?:\s+[A-Z\u00c0-\u00d6\u00d8-\u00de][\w-]{1,59}){0,3})')


def named_subjects(question):
    # Only an explicit contextual noun followed by capitalized name tokens.
    # No case-specific product, query, URL or expected answer is embedded.
    return sorted(set(re.findall(SUBJECT_PATTERN, question)))


def contains_subject(text, name):
    return bool(re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)', text, re.I))


def apply(bank, messages, schema, selection, *, contract):
    payload = json.loads(messages[1]['content'], object_pairs_hook=contract.unique_pairs)
    if payload['passages'] != [[ref, bank[ref-1]] for ref in selection['selectedRefs']]:
        raise ValueError('question_focus_source_alignment_failed')
    if (len(messages) != 2 or [value['role'] for value in messages] != ['system', 'user']
            or messages[0]['content'].count(OLD_CAPABILITY_START) != 1):
        raise ValueError('question_focus_instruction_not_compatible')
    question = payload.pop('question')
    subjects = named_subjects(question)
    source = ''.join(quote for _, quote in payload['passages'])
    missing = [name for name in subjects if not contains_subject(source, name)]
    if subjects:
        payload['requestedSubjects'] = subjects
    # Source content and all existing metadata values remain exactly the same.
    # The actual question ends the user input, after the metadata, without a
    # third role, repetition, hidden hint, synthetic fact or forced answer.
    payload['question'] = question
    revised = copy.deepcopy(messages)
    revised[0]['content'] = revised[0]['content'].replace(OLD_CAPABILITY_START, NEUTRAL_PERFORMANCE_START, 1)
    revised[0]['content'] += INSTRUCTION
    revised[1]['content'] = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    policy = {'mode': 'unchanged_question_last_and_literal_named_subject_scope',
              'questionFieldLast': True, 'unconditionalCapabilityInstructionRemoved': True,
              'requestedSubjects': subjects, 'subjectsAbsentFromSelectedContext': missing,
              'sourceBytesOrNumbersChanged': False, 'nativeSchemaChanged': False,
              'modelMustGenerateOwnAbstention': True, 'noForcedEmptySchema': True,
              'wholeAnswerRefusal': True, 'semanticAnswerabilityCertified': False,
              'noOutputRepair': True}
    return bank, revised, copy.deepcopy(schema), {**selection, 'questionFocusPolicy': policy}


def relevance_diagnostic(raw, selection, *, contract):
    try:
        data = json.loads(raw, object_pairs_hook=contract.unique_pairs)
    except (ValueError, TypeError):
        return {'outcome': 'not_assessed_invalid_model_json'}
    if (not isinstance(data, dict) or set(data) != {'claims'}
            or not isinstance(data['claims'], list)):
        return {'outcome': 'not_assessed_invalid_model_shape'}
    missing = selection['questionFocusPolicy']['subjectsAbsentFromSelectedContext']
    if missing and data['claims']:
        return {'outcome': 'nonempty_answer_with_requested_subject_absent',
                'subjectsAbsentFromSelectedContext': missing, 'diagnosticOnly': True}
    return {'outcome': 'model_abstained' if not data['claims'] else 'no_absent_subject_lexical_failure',
            'semanticAnswerabilityCertified': False}


def validate_generation(result, selection):
    if result['outcome'] != 'accepted_pending_semantic_review':
        return result
    missing = selection['questionFocusPolicy']['subjectsAbsentFromSelectedContext']
    if missing:
        return {'outcome': 'rejected', 'reason': 'requested_subject_absent_from_supplied_context',
                'claims': [], 'details': {'subjectsAbsentFromSelectedContext': missing,
                                        'diagnosticOnly': True}}
    return result
