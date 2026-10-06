"""Actual control-to-execution regressions and native source-verb preparation."""
import ast
import copy
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import unittest
from unittest.mock import patch

import web_native_operation_verb as verbs
import web_native_operation_verb_probe as candidate
import web_operation_predicate_probe as previous
from test_andrea_web_capability_scope import page, NETWORK, CONTROL, CSV_RULE
from test_andrea_web_definition_context import extracted, html_entry
import test_andrea_web_native_identifiers as native_tests
from test_andrea_web_native_identifiers import branch_for, pattern_allows

ROOT = Path(__file__).resolve().parents[1]


def observed():
    return json.loads((ROOT/'docs/andrea/web-operation-predicate-v8-mac-2026-10-06.json').read_text())


def validate(raw, bank, selection):
    result = candidate.context.validate(raw, bank, True, heading_ranges=[], contract=candidate.baseline, selection=selection)
    result = candidate.rule_budget.validate_cardinality(result, selection['outputPolicy'])
    for adapter in (candidate.source_labels, candidate.native_identifiers, candidate.capability_evidence,
                    candidate.performance_scope, candidate.question_focus, candidate.operation_scope,
                    candidate.operation_verb):
        result = adapter.validate_generation(result, selection)
    return result


class SubmittedV8Tests(unittest.TestCase):
    def test_original_rejection_and_separate_meaning_reviews_are_preserved(self):
        report = observed()
        self.assertEqual(report['originalAutomaticReport']['completedTransports'], 6)
        self.assertFalse(report['originalAutomaticReport']['technicalCaseShapesMet'])
        self.assertEqual(report['originalAutomaticReport']['performanceOutcome'], 'gates_not_met')
        self.assertTrue(all(pair['performanceGateMet'] for pair in report['originalAutomaticReport']['pairs']))
        self.assertEqual(report['originalTechnicalShapeCounts'], {'met':5,'notMet':1})
        self.assertEqual(report['manualReviewCounts'], {'favorable':5,'unfavorable':1})
        self.assertEqual(report['compactManualReviewCounts'], {'favorable':3,'unfavorable':0})
        self.assertEqual(report['overallReview'], 'not_passed_no_adoption')
        self.assertEqual(report['rows'][0]['checks']['reason'], 'operation_example_not_in_own_passage')
        self.assertEqual(report['rows'][0]['manualReview']['outcome'], 'unfavorable')
        self.assertNotIn('/Users/', json.dumps(report))
        self.assertNotIn('Last login:', json.dumps(report))

    def test_actual_bad_predicate_is_excluded_by_the_native_branch_before_generation(self):
        row = observed()['rows'][0]
        claim = row['checks']['details']
        self.assertEqual(claim['quote'], CONTROL)
        self.assertEqual(claim['text'], 'asyncio consente l\'esecuzione di sottoprocessi.')
        bank, _, schema, selection = candidate.prepared(page(), candidate.baseline.CASES[0], 'production')
        ref = bank.index(CONTROL)+1
        self.assertFalse(pattern_allows(schema, ref, claim['text']))
        before = copy.deepcopy(row['preOperationPredicateChecks'])
        rule = selection['nativeOperationVerbPolicy']['rules'][0]
        rule = {**rule, 'passage':claim['passage']}
        result = verbs.validate_generation(before, {'nativeOperationVerbPolicy':{'rules':[rule]}})
        self.assertEqual(result['reason'], 'native_operation_verb_not_observed')
        self.assertEqual(before, row['preOperationPredicateChecks'])
        self.assertEqual(len(json.loads(row['result']['modelAnswer'])['claims']), 2)

    def test_previous_added_execution_example_is_not_forgiven(self):
        old = json.loads((ROOT/'docs/andrea/web-question-focus-v7-mac-2026-10-06.json').read_text())
        text = old['rows'][0]['checks']['claims'][1]['text']
        bank, _, schema, _ = candidate.prepared(page(), candidate.baseline.CASES[0], 'compact')
        self.assertFalse(pattern_allows(schema, bank.index(CONTROL)+1, text))
        self.assertEqual(old['rows'][0]['checks']['outcome'], 'accepted_pending_semantic_review')

    def test_original_pair_numbers_and_failed_overall_gate_recompute_from_raw_metrics(self):
        report = observed()
        recalculated = candidate.baseline.comparison(report['rows'])
        for key in ('pairs','allNativeCacheCountsEligible','technicalCaseShapesMet','performanceOutcome','fixedGates'):
            self.assertEqual(recalculated[key], report['originalAutomaticReport'][key])
        self.assertEqual([row['result']['native']['prompt_eval_cached_count'] for row in report['rows']], [0,3,4,3,3,3])


class SourceVerbTests(unittest.TestCase):
    def test_positive_control_fragments_are_recognized_without_page_or_reference_constants(self):
        for source in (CONTROL, 'control remote devices;\n', 'control IPC processes.\n'):
            self.assertTrue(verbs.simple_control_statement(source))
        for source in ('run subprocesses;\n', 'Control subprocesses;\n', 'control subprocesses',
                       'do not control subprocesses;\n', 'control no subprocesses;\n',
                       'control devices unless disabled;\n', 'control devices and execute commands;\n',
                       'control devices with a shell;\n', 'The API controls subprocesses.\n'):
            self.assertFalse(verbs.simple_control_statement(source), source)

    def test_only_control_branches_change_and_both_free_complements_are_possible(self):
        for variant in ('production','compact'):
            before = previous.prepared(page(), previous.baseline.CASES[0], variant)
            bank, messages, schema, selection = candidate.prepared(page(), candidate.baseline.CASES[0], variant)
            ref = bank.index(CONTROL)+1
            self.assertNotEqual(branch_for(schema,ref), branch_for(before[2],ref))
            for other in selection['sourceCapabilityScopePolicy']['eligibleOperationRefs']:
                if other != ref:
                    expected=copy.deepcopy(branch_for(before[2],other))
                    expected['properties']['passage']['enum']=[r for r in expected['properties']['passage']['enum'] if r!=ref]
                    self.assertEqual(branch_for(schema,other),expected)
            for text in ('Permette di controllare i sottoprocessi.', 'Consente di controllare i processi figli.'):
                self.assertTrue(pattern_allows(schema,ref,text))
                self.assertTrue(pattern_allows(before[2],ref,text))
            self.assertNotIn('enum', branch_for(schema,ref)['properties']['text'])
            self.assertNotIn('maxLength', json.dumps(schema))
            self.assertFalse(selection['nativeOperationVerbPolicy']['wholeSentenceForced'])
            self.assertFalse(selection['nativeOperationVerbPolicy']['sourceObjectForced'])
            self.assertEqual(schema['properties']['claims'].get('minItems',0),0)
            self.assertEqual(schema['properties']['claims']['maxItems'], before[2]['properties']['claims']['maxItems'])
            self.assertEqual(bank, before[0])
            self.assertEqual(selection['selectedRefs'], before[3]['selectedRefs'])
            payload=json.loads(messages[1]['content']); old=json.loads(before[1][1]['content'])
            self.assertEqual({k:v for k,v in payload.items() if k!='sourceControlVerbStarts'},old)
            self.assertEqual(list(payload)[-1],'question')

    def test_native_verb_and_old_foreign_label_constraint_compose(self):
        bank, _, schema, selection = candidate.prepared(page(), candidate.baseline.CASES[0], 'compact')
        ref=bank.index(CONTROL)+1
        for text in ('I/O: Permette di controllare i sottoprocessi.',
                     'IPC: Consente di controllare i sottoprocessi.',
                     'Permette di eseguire i sottoprocessi.',
                     'asyncio consente l\'esecuzione di sottoprocessi.'):
            self.assertFalse(pattern_allows(schema,ref,text))
        guard=next(g for g in selection['sourceLabelScopePolicy']['guardBranches'] if ref in g['passages'])
        for starter in verbs.CONTROL_STARTS:
            for complement in ('i sottoprocessi.','dispositivi remoti.','i processi tramite una API.'):
                self.assertIsNotNone(re.fullmatch(guard['pattern'],starter+complement))

    def test_existing_mandatory_source_names_stay_before_the_control_verb(self):
        p=extracted('<p>'+NETWORK+'</p><p>control IPC processes;</p>')
        bank, _, schema, selection=candidate.prepared(p,candidate.baseline.CASES[0],'production')
        ref=next(i+1 for i,q in enumerate(bank) if q.startswith('control'))
        rule=next(r for r in selection['nativeOperationVerbPolicy']['rules'] if r['passage']==ref)
        self.assertEqual(rule['sourceStart'],'IPC: ')
        self.assertTrue(pattern_allows(schema,ref,'IPC: Consente di controllare i processi.'))
        self.assertFalse(pattern_allows(schema,ref,'Consente di controllare i processi IPC.'))
        prior=next(r for r in selection['nativeIdentifierPolicy']['rules'] if r['passage']==ref)
        self.assertIsNotNone(re.fullmatch(prior['pattern'],'IPC: Consente di controllare i processi.'))

    def test_added_execution_in_free_complement_still_fails_previous_guard(self):
        bank, _, schema, selection=candidate.prepared(page(),candidate.baseline.CASES[0],'compact')
        ref=bank.index(CONTROL)+1
        text='Consente di controllare i sottoprocessi ed eseguire comandi esterni.'
        # The new grammar encodes the main verb, not general entailment. It
        # must not replace the existing operation/example application guard.
        self.assertTrue(pattern_allows(schema,ref,text))
        result=validate(json.dumps({'claims':[{'passage':ref,'text':text}]}),bank,selection)
        self.assertEqual(result['reason'],'operation_example_not_in_own_passage')
        self.assertEqual(result['claims'],[])
        self.assertFalse(selection['nativeOperationVerbPolicy']['semanticEntailmentCertified'])

    def test_genuine_abstentions_and_previous_refusals_are_unchanged(self):
        for result in ({'outcome':'abstained','claims':[]},
                       {'outcome':'rejected','reason':'operation_example_not_in_own_passage','claims':[]}):
            self.assertIs(verbs.validate_generation(result,{}),result)

    def test_unknown_prior_patterns_are_never_overwritten_and_double_apply_fails(self):
        bank,messages,schema,selection=previous.prepared(page(),previous.baseline.CASES[0],'production')
        ref=bank.index(CONTROL)+1
        broken=copy.deepcopy(schema)
        branch_for(broken,ref)['properties']['text']['pattern']='^Unknown.*[.]$'
        with self.assertRaisesRegex(ValueError,'native_operation_prior_constraint_not_compatible'):
            verbs.apply(bank,messages,broken,selection,contract=candidate.baseline,native_contract=candidate.native_identifiers)
        revised=verbs.apply(bank,messages,schema,selection,contract=candidate.baseline,native_contract=candidate.native_identifiers)
        with self.assertRaisesRegex(ValueError,'native_operation_already_applied'):
            verbs.apply(*revised,contract=candidate.baseline,native_contract=candidate.native_identifiers)

    def test_source_alignment_failure_does_not_construct_native_rules(self):
        bank,messages,schema,selection=previous.prepared(page(),previous.baseline.CASES[0],'compact')
        bank[bank.index(CONTROL)]='run external commands;\n'
        with self.assertRaisesRegex(ValueError,'native_operation_source_alignment_failed'):
            verbs.apply(bank,messages,schema,selection,contract=candidate.baseline,native_contract=candidate.native_identifiers)

    def test_csv_and_missing_prompts_and_schemas_remain_exact_v8(self):
        cp=extracted('<h1>csv</h1>'+html_entry('csv.reader','<p>'+CSV_RULE+'</p>'))
        for index in (1,2):
            for variant in ('production','compact'):
                before=previous.prepared(cp,previous.baseline.CASES[index],variant)
                after=candidate.prepared(cp,candidate.baseline.CASES[index],variant)
                self.assertEqual(after[:3],before[:3])
                self.assertEqual(after[3]['nativeOperationVerbPolicy']['rules'],[])
                self.assertFalse(after[3]['nativeOperationVerbPolicy']['nativeSchemaChanged'])


class NewPatternConverterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        native_tests.PinnedNativePatternTests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        native_tests.PinnedNativePatternTests.tearDownClass.__func__(cls)

    def test_new_simple_and_source_name_prefixed_patterns_compile_in_b11232(self):
        for prefix in ('','IPC: ','I/O di rete: '):
            expression=verbs.control_pattern(prefix,native_contract=candidate.native_identifiers)
            result=subprocess.run([str(self.binary)],input=expression,text=True,capture_output=True,timeout=3)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('root ::=',result.stdout)
            for starter in verbs.CONTROL_STARTS:
                self.assertIn('"'+starter+'"',result.stdout)
            self.assertNotIn('(?=',expression)
            self.assertNotIn('.*',expression[:expression.index('controllare')])


class RunnerBoundaryTests(unittest.TestCase):
    def test_all_twelve_prior_sources_and_transport_functions_are_exact_v8(self):
        for node in ast.parse((ROOT/'scripts/andrea/web_operation_predicate_probe.py').read_text()).body:
            if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id.endswith('_SOURCE'):
                name=node.targets[0].id
                self.assertEqual(getattr(candidate,name),getattr(previous,name))
        self.assertEqual(candidate.NATIVE_OPERATION_VERB_SOURCE,(ROOT/'scripts/andrea/web_native_operation_verb.py').read_text())
        for name in ('CASES','ORDER','EXPECTED','MAX_CACHED_TOKENS','MIN_UNCACHED_FRACTION','MIN_INPUT_REDUCTION_PERCENT','MIN_PREFILL_REDUCTION_PERCENT'):
            self.assertEqual(getattr(candidate.baseline,name),getattr(previous.baseline,name))
        def functions(filename):
            return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse((ROOT/'scripts/andrea'/filename).read_text()).body if isinstance(n,ast.FunctionDef)}
        old=functions('web_operation_predicate_probe_body.py'); new=functions('web_native_operation_verb_probe_body.py')
        for name in ('collect','model_worker','read_page','page_worker','thermal_sample','checked_worker'):
            self.assertEqual(new[name],old[name],name)

    def test_native_schema_reaches_ollama_once_with_unchanged_model_options(self):
        _,messages,schema,selection=candidate.prepared(page(),candidate.baseline.CASES[0],'compact')
        isolated=candidate.baseline.isolated_messages(messages,'Z'+'a'*32)
        calls=[]
        class Opener:
            def open(self,request,timeout):
                calls.append((json.loads(request.data),timeout))
                return io.BytesIO(b'{"message":{"content":"{\\"claims\\":[]}"},"done":true,"done_reason":"stop"}\n')
        candidate.baseline.stream_probe(Opener(),isolated,schema)
        self.assertEqual(len(calls),1)
        body,timeout=calls[0]
        self.assertEqual(body['format'],schema)
        self.assertEqual(body['messages'],isolated)
        self.assertEqual(body['options'],{'temperature':.4,'num_predict':512,'num_ctx':4096})
        self.assertEqual(body['keep_alive'],'15m')
        self.assertFalse(body['think'])
        self.assertEqual(timeout,90)
        self.assertTrue(selection['nativeOperationVerbPolicy']['nativeSchemaChanged'])
        self.assertEqual(isolated[1],messages[1])

    def mock_series(self, *, bad_complement=False, wrong_missing=False, timeout=False):
        ap=page(); ap['url']=candidate.baseline.CASES[0]['url']
        cp=extracted('<h1>csv</h1>'+html_entry('csv.reader','<p>'+CSV_RULE+'</p>')); cp['url']=candidate.baseline.CASES[1]['url']
        pages={ap['url']:ap,cp['url']:cp}; calls=[]; emitted=[]
        class Reader:
            def get(self,path):
                return {'version':candidate.EXPECTED_OLLAMA_VERSION} if path=='/api/version' else {'models':[]}
        def collect(project,p,index,variant):
            calls.append((index,variant))
            if timeout and len(calls)==2:
                return {'result':{'status':'error','errorKind':'timeout','modelAnswer':'','native':candidate.baseline.native_metrics({})}},[],[],True
            bank=candidate.baseline.sentence_bank(p['text'])
            if index==0:
                text='Consente di controllare i sottoprocessi.'
                if bad_complement and variant=='production': text='Consente di controllare i sottoprocessi ed eseguire comandi esterni.'
                claims=[{'passage':bank.index(NETWORK)+1,'text':'I/O di rete e IPC: asyncio permette queste operazioni.'},
                        {'passage':bank.index(CONTROL)+1,'text':text}]
            elif index==1 or (wrong_missing and variant=='compact'):
                claims=[{'passage':next(i+1 for i,q in enumerate(bank) if 'No automatic data type conversion' in q),
                         'text':json.loads(observed()['rows'][2]['result']['modelAnswer'])['claims'][0]['text']}]
            else: claims=[]
            metrics={'prompt_eval_count':2800 if variant=='production' else 1400,'prompt_eval_cached_count':0,
                     'prompt_evalMs':50000 if variant=='production' else 25000}
            return {'result':{'status':'completed','modelAnswer':json.dumps({'claims':claims}),'native':metrics}},[],[],True
        with patch.object(candidate.platform,'system',return_value='Darwin'), patch.object(candidate.baseline,'verify_project'), \
                patch.object(candidate.resources,'Reader',Reader), patch.object(candidate,'read_page',side_effect=lambda project,url:copy.deepcopy(pages[url])), \
                patch.object(candidate,'thermal_sample',return_value={}), patch.object(candidate,'collect',side_effect=collect):
            if timeout:
                with self.assertRaisesRegex(ValueError,'series_stopped_after_incomplete_request_no_retry'):
                    candidate.run(ROOT,emit=emitted.append)
                report=json.loads(next(v for v in reversed(emitted) if v.startswith('{')))
            else: report=candidate.run(ROOT,emit=emitted.append)
        rows=[json.loads(v) for v in emitted if v.startswith('{') and '"variant"' in v and '"case"' in v]
        return calls,report,rows,emitted

    def test_mock_acceptable_six_requests_do_not_certify_meaning_or_allow_install(self):
        calls,report,rows,emitted=self.mock_series()
        self.assertEqual(calls,list(candidate.baseline.ORDER))
        self.assertEqual(report['completedTransports'],6)
        self.assertTrue(report['technicalCaseShapesMet'])
        self.assertTrue(report['nativeOperationSchemaChanged'])
        self.assertTrue(report['previousV8MeasurementsNotReused'])
        self.assertFalse(report['integrationAllowedByThisAutomaticReport'])
        self.assertEqual(report['qualityVerdict'],'pending_review')
        self.assertFalse(report['wholeModelSentenceForced'])
        self.assertFalse(report['modelOutputRewritten'])
        self.assertEqual([r['nativeOperationVerbConstraintApplied'] for r in rows],[True,True,False,False,False,False])
        self.assertIn('non premere Command+R o Control+C',emitted[0])

    def test_bad_tail_still_fails_whole_answer_without_rewriting_or_dropping_it(self):
        _,report,rows,_=self.mock_series(bad_complement=True)
        self.assertFalse(report['technicalCaseShapesMet'])
        self.assertEqual(report['performanceOutcome'],'gates_not_met')
        self.assertEqual(rows[0]['preOperationPredicateChecks']['outcome'],'accepted_pending_semantic_review')
        self.assertEqual(rows[0]['checks']['reason'],'operation_example_not_in_own_passage')
        self.assertEqual(rows[0]['preNativeOperationVerbChecks'],rows[0]['checks'])
        self.assertEqual(len(json.loads(rows[0]['result']['modelAnswer'])['claims']),2)

    def test_unrelated_missing_answer_is_not_relabeled_as_genuine_abstention(self):
        _,report,rows,_=self.mock_series(wrong_missing=True)
        self.assertFalse(report['technicalCaseShapesMet'])
        self.assertEqual(rows[-1]['checks']['outcome'],'rejected')
        self.assertFalse(rows[-1]['nativeOperationVerbConstraintApplied'])
        self.assertNotEqual(json.loads(rows[-1]['result']['modelAnswer']),{'claims':[]})

    def test_incomplete_transport_stops_after_owned_call_without_retry(self):
        calls,report,_,_=self.mock_series(timeout=True)
        self.assertEqual(calls,list(candidate.baseline.ORDER)[:2])
        self.assertEqual(report['completedTransports'],1)
        self.assertEqual(report['notExecutedRequests'],4)

    def test_preparation_leaves_installed_sources_unchanged(self):
        paths=[ROOT/p for p in candidate.baseline.EXPECTED if (ROOT/p).exists()]
        before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        for variant in ('production','compact'):
            candidate.prepared(page(),candidate.baseline.CASES[0],variant)
        self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})


if __name__=='__main__':
    unittest.main()
