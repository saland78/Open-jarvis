"""CPU-only option experiment: exact evidence, fixed calls and honest gates."""
import copy
import io
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import check_web_compact_v9 as check
import web_candidate_pipeline as pipeline
import web_cpu_batch_probe as probe
from test_andrea_web_compact_integration import csv_page
from test_andrea_web_capability_scope import page
from test_andrea_web_heading_latency import GOOD_CSV


class Response(io.BytesIO):
    status = 200


class Transport:
    def __init__(self, frames):
        self.body = ''.join(json.dumps(f)+'\n' for f in frames).encode()
        self.calls = []
    def open(self, request, timeout):
        self.calls.append((request, timeout))
        return Response(self.body)


def frames(raw, reason='stop'):
    return [{'done': False, 'message': {'content': raw[:5]}},
            {'done': True, 'done_reason': reason, 'message': {'content': raw[5:]},
             'total_duration': 3000000000, 'load_duration': 1000,
             'prompt_eval_duration': 2000000000, 'eval_duration': 900000000,
             'prompt_eval_count': 1000, 'prompt_eval_cached_count': 0, 'eval_count': 70}]


def row(index, batch, cost=None, total=None):
    case = check.CASES[index]['id']
    return {'case': case, 'numBatchRequested': batch, 'sourceTextSha256': 'same',
            'messagesBeforeCacheMarkerSha256': 'same', 'nativeSchemaSha256': 'same',
            'modelSourceCharacters': 2000, 'observerClosed': True,
            'residency': {'expectedModelLoaded': True, 'sizeVram': 0},
            'result': {'completed': True, 'doneReason': 'stop',
                'totalClientMs': total or (5000 if batch == 512 else 4000),
                'native': {'prompt_eval_count': 1000, 'prompt_eval_cached_count': 0,
                    'prompt_eval_duration': cost or (2000000000 if batch == 512 else 1600000000),
                    'eval_duration': 900000000, 'eval_count': 70, 'load_duration': 1000,
                    'total_duration': 3000000000}},
            'checks': {'outcome': 'abstained' if index == 2 else 'accepted_pending_semantic_review',
                       'claims': [{}] * (2, 1, 0)[index]}, 'qualityVerdict': 'pending_review'}


class TransportTests(unittest.TestCase):
    def test_only_batch_differs_and_schema_roles_source_are_preserved(self):
        source=csv_page()
        bank,messages,schema,selection=pipeline.prepare(source,check.CASES[1]['question'])
        raw=json.dumps({'claims':[{'passage':selection['outputPolicy']['sourceRuleRefs'][0],'text':GOOD_CSV}]})
        original=copy.deepcopy((source,messages,schema))
        payloads=[]
        for batch in (512,128):
            transport=Transport(frames(raw))
            result=probe.stream_once(messages,schema,batch,transport)
            self.assertTrue(result['completed'])
            self.assertEqual(result['raw'],raw)
            self.assertEqual(len(transport.calls),1)
            req,timeout=transport.calls[0]
            self.assertEqual(req.full_url,probe.OLLAMA+'/api/chat')
            self.assertEqual(timeout,90)
            payloads.append(json.loads(req.data))
            checked=pipeline.validate(result['raw'],bank,result['completed'],source,selection)
            self.assertEqual(checked['outcome'],'accepted_pending_semantic_review')
            self.assertEqual(checked['claims'][0]['text'],GOOD_CSV)
        payloads[1]['options']['num_batch']=512
        self.assertEqual(payloads[0],payloads[1])
        self.assertEqual(payloads[0]['format'],schema)
        self.assertNotIn('num_thread',payloads[0]['options'])
        self.assertEqual((source,messages,schema),original)

    def test_empty_answer_remains_model_generated_not_forced_schema(self):
        source=csv_page()
        bank,messages,schema,selection=pipeline.prepare(source,check.CASES[2]['question'])
        self.assertNotEqual(schema['properties']['claims'].get('maxItems'),0)
        transport=Transport(frames('{"claims":[]}'))
        result=probe.stream_once(messages,schema,128,transport)
        self.assertEqual(pipeline.validate(result['raw'],bank,result['completed'],source,selection)['outcome'],'abstained')
        self.assertEqual(result['raw'],'{"claims":[]}')

    def test_length_finish_is_retained_and_fails_completion(self):
        result=probe.stream_once([],{},128,Transport(frames('{"claims":[]}', 'length')))
        self.assertFalse(result['completed'])
        self.assertEqual(result['doneReason'],'length')
        self.assertEqual(result['raw'],'{"claims":[]}')

    def test_eof_without_terminal_is_not_completion(self):
        result=probe.stream_once([],{},128,Transport([{'done':False,'message':{'content':'{}'}}]))
        self.assertFalse(result['completed'])

    def test_extra_terminal_or_tool_call_refuses_without_retry(self):
        for data in (frames('{}')+[frames('{}')[-1]],
                     [{'done':False,'message':{'content':'','tool_calls':[{}]}}]):
            transport=Transport(data)
            with self.assertRaises(ValueError): probe.stream_once([],{},128,transport)
            self.assertEqual(len(transport.calls),1)

    def test_raw_answer_bound_refuses_without_truncation(self):
        with self.assertRaises(ValueError):
            probe.stream_once([],{},128,Transport(frames('x'*5001)))

    def test_duplicate_keys_are_rejected(self):
        with self.assertRaises(ValueError):
            json.loads('{"done":true,"done":false}',object_pairs_hook=probe.unique_pairs)

    def test_bool_or_missing_metrics_are_unknown_not_zero(self):
        self.assertIsNone(probe.numeric_metrics({'load_duration':False})['load_duration'])
        self.assertIsNone(probe.numeric_metrics({})['prompt_eval_cached_count'])

    def test_cache_marker_keeps_roles_all_instructions_and_exact_user_bytes(self):
        messages=[{'role':'system','content':'Rules'}, {'role':'user','content':'Original bytes'}]
        original=copy.deepcopy(messages)
        revised=probe.isolated_messages(messages,'a'*32)
        self.assertEqual(revised[1],messages[1])
        self.assertTrue(revised[0]['content'].endswith('Rules'))
        self.assertEqual(messages,original)
        with self.assertRaises(ValueError):probe.isolated_messages(messages,'bad')

    def test_no_proxy_or_redirect_fallback(self):
        transport=probe.opener()
        with self.assertRaises(ValueError):
            probe.NoRedirect().redirect_request(None,None,302,'Moved',{},'https://external.example')
        self.assertFalse(any(getattr(h,'proxies',None) for h in transport.handlers))


class GateTests(unittest.TestCase):
    def rows(self): return [row(i,b) for i,b in probe.ORDER]
    def test_numeric_pass_is_never_meaning_or_adoption(self):
        result=probe.comparison(self.rows())
        self.assertTrue(result['numericGatesMet'])
        self.assertFalse(result['integrationAllowed'])
        self.assertEqual(result['qualityVerdict'],'pending_review')
        self.assertFalse(result['historicalBenchmarksChanged'])
    def test_both_positive_cases_must_meet_gain(self):
        rows=self.rows();rows[2]=row(1,128,cost=1990000000)
        self.assertFalse(probe.comparison(rows)['numericGatesMet'])
    def test_total_regression_prevents_adoption_even_with_fast_prefill(self):
        rows=self.rows();rows[-1]=row(2,128,total=6000)
        self.assertFalse(probe.comparison(rows)['numericGatesMet'])
    def test_cached_run_cannot_pass_as_prefill_gain(self):
        rows=self.rows();rows[1]['result']['native']['prompt_eval_cached_count']=900
        self.assertFalse(probe.comparison(rows)['pairs'][0]['eligible'])
    def test_missing_cached_count_cannot_pass(self):
        rows=self.rows();del rows[0]['result']['native']['prompt_eval_cached_count']
        self.assertFalse(probe.comparison(rows)['numericGatesMet'])
    def test_positive_abstention_cannot_pass(self):
        rows=self.rows();rows[1]['checks']={'outcome':'abstained','claims':[]}
        self.assertFalse(probe.comparison(rows)['numericGatesMet'])
    def test_changed_source_prompt_or_schema_cannot_be_compared(self):
        for field in ('sourceTextSha256','messagesBeforeCacheMarkerSha256','nativeSchemaSha256','modelSourceCharacters'):
            rows=self.rows();rows[1][field]='changed'
            self.assertFalse(probe.comparison(rows)['pairs'][0]['eligible'])
    def test_unknown_gpu_residency_cannot_pass_cpu_gate(self):
        for residency in ({'expectedModelLoaded':None,'sizeVram':None},
                          {'expectedModelLoaded':True,'sizeVram':1000}):
            rows=self.rows();rows[1]['residency']=residency
            self.assertFalse(probe.comparison(rows)['numericGatesMet'])
    def test_interrupted_partial_series_does_not_crash_or_pass(self):
        rows=self.rows()[:3]
        rows.append({'case':'csv_conversion_condition','numBatchRequested':512,'result':{},'checks':{}})
        self.assertFalse(probe.comparison(rows)['numericGatesMet'])
    def test_reordered_or_duplicate_series_does_not_pass(self):
        rows=self.rows();rows.reverse()
        self.assertFalse(probe.comparison(rows)['numericGatesMet'])
    def test_numeric_path_does_not_require_favorable_missing_price_gain(self):
        rows=self.rows();rows[-1]['result']['native']['prompt_eval_duration']=2500000000
        self.assertTrue(probe.comparison(rows)['numericGatesMet'])


class OrchestrationTests(unittest.TestCase):
    def test_changed_checker_refuses_before_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'scripts/andrea').mkdir(parents=True)
            (root/'scripts/andrea/check_web_compact_v9.py').write_text('raise RuntimeError("must not import")')
            with self.assertRaisesRegex(ValueError,'checker_changed'):probe.load_project(root)
    def test_symlink_parent_refuses_even_for_verified_checker_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'real/andrea').mkdir(parents=True)
            (root/'real/andrea/check_web_compact_v9.py').write_bytes(Path(check.__file__).read_bytes())
            (root/'scripts').symlink_to(root/'real',target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'checker_changed'):probe.load_project(root)
    def test_wrong_version_refuses_without_model_request(self):
        class MetadataTransport:
            def __init__(self):self.calls=[]
            def open(self,url,timeout):
                self.calls.append(url)
                return Response(json.dumps({'version':'changed'} if url.endswith('/version') else {'models':[]}).encode())
        transport=MetadataTransport()
        with patch.object(probe,'load_project',return_value=(check,pipeline)),patch.object(probe,'opener',return_value=transport):
            with self.assertRaisesRegex(ValueError,'version_changed'):
                probe.worker(Path('/project'),{'operation':'metadata'})
        self.assertEqual(transport.calls,[probe.OLLAMA+'/api/version',probe.OLLAMA+'/api/ps'])
    def test_worker_uses_exact_production_validation_for_missing_price(self):
        source=csv_page()
        with patch.object(probe,'load_project',return_value=(check,pipeline)),patch.object(probe,'stream_once',return_value={
                'raw':'{"claims":[]}','completed':True,'doneReason':'stop','native':{}}) as stream,patch.object(probe,'cpu_residency',return_value={}):
            result=probe.worker(Path('/project'),{'operation':'model','case':2,'page':{
                **source,'pageId':'token','sourceId':'W1','modelUsed':False},'batch':128,'marker':'a'*32})
        self.assertEqual(result['checks']['outcome'],'abstained')
        self.assertEqual(stream.call_args.args[1],pipeline.prepare(source,check.CASES[2]['question'])[2])
        self.assertEqual(result['qualityVerdict'],'pending_review')
    def test_worker_timeout_kills_only_owned_child_and_stops_observer(self):
        child=SimpleNamespace(communicate=unittest.mock.Mock(side_effect=[subprocess.TimeoutExpired('owned',1),(b'',b'')]),
                              poll=unittest.mock.Mock(return_value=None),kill=unittest.mock.Mock())
        observer=SimpleNamespace(start=unittest.mock.Mock(),close=unittest.mock.Mock(return_value=True),rows=[])
        with patch.object(probe.subprocess,'Popen',return_value=child),patch.object(probe,'Observer',return_value=observer):
            with self.assertRaisesRegex(ValueError,'deadline'):
                probe.owned_worker(Path('/project'),{'operation':'model'},1,True)
        child.kill.assert_called_once();observer.close.assert_called_once()
    def test_early_platform_refusal_has_no_reads_or_requests(self):
        with patch.object(probe.platform,'system',return_value='Linux'),patch.object(probe,'owned_worker') as calls:
            with self.assertRaises(ValueError):probe.run(Path('/project'))
        calls.assert_not_called()
    def test_fixed_six_calls_only_no_install_or_retries(self):
        fakecheck=SimpleNamespace(CASES=check.CASES)
        def owned(project,payload,timeout,observe=False):
            if payload['operation']=='metadata':return {},[],True
            if payload['operation']=='read':return (page() if payload['case']==0 else csv_page()),[],True
            return row(payload['case'],payload['batch']),[],True
        with patch.object(probe.platform,'system',return_value='Darwin'),patch.object(probe,'load_project',return_value=(fakecheck,pipeline)),patch.object(probe,'owned_worker',side_effect=owned) as calls:
            result=probe.run(Path('/project'),emit=lambda *a,**k:None)
        model=[c.args[1] for c in calls.call_args_list if c.args[1]['operation']=='model']
        self.assertEqual([(p['case'],p['batch']) for p in model],list(probe.ORDER))
        self.assertEqual(result['automaticRetries'],0)
        self.assertFalse(result['productionModified'])
        self.assertEqual(result['completedRows'],6)
    def test_bad_csv_source_stops_before_model_request(self):
        fakecheck=SimpleNamespace(CASES=check.CASES)
        def owned(project,payload,timeout,observe=False):
            return ({'text':'condition missing'} if payload['operation']=='read' else {}),[],True
        with patch.object(probe.platform,'system',return_value='Darwin'),patch.object(probe,'load_project',return_value=(fakecheck,pipeline)),patch.object(probe,'owned_worker',side_effect=owned) as calls:
            with self.assertRaisesRegex(ValueError,'condition_missing'):probe.run(Path('/project'))
        self.assertFalse(any(c.args[1]['operation']=='model' for c in calls.call_args_list))
    def test_thermal_unavailable_stays_unknown(self):
        with patch.object(probe.subprocess,'run',side_effect=subprocess.TimeoutExpired('pmset',1)):
            sample=probe.thermal_sample()
        self.assertFalse(sample['available']);self.assertIsNone(sample['reportedLimits'])


if __name__=='__main__':unittest.main()
