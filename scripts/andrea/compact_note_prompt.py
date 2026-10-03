"""Experimental prompt compaction; native schema and facts stay unchanged.

This is a candidate for a read-only A/B probe, not a production change.
An empty-text outline replaces the full schema only in the message. The
original full schema must still be passed as Ollama's native format.
"""
import json

SCHEMA_INSTRUCTION = 'Restituisci esclusivamente JSON conforme a response_schema.'
SHAPE_INSTRUCTION = (
    'Restituisci esclusivamente JSON nella struttura response_shape; '
    'sostituisci i testi vuoti con le frasi richieste.'
)


def messages(case, plan, synthesis):
    """Retain the exact mandatory information and every substantive instruction."""
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
        fact['id']: {'text': ''} | (
            {'contextDate': fact['contextDate']} if 'contextDate' in fact else {}
        ) for fact in plan['facts']
    }}
    return [
        {'role': 'system', 'content': original[0]['content'].replace(
            SCHEMA_INSTRUCTION, SHAPE_INSTRUCTION)},
        {'role': 'user', 'content': json.dumps(body, ensure_ascii=False)},
    ]
