"""Finite CPU prefill comparison; no installation or persistent option changes.

Uses the fingerprinted installed v9 preparation and validation. Exactly six
calls compare default batch 512 with batch 128, preserving every source byte,
schema and generation setting. No retry, preload, unload or forced abstention.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import platform
import re
import secrets
import subprocess
import sys
import threading
import time
import urllib.request

sys.dont_write_bytecode = True
MODEL = 'qwen3:4b-instruct-2507-q4_K_M'
OLLAMA = 'http://127.0.0.1:11434'
APP = 'http://127.0.0.1:8008'
VERSION = '0.35.1'
MAX_BYTES = 65536
WORKER_SECONDS = 95
ORDER = ((0, 512), (0, 128), (1, 128), (1, 512), (2, 512), (2, 128))
MIN_PREFILL_GAIN_PERCENT = 10
MAX_TOTAL_REGRESSION_PERCENT = 5
MAX_CACHED_TOKENS = 8
EXPECTED_CHECKER = 'b9508c930f086506976d723bbe87a7c789354444e0d969396853b8208ed60c21'


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_json_key')
        result[key] = value
    return result


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                   separators=(',', ':')).encode()).hexdigest()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('unexpected_redirect')


def opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())


def load_project(project):
    file = project / 'scripts/andrea/check_web_compact_v9.py'
    parts = ('scripts', 'andrea', 'check_web_compact_v9.py')
    if (any(project.joinpath(*parts[:i]).is_symlink() for i in range(1, 4))
            or not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != EXPECTED_CHECKER):
        raise ValueError('installed_v9_checker_changed')
    spec = importlib.util.spec_from_file_location('_verified_batch_check', file)
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    check.verify_project(project)
    sys.path.insert(0, str(project / 'scripts/andrea'))
    import web_candidate_pipeline as pipeline
    if pipeline.CONTRACT_REVISION != 'compact_web_evidence_v9':
        raise ValueError('unexpected_contract_revision')
    return check, pipeline


def request_options(batch):
    if type(batch) is not int or batch not in (128, 512):
        raise ValueError('unexpected_batch')
    return {'temperature': 0.4, 'num_predict': 512, 'num_ctx': 4096,
            'num_batch': batch}


def isolated_messages(messages, marker):
    if not re.fullmatch('[0-9a-f]{32}', marker):
        raise ValueError('invalid_cache_marker')
    result = copy.deepcopy(messages)
    if len(result) != 2 or [item['role'] for item in result] != ['system', 'user']:
        raise ValueError('unexpected_roles')
    result[0]['content'] = marker + '\nDiagnostic cache marker only; not source evidence.\n' + result[0]['content']
    return result


def numeric_metrics(frame):
    result = {}
    for key in ('total_duration', 'load_duration', 'prompt_eval_duration', 'eval_duration',
                'prompt_eval_count', 'prompt_eval_cached_count', 'eval_count'):
        value = frame.get(key)
        result[key] = value if type(value) is int and 0 <= value <= 2**53 - 1 else None
    return result


def stream_once(messages, schema, batch, transport=None):
    """One bounded POST; parent owns the hard deadline even for stalled reads."""
    payload = {'model': MODEL, 'messages': messages, 'format': schema, 'stream': True,
               'think': False, 'keep_alive': '15m', 'options': request_options(batch)}
    req = urllib.request.Request(OLLAMA + '/api/chat',
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={'Content-Type': 'application/json'})
    started = time.monotonic()
    parts, size, wire_size, count, terminal, first = [], 0, 0, 0, None, None
    with (transport or opener()).open(req, timeout=90) as response:
        if response.status != 200:
            raise ValueError('unexpected_model_http_status')
        while True:
            line = response.readline(MAX_BYTES + 1)
            if not line:
                break
            wire_size += len(line)
            if len(line) > MAX_BYTES or wire_size > 4 * 1024 * 1024 or time.monotonic() - started > 90:
                raise ValueError('model_stream_limit')
            if not line.strip():
                continue
            count += 1
            if count > 2048 or terminal is not None:
                raise ValueError('unexpected_frame_after_terminal_or_frame_limit')
            frame = json.loads(line, object_pairs_hook=unique_pairs)
            if not isinstance(frame, dict) or frame.get('error') or type(frame.get('done')) is not bool:
                raise ValueError('invalid_model_frame')
            message = frame.get('message')
            if not isinstance(message, dict) or message.get('tool_calls') or message.get('thinking'):
                raise ValueError('unexpected_model_message')
            content = message.get('content', '')
            if not isinstance(content, str):
                raise ValueError('invalid_model_content')
            size += len(content)
            if size > 5000:
                raise ValueError('model_answer_too_large')
            if content and first is None:
                first = (time.monotonic() - started) * 1000
            parts.append(content)
            if frame['done']:
                terminal = frame
    finished = time.monotonic()
    raw = ''.join(parts)
    complete = terminal is not None and terminal.get('done_reason') == 'stop'
    return {'raw': raw, 'completed': complete,
            'doneReason': terminal.get('done_reason') if terminal else None,
            'firstJsonClientMs': round(first, 3) if first is not None else None,
            'totalClientMs': round((finished - started) * 1000, 3),
            'native': numeric_metrics(terminal or {})}


def thermal_sample():
    """Only numerical reported CPU limits; no process list or temperature guess."""
    started = time.monotonic()
    try:
        value = subprocess.run(['/usr/bin/pmset', '-g', 'therm'],
            capture_output=True, timeout=1.5, check=False)
        if value.returncode != 0 or len(value.stdout) > 16384:
            raise ValueError()
        text = value.stdout.decode('utf-8', errors='replace')
        limits = {}
        for key in ('CPU_Speed_Limit', 'CPU_Scheduler_Limit', 'CPU_Available_CPUs'):
            match = re.search(r'\b' + key + r'\s*=\s*(\d+)\b', text)
            limits[key] = int(match.group(1)) if match else None
        return {'reportedLimits': limits, 'available': any(v is not None for v in limits.values()),
                'readMs': round((time.monotonic() - started) * 1000, 3)}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {'reportedLimits': None, 'available': False,
                'readMs': round((time.monotonic() - started) * 1000, 3)}


def cpu_residency():
    # Post-request metadata, not a load, inference or configuration operation.
    try:
        with opener().open(OLLAMA + '/api/ps', timeout=4) as response:
            raw = response.read(MAX_BYTES + 1)
            if response.status != 200 or len(raw) > MAX_BYTES:
                raise ValueError()
            data = json.loads(raw, object_pairs_hook=unique_pairs)
        models = data.get('models') if isinstance(data, dict) else None
        if (not isinstance(models, list) or len(models) != 1 or not isinstance(models[0], dict)
                or models[0].get('name') != MODEL or type(models[0].get('size_vram')) is not int):
            raise ValueError()
        return {'expectedModelLoaded': True, 'sizeVram': models[0]['size_vram'],
                'phase': 'after_request_not_effective_batch_confirmation'}
    except (OSError, ValueError, TypeError):
        return {'expectedModelLoaded': None, 'sizeVram': None,
                'phase': 'after_request_not_effective_batch_confirmation'}


class Observer:
    def __init__(self):
        self.stop = threading.Event()
        self.rows = []
        self.started = time.monotonic()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self):
        for delay in (6, 18, 36):
            if self.stop.wait(max(0, self.started + delay - time.monotonic())):
                return
            row = thermal_sample()
            row['scheduledWorkerOffsetSeconds'] = delay
            row['nativePrefillPhaseProven'] = False
            self.rows.append(row)

    def start(self):
        self.thread.start()

    def close(self):
        self.stop.set()
        self.thread.join(timeout=2)
        return not self.thread.is_alive()


def owned_worker(project, payload, timeout, observe=False):
    encoded = json.dumps(payload, ensure_ascii=False).encode()
    if len(encoded) > MAX_BYTES:
        raise ValueError('worker_input_too_large')
    child = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), str(project), '--worker'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    observer = Observer() if observe else None
    cleaned = True
    try:
        if observer:
            observer.start()
        output, _ = child.communicate(encoded, timeout=timeout)
        if child.returncode != 0 or len(output) > MAX_BYTES:
            raise ValueError('owned_worker_failed_or_oversized')
        value = json.loads(output, object_pairs_hook=unique_pairs)
        if not isinstance(value, dict):
            raise ValueError('owned_worker_invalid')
    except subprocess.TimeoutExpired:
        raise ValueError('owned_worker_deadline_no_retry') from None
    finally:
        if child.poll() is None:
            child.kill()  # Only this probe's child; never the Ollama/Jarvis process.
            child.communicate(timeout=2)
        if observer:
            cleaned = observer.close()
    return value, list(observer.rows) if observer else [], cleaned


def worker(project, payload):
    check, pipeline = load_project(project)
    if not isinstance(payload, dict):
        raise ValueError('invalid_worker_input')
    operation = payload.get('operation')
    if operation == 'metadata' and set(payload) == {'operation'}:
        values = []
        for path in ('/api/version', '/api/ps'):
            with opener().open(OLLAMA + path, timeout=4) as response:
                raw = response.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES or response.status != 200:
                    raise ValueError('invalid_ollama_metadata')
                values.append(json.loads(raw, object_pairs_hook=unique_pairs))
        version, loaded = values
        if not isinstance(version, dict) or version.get('version') != VERSION:
            raise ValueError('ollama_version_changed')
        models = loaded.get('models') if isinstance(loaded, dict) else None
        if not isinstance(models, list) or len(models) > 1:
            raise ValueError('unknown_loaded_model_state')
        if models and (not isinstance(models[0], dict) or models[0].get('name') != MODEL
                       or type(models[0].get('size_vram')) is not int or models[0]['size_vram'] != 0):
            raise ValueError('unexpected_loaded_model_or_not_cpu')
        return {'version': VERSION, 'loadedModelCount': len(models),
                'expectedCpuModelLoaded': bool(models)}
    if operation == 'read' and set(payload) == {'operation', 'case'}:
        index = payload['case']
        if type(index) is not int or index not in (0, 1):
            raise ValueError('invalid_read_case')
        page = check.post('/api/andrea/web/read', {'url': check.CASES[index]['url']}, 30, opener())
        check.checked_page(page)
        return page
    if operation != 'model' or set(payload) != {'operation', 'case', 'page', 'batch', 'marker'}:
        raise ValueError('invalid_worker_operation')
    index = payload['case']
    if type(index) is not int or not 0 <= index < 3:
        raise ValueError('invalid_model_case')
    page = payload['page']
    check.checked_page(page)
    case = check.CASES[index]
    bank, messages, schema, selection = pipeline.prepare(page, case['question'])
    message_sha, schema_sha = digest(messages), digest(schema)
    result = stream_once(isolated_messages(messages, payload['marker']), schema, payload['batch'])
    checked = pipeline.validate(result['raw'], bank, result['completed'], page, selection)
    return {'case': case['id'], 'numBatchRequested': payload['batch'],
            'sourceTextSha256': hashlib.sha256(page['text'].encode()).hexdigest(),
            'messagesBeforeCacheMarkerSha256': message_sha, 'nativeSchemaSha256': schema_sha,
            'modelSourceCharacters': selection['modelSourceCharacters'],
            'result': result, 'checks': checked, 'criteria': case['criteria'], 'residency': cpu_residency(),
            'qualityVerdict': 'pending_review'}


def eligible(row):
    result = row.get('result', {})
    native = result.get('native', {})
    expected_count = {'asyncio_scope': 2, 'csv_conversion_condition': 1, 'missing_price': 0}
    expected_outcome = 'abstained' if row['case'] == 'missing_price' else 'accepted_pending_semantic_review'
    if (result.get('completed') is not True or result.get('doneReason') != 'stop'
            or row.get('checks', {}).get('outcome') != expected_outcome
            or len(row.get('checks', {}).get('claims', [])) != expected_count[row['case']]
            or row.get('observerClosed') is not True
            or row.get('residency', {}).get('expectedModelLoaded') is not True
            or type(row.get('residency', {}).get('sizeVram')) is not int
            or row['residency']['sizeVram'] != 0):
        return False
    values = [native.get(k) for k in ('prompt_eval_count', 'prompt_eval_cached_count',
              'prompt_eval_duration', 'eval_duration', 'load_duration', 'total_duration', 'eval_count')]
    if any(type(n) is not int or n < 0 or n > 2**53 - 1 for n in values):
        return False
    count, cached, duration = values[:3]
    total = result.get('totalClientMs')
    return (count > cached and cached <= MAX_CACHED_TOKENS and duration > 0
            and type(total) in (int, float) and math.isfinite(total) and total > 0)


def comparison(rows):
    pairs = []
    ids = ('asyncio_scope', 'csv_conversion_condition', 'missing_price')
    ordered = [(ids[i], batch) for i, batch in ORDER]
    complete = [(r.get('case'), r.get('numBatchRequested')) for r in rows] == ordered
    for case in ids:
        group = [r for r in rows if r.get('case') == case]
        row = {'case': case, 'eligible': False, 'prefillGainPercent': None,
               'rawPrefillGainPercent': None, 'clientTotalChangePercent': None, 'numericGatesMet': False}
        if len(group) == 2:
            by_batch = {r['numBatchRequested']: r for r in group}
            if set(by_batch) != {128, 512}:
                pairs.append(row)
                continue
            base, candidate = by_batch[512], by_batch[128]
            same = all(base.get(k) == candidate.get(k) for k in
                ('sourceTextSha256', 'messagesBeforeCacheMarkerSha256', 'nativeSchemaSha256', 'modelSourceCharacters'))
            if same and eligible(base) and eligible(candidate):
                bn, cn = base['result']['native'], candidate['result']['native']
                cost_b = bn['prompt_eval_duration'] / (bn['prompt_eval_count'] - bn['prompt_eval_cached_count'])
                cost_c = cn['prompt_eval_duration'] / (cn['prompt_eval_count'] - cn['prompt_eval_cached_count'])
                gain = 100 * (1 - cost_c / cost_b)
                raw_gain = 100 * (1 - cn['prompt_eval_duration'] / bn['prompt_eval_duration'])
                change = 100 * (candidate['result']['totalClientMs'] / base['result']['totalClientMs'] - 1)
                gates = (case == 'missing_price' or min(gain, raw_gain) >= MIN_PREFILL_GAIN_PERCENT) and change <= MAX_TOTAL_REGRESSION_PERCENT
                row.update(eligible=True, prefillGainPercent=round(gain, 3),
                    rawPrefillGainPercent=round(raw_gain, 3), clientTotalChangePercent=round(change, 3), numericGatesMet=gates)
        pairs.append(row)
    numeric = complete and all(pair['numericGatesMet'] for pair in pairs)
    return {'completeFixedOrder': complete, 'pairs': pairs, 'numericGatesMet': numeric,
            'decision': 'requires_all_six_meaning_reviews_and_installed_validation' if numeric else 'do_not_adopt',
            'performanceVerdict': 'numeric_gates_met_not_causal_proof' if numeric else 'not_demonstrated',
            'qualityVerdict': 'pending_review', 'integrationAllowed': False,
            'browserRendering': 'not_measured', 'historicalBenchmarksChanged': False}


def run(project, emit=print):
    if platform.system() != 'Darwin':
        raise ValueError('comparison_requires_macos')
    check, _ = load_project(project)
    metadata, _, _ = owned_worker(project, {'operation': 'metadata'}, 12)
    pages = {}
    for index in (0, 1):
        pages[index], _, _ = owned_worker(project, {'operation': 'read', 'case': index}, 35)
    pages[2] = pages[1]
    required = check.CASES[1]['requiredContext']
    if ' '.join(required.split()) not in ' '.join(pages[1]['text'].split()):
        raise ValueError('required_csv_condition_missing_no_inference')
    emit('Sei richieste, una sola serie: batch 512 contro 128. OpenJarvis resta acceso ma senza altre richieste. Nessuna installazione o retry. Circa 4–8 minuti; limite massimo circa 11 minuti.')
    rows = []
    for number, (index, batch) in enumerate(ORDER, 1):
        case = check.CASES[index]
        emit(f'Richiesta {number}/6: {case["id"]}, batch {batch}…', flush=True)
        try:
            row, observations, closed = owned_worker(project, {'operation': 'model',
                'case': index, 'page': pages[index], 'batch': batch, 'marker': secrets.token_hex(16)},
                WORKER_SECONDS, observe=True)
            row['thermalObservations'], row['observerClosed'] = observations, closed
            rows.append(row)
            emit(json.dumps(row, ensure_ascii=False, indent=2), flush=True)
            if row['result'].get('completed') is not True:
                emit('Trasporto non completato: serie fermata, nessun retry.', flush=True)
                break
        except (OSError, ValueError, TypeError) as exc:
            rows.append({'case': case['id'], 'numBatchRequested': batch,
                'error': str(exc), 'result': {}, 'checks': {}, 'qualityVerdict': 'not_evaluated'})
            emit('Richiesta interrotta: serie fermata, nessun retry.', flush=True)
            break
    return {'mode': 'installed_v9_cpu_batch_comparison', 'contractRevision': 'compact_web_evidence_v9',
            'productionModified': False, 'vaultRead': False, 'automaticRetries': 0,
            'requested': 6, 'completedRows': len(rows), 'metadata': metadata,
            'onlyExperimentalOption': 'num_batch', 'referenceBatch': 512, 'candidateBatch': 128,
            'threadPolicy': 'unchanged_automatic', 'cacheMarkerIsDiagnosticNotProduction': True,
            'modelOptionsPersistent': False, 'loadedRunnerMayReloadOrRetainLastRequestOptions': True,
            'nextOrdinaryRequestUsesOrdinarySettings': True,
            'thresholds': {'minimumPrefillGainPercentForBothPositiveCases': MIN_PREFILL_GAIN_PERCENT,
                           'maximumClientTotalRegressionPercentPerCase': MAX_TOTAL_REGRESSION_PERCENT,
                           'maximumCachedTokensPerRequest': MAX_CACHED_TOKENS},
            'comparison': comparison(rows), 'rows': rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('project', type=Path)
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    try:
        project = args.project.expanduser().resolve(strict=True)
        if args.worker:
            raw = sys.stdin.buffer.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError('worker_input_too_large')
            report = worker(project, json.loads(raw, object_pairs_hook=unique_pairs))
        else:
            report = run(project)
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print('Confronto fermato: ' + str(exc) + '. Nessun retry o modifica del progetto.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
