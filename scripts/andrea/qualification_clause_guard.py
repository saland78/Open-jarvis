"""Source-bound clause constraints for the recognised qualification route.

The essential current predicate and note scope are copied into a native
schema constraint BEFORE generation and checked independently afterwards.
The model's returned text is never repaired or given a missing predicate.
This is constrained generation, not proof of semantic learning or truth.
"""
import copy
import re

KINDS = ('reported_book_count', 'period_variability',
         'current_qualification', 'historical_qualification')
CLAUSE = re.compile(
    r'^(I valori(?: aggiornati)? (?:sono|restano|risultano) '
    r'DATO NON VERIFICATO (?:(?:soltanto|solo) )?in questa nota:) (.+)$'
)
INSTRUCTION = (
    ' Nel record indicato da protected_qualification, conserva integralmente '
    'source_prefix all’inizio di text: proviene dal passaggio originale e '
    'protegge predicato, qualifica e ambito. Riformula soltanto la continuazione, '
    'conservando le indicazioni di consultazione. Non aggiungere fatti, '
    'negazioni o verifiche esterne. Il prefisso vincolato non è una verifica '
    'dei dati della nota.'
)


def literal_pattern(value):
    # Avoid regex shorthand classes/lookarounds and re.escape's escaped
    # spaces: use only anchored literals and a bounded character class.
    return re.sub(r'([.\[\]{}()|+*?^$\\])', r'\\\1', value)


def pattern_for(prefix, max_tail=None):
    available = 400 - len(prefix) - 1
    maximum = available if max_tail is None else min(available, max_tail)
    if not 1 <= maximum <= 399:
        raise ValueError('qualification_clause_too_long')
    return '^' + literal_pattern(prefix) + r' [^\r\n]{1,' + str(maximum) + '}$'


def source_clause(bundle):
    if (bundle.get('kind') != 'qualifications'
            or tuple(f['kind'] for f in bundle['plan']['facts']) != KINDS):
        raise ValueError('unsupported_qualification_plan')
    fact = bundle['plan']['facts'][2]
    proofs = [p for p in fact['proofs'] if p['role'] == 'qualification']
    if len(proofs) != 1:
        raise ValueError('ambiguous_qualification_proof')
    proof = proofs[0]
    source = {s['id']: s['text'] for s in bundle['case']['sources']}[proof['sourceId']]
    start, end = proof['start'], proof['end']
    if (type(start) is not int or type(end) is not int
            or not 0 <= start < end <= len(source)
            or source[start:end] != proof['quote']):
        raise ValueError('original_qualification_span_changed')
    raw = proof['quote']
    if len(raw) > 2000:
        raise ValueError('qualification_proof_too_long')
    visible = re.sub(r'\s+', ' ', re.sub(r'[*`>]', '', raw)).strip()
    match = CLAUSE.fullmatch(visible)
    if match is None:
        raise ValueError('unsupported_qualification_clause')
    prefix = match.group(1)
    if len(visible) > 400:
        raise ValueError('qualification_sentence_too_long')
    return {'factId': fact['id'], 'source_prefix': prefix,
            'pattern': pattern_for(prefix)}


def protect(bundle):
    """Return a new bound schema/prompt without changing original facts."""
    clause = source_clause(bundle)
    secured = copy.deepcopy(bundle)
    plan = secured['plan']
    text_schema = plan['schema']['properties']['records']['properties'][clause['factId']]['properties']['text']
    if text_schema != {'type': 'string', 'minLength': 1, 'maxLength': 400}:
        raise ValueError('unexpected_text_schema')
    text_schema['pattern'] = clause['pattern']
    messages = secured['messages']
    if (len(messages) != 2 or messages[0]['role'] != 'system'
            or messages[1]['role'] != 'user'):
        raise ValueError('unexpected_messages')
    import json
    body = json.loads(messages[1]['content'])
    if set(body) != {'richiesta', 'informazioni_obbligatorie', 'response_shape'}:
        raise ValueError('unexpected_qualification_prompt')
    body['protected_qualification'] = {
        'factId': clause['factId'], 'source_prefix': clause['source_prefix'],
        'text_pattern': clause['pattern'],
    }
    messages[0]['content'] += INSTRUCTION
    messages[1]['content'] = json.dumps(body, ensure_ascii=False)
    secured['qualificationClause'] = clause
    return secured


def validate(raw, bundle, modules, *, completed):
    """Preserve every original check, then reject omission of the source clause."""
    result = modules.adapter.validate(raw, bundle['case'], bundle['plan'],
                                      modules.synthesis, modules.validator, completed=completed)
    if result['status'] != 'valid_structure_pending_semantic_review':
        return result
    try:
        clause = source_clause(bundle)
        field = bundle['plan']['schema']['properties']['records']['properties'][clause['factId']]['properties']['text']
        if (bundle.get('qualificationClause') != clause
                or field != {'type': 'string', 'minLength': 1, 'maxLength': 400, 'pattern': clause['pattern']}):
            raise ValueError('qualification_constraint_changed')
        claim = next(c for c in result['claims'] if c['factId'] == clause['factId'])
        if re.fullmatch(clause['pattern'], claim['text']) is None:
            raise ValueError('qualification_clause_missing_or_changed')
    except (ValueError, TypeError, KeyError, StopIteration):
        return {'status': 'rejected', 'reason': 'qualification_clause_missing_or_changed',
                'claims': [], 'semanticVerdict': 'not_assessed'}
    result['qualificationClausePreserved'] = True
    result['qualificationClauseMechanism'] = 'source_bound_generation_constraint_and_independent_check'
    # Never turn this lexical invariant into a general entailment verdict.
    return result
