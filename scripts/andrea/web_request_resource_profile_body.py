"""Implementation included in the self-contained, hash-pinned resource profiler.

One installed-baseline CSV request, no retries or option changes. Samples are
diagnostic reads in an observer thread; they never generate model responses.
This file is bundled with two already reviewed sources for the Mac script.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
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
import types

sys.dont_write_bytecode = True
EXPECTED_OLLAMA_VERSION = '0.35.1'
SAMPLE_SECONDS = (6, 18, 36)
SAMPLE_BUDGET_SECONDS = 8
MODEL_WORKER_DEADLINE_SECONDS = 95
MAX_WORKER_BYTES = 65536


def embedded_module(name, source):
    module = types.ModuleType(name)
    module.__file__ = str(Path(__file__).resolve())
    exec(compile(source, module.__file__ + ':' + name, 'exec'), module.__dict__)
    return module


baseline = embedded_module('_profile_baseline', BASELINE_SOURCE)
resources = embedded_module('_profile_resources', RESOURCE_SOURCE)


class WindowReader(resources.Reader):
    def __init__(self, stop, **kwargs):
        self.stop = stop
        super().__init__(**kwargs)

    def timeout(self):
        remaining = SAMPLE_BUDGET_SECONDS - (self.clock() - self.started)
        if self.stop.is_set() or remaining <= 0:
            raise TimeoutError('observation_cancelled_or_exhausted')
        return min(1.5, remaining)


def snapshot(stop, *, reader=None):
    reader = reader or WindowReader(stop)
    started = time.monotonic()
    before = resources.vm_counters(reader.command('vm_before', ['/usr/bin/vm_stat']))
    therm = resources.thermal_limits(reader.command('thermal', ['/usr/bin/pmset', '-g', 'therm']))
    model = resources.selected_model(reader.get('/api/ps'))
    processes = resources.ollama_processes(reader)
    cpu = resources.cpu_usage(reader.command('cpu_usage',
        ['/usr/bin/top', '-l', '2', '-s', '1', '-n', '0', '-R', '-F']))
    load = resources.load_average(reader.command('load_average', ['/usr/sbin/sysctl', '-n', 'vm.loadavg']))
    swap = resources.swap_used_bytes(reader.command('swap_used', ['/usr/sbin/sysctl', '-n', 'vm.swapusage']))
    after = resources.vm_counters(reader.command('vm_after', ['/usr/bin/vm_stat']))
    return {'startedMonotonic': started, 'finishedMonotonic': time.monotonic(),
            'thermalLimits': therm, 'loadedModels': model, 'ollamaProcesses': processes,
            'cpuUsageLastInterval': cpu, 'loadAverage1_5_15m': load,
            'swapUsedBytes': swap,
            'vmCounterDeltasPages': {key: resources.counter_delta(before, after, key)
                                   for key in ('Swapins', 'Swapouts', 'Pageouts')},
            'unavailableQueries': copy.deepcopy(reader.issues)}


class Observer:
    def __init__(self, worker, *, clock=time.monotonic, sampler=snapshot):
        self.worker = worker
        self.clock = clock
        self.sampler = sampler
        self.started = clock()
        self.stop = threading.Event()
        self.rows = []
        self.errors = []
        self.thread = threading.Thread(target=self.observe, daemon=True)

    def observe(self):
        for scheduled in SAMPLE_SECONDS:
            if self.stop.wait(max(0, self.started + scheduled - self.clock())):
                return
            if self.worker.poll() is not None:
                return
            try:
                row = self.sampler(self.stop)
                row['scheduledWorkerOffsetSeconds'] = scheduled
                self.rows.append(row)
            except Exception:
                # Never include raw system stderr, process arguments or paths.
                self.errors.append({'scheduledWorkerOffsetSeconds': scheduled,
                                    'reason': 'sample_unavailable'})

    def start(self):
        self.thread.start()

    def close(self):
        self.stop.set()
        self.thread.join(timeout=SAMPLE_BUDGET_SECONDS + 2)
        return not self.thread.is_alive()


def worker_error(kind):
    return {'requestStartedMonotonic': None, 'requestFinishedMonotonic': None,
            'result': {'status': 'error', 'errorKind': kind, 'modelAnswer': '',
                       'firstContentClientMs': None, 'totalClientMs': None,
                       'doneReason': None, 'native': baseline.native_metrics({}),
                       'qualityVerdict': 'pending_review'}}


def validate_worker(value):
    if not isinstance(value, dict) or set(value) != {'requestStartedMonotonic', 'requestFinishedMonotonic', 'result'}:
        raise ValueError('invalid_worker_shape')
    start, finish = value['requestStartedMonotonic'], value['requestFinishedMonotonic']
    if (any(type(n) not in (int, float) or not math.isfinite(n) or n < 0 for n in (start, finish))
            or finish < start or finish - start > MODEL_WORKER_DEADLINE_SECONDS
            or not isinstance(value['result'], dict)):
        raise ValueError('invalid_worker_timing')
    result = value['result']
    if (result.get('status') not in ('completed', 'error', 'truncated', 'incomplete')
            or not isinstance(result.get('modelAnswer'), str) or len(result['modelAnswer']) > 32000
            or not isinstance(result.get('native'), dict)):
        raise ValueError('invalid_worker_result')
    return value


def collect(project, page, *, popen=subprocess.Popen, observer_factory=Observer):
    payload = json.dumps(page, ensure_ascii=False).encode()
    if len(payload) > MAX_WORKER_BYTES:
        raise ValueError('page_payload_too_large')
    worker = popen([sys.executable, str(Path(__file__).resolve()), str(project), '--model-worker'],
                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    observer = observer_factory(worker)
    observer.start()
    try:
        try:
            output, _stderr = worker.communicate(payload, timeout=MODEL_WORKER_DEADLINE_SECONDS)
            if worker.returncode != 0 or len(output) > MAX_WORKER_BYTES:
                value = worker_error('owned_worker_invalid_or_failed')
            else:
                value = validate_worker(json.loads(output, object_pairs_hook=baseline.unique_pairs))
        except subprocess.TimeoutExpired:
            # Terminate only the process we created; no signal to Ollama/Jarvis.
            worker.kill()
            worker.communicate(timeout=2)
            value = worker_error('owned_worker_deadline')
        except (ValueError, TypeError, OSError):
            value = worker_error('owned_worker_invalid_result')
    finally:
        if worker.poll() is None:
            worker.kill()
            worker.communicate(timeout=2)
        cleaned = observer.close()
    return value, copy.deepcopy(observer.rows), copy.deepcopy(observer.errors), cleaned


def classify_samples(rows, value):
    start = value.get('requestStartedMonotonic')
    finish = value.get('requestFinishedMonotonic')
    first = value.get('result', {}).get('firstContentClientMs')
    result = []
    for row in rows:
        current = copy.deepcopy(row)
        a, b = current.pop('startedMonotonic'), current.pop('finishedMonotonic')
        valid = (type(start) in (int, float) and type(finish) in (int, float)
                 and math.isfinite(start) and math.isfinite(finish) and start <= finish)
        inside = bool(valid and start <= a <= b <= finish)
        current['startedClientOffsetMs'] = round((a-start)*1000, 3) if valid else None
        current['finishedClientOffsetMs'] = round((b-start)*1000, 3) if valid else None
        current['entirelyWithinClientRequest'] = inside
        current['entirelyBeforeFirstJsonArrival'] = (
            bool(inside and (b-start)*1000 <= first) if type(first) in (int, float)
            and math.isfinite(first) and first >= 0 else None)
        current['nativePrefillPhaseProven'] = False
        result.append(current)
    return result


def stricter_checks(raw, bank, complete, *, heading_ranges):
    result = baseline.validate(raw, bank, complete, heading_ranges=heading_ranges)
    if result['outcome'] != 'accepted_pending_semantic_review':
        return result
    for index, claim in enumerate(result['claims'], 1):
        quote, text = claim['quote'], claim['text']
        if re.fullmatch(r'control\s+subprocesses[.;]?', quote.strip(), re.I) and re.search(
            r'\b(?:attraverso|tramite|mediante|usando|utilizzando|through|via|using|'
            r'interfacci[ae]|interfaces?|protocoll[oi]|protocols?)\b|\bper\s+mezzo\s+di\b', text, re.I):
            return {'outcome': 'rejected', 'reason': 'subprocess_mechanism_not_in_passage', 'claims': [],
                    'details': {'claimIndex': index, 'passage': claim['passage'], 'text': text,
                                'quote': quote, 'diagnosticOnly': True}}
    return result


def checked_csv(page):
    baseline.checked_page(page)
    case = baseline.CASES[1]
    if page['url'] != case['url'] or baseline.normalized(case['requiredContext']) not in baseline.normalized(page['text']):
        raise ValueError('csv_source_or_required_context_missing')
    return case


def model_worker(project):
    baseline.verify_project(project)
    raw = sys.stdin.buffer.read(MAX_WORKER_BYTES + 1)
    if len(raw) > MAX_WORKER_BYTES:
        raise ValueError('worker_input_too_large')
    page = json.loads(raw, object_pairs_hook=baseline.unique_pairs)
    case = checked_csv(page)
    _, messages, schema = baseline.baseline_prepare(page['text'], case['question'])
    messages = baseline.isolated_messages(messages, 'A' + secrets.token_hex(16))
    opener = baseline.urllib.request.build_opener(baseline.urllib.request.ProxyHandler({}), baseline.NoRedirect())
    started = time.monotonic()
    result = baseline.stream_probe(opener, messages, schema, clock=time.monotonic)
    print(json.dumps({'requestStartedMonotonic': started, 'requestFinishedMonotonic': time.monotonic(),
                      'result': result}, ensure_ascii=False))


def run(project, *, emit=print):
    if platform.system() != 'Darwin':
        raise ValueError('profile_requires_macos')
    baseline.verify_project(project)
    before = resources.run(project)
    if before['ollamaVersion'] != EXPECTED_OLLAMA_VERSION:
        raise ValueError('ollama_version_changed_before_inference')
    models = before['loadedModels']
    if (models['loadedModelCount'] not in (0, 1)
            or (models['loadedModelCount'] == 1 and models['expectedModelLoaded'] is not True)):
        raise ValueError('loaded_state_unknown_or_other_model')
    emit('Una richiesta CSV con il prompt di produzione. Letture delle risorse durante la stessa operazione; nessuna nota personale, impostazione cambiata o retry.')
    page = baseline.read_heading_page(project, baseline.CASES[1]['url'])
    case = checked_csv(page)
    bank, messages, schema = baseline.baseline_prepare(page['text'], case['question'])
    emit('Profilo 1/1 in corso. Le osservazioni sono previste a 6, 18 e 36 secondi; quelle successive alla fine vengono saltate.')
    value, observations, observation_errors, cleaned = collect(project, page)
    result = value['result']
    checks = stricter_checks(result['modelAnswer'], bank, result['status'] == 'completed', heading_ranges=page['headingRanges'])
    after_version = resources.Reader().get('/api/version')
    actual_version = after_version.get('version') if isinstance(after_version, dict) else None
    baseline.verify_project(project)
    report = {'schema': 1, 'mode': 'one_csv_request_with_contemporaneous_resources',
              'modelInferenceRequests': 1 if value['requestStartedMonotonic'] is not None else None,
              'modelInferenceRequestsLimit': 1, 'automaticRetries': 0, 'productionModified': False,
              'vaultRead': False, 'modelOptionsChanged': False, 'existingProcessesTerminated': False,
              'modelWorkerDeadlineSeconds': MODEL_WORKER_DEADLINE_SECONDS,
              'scheduledWorkerOffsetSeconds': list(SAMPLE_SECONDS), 'before': before,
              'ollamaVersionBefore': EXPECTED_OLLAMA_VERSION, 'ollamaVersionAfter': actual_version,
              'versionUnchanged': actual_version == EXPECTED_OLLAMA_VERSION,
              'sourceURL': case['url'], 'question': case['question'], 'criteria': case['criteria'],
              'inputCharacters': len(page['text']), 'partial': page['partial'], 'readMs': page['readMs'],
              'sourceTextSha256': hashlib.sha256(page['text'].encode()).hexdigest(),
              'headingRanges': page['headingRanges'], 'fullSourcePreserved': True,
              'installedBaselineInputUnchangedExceptDiagnosticNonce': True,
              'baselineMessagesSha256': hashlib.sha256(json.dumps(messages, ensure_ascii=False).encode()).hexdigest(),
              'result': result, 'checks': checks,
              'installedPolicyChecks': baseline.installed_validate(result['modelAnswer'], bank, result['status'] == 'completed'),
              'cacheQualification': baseline.cache_qualification(result['native']),
              'observations': classify_samples(observations, value),
              'observationErrors': observation_errors, 'observerCleanupCompleted': cleaned,
              'performanceVerdict': 'diagnostic_only_no_ab_comparison', 'qualityVerdict': 'pending_review',
              'browserRendering': 'not_measured', 'integrationAllowed': False,
              'notes': ['Campioni di risorse, non una prova causale né il superamento della serie precedente.',
                        'Prima del JSON include attesa e caricamento: non dimostra la sola fase nativa di prefill.',
                        'Letture concorrenti hanno un costo di osservazione; tempi nativi, client e campioni non si sommano.',
                        'Un timeout chiude solo il processo posseduto e il suo collegamento; la fine del lavoro nel server non è confermata.']}
    emit(json.dumps(report, ensure_ascii=False, indent=2))
    emit('Profilo finito. Nessuna ottimizzazione adottata automaticamente; risorse e risposta richiedono analisi.')
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('project', type=Path, nargs='?')
    parser.add_argument('--page-worker', action='store_true')
    parser.add_argument('--model-worker', action='store_true')
    parser.add_argument('--ollama-read', choices=('/api/version', '/api/ps'))
    args = parser.parse_args()
    if args.ollama_read:
        if args.project or args.page_worker or args.model_worker:
            parser.error('Invalid internal read mode')
        return resources.main()
    if args.project is None or (args.page_worker and args.model_worker):
        parser.error('Specify one project and one mode')
    try:
        project = args.project.expanduser().resolve(strict=True)
        if args.page_worker:
            baseline.page_worker(project)
        elif args.model_worker:
            model_worker(project)
        else:
            run(project)
        return 0
    except KeyboardInterrupt:
        print('Profilo interrotto dall’utente. Nessun retry o modifica.', file=sys.stderr)
        return 130
    except (OSError, ValueError, TypeError):
        print('Profilo interrotto: versione, sorgente, servizio o lettura non corrispondono ai controlli previsti. Nessuna modifica e nessun retry.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
