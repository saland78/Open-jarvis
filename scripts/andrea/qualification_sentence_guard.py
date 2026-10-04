"""Preserve the entire proved qualification, including consultation prerequisites.

The current qualification is a literal source-bound field, not a free
paraphrase. Other records still come from the model. The returned text is
checked independently, never repaired after generation.
"""
import copy
import json
import re

from qualification_clause_guard import source_clause

# Recognise only the consultation convention present in the public test
# and the installed note. Unknown wording is unsupported, never completed.
CONSULTATION = re.compile(
    r'consultare dashboard o report(?: KDP)? indicando periodo, titolo e marketplace\.'
)
INSTRUCTION = (
    ' Il record indicato da protected_qualification contiene una frase '
    'letterale della fonte: emetti source_text integralmente, senza '
    'parafrasarla, accorciarla o aggiungere altro. Comprende qualifica, '
    'ambito e indicazioni di consultazione. Gli altri record rimangono '
    'sintesi del modello da verificare. La frase protetta non verifica '
    'i dati della nota e non autorizza alcuna azione esterna.'
)


def source_sentence(bundle):
    """Derive the full string only from the already-proved original span."""
    prefix = source_clause(bundle)
    fact = next(f for f in bundle['plan']['facts'] if f['id'] == prefix['factId'])
    proof = next(p for p in fact['proofs'] if p['role'] == 'qualification')
    # source_clause already checks uniqueness and exact original offsets.
    visible = re.sub(r'\s+', ' ', re.sub(r'[*`>]', '', proof['quote'])).strip()
    beginning = prefix['source_prefix'] + ' '
    if not visible.startswith(beginning):
        raise ValueError('qualification_prefix_changed')
    consultation = visible[len(beginning):]
    if CONSULTATION.fullmatch(consultation) is None:
        raise ValueError('unsupported_consultation_sentence')
    return {'factId': fact['id'], 'source_text': visible,
            'source_prefix': prefix['source_prefix'], 'consultation': consultation}


def protect(bundle):
    """Protect the complete source sentence BEFORE generation, without repair."""
    sentence = source_sentence(bundle)
    secured = copy.deepcopy(bundle)
    field = secured['plan']['schema']['properties']['records']['properties'][sentence['factId']]['properties']['text']
    if field != {'type': 'string', 'minLength': 1, 'maxLength': 400}:
        raise ValueError('unexpected_text_schema')
    field['const'] = sentence['source_text']
    messages = secured['messages']
    if (len(messages) != 2 or messages[0]['role'] != 'system'
            or messages[1]['role'] != 'user'):
        raise ValueError('unexpected_messages')
    body = json.loads(messages[1]['content'])
    if set(body) != {'richiesta', 'informazioni_obbligatorie', 'response_shape'}:
        raise ValueError('unexpected_qualification_prompt')
    body['protected_qualification'] = {
        'factId': sentence['factId'], 'source_text': sentence['source_text'],
        'origin': 'literal_original_qualification_span',
    }
    messages[0]['content'] += INSTRUCTION
    messages[1]['content'] = json.dumps(body, ensure_ascii=False)
    secured['qualificationSentence'] = sentence
    return secured


def validate(raw, bundle, modules, *, completed):
    """All original checks, followed by exact source sentence verification."""
    result = modules.adapter.validate(raw, bundle['case'], bundle['plan'],
                                      modules.synthesis, modules.validator, completed=completed)
    if result['status'] != 'valid_structure_pending_semantic_review':
        return result
    try:
        sentence = source_sentence(bundle)
        field = bundle['plan']['schema']['properties']['records']['properties'][sentence['factId']]['properties']['text']
        if (bundle.get('qualificationSentence') != sentence
                or field != {'type': 'string', 'minLength': 1, 'maxLength': 400,
                             'const': sentence['source_text']}):
            raise ValueError('qualification_constraint_changed')
        claim = next(c for c in result['claims'] if c['factId'] == sentence['factId'])
        if claim['text'] != sentence['source_text']:
            raise ValueError('qualification_sentence_missing_or_changed')
    except (ValueError, KeyError, TypeError, StopIteration):
        return {'status': 'rejected', 'reason': 'qualification_sentence_missing_or_changed',
                'claims': [], 'semanticVerdict': 'not_assessed'}
    result['qualificationSentencePreserved'] = True
    result['consultationPreserved'] = True
    result['literalSourceFactIds'] = [sentence['factId']]
    result['qualificationSentenceMechanism'] = 'source_bound_const_and_independent_check'
    # A literal field does not certify the model's other records or truth.
    return result
