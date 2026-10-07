"""Three synthetic streaming probes of Ollama, without changing the application.

Only numeric measurements are emitted; generated text is discarded. This direct
probe excludes the OpenJarvis server/browser and does not certify answer quality.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
import time
from urllib.request import Request, build_opener, ProxyHandler

MODEL = 'qwen3:4b-instruct-2507-q4_K_M'
BASE = 'http://127.0.0.1:11434'
EXPECTED_RUNTIME = 'af38a56db92227dc2e2f4034792cc4cd474c161b034a9368c62477478c42f68c'
QUERY = 'Quale problema risulta ancora aperto per la copertina?'
SOURCE = {'id': 'N1', 'title': 'Storia della copertina', 'text':
    'Il 2026-08-19 il codice a barre su fondo nero causò una bocciatura. '
    'Il problema fu risolto e la copertina corretta è online dal 2026-08-20. '
    'Questa nota non documenta problemi successivi.'}
LIMIT = 4 * 1024 * 1024


def number(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def milliseconds(value):
    valid = number(value)
    return round(valid / 1_000_000, 3) if valid is not None else None


def messages_from_runtime(project):
    """Compile only verified public prompt definitions, not runtime imports/code."""
    file = project / 'scripts/andrea/runtime.py'
    data = file.read_bytes()
    if hashlib.sha256(data).hexdigest() != EXPECTED_RUNTIME:
        raise ValueError('Runtime diverso dalla versione verificata; nessuna richiesta inviata.')
    tree = ast.parse(data)
    nodes = [node for node in tree.body if
        isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'NOTES_PROMPT' for t in node.targets)
        or isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and node.target.id == 'NOTES_PROMPT'
        or isinstance(node, ast.FunctionDef) and node.name == 'notes_messages']
    if len(nodes) != 3:
        raise ValueError('Definizioni del prompt diverse dal previsto.')
    namespace = {'json': json}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(file), 'exec'), namespace)
    return namespace['notes_messages'](QUERY, [SOURCE])


def loaded_snapshot(opener):
    """Read-only selected model snapshot; never retain other model identities."""
    try:
        with opener.open(BASE + '/api/ps', timeout=5) as response:
            data = response.read(LIMIT + 1)
        if len(data) > LIMIT:
            raise ValueError('response_limit')
        raw = json.loads(data)
        models = raw['models']
        if not isinstance(models, list) or any(not isinstance(m, dict) for m in models):
            raise ValueError('invalid_models')
        selected = next((m for m in models if m.get('name') == MODEL or m.get('model') == MODEL), None)
        return {'available': True, 'selectedModelLoaded': selected is not None,
                **{field: number(selected.get(key)) if selected else None for field, key in
                   (('contextLength', 'context_length'), ('sizeBytes', 'size'), ('sizeVramBytes', 'size_vram'))}}
    except (OSError, ValueError, KeyError, TypeError):
        return {'available': False, 'selectedModelLoaded': None,
                'contextLength': None, 'sizeBytes': None, 'sizeVramBytes': None}


def native_metrics(event):
    fields = ('total_duration', 'load_duration', 'prompt_eval_duration', 'eval_duration')
    result = {field.removesuffix('_duration') + 'Ms': milliseconds(event.get(field)) for field in fields}
    result.update({field: number(event.get(field)) for field in
                   ('prompt_eval_count', 'prompt_eval_cached_count', 'eval_count')})
    tokens, elapsed = result['eval_count'], result['evalMs']
    result['evalTokensPerSecond'] = round(tokens * 1000 / elapsed, 3) if tokens is not None and elapsed and tokens > 0 else None
    # Do not interpret a residual as a particular phase or mix with client time.
    return result


def stream_probe(opener, messages, clock=time.perf_counter):
    body = {'model': MODEL, 'messages': messages, 'stream': True, 'think': False,
            'options': {'temperature': 0.4, 'num_predict': 512, 'num_ctx': 4096}}
    request = Request(BASE + '/api/chat', data=json.dumps(body, ensure_ascii=False).encode(),
                      headers={'Content-Type': 'application/json'}, method='POST')
    started = clock()
    first = None
    count = 0
    final = None
    try:
        with opener.open(request, timeout=90) as response:
            while True:
                if clock() - started > 90:
                    raise TimeoutError('deadline')
                line = response.readline(262145)
                if clock() - started > 90:
                    raise TimeoutError('deadline')
                if not line:
                    break
                count += len(line)
                if len(line) > 262144 or count > LIMIT:
                    raise ValueError('response_limit')
                if not line.strip():
                    continue
                event = json.loads(line)
                if not isinstance(event, dict) or 'error' in event:
                    raise ValueError('invalid_event')
                content = event.get('message', {}).get('content')
                if isinstance(content, str) and content and first is None:
                    first = round((clock() - started) * 1000, 3)
                if event.get('done') is True:
                    final = event
                    break
        reason = final.get('done_reason') if final else None
        reason = reason if reason in ('stop', 'length') else None
        status = 'completed' if final and reason == 'stop' and first is not None else 'truncated' if reason == 'length' else 'incomplete'
        return {'status': status, 'firstContentClientMs': first,
                'totalClientMs': round((clock() - started) * 1000, 3),
                'doneReason': reason, 'native': native_metrics(final or {}), 'qualityVerdict': 'not_assessed'}
    except (OSError, ValueError, TypeError, AttributeError):
        return {'status': 'error', 'firstContentClientMs': first,
                'totalClientMs': round((clock() - started) * 1000, 3),
                'doneReason': None, 'native': native_metrics({}), 'qualityVerdict': 'not_assessed'}


def collect(opener, messages):
    rows = []
    for ordinal in range(1, 4):
        print(f'Richiesta sintetica Ollama {ordinal}/3…', flush=True)
        before = loaded_snapshot(opener)
        probe = stream_probe(opener, messages)
        rows.append({'ordinal': ordinal, 'loadedBefore': before, **probe,
                     'loadedAfter': loaded_snapshot(opener)})
    return {'schema': 1, 'mode': 'direct_ollama_phases', 'model': MODEL,
            'requested': 3, 'automaticRetries': 0, 'vaultRead': False,
            'observer': 'direct_ollama_not_openjarvis_or_browser',
            'coldWarmState': 'not_determined_from_loaded_snapshot', 'rows': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    args = parser.parse_args()
    messages = messages_from_runtime(args.project.expanduser().resolve(strict=True))
    # Disable environment HTTP proxies and never follow redirects away from localhost.
    from urllib.request import HTTPRedirectHandler
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = build_opener(ProxyHandler({}), NoRedirect())
    print('Tre richieste con estratti sintetici e prompt di produzione verificato. Nessuna nota letta.', flush=True)
    print('Modello e opzioni invariati; nessun warm-up, unload, retry o modifica di configurazione.', flush=True)
    print(json.dumps(collect(opener, messages), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit('Controllo interrotto; serie non conclusa.')
    except (OSError, ValueError):
        raise SystemExit('Controllo non avviato: runtime assente o diverso dalla versione verificata.')
