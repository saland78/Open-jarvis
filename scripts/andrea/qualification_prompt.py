"""Compact message only for the reviewed, bounded dated-qualification plan.

Native schema, mandatory information and existing guards stay unchanged.
Book and other synthesis paths retain their original messages.
"""
import json

KINDS = ('reported_book_count', 'period_variability',
         'current_qualification', 'historical_qualification')
SCHEMA_INSTRUCTION = 'Restituisci esclusivamente JSON conforme a response_schema.'
SHAPE_INSTRUCTION = (
    'Restituisci esclusivamente JSON nella struttura response_shape; '
    'sostituisci i testi vuoti con le frasi richieste.'
)


def messages(case, plan, synthesis):
    if tuple(f['kind'] for f in plan['facts']) != KINDS:
        raise ValueError('unsupported_qualification_plan')
    original = synthesis.messages(case, plan)
    if (len(original) != 2 or original[0]['role'] != 'system'
            or original[1]['role'] != 'user'
            or original[0]['content'].count(SCHEMA_INSTRUCTION) != 1):
        raise ValueError('unexpected_prompt_structure')
    body = json.loads(original[1]['content'])
    if (set(body) != {'richiesta', 'informazioni_obbligatorie', 'response_schema'}
            or body['response_schema'] != plan['schema']):
        raise ValueError('unexpected_prompt_schema')
    body.pop('response_schema')
    body['response_shape'] = {'records': {
        f['id']: {'text': ''} | ({'contextDate': f['contextDate']} if 'contextDate' in f else {})
        for f in plan['facts']
    }}
    return [
        {'role': 'system', 'content': original[0]['content'].replace(
            SCHEMA_INSTRUCTION, SHAPE_INSTRUCTION)},
        {'role': 'user', 'content': json.dumps(body, ensure_ascii=False)},
    ]
