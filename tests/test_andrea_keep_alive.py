"""Exercise actual engine methods with isolated transports; no real inference."""
import ast
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
import importlib.util

ROOT = Path(__file__).resolve().parents[1]


def engine_class():
    tree = ast.parse((ROOT / 'src/openjarvis/engine/ollama.py').read_text())
    engine = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'OllamaEngine')
    methods = [n for n in engine.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name in ('generate', 'stream', 'stream_full')]
    options = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_ollama_request_options')
    isolated = ast.ClassDef(name='Engine', bases=[], keywords=[], body=methods, decorator_list=[])
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), options, isolated], type_ignores=[])
    namespace = {'json': json, 'messages_to_dicts': lambda m: [dict(v) for v in m],
                 'estimate_prompt_tokens': lambda m: 10, '_default_num_ctx': lambda: 4096,
                 'httpx': SimpleNamespace(ConnectError=ConnectionError, TimeoutException=TimeoutError, HTTPStatusError=RuntimeError),
                 'STREAM_TRANSPORT_ERRORS': (ConnectionError, TimeoutError), 'EngineConnectionError': ConnectionError}
    exec(compile(ast.fix_missing_locations(module), 'actual_ollama_methods', 'exec'), namespace)
    return namespace['Engine']


class Response:
    status_code = 200
    is_success = True
    def raise_for_status(self):
        pass
    def json(self):
        return {'message': {'content': 'synthetic'}, 'eval_count': 1, 'prompt_eval_count': 10}
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass
    async def aiter_lines(self):
        yield json.dumps({'message': {'content': 'synthetic'}})
        yield json.dumps({'done': True, 'eval_count': 1, 'prompt_eval_count': 10})


class Transport:
    def __init__(self):
        self.payloads = []
    def post(self, path, *, json):
        self.payloads.append(json)
        return Response()
    def stream(self, method, path, *, json):
        self.payloads.append(json)
        return Response()


def bounded_class():
    tree = ast.parse((ROOT / 'scripts/andrea/runtime.py').read_text())
    build = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'build_app')
    klass = next(n for n in build.body if isinstance(n, ast.ClassDef) and n.name == 'BudgetOllama')
    namespace = {'OllamaEngine': engine_class()}
    exec(compile(ast.Module(body=[klass], type_ignores=[]), 'actual_budget_ollama', 'exec'), namespace)
    return namespace['BudgetOllama']


class KeepAliveTests(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, cls, kwargs):
        engine = cls()
        transport = Transport()
        engine._client = transport
        engine._get_async_client = lambda: transport
        async def run_stream(payload, messages, **kwargs):
            transport.payloads.append(payload)
            yield 'rich-synthetic'
        engine._run_stream = run_stream
        messages = [{'role': 'system', 'content': 'unchanged prompt'}, {'role': 'user', 'content': 'unchanged question'}]
        engine.generate(messages, model='selected', **kwargs)
        self.assertEqual([v async for v in engine.stream(messages, model='selected', **kwargs)], ['synthetic'])
        self.assertEqual([v async for v in engine.stream_full(messages, model='selected', **kwargs)], ['rich-synthetic'])
        self.assertEqual(len(transport.payloads), 3)
        for payload in transport.payloads:
            self.assertEqual(payload['messages'], messages)
            self.assertEqual(payload['model'], 'selected')
        return transport.payloads

    async def test_all_engine_paths_forward_top_level_keep_alive(self):
        for value in ('15m', 0, 900):
            payloads = await self.exercise(engine_class(), {'keep_alive': value})
            for payload in payloads:
                self.assertEqual(payload['keep_alive'], value)
                self.assertNotIn('keep_alive', payload['options'])

    async def test_unspecified_and_none_preserve_other_callers(self):
        for kwargs in ({}, {'keep_alive': None}):
            payloads = await self.exercise(engine_class(), kwargs)
            for payload in payloads:
                self.assertNotIn('keep_alive', payload)

    async def test_local_budget_forces_retention_and_preserves_generation_parameters(self):
        payloads = await self.exercise(bounded_class(), {'keep_alive': 0, 'think': True,
                                  'temperature': 1, 'max_tokens': 9999, 'num_ctx': 64000})
        for payload in payloads:
            self.assertEqual(payload['keep_alive'], '15m')
            self.assertEqual(payload['options'], {'temperature': .4, 'num_predict': 512, 'num_ctx': 4096})
            self.assertIs(payload['think'], False)

    def test_production_prompt_unchanged_from_verified_baseline(self):
        import hashlib
        # The only runtime difference must be this one optional retention value.
        data = (ROOT / 'scripts/andrea/runtime.py').read_text()
        old = data.replace(', "keep_alive": "15m"}', '}')
        self.assertEqual(hashlib.sha256(old.encode()).hexdigest(), 'af38a56db92227dc2e2f4034792cc4cd474c161b034a9368c62477478c42f68c')

    def test_reuse_check_keeps_two_requests_and_semantic_review_pending(self):
        spec = importlib.util.spec_from_file_location('reuse_check', ROOT / 'scripts/andrea/check_reuse.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        calls = []
        def run(payload, **kwargs):
            calls.append(payload)
            self.assertTrue(kwargs['keep_answer'])
            self.assertEqual(payload['notes_sources'], [module.SOURCE])
            return {'done': True, 'finishReason': 'stop', 'firstTextClientMs': 5,
                    'totalClientMs': 10, 'answer': 'synthetic',
                    'server': {'id': 'PRIVATE_ID', 'kind': 'notes', 'status': 'completed',
                               'answerMode': 'model_synthesis', 'inferenceUsed': True}}
        report = module.collect(run, observe=lambda: {'available': True, 'selectedModelLoaded': True, 'remainingSeconds': 899})
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(r['completed'] and r['expectedPathObserved'] and r['retentionOverTenMinutesObserved'] for r in report['rows']))
        self.assertTrue(all(r['qualityVerdict'] == 'pending_review' for r in report['rows']))
        self.assertNotIn('PRIVATE', json.dumps(report))

    def test_reuse_check_errors_missing_expiry_do_not_become_success_or_retry(self):
        spec = importlib.util.spec_from_file_location('reuse_check_errors', ROOT / 'scripts/andrea/check_reuse.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        calls = []
        def run(payload, **kwargs):
            calls.append(payload)
            raise ValueError('PRIVATE DETAIL')
        report = module.collect(run, observe=lambda: {'available': False, 'selectedModelLoaded': None, 'remainingSeconds': None})
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(not r['completed'] and not r['retentionOverTenMinutesObserved'] for r in report['rows']))
        self.assertNotIn('PRIVATE', json.dumps(report))


if __name__ == '__main__':
    unittest.main()
