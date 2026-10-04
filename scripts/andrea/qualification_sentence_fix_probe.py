"""One fixed synthetic check for the complete source-bound qualification.

No retry, extra canary, vault access or production modification. The current
qualification is literal from the source; other records are model synthesis.
The previous prefix experiment remains semantically failed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from types import ModuleType

sys.dont_write_bytecode = True

PROBE_SHA256 = '6cbfecc754d8ab4fb46399d703e73effcd4bdd1a796994edd621e8fd37a9a975'
PREFIX_SOURCE = '"""Source-bound clause constraints for the recognised qualification route.\n\nThe essential current predicate and note scope are copied into a native\nschema constraint BEFORE generation and checked independently afterwards.\nThe model\'s returned text is never repaired or given a missing predicate.\nThis is constrained generation, not proof of semantic learning or truth.\n"""\nimport copy\nimport re\n\nKINDS = (\'reported_book_count\', \'period_variability\',\n         \'current_qualification\', \'historical_qualification\')\nCLAUSE = re.compile(\n    r\'^(I valori(?: aggiornati)? (?:sono|restano|risultano) \'\n    r\'DATO NON VERIFICATO (?:(?:soltanto|solo) )?in questa nota:) (.+)$\'\n)\nINSTRUCTION = (\n    \' Nel record indicato da protected_qualification, conserva integralmente \'\n    \'source_prefix all’inizio di text: proviene dal passaggio originale e \'\n    \'protegge predicato, qualifica e ambito. Riformula soltanto la continuazione, \'\n    \'conservando le indicazioni di consultazione. Non aggiungere fatti, \'\n    \'negazioni o verifiche esterne. Il prefisso vincolato non è una verifica \'\n    \'dei dati della nota.\'\n)\n\n\ndef literal_pattern(value):\n    # Avoid regex shorthand classes/lookarounds and re.escape\'s escaped\n    # spaces: use only anchored literals and a bounded character class.\n    return re.sub(r\'([.\\[\\]{}()|+*?^$\\\\])\', r\'\\\\\\1\', value)\n\n\ndef pattern_for(prefix, max_tail=None):\n    available = 400 - len(prefix) - 1\n    maximum = available if max_tail is None else min(available, max_tail)\n    if not 1 <= maximum <= 399:\n        raise ValueError(\'qualification_clause_too_long\')\n    return \'^\' + literal_pattern(prefix) + r\' [^\\r\\n]{1,\' + str(maximum) + \'}$\'\n\n\ndef source_clause(bundle):\n    if (bundle.get(\'kind\') != \'qualifications\'\n            or tuple(f[\'kind\'] for f in bundle[\'plan\'][\'facts\']) != KINDS):\n        raise ValueError(\'unsupported_qualification_plan\')\n    fact = bundle[\'plan\'][\'facts\'][2]\n    proofs = [p for p in fact[\'proofs\'] if p[\'role\'] == \'qualification\']\n    if len(proofs) != 1:\n        raise ValueError(\'ambiguous_qualification_proof\')\n    proof = proofs[0]\n    source = {s[\'id\']: s[\'text\'] for s in bundle[\'case\'][\'sources\']}[proof[\'sourceId\']]\n    start, end = proof[\'start\'], proof[\'end\']\n    if (type(start) is not int or type(end) is not int\n            or not 0 <= start < end <= len(source)\n            or source[start:end] != proof[\'quote\']):\n        raise ValueError(\'original_qualification_span_changed\')\n    raw = proof[\'quote\']\n    if len(raw) > 2000:\n        raise ValueError(\'qualification_proof_too_long\')\n    visible = re.sub(r\'\\s+\', \' \', re.sub(r\'[*`>]\', \'\', raw)).strip()\n    match = CLAUSE.fullmatch(visible)\n    if match is None:\n        raise ValueError(\'unsupported_qualification_clause\')\n    prefix = match.group(1)\n    if len(visible) > 400:\n        raise ValueError(\'qualification_sentence_too_long\')\n    return {\'factId\': fact[\'id\'], \'source_prefix\': prefix,\n            \'pattern\': pattern_for(prefix)}\n\n\ndef protect(bundle):\n    """Return a new bound schema/prompt without changing original facts."""\n    clause = source_clause(bundle)\n    secured = copy.deepcopy(bundle)\n    plan = secured[\'plan\']\n    text_schema = plan[\'schema\'][\'properties\'][\'records\'][\'properties\'][clause[\'factId\']][\'properties\'][\'text\']\n    if text_schema != {\'type\': \'string\', \'minLength\': 1, \'maxLength\': 400}:\n        raise ValueError(\'unexpected_text_schema\')\n    text_schema[\'pattern\'] = clause[\'pattern\']\n    messages = secured[\'messages\']\n    if (len(messages) != 2 or messages[0][\'role\'] != \'system\'\n            or messages[1][\'role\'] != \'user\'):\n        raise ValueError(\'unexpected_messages\')\n    import json\n    body = json.loads(messages[1][\'content\'])\n    if set(body) != {\'richiesta\', \'informazioni_obbligatorie\', \'response_shape\'}:\n        raise ValueError(\'unexpected_qualification_prompt\')\n    body[\'protected_qualification\'] = {\n        \'factId\': clause[\'factId\'], \'source_prefix\': clause[\'source_prefix\'],\n        \'text_pattern\': clause[\'pattern\'],\n    }\n    messages[0][\'content\'] += INSTRUCTION\n    messages[1][\'content\'] = json.dumps(body, ensure_ascii=False)\n    secured[\'qualificationClause\'] = clause\n    return secured\n\n\ndef validate(raw, bundle, modules, *, completed):\n    """Preserve every original check, then reject omission of the source clause."""\n    result = modules.adapter.validate(raw, bundle[\'case\'], bundle[\'plan\'],\n                                      modules.synthesis, modules.validator, completed=completed)\n    if result[\'status\'] != \'valid_structure_pending_semantic_review\':\n        return result\n    try:\n        clause = source_clause(bundle)\n        field = bundle[\'plan\'][\'schema\'][\'properties\'][\'records\'][\'properties\'][clause[\'factId\']][\'properties\'][\'text\']\n        if (bundle.get(\'qualificationClause\') != clause\n                or field != {\'type\': \'string\', \'minLength\': 1, \'maxLength\': 400, \'pattern\': clause[\'pattern\']}):\n            raise ValueError(\'qualification_constraint_changed\')\n        claim = next(c for c in result[\'claims\'] if c[\'factId\'] == clause[\'factId\'])\n        if re.fullmatch(clause[\'pattern\'], claim[\'text\']) is None:\n            raise ValueError(\'qualification_clause_missing_or_changed\')\n    except (ValueError, TypeError, KeyError, StopIteration):\n        return {\'status\': \'rejected\', \'reason\': \'qualification_clause_missing_or_changed\',\n                \'claims\': [], \'semanticVerdict\': \'not_assessed\'}\n    result[\'qualificationClausePreserved\'] = True\n    result[\'qualificationClauseMechanism\'] = \'source_bound_generation_constraint_and_independent_check\'\n    # Never turn this lexical invariant into a general entailment verdict.\n    return result\n'
PREFIX_SHA256 = 'ad01e5192b19fc4bad068a0cdc288d9889fa0166eb2db6720283887910559757'
SENTENCE_SOURCE = '"""Preserve the entire proved qualification, including consultation prerequisites.\n\nThe current qualification is a literal source-bound field, not a free\nparaphrase. Other records still come from the model. The returned text is\nchecked independently, never repaired after generation.\n"""\nimport copy\nimport json\nimport re\n\nfrom qualification_clause_guard import source_clause\n\n# Recognise only the consultation convention present in the public test\n# and the installed note. Unknown wording is unsupported, never completed.\nCONSULTATION = re.compile(\n    r\'consultare dashboard o report(?: KDP)? indicando periodo, titolo e marketplace\\.\'\n)\nINSTRUCTION = (\n    \' Il record indicato da protected_qualification contiene una frase \'\n    \'letterale della fonte: emetti source_text integralmente, senza \'\n    \'parafrasarla, accorciarla o aggiungere altro. Comprende qualifica, \'\n    \'ambito e indicazioni di consultazione. Gli altri record rimangono \'\n    \'sintesi del modello da verificare. La frase protetta non verifica \'\n    \'i dati della nota e non autorizza alcuna azione esterna.\'\n)\n\n\ndef source_sentence(bundle):\n    """Derive the full string only from the already-proved original span."""\n    prefix = source_clause(bundle)\n    fact = next(f for f in bundle[\'plan\'][\'facts\'] if f[\'id\'] == prefix[\'factId\'])\n    proof = next(p for p in fact[\'proofs\'] if p[\'role\'] == \'qualification\')\n    # source_clause already checks uniqueness and exact original offsets.\n    visible = re.sub(r\'\\s+\', \' \', re.sub(r\'[*`>]\', \'\', proof[\'quote\'])).strip()\n    beginning = prefix[\'source_prefix\'] + \' \'\n    if not visible.startswith(beginning):\n        raise ValueError(\'qualification_prefix_changed\')\n    consultation = visible[len(beginning):]\n    if CONSULTATION.fullmatch(consultation) is None:\n        raise ValueError(\'unsupported_consultation_sentence\')\n    return {\'factId\': fact[\'id\'], \'source_text\': visible,\n            \'source_prefix\': prefix[\'source_prefix\'], \'consultation\': consultation}\n\n\ndef protect(bundle):\n    """Protect the complete source sentence BEFORE generation, without repair."""\n    sentence = source_sentence(bundle)\n    secured = copy.deepcopy(bundle)\n    field = secured[\'plan\'][\'schema\'][\'properties\'][\'records\'][\'properties\'][sentence[\'factId\']][\'properties\'][\'text\']\n    if field != {\'type\': \'string\', \'minLength\': 1, \'maxLength\': 400}:\n        raise ValueError(\'unexpected_text_schema\')\n    field[\'const\'] = sentence[\'source_text\']\n    messages = secured[\'messages\']\n    if (len(messages) != 2 or messages[0][\'role\'] != \'system\'\n            or messages[1][\'role\'] != \'user\'):\n        raise ValueError(\'unexpected_messages\')\n    body = json.loads(messages[1][\'content\'])\n    if set(body) != {\'richiesta\', \'informazioni_obbligatorie\', \'response_shape\'}:\n        raise ValueError(\'unexpected_qualification_prompt\')\n    body[\'protected_qualification\'] = {\n        \'factId\': sentence[\'factId\'], \'source_text\': sentence[\'source_text\'],\n        \'origin\': \'literal_original_qualification_span\',\n    }\n    messages[0][\'content\'] += INSTRUCTION\n    messages[1][\'content\'] = json.dumps(body, ensure_ascii=False)\n    secured[\'qualificationSentence\'] = sentence\n    return secured\n\n\ndef validate(raw, bundle, modules, *, completed):\n    """All original checks, followed by exact source sentence verification."""\n    result = modules.adapter.validate(raw, bundle[\'case\'], bundle[\'plan\'],\n                                      modules.synthesis, modules.validator, completed=completed)\n    if result[\'status\'] != \'valid_structure_pending_semantic_review\':\n        return result\n    try:\n        sentence = source_sentence(bundle)\n        field = bundle[\'plan\'][\'schema\'][\'properties\'][\'records\'][\'properties\'][sentence[\'factId\']][\'properties\'][\'text\']\n        if (bundle.get(\'qualificationSentence\') != sentence\n                or field != {\'type\': \'string\', \'minLength\': 1, \'maxLength\': 400,\n                             \'const\': sentence[\'source_text\']}):\n            raise ValueError(\'qualification_constraint_changed\')\n        claim = next(c for c in result[\'claims\'] if c[\'factId\'] == sentence[\'factId\'])\n        if claim[\'text\'] != sentence[\'source_text\']:\n            raise ValueError(\'qualification_sentence_missing_or_changed\')\n    except (ValueError, KeyError, TypeError, StopIteration):\n        return {\'status\': \'rejected\', \'reason\': \'qualification_sentence_missing_or_changed\',\n                \'claims\': [], \'semanticVerdict\': \'not_assessed\'}\n    result[\'qualificationSentencePreserved\'] = True\n    result[\'consultationPreserved\'] = True\n    result[\'literalSourceFactIds\'] = [sentence[\'factId\']]\n    result[\'qualificationSentenceMechanism\'] = \'source_bound_const_and_independent_check\'\n    # A literal field does not certify the model\'s other records or truth.\n    return result\n'
SENTENCE_SHA256 = '976e22ad3ba6671011cc63c0d18ae21a39e4647d4ad698454b70db983b943866'


def verified_probe(file):
    if not file.is_absolute() or file.is_symlink():
        raise ValueError('invalid_probe_path')
    data = file.read_bytes()
    if hashlib.sha256(data).hexdigest() != PROBE_SHA256:
        raise ValueError('probe_hash_mismatch')
    module = ModuleType('verified_public_qualification_transport')
    module.__file__ = str(file)
    exec(compile(data, str(file), 'exec'), module.__dict__)
    return module


def guard_module():
    """Load only the two exact embedded public candidates, not installed code."""
    if (hashlib.sha256(PREFIX_SOURCE.encode()).hexdigest() != PREFIX_SHA256
            or hashlib.sha256(SENTENCE_SOURCE.encode()).hexdigest() != SENTENCE_SHA256):
        raise ValueError('embedded_guard_hash_mismatch')
    prior = sys.modules.get('qualification_clause_guard')
    prefix = ModuleType('qualification_clause_guard')
    sentence = ModuleType('verified_qualification_sentence_guard')
    try:
        exec(compile(PREFIX_SOURCE, prefix.__name__, 'exec'), prefix.__dict__)
        sys.modules[prefix.__name__] = prefix
        exec(compile(SENTENCE_SOURCE, sentence.__name__, 'exec'), sentence.__dict__)
    finally:
        if prior is None:
            sys.modules.pop(prefix.__name__, None)
        else:
            sys.modules[prefix.__name__] = prior
    return sentence


def run_check(opener, modules, probe, guard):
    original = modules.bridge.prepare(probe.synthetic_note('adversarial'))
    secured = guard.protect(original)
    sentence = secured['qualificationSentence']
    interrupted = False
    try:
        row = probe.stream_probe(opener, secured['messages'], secured['plan']['schema'])
    except KeyboardInterrupt:
        interrupted = True
        row = {'status': 'cancelled', 'firstContentClientMs': None,
               'totalClientMs': None, 'doneReason': None,
               'native': probe.native_metrics({}), 'modelAnswer': None}
    raw = row.pop('modelAnswer', None)
    result = guard.validate(raw, secured, modules, completed=row['status'] == 'completed')
    row.update({'case': 'adversarial', 'technicalOutcome': result['status'],
                'technicalReason': result.get('reason'), 'factsCovered': result.get('factsCovered'),
                'literalSourceFactIds': result.get('literalSourceFactIds', []),
                'sourceBoundSentence': sentence,
                'sentencePreserved': result.get('qualificationSentencePreserved', False),
                'consultationPreserved': result.get('consultationPreserved', False),
                'qualityVerdict': result['semanticVerdict'],
                'syntheticAnswer': modules.synthesis.render(result),
                'diagnosticModelJson': raw, 'generatedTextRepaired': False,
                'sourcePassages': [{'factId': f['id'], 'kind': f['kind'],
                                    'contextDate': f.get('contextDate'), 'passage': f['quote']}
                                   for f in secured['plan']['facts']]})
    return {
        'schema': 1, 'mode': 'qualification_sentence_fix_check',
        'plannedRequests': 1, 'attemptedRequests': 1, 'automaticRetries': 0,
        'source': 'public_synthetic_markdown', 'vaultRead': False,
        'productionFilesChanged': False, 'productionChangeAdopted': False,
        'browserRendering': 'not_measured', 'serverPathMeasured': False,
        'previousPerformanceExperiment': 'failed_not_reclassified',
        'previousPrefixExperiment': 'semantic_failure_consultation_omitted',
        'mechanism': 'literal_source_sentence_native_const_and_independent_check',
        'literalField': sentence['factId'],
        'modelSynthesisFields': [f['id'] for f in secured['plan']['facts'] if f['id'] != sentence['factId']],
        'criteria': list(probe.CRITERIA) + [
            'La frase corrente completa coincide con il passaggio originale, compresa la consultazione con periodo, titolo e marketplace.',
            'Il campo corrente e letterale e dichiarato come tale; gli altri tre record sono sintesi del modello da riesaminare.',
            'Nessuna riparazione dopo la generazione o ripetizione per promuovere una prova precedente.',
        ],
        'interrupted': interrupted, 'technicalOutcome': result['status'],
        'qualityVerdict': result['semanticVerdict'], 'row': row,
        'interpretation': (
            'The complete qualification and consultation are a literal original '
            'source sentence, protected BEFORE generation, not a free paraphrase '
            'or model learning. The generated response is not repaired. '
            'Compare the other three model records and all source passages; '
            'technical acceptance does not certify external truth or production integration.'
        ),
    }


def main():
    parser = argparse.ArgumentParser(description='Una sintesi sintetica con frase corrente letterale, nessuna modifica.')
    parser.add_argument('project', type=Path)
    parser.add_argument('--probe-script', type=Path,
                        default=Path('/tmp/OpenJarvis-concise-qualification-probe.py'))
    args = parser.parse_args()
    if not args.project.is_absolute() or args.project.is_symlink():
        print('Cartella progetto non valida. Nessuna richiesta inviata.')
        return 1
    try:
        probe = verified_probe(args.probe_script)
        modules = probe.load_modules(args.project)
        guard = guard_module()
        guard.protect(modules.bridge.prepare(probe.synthetic_note('adversarial')))
    except (OSError, ValueError, TypeError, KeyError, SyntaxError):
        print('Baseline o script precedente non verificabili. Nessuna richiesta inviata; nessun file modificato.')
        return 1
    opener = probe.build_opener(probe.ProxyHandler({}), probe.NoRedirect())
    print('Una sola richiesta sintetica. Nessuna nota personale letta o modifica alla produzione; nessun retry.', flush=True)
    print('La frase corrente completa e letterale dalla fonte; gli altri tre punti sono sintesi del modello da confrontare.', flush=True)
    report = run_check(opener, modules, probe, guard)
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    if report['interrupted']:
        return 130
    return 0 if report['technicalOutcome'] == 'valid_structure_pending_semantic_review' else 1


if __name__ == '__main__':
    raise SystemExit(main())
