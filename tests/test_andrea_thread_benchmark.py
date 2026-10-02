"""Finite protocol comparison tests, with synthetic streams only."""
import importlib.util
import io
import json
from pathlib import Path
import unittest
from andrea_historical_runtime import historical_messages
from contextlib import redirect_stdout

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('thread_benchmark', ROOT / 'scripts/andrea/thread_benchmark.py')
bench = importlib.util.module_from_spec(spec); spec.loader.exec_module(bench)


class Response(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *args): self.close()


class Opener:
    def __init__(self, fail=False): self.requests = []; self.fail = fail
    def open(self, request, timeout):
        if isinstance(request, str):
            return Response(b'{"models": []}')
        body = json.loads(request.data); self.requests.append(body)
        if self.fail: return Response(b'{"error": "PRIVATE ERROR"}\n')
        setting = body['options'].get('num_thread')
        rate = {None: 8, 4: 10, 8: 9}[setting]
        events = [{'message': {'content': 'Problema risolto nella fonte [N1].'}},
                  {'done': True, 'done_reason': 'stop', 'eval_count': rate,
                   'eval_duration': 1000000000, 'prompt_eval_count': 567,
                   'message': {'content': ''}, 'private_id': 'PRIVATE'}]
        return Response(b''.join(json.dumps(e).encode()+b'\n' for e in events))


class ThreadBenchmarkTests(unittest.TestCase):
    def test_exact_balanced_nine_calls_default_last_and_parameters_unchanged(self):
        opener = Opener(); messages = historical_messages(bench, ROOT)
        with redirect_stdout(io.StringIO()): report = bench.collect(opener, messages)
        self.assertEqual(len(opener.requests), 9)
        self.assertEqual([r['options'].get('num_thread') for r in opener.requests], list(bench.ORDER))
        for setting in (None,4,8): self.assertEqual(list(bench.ORDER).count(setting), 3)
        self.assertNotIn('num_thread', opener.requests[-1]['options'])
        for body in opener.requests:
            self.assertEqual(body['messages'], messages)
            self.assertEqual(body['model'], bench.MODEL)
            self.assertEqual(body['keep_alive'], '15m')
            self.assertIs(body['think'], False)
            self.assertEqual({k:v for k,v in body['options'].items() if k!='num_thread'}, {'temperature': .4,'num_predict':512,'num_ctx':4096})
        self.assertEqual(report['summary']['automatic']['medianEvalTokensPerSecond'], 8)
        self.assertEqual(report['summary']['4']['gainVsAutomaticPercent'], 25)
        self.assertTrue(report['summary']['4']['meetsExploratorySpeedThreshold'])
        self.assertFalse(report['summary']['8']['meetsExploratorySpeedThreshold'])
        self.assertEqual(report['decision'], 'not_adopted_requires_quality_review_and_server_validation')
        self.assertTrue(report['finalAutomaticRequestCompleted'])
        self.assertNotIn('PRIVATE', json.dumps(report))

    def test_errors_preserved_without_retry_or_fake_zero_or_adoption(self):
        opener=Opener(fail=True)
        with redirect_stdout(io.StringIO()): report=bench.collect(opener, [])
        self.assertEqual(len(opener.requests),9)
        self.assertFalse(report['finalAutomaticRequestCompleted'])
        for group in report['summary'].values():
            self.assertEqual(group['excluded'],3)
            self.assertIsNone(group['medianEvalTokensPerSecond'])
        self.assertNotIn('PRIVATE',json.dumps(report))

    def test_missing_native_metrics_and_incomplete_not_included(self):
        row={'status':'completed','native':{},'numThreadRequested':None}
        result=bench.summarize([row,{'status':'incomplete','native':{'evalTokensPerSecond':50,'eval_count':100},'numThreadRequested':4}])
        self.assertEqual(result['automatic']['included'],0)
        self.assertFalse(result['4']['meetsExploratorySpeedThreshold'])

    def test_invalid_thread_rejected_before_any_request(self):
        opener=Opener()
        for value in (True,0,16,-1,'4'):
            with self.assertRaises(ValueError): bench.stream_probe(opener,[],num_thread=value)
        self.assertEqual(opener.requests,[])

    def test_empty_final_and_truncation_not_success(self):
        class Empty:
            def open(self,*args,**kwargs): return Response(b'{"done":true,"done_reason":"stop"}\n')
        self.assertEqual(bench.stream_probe(Empty(),[])['status'],'incomplete')
        class Truncated:
            def open(self,*args,**kwargs): return Response(b'{"message":{"content":"text"}}\n{"done":true,"done_reason":"length"}\n')
        self.assertEqual(bench.stream_probe(Truncated(),[])['status'],'truncated')

    def test_real_http_nine_streams_with_native_counters(self):
        from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
        from threading import Thread
        from urllib.request import build_opener,ProxyHandler
        calls=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                self.send_response(200);self.end_headers();self.wfile.write(b'{"models":[]}')
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));calls.append(body)
                self.send_response(200);self.send_header('Content-Type','application/x-ndjson');self.end_headers()
                for event in ({'message':{'content':'synthetic [N1]'}},
                              {'done':True,'done_reason':'stop','eval_count':86,'eval_duration':10000000000}):
                    self.wfile.write(json.dumps(event).encode()+b'\n');self.wfile.flush()
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=Thread(target=server.serve_forever,daemon=True);thread.start();previous=bench.BASE
        try:
            bench.BASE=f'http://127.0.0.1:{server.server_port}'
            with redirect_stdout(io.StringIO()): report=bench.collect(build_opener(ProxyHandler({})),historical_messages(bench, ROOT))
            self.assertEqual(len(calls),9)
            self.assertTrue(all(r['status']=='completed' for r in report['rows']))
            self.assertTrue(all(g['included']==3 for g in report['summary'].values()))
        finally:
            bench.BASE=previous;server.shutdown();server.server_close();thread.join()

    def test_response_limits_and_invalid_native_numbers(self):
        class Huge:
            def open(self,*args,**kwargs): return Response(b'x'*262145)
        self.assertEqual(bench.stream_probe(Huge(),[])['status'],'error')
        result=bench.native_metrics({'eval_duration':float('nan'),'eval_count':True,'load_duration':-1})
        self.assertTrue(all(v is None for v in result.values()))


if __name__ == '__main__': unittest.main()
