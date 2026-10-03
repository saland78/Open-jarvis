"""Actual rich transport and ASGI collector, synthetic data, no real Ollama."""
import ast
import asyncio
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/andrea'))
import native_metrics as native
from measurements import RequestMeasurement
import read_native_phases as reader
from test_andrea_keep_alive import engine_class, bounded_class
import test_andrea_note_facts as note_tests
from test_andrea_real_notes_synthesis import answer

FRAME = {'done': True, 'done_reason': 'stop', 'total_duration': 12_000_000_000,
         'load_duration': 2_000_000_000, 'prompt_eval_duration': 3_000_000_000,
         'eval_duration': 6_000_000_000, 'prompt_eval_count': 80,
         'prompt_eval_cached_count': 50, 'eval_count': 48,
         'message': {'content': 'PRIVATE TERMINAL'}, 'created_at': 'PRIVATE DATE',
         'model': 'PRIVATE MODEL', 'unexpected': 'PRIVATE EXTRA'}


def attach_rich_transport(cls):
    tree = ast.parse((ROOT/'src/openjarvis/engine/ollama.py').read_text())
    original = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'OllamaEngine')
    method = next(n for n in original.body if isinstance(n, ast.AsyncFunctionDef) and n.name == '_run_stream')
    control = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_is_control_token_only_args')
    namespace = cls.stream_full.__globals__
    @dataclass
    class Chunk:
        content: str | None = None
        finish_reason: str | None = None
        tool_calls: list | None = None
        usage: dict | None = None
    namespace.update(StreamChunk=Chunk, _QWEN_CONTROL_TOKENS={'/think','/no_think'})
    future = ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future, control, method], type_ignores=[])),
                 'actual_rich_transport', 'exec'), namespace)
    cls._run_stream = namespace['_run_stream']
    return cls


class Response:
    def __init__(self, frames, status=200):
        self.frames = frames; self.status_code = status; self.is_success = status == 200
        self.text = 'PRIVATE ERROR'; self.closed = False
    async def __aenter__(self): return self
    async def __aexit__(self, *args): self.closed = True
    async def aiter_lines(self):
        for frame in self.frames: yield json.dumps(frame)
    async def aread(self): return b''


class Client:
    def __init__(self, responses): self.responses = list(responses); self.payloads = []
    def stream(self, method, path, *, json):
        self.payloads.append(__import__('json').loads(__import__('json').dumps(json)))
        return self.responses.pop(0)


class NativeUnitTests(unittest.TestCase):
    def test_exact_native_units_counts_and_rate_without_content(self):
        measurement = RequestMeasurement('notes','selected')
        with native.bind(measurement): native.capture(FRAME)
        record = measurement.record['ollamaNative']
        self.assertEqual(record['loadMs'], 2000)
        self.assertEqual(record['promptEvalMs'], 3000)
        self.assertEqual(record['evalMs'], 6000)
        self.assertEqual(record['totalMs'], 12000)
        self.assertEqual(record['promptEvalCount'], 80)
        self.assertEqual(record['promptEvalCachedCount'], 50)
        self.assertEqual(record['evalTokensPerSecond'], 8)
        self.assertNotIn('PRIVATE', json.dumps(record))
        FRAME_COPY = dict(FRAME)
        with native.bind(measurement): native.capture(FRAME_COPY)
        FRAME_COPY['load_duration'] = 999
        self.assertEqual(measurement.record['ollamaNative']['loadMs'],2000)

    def test_missing_invalid_and_zero_are_not_confused(self):
        for invalid in (True, False, -1, float('nan'), float('inf'), 1.5, '3', 2**53):
            m = RequestMeasurement('notes','selected')
            with native.bind(m): native.capture({'done': True, 'load_duration': invalid, 'eval_count': invalid})
            self.assertIsNone(m.record['ollamaNative']['loadMs'])
            self.assertIsNone(m.record['ollamaNative']['evalCount'])
        m = RequestMeasurement('notes','selected')
        with native.bind(m): native.capture({'done': True, 'load_duration':0, 'eval_count':0, 'eval_duration':0})
        self.assertEqual(m.record['ollamaNative']['loadMs'],0)
        self.assertEqual(m.record['ollamaNative']['evalCount'],0)
        self.assertIsNone(m.record['ollamaNative']['evalTokensPerSecond'])
        self.assertIsNone(m.record['ollamaNative']['promptEvalCachedCount'])

    def test_nonterminal_unbound_and_exception_reset_do_not_capture(self):
        native.capture(FRAME)
        m=RequestMeasurement('notes','selected')
        with self.assertRaises(RuntimeError):
            with native.bind(m):
                for frame in ({'done':False}, {'done':1}, {'done':'true'}, None): native.capture(frame)
                raise RuntimeError('synthetic')
        native.capture(FRAME)
        self.assertFalse(m.record['ollamaNative']['terminalFrameReceived'])


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, frames, callback=native.capture, *, bounded=False, responses=None, extra=None):
        cls = engine_class()
        attach_rich_transport(cls)
        if bounded:
            local = bounded_class()
            # The AST-isolated budget class has its own base; use that actual base's rich method.
            attach_rich_transport(local.__bases__[0]); cls=local
        engine=cls(); response=Response(frames); client=Client(responses or [response])
        engine._get_async_client=lambda:client
        engine._raise_stream_http_error=lambda *args: (_ for _ in ()).throw(ConnectionError())
        kwargs = {} if callback is None else {'_native_metrics_callback': callback}
        kwargs.update(extra or {})
        m=RequestMeasurement('notes','selected')
        with native.bind(m):
            chunks=[chunk async for chunk in engine.stream_full(
                [{'role':'user','content':'Synthetic'}], model='selected', **kwargs)]
        return m, chunks, client, response

    async def test_actual_transport_callback_only_on_terminal_and_same_payload(self):
        frames=[{'message':{'content':'Synthetic JSON'}}, {**FRAME, 'message':{'content':''}}]
        m,chunks,client,response=await self.exercise(frames)
        plain,plain_chunks,plain_client,_=await self.exercise(frames, None)
        self.assertEqual([vars(c) for c in chunks],[vars(c) for c in plain_chunks])
        self.assertEqual(client.payloads,plain_client.payloads)
        self.assertEqual(len(client.payloads),1)
        self.assertNotIn('_native_metrics_callback',json.dumps(client.payloads))
        self.assertTrue(response.closed)
        self.assertEqual(m.record['ollamaNative']['evalCount'],48)
        self.assertFalse(plain.record['ollamaNative']['terminalFrameReceived'])

    async def test_budget_preserves_schema_prompt_and_options(self):
        schema={'type':'object','properties':{'fact':{'type':'string','enum':['synthetic']}},'required':['fact']}
        m,chunks,client,_=await self.exercise([{**FRAME,'message':{'content':''}}],bounded=True,
                     extra={'response_format':{'type':'json_schema','schema':schema}})
        payload=client.payloads[0]
        self.assertEqual(payload['options'],{'temperature':.4,'num_predict':512,'num_ctx':4096})
        self.assertEqual(payload['keep_alive'],'15m'); self.assertIs(payload['think'],False)
        self.assertEqual(payload['messages'],[{'role':'user','content':'Synthetic'}])
        self.assertEqual(payload['format'],schema)
        self.assertTrue(m.record['ollamaNative']['terminalFrameReceived'])

    async def test_missing_terminal_never_reuses_previous_native_result(self):
        m,*_=await self.exercise([{**FRAME,'message':{'content':''}}])
        next_m,*_=await self.exercise([{'message':{'content':'partial'}}])
        self.assertTrue(m.record['ollamaNative']['terminalFrameReceived'])
        self.assertFalse(next_m.record['ollamaNative']['terminalFrameReceived'])
        self.assertIsNone(next_m.record['ollamaNative']['loadMs'])

    async def test_broken_optional_observer_does_not_change_stream(self):
        def broken(frame): raise RuntimeError('PRIVATE FAILURE')
        _,chunks,client,_=await self.exercise([{**FRAME,'message':{'content':''}}],broken)
        self.assertEqual(chunks[-1].finish_reason,'stop'); self.assertEqual(len(client.payloads),1)

    async def test_tools_retry_keeps_existing_behavior_and_observer(self):
        responses=[Response([],400),Response([{**FRAME,'message':{'content':''}}])]
        m,chunks,client,_=await self.exercise([],responses=responses,extra={'tools':[{'type':'function'}]})
        self.assertEqual(len(client.payloads),2)
        self.assertIn('tools',client.payloads[0]); self.assertNotIn('tools',client.payloads[1])
        self.assertTrue(m.record['ollamaNative']['terminalFrameReceived'])
        self.assertEqual(chunks[-1].finish_reason,'stop')

    async def test_truncated_terminal_reports_metrics_without_becoming_stop(self):
        m,chunks,client,_=await self.exercise([{**FRAME,'done_reason':'length','message':{'content':''}}])
        self.assertTrue(m.record['ollamaNative']['terminalFrameReceived'])
        self.assertEqual(chunks[-1].finish_reason,'length'); self.assertEqual(len(client.payloads),1)

    async def test_request_contexts_stay_separate_across_tasks_and_cancel(self):
        entered=asyncio.Event(); m1=RequestMeasurement('notes','a'); m2=RequestMeasurement('notes','b')
        async def first():
            with native.bind(m1): entered.set(); await asyncio.Event().wait()
        task=asyncio.create_task(first()); await entered.wait()
        with native.bind(m2): native.capture({**FRAME,'eval_count':10})
        task.cancel()
        with self.assertRaises(asyncio.CancelledError): await task
        native.capture(FRAME)
        self.assertFalse(m1.record['ollamaNative']['terminalFrameReceived'])
        self.assertEqual(m2.record['ollamaNative']['evalCount'],10)


class ASGINativeTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=note_tests.NoteFactTests.asyncSetUp
    invoke=note_tests.NoteFactTests.invoke
    payload=note_tests.NoteFactTests.payload
    fixture=note_tests.NoteFactTests.fixture
    engine=note_tests.NoteFactTests.engine
    body=note_tests.NoteFactTests.body
    metric=note_tests.NoteFactTests.metric
    async def test_real_collector_request_correlates_metrics_and_keeps_response(self):
        payload=self.fixture('qualifications')
        self.engine(); before=await self.invoke(payload)
        expected_body=self.body(before)
        async def observed(messages,schema):
            yield SimpleNamespace(content=answer(self.bundle['plan']),finish_reason=None,tool_calls=None)
            native.capture(FRAME)
            yield SimpleNamespace(content=None,finish_reason='stop',tool_calls=None)
        self.app.fact_stream=observed
        after=await self.invoke(payload)
        self.assertEqual(self.body(after),expected_body)
        self.assertEqual(self.metric()['ollamaNative']['evalCount'],48)
        self.assertEqual(self.metric()['structuredOutcome'],'accepted')
        self.assertNotIn('PRIVATE',json.dumps(self.metric()))
        self.assertFalse(self.app.busy)


class ReaderTests(unittest.TestCase):
    def test_only_latest_structured_row_and_numeric_allowlist_are_printed(self):
        m=RequestMeasurement('notes','PRIVATE MODEL')
        with native.bind(m): native.capture(FRAME)
        m.record.update(status='completed',inferenceUsed=True,structuredGenerationMs=12001,
                        structuredOutcome='accepted',text='PRIVATE NOTE',path='PRIVATE PATH')
        result=reader.summary({'records':[m.record,{'kind':'chat','text':'PRIVATE CHAT'}]})
        self.assertEqual(result['native']['evalTokensPerSecond'],8)
        self.assertEqual(result['inferencesIssuedByReader'],0)
        self.assertEqual(result['qualityVerdict'],'not_assessed_by_reader')
        self.assertNotIn('PRIVATE',json.dumps(result)); self.assertNotIn(m.record['id'],json.dumps(result))
        incomplete={**m.record,'status':'cancelled','ollamaNative':{}}
        result=reader.summary({'records':[m.record,incomplete]})
        self.assertEqual(result['transportStatus'],'cancelled')
        self.assertFalse(result['native']['terminalFrameReceived'])
        self.assertIsNone(result['native']['loadMs'])

    def test_reader_issues_one_get_and_bounded_read_no_generation_or_redirect(self):
        calls=[]
        class Reply:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,limit): calls.append(limit); return b'{"records":[]}'
        class Opener:
            def open(self,request,timeout):
                calls.append((request.full_url,request.method,timeout)); return Reply()
        with self.assertRaises(ValueError): reader.read(Opener())
        self.assertEqual(calls,[(reader.URL,'GET',10),reader.LIMIT+1])
        with self.assertRaises(ValueError): reader.NoRedirect().redirect_request(None,None,None,None,None,None)


if __name__=='__main__': unittest.main()
