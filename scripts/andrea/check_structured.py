"""Six fixed requests through production OpenJarvis; no personal vault read."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

EXPECTED_CLIENT = "ebbd828888b1aaccf8a3846d4d242606f5327feccc136af91de757a425142fa4"
MODEL = "qwen3:4b-instruct-2507-q4_K_M"


def collect(run_request, cases):
    rows = []
    for ordinal, case in enumerate(cases, 1):
        print(f"Controllo {ordinal}/{len(cases)}: {case['id']}…", flush=True)
        try:
            result = run_request({"model": MODEL, "stream": True,
                "messages": [{"role": "user", "content": case['query']}],
                "notes_query": case['query'], "notes_sources": case['sources'],
                "notes_structured": True}, keep_answer=True)
            server = result.get('server') or {}
            fields = ('firstTextMs', 'totalMs', 'structuredFirstJsonMs', 'structuredGenerationMs',
                      'structuredValidationMs', 'structuredAcceptedTextMs')
            row = {'transportCompleted': result.get('done') is True and result.get('finishReason') == 'stop',
                   'answerMode': server.get('answerMode'), 'inferenceUsed': server.get('inferenceUsed'),
                   'structuredOutcome': server.get('structuredOutcome'),
                   'firstTextClientMs': result.get('firstTextClientMs'), 'totalClientMs': result.get('totalClientMs'),
                   'server': {key: server.get(key) for key in fields},
                   'syntheticAnswer': result.get('answer')}
        except (OSError, ValueError, RuntimeError, KeyError, TypeError):
            row = {'transportCompleted': False, 'error': 'request_failed'}
        rows.append({'case': case['id'], 'criteria': case['criteria'], **row, 'qualityVerdict': 'pending_review'})
    return {'schema': 1, 'mode': 'production_structured_check', 'requested': len(cases),
            'automaticRetries': 0, 'vaultRead': False, 'browserRendering': 'not_measured', 'rows': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    args = parser.parse_args()
    root = args.project.expanduser().resolve(strict=True)
    client = root/'scripts/andrea/collaudo.py'
    if hashlib.sha256(client.read_bytes()).hexdigest() != EXPECTED_CLIENT:
        raise SystemExit('Client diverso dalla versione verificata; nessuna richiesta inviata.')
    spec = importlib.util.spec_from_file_location('verified_client', client)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    cases = json.loads((root/'scripts/andrea/structured_cases.json').read_text())
    print('Sei richieste sintetiche: trasporto, controlli tecnici e qualità sono esiti distinti. Nessuna nota personale letta.', flush=True)
    print(json.dumps(collect(module.run_request, cases), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit('Controllo interrotto; serie non conclusa.')
