"""Installed facade, real service streaming and finite acceptance checks."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace as Chunk
import unittest
from unittest.mock import patch
import web_candidate_pipeline as pipeline
import web_page_context_contract as facade
import web_page_local as service
import web_native_operation_verb_probe as reviewed
import check_web_compact_v9 as check
from test_andrea_web_capability_scope import page, CSV_RULE
from test_andrea_web_definition_context import extracted, html_entry
from test_andrea_web_heading_latency import GOOD_CSV
from test_andrea_web_api_context_check import Opener, Response, TEXT


def csv_page():
    return extracted('<h1>csv</h1>'+html_entry('csv.reader','<p>'+CSV_RULE+'</p>'))


class LiveCompactIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def run_case(self, source, case, raw):
        original=copy.deepcopy(source)
        pages=service.LocalWebPages()
        pages.page={**source,'pageId':'token'}
        pages.expires=service.time.monotonic()+300
        expected=reviewed.prepared(source,case,'compact')
        calls=[];closed=[]
        async def stream(messages,schema):
            calls.append((messages,schema))
            try:
                yield Chunk(content=raw[:len(raw)//2],finish_reason=None)
                yield Chunk(content=raw[len(raw)//2:],finish_reason='stop')
            finally:
                closed.append(True)
        result=await pages.summarize({'pageId':'token','question':case['question']},stream)
        self.assertEqual(calls,[(expected[1],expected[2])])
        self.assertEqual(closed,[True])
        self.assertEqual(result['contractRevision'],'compact_web_evidence_v9')
        self.assertEqual(result['automaticRetries'],0)
        self.assertEqual(result['qualityVerdict'],'pending_review')
        self.assertEqual(source,original)
        self.assertEqual(result['contextSelection'],expected[3])
        return result,expected

    async def test_actual_csv_service_preserves_condition_and_exact_source(self):
        source=csv_page();case=check.CASES[1]
        bank,_,_,selection=pipeline.prepare(source,case['question'])
        ref=selection['outputPolicy']['sourceRuleRefs'][0]
        raw=json.dumps({'claims':[{'passage':ref,'text':GOOD_CSV}]})
        result,expected=await self.run_case(source,case,raw)
        self.assertEqual(result['outcome'],'accepted_pending_semantic_review')
        self.assertEqual(result['claims'][0]['text'],GOOD_CSV)
        self.assertEqual(result['claims'][0]['quote'],bank[ref-1])
        self.assertEqual(result['timings']['inputCharacters'],expected[3]['modelSourceCharacters'])

    async def test_actual_missing_answer_is_model_abstention_not_forced_empty_schema(self):
        result,expected=await self.run_case(csv_page(),check.CASES[2],'{"claims":[]}')
        self.assertEqual(result['outcome'],'abstained')
        self.assertEqual(result['claims'],[])
        self.assertNotEqual(expected[2]['properties']['claims'].get('maxItems'),0)

    async def test_source_control_verb_does_not_let_execution_pass(self):
        source=page();case=check.CASES[0]
        bank,_,_,selection=pipeline.prepare(source,case['question'])
        ref=selection['nativeOperationVerbPolicy']['rules'][0]['passage']
        raw=json.dumps({'claims':[{'passage':ref,'text':'Permette di eseguire i sottoprocessi.'}]})
        result,_=await self.run_case(source,case,raw)
        self.assertEqual(result['outcome'],'rejected')
        self.assertEqual(result['claims'],[])
        self.assertIn('reason',result)

    async def test_length_finish_is_rejected_without_second_call(self):
        source=csv_page();pages=service.LocalWebPages()
        pages.page={**source,'pageId':'token'};pages.expires=service.time.monotonic()+300
        calls=[]
        async def stream(messages,schema):
            calls.append(True)
            yield Chunk(content='{"claims":[]}',finish_reason='length')
        result=await pages.summarize({'pageId':'token','question':check.CASES[2]['question']},stream)
        self.assertEqual(result['outcome'],'rejected')
        self.assertEqual(result['reason'],'stream_incomplete')
        self.assertEqual(calls,[True])

    def test_live_preparation_is_exact_reviewed_candidate_for_all_questions(self):
        for i,case in enumerate(check.CASES):
            source=page() if i==0 else csv_page()
            self.assertEqual(facade.prepare(source,case['question']),reviewed.prepared(source,case,'compact'))
        self.assertIs(facade.fidelity,pipeline.contract)
        self.assertTrue(callable(facade.context.checked_definitions))


class InstalledAcceptanceTests(unittest.TestCase):
    def test_missing_positive_answer_cannot_pass_as_abstention(self):
        rows=[{'case':c['id'],'outcome':'abstained','claims':[]} for c in check.CASES]
        report=check.summary(rows)
        self.assertFalse(report['technicalCaseShapesMet'])
        self.assertEqual(report['qualityVerdict'],'pending_review')
        self.assertEqual(report['historicalPairedBenchmarkMeaning'],'5_favorable_1_unfavorable_unchanged')

    def test_two_one_zero_shape_still_does_not_certify_meaning(self):
        rows=[{'case':c['id'],'outcome':'accepted_pending_semantic_review' if i<2 else 'abstained',
               'claims':[{'text':'Unreviewed text'}]*n} for i,(c,n) in enumerate(zip(check.CASES,(2,1,0)))]
        report=check.summary(rows)
        self.assertTrue(report['technicalCaseShapesMet'])
        self.assertTrue(report['meaningReviewRequired'])
        self.assertEqual(report['qualityVerdict'],'pending_review')
        self.assertEqual(report['performanceComparison'],'not_repeated_by_this_check')

    def test_old_running_server_is_refused_even_if_files_are_updated(self):
        opener=Opener()
        with patch.object(check,'verify_project'):
            with self.assertRaisesRegex(check.CheckError,'contratto precedente'):
                check.run(Path('.'),opener,lambda _:None)
        self.assertEqual(opener.summaries,1)

    def test_three_actual_api_calls_no_direct_model_retry_or_repair(self):
        opener=Opener();original=opener.open
        def native(request,timeout):
            response=original(request,timeout);value=json.loads(response.data)
            if request.full_url.endswith('/summarize'):
                value['contractRevision']='compact_web_evidence_v9'
                if opener.summaries==1:value['claims']*=2
            return Response(value)
        opener.open=native
        with patch.object(check,'verify_project'):
            rows=check.run(Path('.'),opener,lambda _:None)
        self.assertEqual((opener.reads,opener.summaries),(2,3))
        self.assertTrue(check.summary(rows)['technicalCaseShapesMet'])
        self.assertEqual([r['question'] for r in rows],[c['question'] for c in check.CASES])
        self.assertTrue(all(r['qualityVerdict']=='pending_review' for r in rows))


if __name__=='__main__':unittest.main()
