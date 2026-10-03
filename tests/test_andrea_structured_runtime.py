"""Production ASGI path with simulated secured engine, never a personal vault."""
import asyncio
import json
from types import SimpleNamespace
import unittest
import test_andrea_vault as base
from synthesis_contract import validate_contract, make_coverage_messages
from context_coverage_probe import CASES, validate_contract as historical_validate
from runtime import notes_messages


def output(text='La nota documenta due titoli.', refs=None):
    return json.dumps({'scope':'provided_excerpts','claims':[{'text':text,'sources':refs or ['N1']}]})


class StructuredRuntimeTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = base.BoundaryVaultTests.asyncSetUp
    invoke = base.BoundaryVaultTests.invoke
    payload = base.BoundaryVaultTests.payload
    def request(self, case=None):
        case = case or CASES[1]
        return dict(self.payload(case['query']), notes_sources=case['sources'], notes_structured=True)
    def engine(self, raw, reason='stop', tools=None):
        self.generated = []
        async def stream(messages):
            self.generated.append(messages)
            yield SimpleNamespace(content=raw[:len(raw)//2],finish_reason=None,tool_calls=tools)
            yield SimpleNamespace(content=raw[len(raw)//2:],finish_reason=None,tool_calls=None)
            if reason:
                yield SimpleNamespace(content=None,finish_reason=reason,tool_calls=None)
        self.app.structured_stream = stream
    def body(self, events):
        return b''.join(e.get('body',b'') for e in events).decode()
    def metric(self):
        return self.app.measurements.snapshot()['records'][-1]

    async def test_single_generation_and_validated_text_only_with_distinct_timings(self):
        self.engine(output('La nuova bocciatura è del 2026-10-01.', ['N2']))
        events = await self.invoke(self.request())
        self.assertEqual(events[0]['status'],200)
        self.assertEqual(len(self.generated),1);self.assertFalse(self.calls)
        body = self.body(events)
        self.assertIn('La nuova bocciatura è del 2026-10-01. [N2]',body)
        self.assertNotIn('"claims"',body);self.assertNotIn('provided_excerpts',body)
        record=self.metric()
        self.assertEqual(record['structuredOutcome'],'accepted')
        self.assertGreaterEqual(record['structuredAcceptedTextMs'],record['structuredFirstJsonMs'])
        self.assertIn('structuredValidationMs',record)
        self.assertNotIn('bocciatura',json.dumps(record))
        self.assertFalse(self.app.busy)

    async def test_unknown_sources_bad_json_length_eof_tools_and_size_refused(self):
        for raw, reason, tools in [(output(refs=['N9']),'stop',None), ('not JSON','stop',None),
                 (output(),'length',None),(output(),None,None),(output(),'stop',['forbidden']),('x'*32001,'stop',None)]:
            self.engine(raw,reason,tools)
            body=self.body(await self.invoke(self.request()))
            self.assertIn('Sintesi strutturata non mostrata',body)
            self.assertEqual(self.metric()['structuredOutcome'],'rejected')
            self.assertNotIn('structuredAcceptedTextMs',self.metric())
            self.assertEqual(len(self.generated),1);self.assertFalse(self.app.busy)

    async def test_abstention_distinct_from_acceptance(self):
        self.engine('{"scope":"provided_excerpts","claims":[]}')
        body=self.body(await self.invoke(self.request()))
        self.assertIn('structured_abstained',body)
        self.assertEqual(self.metric()['structuredOutcome'],'abstained')

    async def test_missing_and_swapped_dates_rejected_complete_pairs_accepted(self):
        case=CASES[0]
        self.engine(output('DATO NON VERIFICATO nella nota.'))
        await self.invoke(self.request(case));self.assertEqual(self.metric()['structuredOutcome'],'rejected')
        correct=json.dumps({'scope':'provided_excerpts','claims':[
            {'text':'Al 2026-10-01: DATO NON VERIFICATO in questa nota.','sources':['N1']},
            {'text':'Fotografia al 2026-08-20: DATO ASSENTE.','sources':['N1']}]})
        self.engine(correct);await self.invoke(self.request(case))
        self.assertEqual(self.metric()['structuredOutcome'],'accepted')
        self.assertEqual(len(json.loads(self.generated[0][1]['content'])['mandatory_contexts']),2)
        wrong=correct.replace('2026-10-01','TEMP').replace('2026-08-20','2026-10-01').replace('TEMP','2026-08-20')
        self.engine(wrong);await self.invoke(self.request(case));self.assertEqual(self.metric()['structuredOutcome'],'rejected')

    async def test_ambiguous_contexts_refuse_without_generation(self):
        case=dict(CASES[0],sources=[dict(CASES[0]['sources'][0],text=CASES[0]['sources'][0]['text']+' Evento al 2026-09-01.')])
        self.engine(output());body=self.body(await self.invoke(self.request(case)))
        self.assertFalse(self.generated);self.assertIn('structured_refused',body)
        self.assertFalse(self.metric()['inferenceUsed'])

    async def test_existing_status_guard_and_direct_conflicts_keep_priority(self):
        self.engine(output())
        sources=[{'id':'N1','title':'KPI','text':'Aggiornamento del 2026-10-01\nDATO NON VERIFICATO.\n\nFotografia al 2026-08-20\nDATO ASSENTE.'}]
        body=self.body(await self.invoke(dict(self.request(),notes_sources=sources)))
        self.assertIn('status_scope_quotes',body);self.assertFalse(self.generated)
        case={'query':'Quanti libri pubblicati?', 'sources':[{'id':'N1','title':'KPI','text':'Libri pubblicati: 2.'},{'id':'N2','title':'KPI','text':'Libri pubblicati: 0.'}]}
        body=self.body(await self.invoke(self.request(case)))
        self.assertIn('explicit_fields',body);self.assertIn('N2',body);self.assertFalse(self.generated)

    async def test_flag_validation_and_cross_origin_still_blocked(self):
        self.engine(output())
        for payload in (dict(self.request(),notes_structured='true'),dict(self.request(),notes_brief=True),
                        {'model':base.MODEL,'stream':True,'messages':[{'role':'user','content':'x'}],'notes_structured':True}):
            self.assertEqual((await self.invoke(payload))[0]['status'],400)
        self.assertEqual((await self.invoke(self.request(),origin='https://external.example'))[0]['status'],403)
        self.assertFalse(self.generated)

    async def test_disconnect_releases_busy_cancels_generator_and_never_accepts_partial(self):
        entered=asyncio.Event();closed=asyncio.Event()
        async def stream(messages):
            try:
                yield SimpleNamespace(content='{"scope":',finish_reason=None,tool_calls=None)
                entered.set();await asyncio.Event().wait()
            finally:closed.set()
        self.app.structured_stream=stream
        queue=asyncio.Queue();await queue.put({'type':'http.request','body':json.dumps(self.request()).encode()})
        events=[]
        async def send(event):events.append(event)
        scope={'type':'http','method':'POST','path':'/v1/chat/completions','headers':[(b'host',b'127.0.0.1:8008'),(b'origin',b'http://127.0.0.1:8008'),(b'content-type',b'application/json')]}
        task=asyncio.create_task(self.app(scope,queue.get,send));await entered.wait()
        self.assertTrue(self.app.busy)
        self.assertEqual((await self.invoke(self.request()))[0]['status'],429)
        self.assertEqual((await self.invoke({'vault':''},path='/api/andrea/notes/config'))[0]['status'],409)
        await queue.put({'type':'http.disconnect'})
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertTrue(closed.is_set());self.assertFalse(self.app.busy)
        self.assertNotIn('provided_excerpts',self.body(events));self.assertEqual(self.metric()['status'],'cancelled')

    async def test_timeout_engine_error_no_raw_json_and_busy_released(self):
        async def hang(messages):
            yield SimpleNamespace(content='PRIVATE PARTIAL',finish_reason=None,tool_calls=None)
            await asyncio.Event().wait()
        self.app.structured_stream=hang;self.app.timeout=.01
        body=self.body(await self.invoke(self.request()))
        self.assertNotIn('PRIVATE PARTIAL',body);self.assertEqual(self.metric()['status'],'timeout');self.assertFalse(self.app.busy)
        async def error(messages):
            raise RuntimeError('transport')
            yield
        self.app.structured_stream=error
        with self.assertRaises(RuntimeError):await self.invoke(self.request())
        self.assertEqual(self.metric()['status'],'error');self.assertFalse(self.app.busy)

    async def test_secured_stream_adapter_forwards_json_and_closes_on_cancel(self):
        import ast
        from pathlib import Path
        from runtime import ROOT
        tree=ast.parse((ROOT/'scripts/andrea/runtime.py').read_text())
        build=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='build_app')
        function=next(n for n in build.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='structured_stream')
        calls=[];closed=[]
        class Engine:
            async def stream_full(self,messages,**kwargs):
                try:
                    calls.append((messages,kwargs))
                    yield SimpleNamespace(content='fragment')
                finally:closed.append(True)
        namespace={'sec':SimpleNamespace(engine=Engine()),'cfg':SimpleNamespace(server=SimpleNamespace(model=base.MODEL)),
                   'Message':lambda **kwargs:kwargs,'Role':lambda value:value}
        exec(compile(ast.Module(body=[function],type_ignores=[]),'secured_adapter','exec'),namespace)
        iterator=namespace['structured_stream']([{'role':'user','content':'Synthetic'}])
        await anext(iterator);await iterator.aclose()
        self.assertEqual(calls[0][1],{'model':base.MODEL,'response_format':{'type':'json_object'}})
        self.assertEqual(closed,[True])

    async def test_all_six_collection_cases_use_production_flags_no_retry_or_private_ids(self):
        from check_structured import collect
        from pathlib import Path
        from runtime import ROOT
        cases=json.loads((ROOT/'scripts/andrea/structured_cases.json').read_text())
        calls=[]
        def run(payload,**kwargs):
            calls.append(payload)
            self.assertTrue(payload['notes_structured']);self.assertTrue(kwargs['keep_answer'])
            return {'done':True,'finishReason':'stop','answer':'Synthetic',
                    'requestId':'PRIVATE_ID','server':{'id':'PRIVATE_ID','answerMode':'structured_synthesis',
                    'inferenceUsed':True,'structuredOutcome':'accepted','firstTextMs':3,'totalMs':4}}
        report=collect(run,cases)
        self.assertEqual(len(calls),6);self.assertEqual(report['automaticRetries'],0)
        self.assertNotIn('PRIVATE_ID',json.dumps(report))
        self.assertTrue(all(row['qualityVerdict']=='pending_review' for row in report['rows']))

    async def test_terminal_frame_drained_before_acceptance_for_security_post_hoc(self):
        scanned=[]
        async def stream(messages):
            yield SimpleNamespace(content=output(),finish_reason=None,tool_calls=None)
            yield SimpleNamespace(content=None,finish_reason='stop',tool_calls=None)
            scanned.append(True)
        self.app.structured_stream=stream
        await self.invoke(self.request())
        self.assertEqual(scanned,[True]);self.assertEqual(self.metric()['structuredOutcome'],'accepted')

    def test_extracted_validator_is_identical_to_probe_for_all_four_cases(self):
        for case in CASES:
            for raw in (output(),output('Nel 2030-01-01'),'{"scope":"provided_excerpts","claims":[]}'):
                self.assertEqual(validate_contract(raw,case['sources'],completed=True),historical_validate(raw,case['sources'],completed=True))
            self.assertIn('scope',make_coverage_messages(notes_messages,case)[0]['content'])
