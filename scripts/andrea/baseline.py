"""Nine fixed local timing requests. No vault access, warm-up or automatic retries.

Uses the pinned installed control client; timings are not browser DOM timings.
Answer text and request IDs are discarded. Quality is not automatically judged.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import time
from urllib.error import HTTPError, URLError

EXPECTED_CLIENT = 'ebbd828888b1aaccf8a3846d4d242606f5327feccc136af91de757a425142fa4'
MODEL = 'qwen3:4b-instruct-2507-q4_K_M'
KINDS = ('chat', 'notes_generated', 'notes_direct')
QUERY = 'Quale problema risulta ancora aperto per la copertina?'
GENERATED_SOURCE = {'id': 'N1', 'title': 'Storia della copertina', 'text':
    'Il 2026-08-19 il codice a barre su fondo nero causò una bocciatura. '
    'Il problema fu risolto e la copertina corretta è online dal 2026-08-20. '
    'Questa nota non documenta problemi successivi.'}
DIRECT_QUERY = 'Quanti libri risultano pubblicati e a quale data?'
DIRECT_SOURCE = {'id': 'N1', 'title': 'Catalogo', 'text':
    'Fotografia al 2026-08-20: libri pubblicati 2, nei mercati Italia e Stati Uniti.'}
SERVER_STATUSES = {'completed', 'truncated', 'incomplete', 'error', 'cancelled', 'timeout', 'retrieval_error', 'running'}
MODES = {'model_synthesis', 'explicit_fields', 'brief_quotes', 'status_scope_quotes'}


def payload_for(kind):
    query = 'Scrivi soltanto: pronto.' if kind == 'chat' else QUERY if kind == 'notes_generated' else DIRECT_QUERY
    payload = {'model': MODEL, 'stream': True, 'messages': [{'role': 'user', 'content': query}]}
    if kind != 'chat':
        payload.update(notes_query=query, notes_sources=[dict(GENERATED_SOURCE if kind == 'notes_generated' else DIRECT_SOURCE)])
    return payload


def duration(value):
    return round(value, 2) if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def sanitize(kind, result):
    raw = result.get('server')
    raw = raw if isinstance(raw, dict) else {}
    status = raw.get('status') if raw.get('status') in SERVER_STATUSES else None
    mode = raw.get('answerMode') if raw.get('answerMode') in MODES else None
    inference = raw.get('inferenceUsed') if type(raw.get('inferenceUsed')) is bool else None
    server = {field: duration(raw.get(field)) for field in
              ('retrievalMs', 'firstTextMs', 'generationFirstTextMs', 'generationMs', 'totalMs')}
    usage = raw.get('usage')
    usage = usage if isinstance(usage, dict) else {}
    server.update(status=status, answerMode=mode, inferenceUsed=inference,
                  usage={field: duration(usage.get(field)) for field in ('prompt_tokens', 'completion_tokens', 'total_tokens')})
    expected_kind = 'chat' if kind == 'chat' else 'notes'
    path_ok = raw.get('kind') == expected_kind and (
        server['generationMs'] is not None if kind == 'chat' else
        mode == 'model_synthesis' and inference is True if kind == 'notes_generated' else
        mode == 'explicit_fields' and inference is False and server['generationMs'] is None)
    reason = result.get('finishReason')
    reason = reason if reason in ('stop', 'length', 'error') else None
    done = result.get('done') is True
    first = duration(result.get('firstTextClientMs'))
    total = duration(result.get('totalClientMs'))
    valid = done and reason == 'stop' and status == 'completed' and path_ok and first is not None and total is not None
    return {'firstTextClientMs': first, 'totalClientMs': total, 'done': done, 'finishReason': reason,
            'server': server, 'expectedPathObserved': path_ok, 'includedInSummary': valid,
            'qualityVerdict': 'not_assessed'}


def collect(run_request):
    rows = []
    # Interleave the paths; first in this batch does not mean a cold model.
    for round_number in range(1, 4):
        for kind in KINDS:
            ordinal = len(rows) + 1
            print(f'Richiesta {ordinal}/9 — {kind}, prova {round_number}/3…', flush=True)
            started = time.perf_counter()
            try:
                values = sanitize(kind, run_request(payload_for(kind), keep_answer=False))
            except (HTTPError, URLError, TimeoutError, ValueError, RuntimeError, OSError) as exc:
                # Keep the failed slot. Do not emit exception messages or retry it.
                values = {'firstTextClientMs': None, 'totalClientMs': None,
                          'elapsedAttemptMs': duration((time.perf_counter() - started) * 1000),
                          'error': 'http' if isinstance(exc, HTTPError) else 'transport_or_invalid_response',
                          'httpStatus': exc.code if isinstance(exc, HTTPError) else None,
                          'server': None, 'expectedPathObserved': False, 'includedInSummary': False,
                          'qualityVerdict': 'not_assessed'}
            rows.append({'ordinal': ordinal, 'round': round_number, 'kind': kind,
                         'firstInBatch': ordinal == 1, **values})
    summary = {}
    for kind in KINDS:
        all_rows = [row for row in rows if row['kind'] == kind]
        included = [row for row in all_rows if row['includedInSummary']]
        summary[kind] = {'attempted': len(all_rows), 'included': len(included),
                         'excluded': len(all_rows) - len(included),
                         **{field: round(statistics.median(row[field] for row in included), 2) if included else None
                            for field in ('firstTextClientMs', 'totalClientMs')}}
    return {'schema': 1, 'mode': 'synthetic_baseline', 'model': MODEL, 'requested': 9,
            'observer': 'control_client_not_browser', 'modelColdWarmState': 'not_determined',
            'vaultRead': False, 'automaticRetries': 0, 'rows': rows, 'summary': summary}


def load_client(project):
    file = project / 'scripts/andrea/collaudo.py'
    if hashlib.sha256(file.read_bytes()).hexdigest() != EXPECTED_CLIENT:
        raise ValueError('Collaudo locale diverso dalla versione verificata. Nessuna richiesta inviata.')
    spec = importlib.util.spec_from_file_location('andrea_baseline_control_client', file)
    client = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(client)
    if client.BASE != 'http://127.0.0.1:8008' or client.MODEL != MODEL:
        raise ValueError('Client diverso dal profilo locale previsto. Nessuna richiesta inviata.')
    return client.run_request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path, help='Cartella OpenJarvis esistente; deve essere già acceso')
    args = parser.parse_args()
    run_request = load_client(args.project.expanduser().resolve(strict=True))
    print('Baseline finita: 9 richieste sintetiche, tre per percorso. Nessuna nota personale letta.', flush=True)
    print('Client di controllo, non rendering browser. Nessun warm-up, scaricamento del modello o retry.', flush=True)
    print('Le note sono estratti forniti: il recupero non misura la ricerca nel vault. Qualità non certificata.', flush=True)
    print(json.dumps(collect(run_request), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit('Baseline fermata dall’utente; serie non conclusa. Nessuna configurazione modificata.')
    except (OSError, ValueError) as exc:
        raise SystemExit(f'Baseline non avviata: {exc}')
