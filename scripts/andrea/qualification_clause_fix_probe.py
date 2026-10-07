"""Two finite synthetic requests for a source-bound qualification clause fix.

A short native pattern canary must pass before the defect case is attempted.
The existing immutable transport/baseline is verified before any execution.
No project file, configuration, vault, database or dependency is changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from types import ModuleType

sys.dont_write_bytecode = True

PROBE_SHA256 = '6cbfecc754d8ab4fb46399d703e73effcd4bdd1a796994edd621e8fd37a9a975'
# Embedded from qualification_clause_guard.py; checked by the regression suite.
GUARD_SOURCE = '"""Source-bound clause constraints for the recognised qualification route.\n\nThe essential current predicate and note scope are copied into a native\nschema constraint BEFORE generation and checked independently afterwards.\nThe model\'s returned text is never repaired or given a missing predicate.\nThis is constrained generation, not proof of semantic learning or truth.\n"""\nimport copy\nimport re\n\nKINDS = (\'reported_book_count\', \'period_variability\',\n         \'current_qualification\', \'historical_qualification\')\nCLAUSE = re.compile(\n    r\'^(I valori(?: aggiornati)? (?:sono|restano|risultano) \'\n    r\'DATO NON VERIFICATO (?:(?:soltanto|solo) )?in questa nota:) (.+)$\'\n)\nINSTRUCTION = (\n    \' Nel record indicato da protected_qualification, conserva integralmente \'\n    \'source_prefix all’inizio di text: proviene dal passaggio originale e \'\n    \'protegge predicato, qualifica e ambito. Riformula soltanto la continuazione, \'\n    \'conservando le indicazioni di consultazione. Non aggiungere fatti, \'\n    \'negazioni o verifiche esterne. Il prefisso vincolato non è una verifica \'\n    \'dei dati della nota.\'\n)\n\n\ndef literal_pattern(value):\n    # Avoid regex shorthand classes/lookarounds and re.escape\'s escaped\n    # spaces: use only anchored literals and a bounded character class.\n    return re.sub(r\'([.\\[\\]{}()|+*?^$\\\\])\', r\'\\\\\\1\', value)\n\n\ndef pattern_for(prefix, max_tail=None):\n    available = 400 - len(prefix) - 1\n    maximum = available if max_tail is None else min(available, max_tail)\n    if not 1 <= maximum <= 399:\n        raise ValueError(\'qualification_clause_too_long\')\n    return \'^\' + literal_pattern(prefix) + r\' [^\\r\\n]{1,\' + str(maximum) + \'}$\'\n\n\ndef source_clause(bundle):\n    if (bundle.get(\'kind\') != \'qualifications\'\n            or tuple(f[\'kind\'] for f in bundle[\'plan\'][\'facts\']) != KINDS):\n        raise ValueError(\'unsupported_qualification_plan\')\n    fact = bundle[\'plan\'][\'facts\'][2]\n    proofs = [p for p in fact[\'proofs\'] if p[\'role\'] == \'qualification\']\n    if len(proofs) != 1:\n        raise ValueError(\'ambiguous_qualification_proof\')\n    proof = proofs[0]\n    source = {s[\'id\']: s[\'text\'] for s in bundle[\'case\'][\'sources\']}[proof[\'sourceId\']]\n    start, end = proof[\'start\'], proof[\'end\']\n    if (type(start) is not int or type(end) is not int\n            or not 0 <= start < end <= len(source)\n            or source[start:end] != proof[\'quote\']):\n        raise ValueError(\'original_qualification_span_changed\')\n    raw = proof[\'quote\']\n    if len(raw) > 2000:\n        raise ValueError(\'qualification_proof_too_long\')\n    visible = re.sub(r\'\\s+\', \' \', re.sub(r\'[*`>]\', \'\', raw)).strip()\n    match = CLAUSE.fullmatch(visible)\n    if match is None:\n        raise ValueError(\'unsupported_qualification_clause\')\n    prefix = match.group(1)\n    if len(visible) > 400:\n        raise ValueError(\'qualification_sentence_too_long\')\n    return {\'factId\': fact[\'id\'], \'source_prefix\': prefix,\n            \'pattern\': pattern_for(prefix)}\n\n\ndef protect(bundle):\n    """Return a new bound schema/prompt without changing original facts."""\n    clause = source_clause(bundle)\n    secured = copy.deepcopy(bundle)\n    plan = secured[\'plan\']\n    text_schema = plan[\'schema\'][\'properties\'][\'records\'][\'properties\'][clause[\'factId\']][\'properties\'][\'text\']\n    if text_schema != {\'type\': \'string\', \'minLength\': 1, \'maxLength\': 400}:\n        raise ValueError(\'unexpected_text_schema\')\n    text_schema[\'pattern\'] = clause[\'pattern\']\n    messages = secured[\'messages\']\n    if (len(messages) != 2 or messages[0][\'role\'] != \'system\'\n            or messages[1][\'role\'] != \'user\'):\n        raise ValueError(\'unexpected_messages\')\n    import json\n    body = json.loads(messages[1][\'content\'])\n    if set(body) != {\'richiesta\', \'informazioni_obbligatorie\', \'response_shape\'}:\n        raise ValueError(\'unexpected_qualification_prompt\')\n    body[\'protected_qualification\'] = {\n        \'factId\': clause[\'factId\'], \'source_prefix\': clause[\'source_prefix\'],\n        \'text_pattern\': clause[\'pattern\'],\n    }\n    messages[0][\'content\'] += INSTRUCTION\n    messages[1][\'content\'] = json.dumps(body, ensure_ascii=False)\n    secured[\'qualificationClause\'] = clause\n    return secured\n\n\ndef validate(raw, bundle, modules, *, completed):\n    """Preserve every original check, then reject omission of the source clause."""\n    result = modules.adapter.validate(raw, bundle[\'case\'], bundle[\'plan\'],\n                                      modules.synthesis, modules.validator, completed=completed)\n    if result[\'status\'] != \'valid_structure_pending_semantic_review\':\n        return result\n    try:\n        clause = source_clause(bundle)\n        field = bundle[\'plan\'][\'schema\'][\'properties\'][\'records\'][\'properties\'][clause[\'factId\']][\'properties\'][\'text\']\n        if (bundle.get(\'qualificationClause\') != clause\n                or field != {\'type\': \'string\', \'minLength\': 1, \'maxLength\': 400, \'pattern\': clause[\'pattern\']}):\n            raise ValueError(\'qualification_constraint_changed\')\n        claim = next(c for c in result[\'claims\'] if c[\'factId\'] == clause[\'factId\'])\n        if re.fullmatch(clause[\'pattern\'], claim[\'text\']) is None:\n            raise ValueError(\'qualification_clause_missing_or_changed\')\n    except (ValueError, TypeError, KeyError, StopIteration):\n        return {\'status\': \'rejected\', \'reason\': \'qualification_clause_missing_or_changed\',\n                \'claims\': [], \'semanticVerdict\': \'not_assessed\'}\n    result[\'qualificationClausePreserved\'] = True\n    result[\'qualificationClauseMechanism\'] = \'source_bound_generation_constraint_and_independent_check\'\n    # Never turn this lexical invariant into a general entailment verdict.\n    return result\n'
GUARD_SHA256 = 'ad01e5192b19fc4bad068a0cdc288d9889fa0166eb2db6720283887910559757'


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
    if hashlib.sha256(GUARD_SOURCE.encode('utf-8')).hexdigest() != GUARD_SHA256:
        raise ValueError('embedded_guard_hash_mismatch')
    module = ModuleType('verified_qualification_clause_guard')
    exec(compile(GUARD_SOURCE, module.__name__, 'exec'), module.__dict__)
    return module


def canary_request(guard, clause):
    pattern = guard.pattern_for(clause['source_prefix'], max_tail=10)
    schema = {'type': 'object', 'additionalProperties': False,
              'properties': {'text': {'type': 'string', 'pattern': pattern}},
              'required': ['text']}
    # A deliberately incompatible instruction checks observed native schema
    # conformance. It does not claim universal grammar or semantic correctness.
    messages = [{'role': 'system', 'content': 'Emetti soltanto un oggetto JSON con il campo text.'},
                {'role': 'user', 'content': 'Il valore di text deve essere esattamente NON_CONFORME.'}]
    return messages, schema, pattern


def request_once(opener, probe, messages, schema):
    try:
        return probe.stream_probe(opener, messages, schema), False
    except KeyboardInterrupt:
        return {'status': 'cancelled', 'firstContentClientMs': None,
                'totalClientMs': None, 'doneReason': None,
                'native': probe.native_metrics({}), 'modelAnswer': None}, True


def run_check(opener, modules, probe, guard):
    original = modules.bridge.prepare(probe.synthetic_note('adversarial'))
    secured = guard.protect(original)
    clause = secured['qualificationClause']
    messages, schema, pattern = canary_request(guard, clause)
    report = {
        'schema': 1, 'mode': 'qualification_clause_fix_check',
        'plannedRequests': 2, 'attemptedRequests': 1, 'automaticRetries': 0,
        'source': 'public_synthetic_markdown', 'vaultRead': False,
        'productionFilesChanged': False, 'productionChangeAdopted': False,
        'browserRendering': 'not_measured', 'serverPathMeasured': False,
        'previousPerformanceExperiment': 'failed_not_reclassified',
        'scope': 'current_qualification_predicate_label_and_note_scope',
        'mechanism': 'native_source_prefix_pattern_plus_independent_check',
        'criteria': list(probe.CRITERIA) + [
            'Conserva letteralmente il predicato restano, l aggettivo aggiornati e soltanto in questa nota dalla fonte.',
            'Non ripara il testo dopo la generazione; mantiene tutti i controlli originali.',
        ],
        'interrupted': False, 'technicalOutcome': 'not_completed',
        'qualityVerdict': 'not_assessed', 'defectCase': None,
    }
    row, interrupted = request_once(opener, probe, messages, schema)
    raw = row.pop('modelAnswer', None)
    accepted = False
    try:
        value = json.loads(raw, object_pairs_hook=modules.validator.unique_object)
        accepted = (row['status'] == 'completed' and type(value) is dict
                    and set(value) == {'text'} and type(value['text']) is str
                    and re.fullmatch(pattern, value['text']) is not None)
    except (ValueError, TypeError, RecursionError):
        pass
    row.update({'pattern': pattern, 'nativeConformanceObserved': accepted,
                'diagnosticModelJson': raw, 'diagnosticTextIsAcceptedAnswer': False})
    report['canary'] = row
    report['interrupted'] = interrupted
    if not accepted:
        report['technicalOutcome'] = 'native_pattern_canary_failed'
        return report

    report['attemptedRequests'] = 2
    row, interrupted = request_once(opener, probe, secured['messages'], secured['plan']['schema'])
    raw = row.pop('modelAnswer', None)
    result = guard.validate(raw, secured, modules, completed=row['status'] == 'completed')
    row.update({'case': 'adversarial', 'technicalOutcome': result['status'],
                'technicalReason': result.get('reason'), 'factsCovered': result.get('factsCovered'),
                'sourceBoundClause': clause, 'clausePreserved': result.get('qualificationClausePreserved', False),
                'qualityVerdict': result['semanticVerdict'],
                'syntheticAnswer': modules.synthesis.render(result),
                'diagnosticModelJson': raw, 'generatedTextRepaired': False,
                'sourcePassages': [{'factId': f['id'], 'kind': f['kind'],
                                    'contextDate': f.get('contextDate'), 'passage': f['quote']}
                                   for f in secured['plan']['facts']]})
    report['defectCase'] = row
    report['interrupted'] = interrupted
    report['technicalOutcome'] = result['status']
    report['qualityVerdict'] = result['semanticVerdict']
    report['interpretation'] = (
        'The source prefix is protected before generation, not supplied as a missing '
        'predicate afterwards. Native conformance and the independent clause check '
        'do not certify the free continuation, other records, external truth or '
        'production integration. Compare the synthetic answer with all source passages.'
    )
    return report


def main():
    parser = argparse.ArgumentParser(description='Vincolo dalla fonte: due richieste sintetiche al massimo, nessuna modifica.')
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
        # Resolve the exact original passage before either request is possible.
        guard.protect(modules.bridge.prepare(probe.synthetic_note('adversarial')))
    except (OSError, ValueError, TypeError, KeyError, SyntaxError):
        print('Baseline o script precedente non verificabili. Nessuna richiesta inviata; nessun file modificato.')
        return 1
    opener = probe.build_opener(probe.ProxyHandler({}), probe.NoRedirect())
    print('Due richieste sintetiche al massimo: compatibilita del vincolo e caso difettoso. Nessuna nota personale letta.', flush=True)
    print('Il secondo controllo parte soltanto se il primo passa. Nessun retry; la qualita richiede confronto con le fonti.', flush=True)
    report = run_check(opener, modules, probe, guard)
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    if report['interrupted']:
        return 130
    return 0 if report['technicalOutcome'] == 'valid_structure_pending_semantic_review' else 1


if __name__ == '__main__':
    raise SystemExit(main())
