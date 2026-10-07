"""One synthetic production-reference request, retaining rejected diagnostic JSON.

This is not a retry of the failed performance experiment or a production fix.
The previous immutable probe supplies verified modules, transport and the same
public adversarial case. No vault, project file or configuration is changed.
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


def verified_probe(file):
    """Never execute an unverified dependency or its CLI entry point."""
    if not file.is_absolute() or file.is_symlink():
        raise ValueError('invalid_probe_path')
    data = file.read_bytes()
    if hashlib.sha256(data).hexdigest() != PROBE_SHA256:
        raise ValueError('probe_hash_mismatch')
    module = ModuleType('verified_public_concise_probe')
    module.__file__ = str(file)
    exec(compile(data, str(file), 'exec'), module.__dict__)
    return module


def predicate_diagnostics(raw, bundle, modules):
    """Apply the existing predicate guard to each dated record, without repair.

    These observations do not establish which guard failed first or assess
    meaning. Full original validation is reported separately.
    """
    try:
        if not isinstance(raw, str) or len(raw) > 32000:
            raise ValueError('invalid_raw')
        value = json.loads(raw, object_pairs_hook=modules.validator.unique_object)
        if not isinstance(value, dict) or not isinstance(value.get('records'), dict):
            raise ValueError('invalid_records')
    except (ValueError, TypeError, RecursionError):
        return {'inspectionStatus': 'invalid_json_or_records', 'records': []}
    rows = []
    for fact in bundle['plan']['facts']:
        if 'contextDate' not in fact:
            continue
        record = value['records'].get(fact['id'])
        text = record.get('text') if isinstance(record, dict) else None
        text = text if isinstance(text, str) and len(text) <= 400 else None
        rows.append({
            'factId': fact['id'], 'kind': fact['kind'],
            'sourceContextDate': fact['contextDate'],
            'sourcePassage': fact['quote'], 'generatedText': text,
            'predicateGuardRejected': modules.synthesis.unsupported_value_update(
                text, fact['quote'], fact['kind']) if text is not None else None,
        })
    return {'inspectionStatus': 'parsed_for_diagnostics', 'records': rows}


def diagnose(opener, modules, probe_module):
    bundle = modules.bridge.prepare(probe_module.synthetic_note('adversarial'))
    if (bundle is None or bundle['kind'] != 'qualifications'
            or tuple(f['kind'] for f in bundle['plan']['facts']) != probe_module.KINDS):
        raise ValueError('synthetic_plan_unavailable')
    interrupted = False
    try:
        # Same production messages and schema; no concise style addition,
        # warm-up, seed change, retry, alternative prompt or second request.
        row = probe_module.stream_probe(opener, bundle['messages'], bundle['plan']['schema'])
    except KeyboardInterrupt:
        interrupted = True
        row = {'status': 'cancelled', 'firstContentClientMs': None,
               'totalClientMs': None, 'doneReason': None,
               'native': probe_module.native_metrics({}), 'modelAnswer': None}
    raw = row.pop('modelAnswer', None)
    raw = raw if isinstance(raw, str) and len(raw) <= 32000 else None
    row.update(probe_module.validate_model(modules, bundle, row | {'modelAnswer': raw}))
    return {
        'schema': 1, 'mode': 'single_qualification_rejection_diagnostic',
        'plannedRequests': 1, 'attemptedRequests': 1, 'automaticRetries': 0,
        'interrupted': interrupted, 'source': 'public_synthetic_markdown',
        'vaultRead': False, 'productionFilesChanged': False,
        'browserRendering': 'not_measured', 'serverPathMeasured': False,
        'previousPerformanceExperiment': 'failed_not_reclassified',
        'productionChangeAdopted': False, 'case': 'adversarial',
        'variant': 'production', 'criteria': probe_module.CRITERIA,
        'row': row,
        'diagnosticModelJson': raw,
        'diagnosticTextIsAcceptedAnswer': False,
        'predicateInspection': predicate_diagnostics(raw, bundle, modules),
        'interpretation': (
            'A rejection may or may not recur: this is a new sample, not recovery '
            'of the discarded response. Predicate inspection is separate from '
            'full validation and semantic review. No generated text is repaired.'
        ),
    }


def main():
    parser = argparse.ArgumentParser(description='Una diagnosi sintetica, nessuna modifica alla produzione.')
    parser.add_argument('project', type=Path)
    parser.add_argument('--probe-script', type=Path,
                        default=Path('/tmp/OpenJarvis-concise-qualification-probe.py'))
    args = parser.parse_args()
    if not args.project.is_absolute() or args.project.is_symlink():
        print('Cartella progetto non valida. Nessuna richiesta inviata.')
        return 1
    try:
        probe_module = verified_probe(args.probe_script)
        modules = probe_module.load_modules(args.project)
    except (OSError, ValueError, TypeError, SyntaxError):
        print('Script precedente o baseline non verificabili. Nessuna richiesta inviata; nessun file modificato.')
        return 1
    opener = probe_module.build_opener(probe_module.ProxyHandler({}), probe_module.NoRedirect())
    print('Una sola richiesta sintetica con i messaggi di produzione. Nessun retry o lettura del vault.', flush=True)
    print('Il JSON diagnostico, anche rifiutato, verra mostrato per analisi: non e una risposta accettata.', flush=True)
    result = diagnose(opener, modules, probe_module)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 130 if result['interrupted'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
