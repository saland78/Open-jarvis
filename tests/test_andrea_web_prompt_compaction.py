"""Static instructions preserve evidence and validators; gains need Mac data."""
import ast
import copy
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import check_web_compact_v9 as check
import web_candidate_pipeline as pipeline
import web_prompt_compaction_probe as probe
import web_cpu_batch_probe as previous
from test_andrea_web_cpu_batch import Transport, frames
from test_andrea_web_compact_integration import csv_page
from test_andrea_web_capability_scope import page
from test_andrea_web_heading_latency import GOOD_CSV

ROOT = Path(__file__).resolve().parents[1]


def prepared(index):
    return pipeline.prepare(page() if index == 0 else csv_page(), check.CASES[index]['question'])


def row(index, variant):
    return {'case': check.CASES[index]['id'], 'variant': variant,
            'sourceTextSha256': 'same', 'referencePreparationSha256': 'same',
            'nativeSchemaSha256': 'same', 'modelSourceCharacters': 2000, 'observerClosed': True,
            'residency': {'expectedModelLoaded': True, 'sizeVram': 0},
            'result': {'completed': True, 'doneReason': 'stop',
                       'totalClientMs': 5000 if variant == 'reference' else 4000,
                       'native': {'prompt_eval_count': 1000 if variant == 'reference' else 800,
                                  'prompt_eval_cached_count': 0,
                                  'prompt_eval_duration': 2000000000 if variant == 'reference' else 1600000000,
                                  'eval_duration': 900000000, 'eval_count': 70,
                                  'load_duration': 1000, 'total_duration': 3000000000}},
            'checks': {'outcome': 'abstained' if index == 2 else 'accepted_pending_semantic_review',
                       'claims': [{}]*(2, 1, 0)[index]}, 'qualityVerdict': 'pending_review'}


class PreparationTests(unittest.TestCase):
    def test_source_schema_and_every_existing_metadata_value_preserved_all_cases(self):
        for index in range(3):
            before=prepared(index); snapshot=copy.deepcopy(before)
            after=probe.compact_prepared(before)
            proof=probe.input_proof(before,after)
            self.assertTrue(proof['sourceBytesAndReferencesIdentical'])
            self.assertTrue(proof['nativeSchemaIdentical'])
            self.assertTrue(proof['existingMetadataValuesIdentical'])
            self.assertEqual(before,snapshot)
            self.assertEqual(list(json.loads(after[1][1]['content']))[-1],'question')

    def test_system_is_fixed_across_different_pages_questions_and_output_limits(self):
        systems=[probe.compact_prepared(prepared(i))[1][0]['content'] for i in range(3)]
        self.assertEqual(systems,[probe.STATIC_SYSTEM]*3)
        limits=[json.loads(probe.compact_prepared(prepared(i))[1][1]['content'])['claimLimit'] for i in range(3)]
        self.assertEqual(limits,[2,1,2])

    def test_less_instruction_text_is_not_claimed_as_seconds_or_tokens(self):
        for index in range(3):
            before=prepared(index);proof=probe.input_proof(before,probe.compact_prepared(before))
            self.assertLess(proof['compactMessagesCharacters'],proof['referenceMessagesCharacters'])
            self.assertTrue(proof['charactersAreNotTokenMeasurements'])

    def test_ordinary_question_cannot_get_forced_empty_schema(self):
        after=probe.compact_prepared(prepared(2))
        self.assertEqual(after[2]['properties']['claims']['maxItems'],2)
        self.assertEqual(after[2]['properties']['claims'].get('minItems',0),0)

    def test_bad_input_alignment_refuses_before_inference(self):
        before=list(copy.deepcopy(prepared(0)))
        payload=json.loads(before[1][1]['content']);payload['passages'][0][1]='changed'
        before[1][1]['content']=json.dumps(payload)
        with self.assertRaisesRegex(ValueError,'contract_changed'):probe.compact_prepared(before)

    def test_claim_budget_cannot_be_changed_by_compaction(self):
        before=list(copy.deepcopy(prepared(1)))
        before[2]['properties']['claims']['maxItems']=2
        with self.assertRaisesRegex(ValueError,'not_aligned'):probe.compact_prepared(before)

    def test_proof_refuses_metadata_removal_reference_change_or_schema_change(self):
        before=prepared(0)
        for target in ('metadata','passage','schema'):
            after=list(copy.deepcopy(probe.compact_prepared(before)))
            if target=='schema':after[2]['properties']['claims']['maxItems']=1
            else:
                payload=json.loads(after[1][1]['content'])
                if target=='metadata':del payload['protectedIdentifiers']
                else:payload['passages'][1][0]=999
                after[1][1]['content']=json.dumps(payload)
            with self.assertRaisesRegex(ValueError,'changed'):probe.input_proof(before,after)

    def test_original_conditional_csv_validator_remains_mandatory(self):
        source=csv_page();bank,_,_,selection=probe.compact_prepared(prepared(1))
        ref=selection['outputPolicy']['sourceRuleRefs'][0]
        raw=json.dumps({'claims':[{'passage':ref,'text':GOOD_CSV}]})
        good=pipeline.validate(raw,bank,True,source,selection)
        self.assertEqual(probe.control_audit(good,selection),good)
        self.assertEqual(good['claims'][0]['text'],GOOD_CSV)
        bad=json.dumps({'claims':[{'passage':ref,'text':'csv.reader converte automaticamente tutti i campi in float.'}]})
        self.assertEqual(pipeline.validate(bad,bank,True,source,selection)['outcome'],'rejected')

    def test_unknown_citation_incomplete_sentence_and_unrelated_fact_still_rejected(self):
        for raw in ('{"claims":[{"passage":999,"text":"Una frase completa."}]}',
                    '{"claims":[{"passage":2,"text":"Parola incomple"}]}'):
            bank,_,_,selection=probe.compact_prepared(prepared(0))
            self.assertEqual(pipeline.validate(raw,bank,True,page(),selection)['outcome'],'rejected')
        bank,_,_,selection=probe.compact_prepared(prepared(2))
        ref=selection['selectedRefs'][-1]
        raw=json.dumps({'claims':[{'passage':ref,'text':GOOD_CSV}]})
        self.assertEqual(pipeline.validate(raw,bank,True,csv_page(),selection)['outcome'],'rejected')


class ObservedControlFailureTests(unittest.TestCase):
    def test_both_actual_bad_batch_answers_refused_whole_without_reanchoring(self):
        report=json.loads((ROOT/'docs/andrea/web-cpu-batch-mac-2026-10-07.json').read_text())
        for row in report['originalAutomaticReport']['rows'][:2]:
            original=copy.deepcopy(row['checks'])
            result=probe.control_audit(original,{'sourceCapabilityScopePolicy':{'active':True}})
            self.assertEqual(result['reason'],'control_not_in_own_operation_passage')
            self.assertEqual(result['claims'],[])
            self.assertEqual(result['details']['claimIndex'],2)
            self.assertEqual(result['details']['quote'],original['claims'][1]['quote'])
            self.assertEqual(original,row['checks'])
        self.assertEqual(report['manualReviewCounts'],{'favorable':4,'unfavorable':2})

    def test_supported_control_and_running_are_not_rejected(self):
        for text,quote in [('Permette di controllare sottoprocessi.','control subprocesses;\n'),
                           ('Permette di eseguire sottoprocessi.','running subprocesses;\n')]:
            value={'outcome':'accepted_pending_semantic_review','claims':[{'text':text,'quote':quote,'passage':8}]}
            self.assertIs(probe.control_audit(value,{'sourceCapabilityScopePolicy':{'active':True}}),value)

    def test_prior_refusals_and_genuine_abstention_are_unchanged(self):
        for value in ({'outcome':'rejected','claims':[],'reason':'old'}, {'outcome':'abstained','claims':[]}):
            self.assertIs(probe.control_audit(value,{}),value)

    def test_other_source_control_does_not_license_claims_own_running_passage(self):
        value={'outcome':'accepted_pending_semantic_review','claims':[
            {'text':'Permette di controllare sottoprocessi.','quote':'running subprocesses;\n','passage':5}]}
        selection={'sourceCapabilityScopePolicy':{'active':True,'eligibleOperationRefs':[4,5]}}
        self.assertEqual(probe.control_audit(value,selection)['outcome'],'rejected')


class TransportTests(unittest.TestCase):
    def test_one_model_post_preserves_schema_source_and_production_options(self):
        _,messages,schema,_=probe.compact_prepared(prepared(2))
        transport=Transport(frames('{"claims":[]}'))
        result=probe.stream_once(messages,schema,512,transport)
        self.assertEqual(result['raw'],'{"claims":[]}');self.assertTrue(result['completed'])
        self.assertEqual(len(transport.calls),1)
        payload=json.loads(transport.calls[0][0].data)
        self.assertEqual(payload['messages'],messages);self.assertEqual(payload['format'],schema)
        self.assertEqual(payload['options'],previous.request_options(512))
        self.assertFalse(payload['think']);self.assertEqual(payload['keep_alive'],'15m')
        self.assertNotIn('num_thread',payload['options'])

    def test_rejected_batch_option_never_reaches_transport(self):
        transport=Transport(frames('{}'))
        with self.assertRaisesRegex(ValueError,'production_batch'):probe.stream_once([],{},128,transport)
        self.assertEqual(transport.calls,[])

    def test_length_and_eof_are_never_completed_or_retried(self):
        for stream in (frames('{}','length'),[{'done':False,'message':{'content':'{}'}}]):
            transport=Transport(stream);result=probe.stream_once([],{},512,transport)
            self.assertFalse(result['completed']);self.assertEqual(result['raw'],'{}')
            self.assertEqual(len(transport.calls),1)

    def test_answer_over_limit_refused_without_trimming(self):
        transport=Transport(frames('x'*5001))
        with self.assertRaises(ValueError):probe.stream_once([],{},512,transport)
        self.assertEqual(len(transport.calls),1)

    def test_timeout_kills_only_owned_child(self):
        child=SimpleNamespace(communicate=Mock(side_effect=[subprocess.TimeoutExpired('owned',1),(b'',b'')]),
                              poll=Mock(return_value=None),kill=Mock())
        observer=SimpleNamespace(start=Mock(),close=Mock(return_value=True),rows=[])
        with patch.object(probe.subprocess,'Popen',return_value=child),patch.object(probe,'Observer',return_value=observer):
            with self.assertRaisesRegex(ValueError,'deadline'):probe.owned_worker(Path('/project'),{},1,True)
        child.kill.assert_called_once();observer.close.assert_called_once()

    def test_transport_deadline_parser_and_cleanup_are_exact_tested_batch_helpers(self):
        def definitions(module):
            tree=ast.parse(Path(module.__file__).read_text())
            return {n.name:ast.dump(n) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        old,new=definitions(previous),definitions(probe)
        for name in ('stream_once','owned_worker','load_project','numeric_metrics','opener','NoRedirect','Observer'):
            self.assertEqual(old[name],new[name],name)


class GateTests(unittest.TestCase):
    def rows(self):return [row(i,v) for i,v in probe.ORDER]
    def test_timing_and_shapes_are_not_meaning_or_installation(self):
        result=probe.comparison(self.rows())
        self.assertTrue(result['numericGatesMet']);self.assertTrue(result['candidateTechnicalShapesMet'])
        self.assertFalse(result['integrationAllowed']);self.assertEqual(result['qualityVerdict'],'pending_review')
        self.assertIn('not_measured',result['prefixCacheBenefit'])

    def test_positive_empty_answer_cannot_pass_as_solution(self):
        rows=self.rows();rows[1]['checks']={'outcome':'abstained','claims':[]}
        result=probe.comparison(rows)
        self.assertFalse(result['candidateTechnicalShapesMet']);self.assertEqual(result['decision'],'do_not_adopt')

    def test_candidate_control_rejection_cannot_pass_despite_fast_time(self):
        rows=self.rows();rows[1]['checks']={'outcome':'rejected','claims':[]}
        self.assertEqual(probe.comparison(rows)['decision'],'do_not_adopt')

    def test_no_gain_or_total_regression_prevents_adoption(self):
        for path,value in [('prompt_eval_count',999),('prompt_eval_duration',1990000000),('totalClientMs',6000)]:
            rows=self.rows()
            if path=='totalClientMs':rows[1]['result'][path]=value
            else:rows[1]['result']['native'][path]=value
            self.assertEqual(probe.comparison(rows)['decision'],'do_not_adopt')

    def test_missing_answer_must_also_have_lower_input_and_no_total_regression(self):
        for field,value in [('prompt_eval_count',1000),('totalClientMs',6000)]:
            rows=self.rows()
            if field=='totalClientMs':rows[-1]['result'][field]=value
            else:rows[-1]['result']['native'][field]=value
            self.assertFalse(probe.comparison(rows)['numericGatesMet'])

    def test_cache_unknown_metrics_changed_source_or_gpu_invalidates_comparison(self):
        for target in ('cached','unknown','source','schema','preparation','gpu'):
            rows=self.rows();r=rows[1]
            if target=='cached':r['result']['native']['prompt_eval_cached_count']=100
            elif target=='unknown':del r['result']['native']['prompt_eval_cached_count']
            elif target=='gpu':r['residency']['sizeVram']=1024
            else:r[{'source':'sourceTextSha256','schema':'nativeSchemaSha256','preparation':'referencePreparationSha256'}[target]]='changed'
            self.assertFalse(probe.comparison(rows)['pairs'][0]['eligible'])

    def test_partial_reordered_duplicate_or_error_rows_cannot_pass(self):
        rows=self.rows()
        for bad in (rows[:3],list(reversed(rows)),rows+[rows[0]],
                    rows[:1]+[{'case':rows[1]['case'],'variant':'compact','error':'timeout'}]):
            self.assertEqual(probe.comparison(bad)['decision'],'do_not_adopt')


class OrchestrationTests(unittest.TestCase):
    def test_changed_checker_refuses_before_import(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'scripts/andrea').mkdir(parents=True)
            (root/'scripts/andrea/check_web_compact_v9.py').write_text('raise RuntimeError("no import")')
            with self.assertRaisesRegex(ValueError,'checker_changed'):probe.load_project(root)

    def test_six_calls_once_with_unchanged_pages_and_no_install(self):
        def owned(project,payload,timeout,observe=False):
            if payload['operation']=='metadata':return {},[],True
            if payload['operation']=='read':return page() if payload['case']==0 else csv_page(),[],True
            return row(payload['case'],payload['variant']),[],True
        with patch.object(probe.platform,'system',return_value='Darwin'),patch.object(probe,'load_project',return_value=(check,pipeline)),patch.object(probe,'owned_worker',side_effect=owned) as calls:
            result=probe.run(Path('/project'),emit=lambda *a,**k:None)
        model=[c.args[1] for c in calls.call_args_list if c.args[1]['operation']=='model']
        self.assertEqual([(p['case'],p['variant']) for p in model],list(probe.ORDER))
        self.assertEqual(len({p['marker'] for p in model}),6)
        self.assertEqual(model[2]['page'],model[-1]['page'])
        self.assertFalse(result['productionModified']);self.assertFalse(result['vaultRead'])
        self.assertFalse(result['modelOptionsChanged']);self.assertEqual(result['automaticRetries'],0)

    def test_interrupted_model_transport_stops_series_without_retry(self):
        def owned(project,payload,timeout,observe=False):
            if payload['operation']=='metadata':return {},[],True
            if payload['operation']=='read':return csv_page(),[],True
            r=row(payload['case'],payload['variant']);r['result']['completed']=False
            return r,[],True
        with patch.object(probe.platform,'system',return_value='Darwin'),patch.object(probe,'load_project',return_value=(check,pipeline)),patch.object(probe,'owned_worker',side_effect=owned):
            result=probe.run(Path('/project'),emit=lambda *a,**k:None)
        self.assertEqual(result['completedRows'],1);self.assertEqual(result['comparison']['decision'],'do_not_adopt')

    def test_worker_retains_raw_answer_and_calls_original_validation_once(self):
        source={**csv_page(),'pageId':'token','sourceId':'W1','modelUsed':False}
        generated={'raw':'{"claims":[]}','completed':True,'doneReason':'stop','native':{}}
        with patch.object(probe,'load_project',return_value=(check,pipeline)),patch.object(probe,'stream_once',return_value=generated) as stream,patch.object(probe,'cpu_residency',return_value={}),patch.object(pipeline,'validate',wraps=pipeline.validate) as validate:
            r=probe.worker(Path('/project'),{'operation':'model','case':2,'variant':'compact','page':source,'marker':'a'*32})
        validate.assert_called_once();self.assertEqual(validate.call_args.args[0],generated['raw'])
        self.assertEqual(r['checks']['outcome'],'abstained');self.assertEqual(r['result']['raw'],'{"claims":[]}')
        self.assertEqual(stream.call_args.args[2],512)


if __name__=='__main__':unittest.main()
