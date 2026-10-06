"""One-request profiling: exact baseline, concurrent evidence and owned deadlines."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import web_request_resource_profile as probe
import web_type_latency_probe as preceding
import latency_resource_diagnostic as resources
import web_mechanism_latency_candidate as mechanism
import test_andrea_latency_resources as resource_tests
from test_andrea_web_type_latency import CSV, OBSERVED_DECIMAL

ROOT = Path(__file__).resolve().parents[1]
GOOD = ('csv.reader restituisce ogni riga come lista di stringhe, senza conversione automatica dei tipi, '
        'salvo QUOTE_NONNUMERIC, che trasforma i campi non quotati in float.')


def page():
    return {'url': preceding.CASES[1]['url'], 'title': 'csv', 'text': CSV,
            'partial': False, 'redirects': 0, 'headingRanges': [], 'readMs': 1}


def result(status='completed'):
    return {'status': status, 'modelAnswer': json.dumps({'claims': [{'passage': 1, 'text': GOOD}]}),
            'native': {'prompt_eval_count': 2441, 'prompt_eval_cached_count': 3, 'prompt_evalMs': 50000},
            'firstContentClientMs': 50000, 'totalClientMs': 65000, 'doneReason': 'stop'}


def worker_value(status='completed'):
    return {'requestStartedMonotonic': 100., 'requestFinishedMonotonic': 165., 'result': result(status)}


class Child:
    def __init__(self, *, timeout=False, raw=None):
        self.returncode = None
        self.timeout = timeout
        self.raw = raw or json.dumps(worker_value()).encode()
        self.calls = []
        self.kills = 0

    def communicate(self, payload=None, timeout=None):
        self.calls.append((payload, timeout))
        if self.timeout and self.kills == 0:
            raise subprocess.TimeoutExpired('owned', timeout)
        self.returncode = -9 if self.kills else 0
        return self.raw, b'/Users/private/secret-credentials'

    def poll(self): return self.returncode
    def kill(self): self.kills += 1


class StubObserver:
    def __init__(self, worker):
        self.worker = worker
        self.rows = [{'startedMonotonic': 110., 'finishedMonotonic': 112.,
                      'scheduledWorkerOffsetSeconds': 6}]
        self.errors = []
        self.started = False
        self.closed = False
    def start(self): self.started = True
    def close(self): self.closed = True; return True


class EmbeddedParityTests(unittest.TestCase):
    def test_sources_are_exact_reviewed_baseline_and_resource_code(self):
        folder = ROOT/'scripts/andrea'
        self.assertEqual(probe.BASELINE_SOURCE, (folder/'web_type_latency_probe.py').read_text())
        self.assertEqual(probe.RESOURCE_SOURCE, (folder/'latency_resource_diagnostic.py').read_text())
        standalone = (folder/'web_request_resource_profile.py').read_text()
        body = (folder/'web_request_resource_profile_body.py').read_text().replace('from __future__ import annotations\n', '')
        self.assertTrue(standalone.endswith(body))
        self.assertEqual(probe.baseline.EXPECTED, preceding.EXPECTED)

    def test_baseline_source_question_schema_and_options_are_not_changed(self):
        before = preceding.baseline_prepare(CSV, preceding.CASES[1]['question'])
        self.assertEqual(probe.baseline.baseline_prepare(CSV, probe.baseline.CASES[1]['question']), before)
        self.assertEqual(probe.baseline.CASES, preceding.CASES)
        self.assertEqual(probe.SAMPLE_SECONDS, (6, 18, 36))
        self.assertEqual(probe.MODEL_WORKER_DEADLINE_SECONDS, 95)

    def test_existing_rejections_and_actual_mechanism_failure_are_retained(self):
        for text, quote in ((GOOD, CSV), (OBSERVED_DECIMAL, CSV),
                            ("asyncio consente di gestire sottoprocessi attraverso un'interfaccia specifica.",
                             'control subprocesses;\n')):
            raw = json.dumps({'claims': [{'passage': 1, 'text': text}]})
            self.assertEqual(probe.stricter_checks(raw, [quote], True, heading_ranges=[]),
                             mechanism.validate(raw, [quote], True, heading_ranges=[]))


class OwnedBoundaryTests(unittest.TestCase):
    def test_one_worker_exact_page_no_shell_no_retry_and_observer_cleanup(self):
        child = Child(); observers = []
        def observer(worker):
            value = StubObserver(worker); observers.append(value); return value
        with patch.object(probe.subprocess, 'Popen', return_value=child) as create:
            value, rows, errors, cleaned = probe.collect(Path('project'), page(), popen=create, observer_factory=observer)
        self.assertEqual(create.call_count, 1)
        self.assertEqual(create.call_args.args[0][-1], '--model-worker')
        self.assertNotIn('shell', create.call_args.kwargs)
        self.assertEqual(json.loads(child.calls[0][0]), page())
        self.assertEqual(child.calls[0][1], 95)
        self.assertEqual(child.kills, 0); self.assertTrue(cleaned)
        self.assertTrue(observers[0].started); self.assertTrue(observers[0].closed)
        self.assertEqual(value, worker_value()); self.assertEqual(errors, [])
        self.assertEqual(len(rows), 1)

    def test_deadline_terminates_only_owned_worker_and_has_unknown_inference_count(self):
        child = Child(timeout=True)
        value, _, _, cleaned = probe.collect(Path('project'), page(), popen=lambda *a, **k: child, observer_factory=StubObserver)
        self.assertEqual(child.kills, 1); self.assertTrue(cleaned)
        self.assertEqual(child.calls[1], (None, 2))
        self.assertEqual(value['result']['errorKind'], 'owned_worker_deadline')
        self.assertIsNone(value['requestStartedMonotonic'])

    def test_interrupt_cleans_owned_model_and_observer_without_retry(self):
        child = Child()
        original = child.communicate
        calls = 0
        def interrupt(*a, **k):
            nonlocal calls
            calls += 1
            if calls == 1: raise KeyboardInterrupt()
            return original(*a, **k)
        child.communicate = interrupt
        observer = StubObserver(child)
        with self.assertRaises(KeyboardInterrupt):
            probe.collect(Path('project'), page(), popen=lambda *a, **k: child,
                          observer_factory=lambda _: observer)
        self.assertEqual(child.kills, 1); self.assertTrue(observer.closed)

    def test_malformed_oversized_and_duplicate_worker_results_are_not_retried_or_leaked(self):
        for raw in (b'invalid /Users/private/secret', b'x'*65537,
                    b'{"result":{},"result":{}}', b'{"result":{}}'):
            child = Child(raw=raw)
            value, _, _, _ = probe.collect(Path('project'), page(), popen=lambda *a, **k: child, observer_factory=StubObserver)
            self.assertEqual(len(child.calls), 1)
            self.assertEqual(value['result']['status'], 'error')
            self.assertNotIn('private', json.dumps(value)); self.assertNotIn('secret', json.dumps(value))

    def test_oversized_page_refused_before_starting_worker(self):
        changed = page(); changed['text'] = 'x'*65537
        with self.assertRaises(ValueError):
            probe.collect(Path('project'), changed, popen=lambda *a, **k: self.fail('unexpected child'))

    def test_worker_times_and_nonfinite_values_are_refused(self):
        for start, end in ((True, 165), (100, 99), (100, 196), (float('nan'), 165), (100, float('inf'))):
            value = worker_value(); value['requestStartedMonotonic'] = start; value['requestFinishedMonotonic'] = end
            with self.assertRaises(ValueError): probe.validate_worker(value)


class ObservationTests(unittest.TestCase):
    def test_all_queries_reuse_readonly_whitelist_and_sanitized_parsers(self):
        commands = []
        outputs = {('/usr/bin/vm_stat',): resource_tests.VM,
                   ('/usr/bin/pmset', '-g', 'therm'): resource_tests.THERM,
                   ('/usr/bin/pgrep', '-x', 'ollama'): '123\n',
                   ('/usr/bin/pgrep', '-x', 'ollama_llama_server'): '',
                   ('/bin/ps', '-p', '123', '-o', 'pcpu=,command='): resource_tests.PS,
                   ('/usr/bin/top', '-l', '2', '-s', '1', '-n', '0', '-R', '-F'): resource_tests.TOP,
                   ('/usr/sbin/sysctl', '-n', 'vm.loadavg'): '{ 2.0 3.0 4.0 }',
                   ('/usr/sbin/sysctl', '-n', 'vm.swapusage'): 'used = 0.00M'}
        def runner(cmd, **kwargs):
            commands.append(cmd)
            self.assertTrue(probe.resources.allowed_command(cmd))
            self.assertLessEqual(kwargs['timeout'], 1.5)
            return SimpleNamespace(returncode=0, stdout=outputs[tuple(cmd)])
        opener = resource_tests.Opener([resource_tests.Response(b'{"models":[]}')])
        reader = probe.WindowReader(threading.Event(), runner=runner, opener=opener)
        measured = probe.snapshot(threading.Event(), reader=reader)
        self.assertEqual(len(opener.calls), 1); self.assertEqual(opener.calls[0][0].get_method(), 'GET')
        self.assertEqual(measured['vmCounterDeltasPages']['Swapouts'], 0)
        self.assertEqual(measured['thermalLimits']['CPU_Speed_Limit'], 75)
        self.assertNotIn('secret', json.dumps(measured)); self.assertNotIn('private', json.dumps(measured))
        self.assertEqual(len(commands), 9)

    def test_sample_deadline_and_cancelled_reads_have_no_commands(self):
        stop = threading.Event(); clock = [100.]
        reader = probe.WindowReader(stop, clock=lambda: clock[0])
        clock[0] = 108.
        with self.assertRaises(TimeoutError): reader.timeout()
        clock[0] = 100.; stop.set()
        with self.assertRaises(TimeoutError): reader.timeout()

    def test_samples_before_during_after_request_do_not_claim_native_prefill_or_causality(self):
        rows = [{'startedMonotonic': a, 'finishedMonotonic': b} for a, b in
                ((99, 101), (110, 112), (148, 151), (163, 166))]
        measured = probe.classify_samples(rows, worker_value())
        self.assertEqual([r['entirelyWithinClientRequest'] for r in measured], [False, True, True, False])
        self.assertEqual([r['entirelyBeforeFirstJsonArrival'] for r in measured], [False, True, False, False])
        self.assertTrue(all(not r['nativePrefillPhaseProven'] for r in measured))
        self.assertNotIn('startedMonotonic', measured[0]); self.assertIn('startedMonotonic', rows[0])
        unknown = probe.classify_samples(rows, probe.worker_error('timeout'))
        self.assertTrue(all(r['startedClientOffsetMs'] is None for r in unknown))
        self.assertTrue(all(r['entirelyBeforeFirstJsonArrival'] is None for r in unknown))

    def test_observer_stops_immediately_after_request_finishes_or_on_close(self):
        child = Child(); child.returncode = 0
        with patch.object(probe, 'SAMPLE_SECONDS', (0, 0, 0)):
            observer = probe.Observer(child, sampler=lambda _: self.fail('sample after completion'))
            observer.start(); self.assertTrue(observer.close()); self.assertEqual(observer.rows, [])

    def test_three_fixed_observations_are_finite_and_errors_are_sanitized(self):
        child = Child(); count = 0
        def sampler(stop):
            nonlocal count
            count += 1
            if count == 2: raise OSError('/Users/private/secret')
            return {'startedMonotonic': 100., 'finishedMonotonic': 101.}
        with patch.object(probe, 'SAMPLE_SECONDS', (0, 0, 0)):
            observer = probe.Observer(child, sampler=sampler)
            observer.thread.start(); observer.thread.join(timeout=1)
            self.assertFalse(observer.thread.is_alive()); self.assertEqual(count, 3)
            self.assertEqual(len(observer.rows), 2); self.assertEqual(len(observer.errors), 1)
            self.assertNotIn('private', json.dumps(observer.errors))


class ProfileTests(unittest.TestCase):
    def before(self, version='0.35.1', count=0, expected=False):
        return {'ollamaVersion': version, 'loadedModels': {'loadedModelCount': count, 'expectedModelLoaded': expected}}

    def test_run_requests_one_baseline_and_has_no_performance_adoption_verdict(self):
        output = []
        with patch.object(probe.platform, 'system', return_value='Darwin'), patch.object(probe.baseline, 'verify_project'), \
                patch.object(probe.resources, 'run', return_value=self.before()), \
                patch.object(probe.baseline, 'read_heading_page', return_value=page()) as read, \
                patch.object(probe, 'collect', return_value=(worker_value(), [], [], True)) as generate, \
                patch.object(probe.resources.Reader, 'get', return_value={'version': '0.35.1'}):
            report = probe.run(Path('project'), emit=output.append)
        self.assertEqual(generate.call_count, 1); self.assertEqual(read.call_count, 1)
        self.assertEqual(report['modelInferenceRequests'], 1); self.assertEqual(report['modelInferenceRequestsLimit'], 1)
        self.assertEqual(report['question'], preceding.CASES[1]['question'])
        self.assertTrue(report['versionUnchanged']); self.assertTrue(report['fullSourcePreserved'])
        self.assertFalse(report['modelOptionsChanged']); self.assertFalse(report['productionModified'])
        self.assertFalse(report['vaultRead']); self.assertEqual(report['automaticRetries'], 0)
        self.assertEqual(report['performanceVerdict'], 'diagnostic_only_no_ab_comparison')
        self.assertEqual(report['qualityVerdict'], 'pending_review'); self.assertFalse(report['integrationAllowed'])
        self.assertEqual(report['checks']['outcome'], 'accepted_pending_semantic_review')
        self.assertIn('Profilo finito', output[-1])

    def test_wrong_version_platform_unknown_or_other_loaded_model_refuses_before_inference(self):
        for state in (self.before('0.35.2'), self.before(count=None), self.before(count=1), self.before(count=2)):
            with patch.object(probe.platform, 'system', return_value='Darwin'), patch.object(probe.baseline, 'verify_project'), \
                    patch.object(probe.resources, 'run', return_value=state), patch.object(probe, 'collect') as generate:
                with self.assertRaises(ValueError): probe.run(Path('project'), emit=lambda _: None)
            generate.assert_not_called()
        with patch.object(probe.platform, 'system', return_value='Linux'), patch.object(probe.resources, 'run') as read:
            with self.assertRaises(ValueError): probe.run(Path('project'))
        read.assert_not_called()

    def test_page_guard_rejects_missing_scope_roles_or_other_destination(self):
        for altered in ({**page(), 'url': 'https://elsewhere.example/'}, {**page(), 'text': 'No relevant context whatsoever in this source.'},
                        {key: value for key, value in page().items() if key != 'headingRanges'}):
            with self.assertRaises(ValueError): probe.checked_csv(altered)

    def test_model_worker_is_one_post_with_the_exact_baseline_options(self):
        calls = []
        answer = json.dumps({'claims': [{'text': GOOD, 'passage': 1}]})
        native = {'total_duration': 65000000000, 'load_duration': 4000000000,
                  'prompt_eval_duration': 50000000000, 'eval_duration': 11000000000,
                  'prompt_eval_count': 2441, 'prompt_eval_cached_count': 0, 'eval_count': 60}
        class Response:
            def __init__(self):
                self.lines = iter([json.dumps({'message': {'content': answer}, 'done': False}).encode()+b'\n',
                                   json.dumps({'done': True, 'done_reason': 'stop', **native}).encode()+b'\n'])
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def readline(self, limit): return next(self.lines, b'')
        class Opener:
            def open(self, request, **kwargs): calls.append((request, kwargs)); return Response()
        output = io.StringIO()
        stdin = SimpleNamespace(buffer=io.BytesIO(json.dumps(page()).encode()))
        with patch.object(probe.baseline, 'verify_project'), patch.object(probe.sys, 'stdin', stdin), \
                patch.object(probe.baseline.urllib.request, 'build_opener', return_value=Opener()), contextlib.redirect_stdout(output):
            probe.model_worker(Path('project'))
        value = json.loads(output.getvalue())
        self.assertEqual(len(calls), 1)
        request = calls[0][0]; body = json.loads(request.data)
        self.assertEqual(request.full_url, 'http://127.0.0.1:11434/api/chat')
        self.assertEqual(request.get_method(), 'POST')
        self.assertEqual(body['options'], {'temperature': .4, 'num_predict': 512, 'num_ctx': 4096})
        self.assertEqual(body['keep_alive'], '15m'); self.assertIs(body['think'], False)
        self.assertEqual(body['model'], preceding.MODEL)
        original = preceding.baseline_prepare(CSV, preceding.CASES[1]['question'])
        self.assertEqual(body['messages'][1], original[1][1]); self.assertTrue(body['messages'][0]['content'].endswith(original[1][0]['content']))
        self.assertEqual(body['format'], original[2]); self.assertEqual(value['result']['modelAnswer'], answer)


if __name__ == '__main__': unittest.main()
