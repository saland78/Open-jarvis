"""Actual StreamChunk and Ollama parser isolated from native dependencies."""
from __future__ import annotations
import ast
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/andrea'))
from structured_stream import collect
from measurements import RequestMeasurement
from test_andrea_keep_alive import engine_class


def stream_chunk_class():
    tree = ast.parse((ROOT/'src/openjarvis/engine/_stubs.py').read_text())
    klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'StreamChunk')
    namespace = {'__name__': __name__, 'dataclass': dataclass, 'Any': Any, 'Dict': Dict, 'List': List, 'Optional': Optional}
    exec(compile(ast.Module(body=[klass], type_ignores=[]), 'actual_stream_chunk', 'exec'), namespace)
    return namespace['StreamChunk']


StreamChunk = stream_chunk_class()
RAW = json.dumps({'scope':'provided_excerpts','claims':[{'text':'Il dato è presente nella nota.', 'sources':['N1']}]})
SOURCES = [{'id':'N1','text':'Il dato è presente nella nota.'}]


def actual_engine(events):
    """Execute actual stream_full and _run_stream; replace only HTTP I/O."""
    tree = ast.parse((ROOT/'src/openjarvis/engine/ollama.py').read_text())
    klass = next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='OllamaEngine')
    method = next(n for n in klass.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='_run_stream')
    namespace = {'json':json, 'StreamChunk':StreamChunk, 'estimate_prompt_tokens':lambda messages:10,
                 'STREAM_TRANSPORT_ERRORS':(ConnectionError,TimeoutError), 'EngineConnectionError':ConnectionError,
                 '_is_control_token_only_args':lambda args:False, 'logger':SimpleNamespace(warning=lambda *args:None)}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),method],type_ignores=[])),'actual_run_stream','exec'),namespace)
    engine = engine_class()()
    engine._run_stream = namespace['_run_stream'].__get__(engine)
    requests=[]
    class Response:
        status_code=200
        is_success=True
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def aiter_lines(self):
            for event in events: yield json.dumps(event)
    class Transport:
        def stream(self,*args,**kwargs):
            requests.append(kwargs['json'])
            return Response()
    engine._get_async_client=lambda:Transport()
    return engine,requests


class FinalChunkTests(unittest.IsolatedAsyncioTestCase):
    async def result(self,events):
        engine,requests = actual_engine(events)
        async def stream(messages):
            async for chunk in engine.stream_full(messages,model='selected',response_format={'type':'json_object'}):
                yield chunk
        measurement = RequestMeasurement('notes','selected')
        result,text = await collect(stream,[],SOURCES,measurement)
        self.assertEqual(len(requests),1)
        self.assertEqual(requests[0]['format'],'json')
        return result,text,measurement.record

    async def test_actual_parser_terminal_none_must_complete_valid_json(self):
        chunk = StreamChunk(finish_reason='stop',usage={'completion_tokens':1})
        self.assertIsNone(chunk.content)
        result,text,record = await self.result([{'message':{'content':RAW}}, {'done':True,'done_reason':'stop','eval_count':1}])
        self.assertEqual(result['status'],'valid_structure_pending_semantic_review')
        self.assertEqual(record['structuredOutcome'],'accepted')
        self.assertIn('[N1]',text)

    async def test_actual_parser_eof_and_length_never_accept_valid_partial_json(self):
        for final in ([], [{'done':True,'done_reason':'length'}]):
            result,_,record=await self.result([{'message':{'content':RAW}}, *final])
            self.assertEqual(result['status'],'rejected')
            self.assertEqual(record['structuredOutcome'],'rejected')

    async def test_actual_parser_tools_stay_forbidden_even_with_valid_json(self):
        result,_,record=await self.result([{'message':{'content':RAW,'tool_calls':[{'function':{'name':'forbidden','arguments':{}}}]}},{'done':True,'done_reason':'stop'}])
        self.assertEqual(result['status'],'rejected')
        self.assertEqual(record['structuredOutcome'],'rejected')

    async def test_empty_none_chunk_does_not_complete_stream_and_non_string_still_rejected(self):
        for value,reason in ((None,None),(42,'stop')):
            async def stream(messages):
                yield StreamChunk(content=RAW)
                yield StreamChunk(content=value,finish_reason=reason)
            result,_=await collect(stream,[],SOURCES,RequestMeasurement('notes','selected'))
            self.assertEqual(result['status'],'rejected')

    async def test_security_post_hoc_drained_after_actual_none_terminal(self):
        scanned=[]
        async def stream(messages):
            yield StreamChunk(content=RAW)
            yield StreamChunk(finish_reason='stop')
            scanned.append(True)
        result,_=await collect(stream,[],SOURCES,RequestMeasurement('notes','selected'))
        self.assertEqual(result['status'],'valid_structure_pending_semantic_review')
        self.assertEqual(scanned,[True])
