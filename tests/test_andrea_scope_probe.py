"""Finite synthetic transport comparison; no semantic model judge."""
import importlib.util
import io
import json
from pathlib import Path
import unittest
from andrea_historical_runtime import historical_messages
from contextlib import redirect_stdout

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('scope_probe', ROOT / 'scripts/andrea/scope_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class Response(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *args): self.close()


class Opener:
    def __init__(self, events=None): self.requests = []; self.events = events
    def open(self, request, timeout):
        self.requests.append(json.loads(request.data))
        events = self.events if self.events is not None else [
            {'message': {'content': 'Risposta sintetica [N1] [N2].'}},
            {'done': True, 'done_reason': 'stop', 'eval_count': 8,
             'eval_duration': 1000000000, 'private_key': 'PRIVATE'}]
        return Response(b''.join(json.dumps(e).encode()+b'\n' for e in events))


class ScopeProbeTests(unittest.TestCase):
    def test_paired_payloads_only_change_system_and_never_mutate_runtime(self):
        runtime = ROOT / 'scripts/andrea/runtime.py'
        before = runtime.read_bytes()
        make = historical_messages(probe, ROOT)
        opener = Opener()
        with redirect_stdout(io.StringIO()): result = probe.collect(opener, make)
        self.assertEqual(len(opener.requests), 12)
        self.assertEqual(runtime.read_bytes(), before)
        for i, case in enumerate(probe.CASES):
            pair = opener.requests[i*2:i*2+2]
            rows = result['rows'][i*2:i*2+2]
            self.assertEqual({r['prompt'] for r in rows}, {'current', 'candidate'})
            self.assertEqual(pair[0]['messages'][1:], pair[1]['messages'][1:])
            for payload, row in zip(pair, rows):
                self.assertEqual(payload['model'], probe.MODEL)
                self.assertEqual(payload['options'], {'temperature': .4, 'num_predict': 512, 'num_ctx': 4096})
                self.assertEqual(payload['keep_alive'], '15m')
                self.assertIs(payload['think'], False)
                expected = make(case['query'], case['sources'])[0]['content']
                if row['prompt']=='candidate': expected += probe.CANDIDATE_ADDENDUM
                self.assertEqual(payload['messages'][0]['content'], expected)
        self.assertTrue(all(r['qualityVerdict']=='pending_review' for r in result['rows']))
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertIs(result['runtimeChanged'], False)
        self.assertIs(result['deterministicGuardsExercised'], False)

    def test_formal_success_does_not_certify_known_semantic_failure(self):
        case = next(c for c in probe.CASES if c['id']=='historical')
        bad = {'status': 'completed', 'syntheticAnswer': 'Il problema è risolto [N1]. Nessun problema esiste [N1].'}
        self.assertTrue(all(probe.formal_checks(case, bad).values()))
        self.assertIn('pending_semantic_review', probe.report([])['decision'])

    def test_error_stops_finite_collection_without_retry_or_error_leak(self):
        opener = Opener([{'error': 'PRIVATE'}])
        with redirect_stdout(io.StringIO()): result = probe.collect(opener, historical_messages(probe, ROOT))
        self.assertEqual(len(opener.requests), 1)
        self.assertEqual(result['attempted'], 1)
        self.assertEqual(result['automaticRetries'], 0)
        self.assertEqual(result['rows'][0]['status'], 'error')
        self.assertNotIn('PRIVATE', json.dumps(result))

    def test_no_native_counters_incomplete_truncated_and_limits(self):
        cases = [([], 'incomplete'), ([{'message': {'content':'text'}}, {'done':True,'done_reason':'length'}], 'truncated'),
                 ([{'done':True,'done_reason':'stop'}], 'incomplete')]
        for events, status in cases:
            self.assertEqual(probe.stream_probe(Opener(events), [])['status'], status)
        complete = probe.stream_probe(Opener([{'message':{'content':'text [N1]'}},{'done':True,'done_reason':'stop'}]), [])
        self.assertEqual(complete['status'], 'completed')
        self.assertIsNone(complete['native']['evalTokensPerSecond'])
        huge = probe.stream_probe(Opener([{'message':{'content':'x'*32001}}]), [])
        self.assertEqual(huge['status'], 'error')
        self.assertIsNone(huge['syntheticAnswer'])

    def test_changed_runtime_refused_before_network(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            file = root / 'scripts/andrea/runtime.py'
            file.parent.mkdir(parents=True); file.write_text('raise RuntimeError("must not run")')
            with self.assertRaises(ValueError): probe.messages_from_runtime(root)

    def test_actual_http_twelve_streams_and_synthetic_inputs_only(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from threading import Thread
        from urllib.request import build_opener, ProxyHandler
        calls = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                calls.append(body)
                self.send_response(200); self.end_headers()
                for event in ({'message':{'content':'Synthetic [N1] [N2]'}}, {'done':True,'done_reason':'stop'}):
                    self.wfile.write(json.dumps(event).encode()+b'\n'); self.wfile.flush()
        server = ThreadingHTTPServer(('127.0.0.1',0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True); thread.start()
        previous = probe.BASE
        try:
            probe.BASE = f'http://127.0.0.1:{server.server_port}'
            with redirect_stdout(io.StringIO()): result = probe.collect(build_opener(ProxyHandler({})), historical_messages(probe, ROOT))
            self.assertEqual(len(calls), 12)
            self.assertTrue(all(r['status']=='completed' for r in result['rows']))
            self.assertIs(result['vaultRead'], False)
            self.assertTrue(all(len(c['messages'])==2 for c in calls))
        finally:
            probe.BASE = previous; server.shutdown(); server.server_close(); thread.join()


if __name__ == '__main__': unittest.main()
