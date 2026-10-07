"""Two fixed synthetic OpenJarvis requests; read-only Ollama expiry observation."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from urllib.request import build_opener, ProxyHandler, HTTPRedirectHandler

MODEL = 'qwen3:4b-instruct-2507-q4_K_M'
EXPECTED_CLIENT = 'ebbd828888b1aaccf8a3846d4d242606f5327feccc136af91de757a425142fa4'
QUERY = 'Quale problema risulta ancora aperto per la copertina?'
SOURCE = {'id': 'N1', 'title': 'Storia della copertina', 'text':
    'Il 2026-08-19 il codice a barre su fondo nero causò una bocciatura. '
    'Il problema fu risolto e la copertina corretta è online dal 2026-08-20. '
    'Questa nota non documenta problemi successivi.'}


def numeric(v):
    return v if type(v) in (int, float) and math.isfinite(v) and v >= 0 else None


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def selected_expiry():
    try:
        opener = build_opener(ProxyHandler({}), NoRedirect())
        with opener.open('http://127.0.0.1:11434/api/ps', timeout=5) as response:
            data = response.read(1024 * 1024 + 1)
        if len(data) > 1024 * 1024:
            raise ValueError('limit')
        models = json.loads(data)['models']
        if not isinstance(models, list) or any(not isinstance(m, dict) for m in models):
            raise ValueError('models')
        model = next((m for m in models if m.get('name') == MODEL or m.get('model') == MODEL), None)
        if model is None:
            return {'available': True, 'selectedModelLoaded': False, 'remainingSeconds': None}
        remaining = None
        value = model.get('expires_at')
        if isinstance(value, str):
            expiry = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if expiry.tzinfo is not None:
                remaining = round((expiry - datetime.now(timezone.utc)).total_seconds(), 2)
        return {'available': True, 'selectedModelLoaded': True, 'remainingSeconds': numeric(remaining)}
    except (OSError, ValueError, KeyError, TypeError):
        return {'available': False, 'selectedModelLoaded': None, 'remainingSeconds': None}


def collect(run_request, observe=selected_expiry):
    rows = []
    for ordinal in (1, 2):
        print(f'Richiesta sintetica OpenJarvis {ordinal}/2…', flush=True)
        before = observe()
        try:
            result = run_request({'model': MODEL, 'stream': True,
                'messages': [{'role': 'user', 'content': QUERY}],
                'notes_query': QUERY, 'notes_sources': [SOURCE]}, keep_answer=True)
            server = result.get('server') or {}
            reason = result.get('finishReason')
            completed = result.get('done') is True and reason == 'stop' and server.get('status') == 'completed'
            path_ok = server.get('kind') == 'notes' and server.get('answerMode') == 'model_synthesis' and server.get('inferenceUsed') is True
            row = {'completed': completed, 'expectedPathObserved': path_ok,
                   'firstTextClientMs': numeric(result.get('firstTextClientMs')),
                   'totalClientMs': numeric(result.get('totalClientMs')),
                   'server': {k: numeric(server.get(k)) for k in ('firstTextMs', 'generationFirstTextMs', 'generationMs', 'totalMs')},
                   # Synthetic source only; retained for human semantic review.
                   'syntheticAnswer': result.get('answer') if isinstance(result.get('answer'), str) else None}
        except (OSError, ValueError, RuntimeError, KeyError, TypeError):
            row = {'completed': False, 'expectedPathObserved': False, 'firstTextClientMs': None,
                   'totalClientMs': None, 'server': None, 'syntheticAnswer': None, 'error': 'request_failed'}
        after = observe()
        remaining = after.get('remainingSeconds')
        row.update(ordinal=ordinal, loadedBefore=before, loadedAfter=after,
                   retentionOverTenMinutesObserved=type(remaining) in (int, float) and 600 < remaining <= 960,
                   qualityVerdict='pending_review')
        rows.append(row)
    return {'schema': 1, 'mode': 'openjarvis_reuse_check', 'requested': 2,
            'vaultRead': False, 'automaticRetries': 0, 'rows': rows,
            'retentionSurvivalAfterIdle': 'not_tested', 'browserRendering': 'not_measured'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    args = parser.parse_args()
    file = args.project.expanduser().resolve(strict=True) / 'scripts/andrea/collaudo.py'
    if hashlib.sha256(file.read_bytes()).hexdigest() != EXPECTED_CLIENT:
        raise ValueError('client version')
    spec = importlib.util.spec_from_file_location('reuse_verified_client', file)
    client = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(client)
    if client.BASE != 'http://127.0.0.1:8008' or client.MODEL != MODEL:
        raise ValueError('client target')
    print('Due richieste sintetiche sul server; scadenza Ollama osservata senza modificarla.', flush=True)
    print('Nessuna nota personale letta. Le risposte sintetiche richiedono revisione.', flush=True)
    print(json.dumps(collect(client.run_request), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit('Controllo interrotto; serie non conclusa.')
    except (OSError, ValueError):
        raise SystemExit('Controllo non avviato: client assente o diverso dalla versione verificata.')
