"""Experimental transport: model prose only, literal fields from proved sources.

Not enabled in production. F3 and context dates are bound before inference;
the model must return F1, F2 and F4 without missing or extra fields. The final
four-record composition passes the unchanged production validators. Invalid
model text is never rewritten, shortened or given missing model information.
"""
import copy
import hashlib
import json

import qualification_prompt
import qualification_sentence_guard as guard

MODEL_IDS = ('F1', 'F2', 'F4')
INSTRUCTION = (
    'Restituisci esclusivamente JSON nella struttura response_shape. '
    'Ogni valore è una stringa con la sintesi del passaggio di quel record. '
    'Il programma riporta separatamente la frase corrente F3, letterale dalla fonte, '
    'e le date dei contesti: non rigenerarle e non aggiungere altri campi.'
)
DATE_INSTRUCTION = (
    'Conserva l’etichetta della qualifica in text e la data in contextDate.'
)
DATE_REPLACEMENT = (
    'Conserva l’etichetta della qualifica nella stringa; '
    'il programma mantiene la data del contesto originale separatamente.'
)


def prepare(bundle, modules):
    """Require the exact current production plan; derive all fixed values anew."""
    original = modules.bridge.prepare(bundle['case']['sources'][0])
    if original != bundle or bundle['kind'] != 'qualifications':
        raise ValueError('changed_or_unsupported_production_bundle')
    facts = bundle['plan']['facts']
    if tuple(f['id'] for f in facts) != ('F1', 'F2', 'F3', 'F4'):
        raise ValueError('unexpected_fact_ids')
    sentence = guard.source_sentence(bundle)
    if sentence != bundle['qualificationSentence'] or sentence['factId'] != 'F3':
        raise ValueError('changed_literal_sentence')
    # Start from the unchanged compact production prompt before its literal
    # generation instruction. Only wire shape, omitted literal record and
    # date transport wording change. Original evidence and policies stay.
    messages = qualification_prompt.messages(bundle['case'], bundle['plan'], modules.synthesis)
    system = messages[0]['content']
    if (system.count(qualification_prompt.SHAPE_INSTRUCTION) != 1
            or system.count(DATE_INSTRUCTION) != 1):
        raise ValueError('unexpected_production_instructions')
    system = system.replace(qualification_prompt.SHAPE_INSTRUCTION, INSTRUCTION)
    system = system.replace(DATE_INSTRUCTION, DATE_REPLACEMENT)
    body = json.loads(messages[1]['content'])
    body['informazioni_obbligatorie'] = [
        f for f in body['informazioni_obbligatorie'] if f['id'] in MODEL_IDS]
    body['response_shape'] = {key: '' for key in MODEL_IDS}
    schema = {'type': 'object', 'properties': {
        key: {'type': 'string', 'minLength': 1, 'maxLength': 400}
        for key in MODEL_IDS}, 'required': list(MODEL_IDS), 'additionalProperties': False}
    return {
        'productionBundle': copy.deepcopy(bundle),
        'sourceSha256': hashlib.sha256(bundle['case']['sources'][0]['text'].encode()).hexdigest(),
        'messages': [{'role': 'system', 'content': system},
                     {'role': 'user', 'content': json.dumps(body, ensure_ascii=False)}],
        'schema': schema, 'modelFactIds': list(MODEL_IDS),
        'literalQualification': sentence,
        'contextDates': {f['id']: f['contextDate'] for f in facts if 'contextDate' in f},
    }


def rejected(reason):
    return {'status': 'rejected', 'reason': reason, 'claims': [],
            'semanticVerdict': 'not_assessed'}


def validate(raw, candidate, modules, *, completed):
    if not completed:
        return rejected('stream_not_completed')
    try:
        # Rebuild the fixed values from the original source and production
        # extractor. Tampered metadata, source offsets or dates cannot become
        # authorised values merely by residing in a saved candidate bundle.
        expected = prepare(candidate['productionBundle'], modules)
        if expected != candidate:
            return rejected('candidate_or_source_changed')
        if not isinstance(raw, str) or len(raw) > 32000:
            return rejected('invalid_compact_envelope')
        value = json.loads(raw, object_pairs_hook=modules.validator.unique_object)
        if not isinstance(value, dict) or set(value) != set(MODEL_IDS):
            return rejected('missing_or_unknown_model_fact')
        if any(not isinstance(text, str) or not text.strip() or len(text) > 400
               for text in value.values()):
            return rejected('invalid_compact_text')
        # This is a declared composition of two origins, not a repair of a
        # rejected four-record response. Every model-owned string is passed
        # byte-for-byte to the existing validators. Nothing fills missing
        # F1/F2/F4 text or changes the model's numbers, qualifications or dates.
        records = {key: {'text': value[key]} for key in MODEL_IDS}
        records['F3'] = {'text': expected['literalQualification']['source_text']}
        for key, date in expected['contextDates'].items():
            records[key]['contextDate'] = date
        composed = json.dumps({'records': records}, ensure_ascii=False)
        result = guard.validate(composed, expected['productionBundle'], modules, completed=True)
        if result['status'] == 'valid_structure_pending_semantic_review':
            result['freeSynthesis'] = False
            result['composition'] = 'three_model_strings_and_prebound_literal_source_sentence_and_dates'
            result['qualificationSentenceMechanism'] = 'program_copy_of_prebound_original_span'
            result['modelFactIds'] = list(MODEL_IDS)
            result['modelTextRepaired'] = False
        return result
    except (ValueError, TypeError, KeyError, RecursionError, StopIteration):
        return rejected('invalid_compact_contract')
