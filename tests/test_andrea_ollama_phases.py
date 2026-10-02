"""Protocol and privacy checks for the diagnostic; no real Ollama inference."""
import importlib.util
import io
import json
from pathlib import Path

import unittest
import tempfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ollama_phases', ROOT / 'scripts/andrea/ollama_phases.py')
diag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diag)


class Response(io.BytesIO):
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()


class Opener:
    def __init__(self, events):
        self.events, self.requests = events, []
    def open(self, request, timeout):
        self.requests.append(request)
        if isinstance(request, str):
            return Response(json.dumps({'models': [
                {'name': 'PRIVATE_OTHER_MODEL', 'digest': 'PRIVATE', 'size': 123},
                {'name': diag.MODEL, 'context_length': 4096, 'size': 250, 'size_vram': 0}]}).encode())
        return Response(b''.join(json.dumps(e).encode() + b'\n' for e in self.events))


def done(reason='stop'):
    return {'done': True, 'done_reason': reason, 'message': {'content': ''},
            'load_duration': 2_000_000, 'prompt_eval_duration': 3_000_000,
            'eval_duration': 5_000_000, 'total_duration': 11_000_000,
            'prompt_eval_count': 100, 'eval_count': 2, 'secret': 'PRIVATE'}


def test_completed_native_units_and_content_discarded():
    opener = Opener([{'message': {'content': 'PRIVATE ANSWER'}}, done()])
    result = diag.stream_probe(opener, [{'role': 'user', 'content': 'PRIVATE PROMPT'}])
    assert result['status'] == 'completed'
    assert result['native']['loadMs'] == 2
    assert result['native']['evalTokensPerSecond'] == 400
    assert result['native']['prompt_eval_cached_count'] is None
    assert 'PRIVATE' not in json.dumps(result)
    body = json.loads(opener.requests[0].data)
    assert body['think'] is False and body['stream'] is True
    assert body['options'] == {'temperature': .4, 'num_ctx': 4096, 'num_predict': 512}
    assert 'keep_alive' not in body


def test_invalid_and_incomplete_stream_not_success():
    cases = [([{'message': {'content': 'text'}}], 'incomplete'),
             ([done()], 'incomplete'),
             ([{'message': {'content': 'text'}}, done('length')], 'truncated'),
             ([{'error': 'PRIVATE exception'}], 'error'),
             ([{'message': None}], 'error')]
    for events, status in cases:
        result = diag.stream_probe(Opener(events), [])
        assert result['status'] == status
        assert 'PRIVATE' not in json.dumps(result)


def test_three_requests_no_retry_even_after_error():
    opener = Opener([{'error': 'PRIVATE'}])
    result = diag.collect(opener, [])
    assert len(result['rows']) == 3
    assert len([r for r in opener.requests if not isinstance(r, str)]) == 3
    assert all(r['status'] == 'error' for r in result['rows'])
    assert 'PRIVATE' not in json.dumps(result)


def test_missing_native_values_are_not_zero_and_invalid_filtered():
    result = diag.native_metrics({'eval_count': True, 'load_duration': -1, 'eval_duration': float('nan')})
    assert all(v is None for v in result.values())


def test_model_snapshot_filters_other_models_and_private_metadata():
    result = diag.loaded_snapshot(Opener([]))
    assert result['selectedModelLoaded'] is True
    assert result['contextLength'] == 4096
    assert 'PRIVATE' not in json.dumps(result)


def test_verified_prompt_uses_real_function_without_importing_runtime():
    # This diagnostic deliberately pins the pre-retention runtime. Reconstruct
    # that public fixture; the live application may have the retention update.
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp) / 'scripts/andrea'
        folder.mkdir(parents=True)
        original = (ROOT / 'tests/fixtures/runtime-before-structured.txt').read_text().replace(', "keep_alive": "15m"}', '}')
        (folder / 'runtime.py').write_text(original)
        messages = diag.messages_from_runtime(Path(tmp))
    assert messages[0]['role'] == 'system'
    assert 'massimo sei frasi' in messages[0]['content']
    assert json.loads(messages[1]['content']) == {'richiesta': diag.QUERY, 'estratti': [diag.SOURCE]}


def test_changed_runtime_refused_before_execution():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp) / 'scripts/andrea'
        folder.mkdir(parents=True)
        (folder / 'runtime.py').write_text('raise RuntimeError("must not execute")')
        with unittest.TestCase().assertRaises(ValueError):
            diag.messages_from_runtime(Path(tmp))


def test_oversize_line_and_deadline_are_errors():
    class Huge:
        def open(self, *args, **kwargs):
            return Response(b'x' * 262145)
    assert diag.stream_probe(Huge(), [])['status'] == 'error'
    times = iter([0, 0, 91, 91])
    assert diag.stream_probe(Opener([done()]), [], clock=lambda: next(times))['status'] == 'error'


def test_real_http_three_streams_and_read_only_snapshots():
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread
    from urllib.request import build_opener, ProxyHandler
    calls = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            assert self.path == '/api/ps'
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"models": []}')
        def do_POST(self):
            assert self.path == '/api/chat'
            calls.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            self.send_response(200)
            self.send_header('Content-Type', 'application/x-ndjson')
            self.end_headers()
            for event in ({'message': {'content': 'simulated'}}, done()):
                self.wfile.write(json.dumps(event).encode() + b'\n')
                self.wfile.flush()
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    previous = diag.BASE
    try:
        diag.BASE = f'http://127.0.0.1:{server.server_port}'
        messages = [{'role': 'system', 'content': 'synthetic'}, {'role': 'user', 'content': 'synthetic'}]
        result = diag.collect(build_opener(ProxyHandler({})), messages)
        assert len(calls) == 3
        assert all(row['status'] == 'completed' for row in result['rows'])
        assert all(row['loadedBefore']['selectedModelLoaded'] is False for row in result['rows'])
        assert all(call['messages'] == messages for call in calls)
    finally:
        diag.BASE = previous
        server.shutdown()
        server.server_close()
        thread.join()


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(unittest.FunctionTestCase(value) for name, value in globals().items()
                              if name.startswith('test_') and callable(value))

if __name__ == '__main__':
    unittest.main()
