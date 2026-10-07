"""Real-output regressions for own-operation examples and genuine abstention."""
import ast
import copy
import hashlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import web_operation_predicate_scope as scope
import web_operation_predicate_probe as candidate
import web_question_focus_probe as previous
from test_andrea_web_capability_scope import page, NETWORK, CONTROL, CSV_RULE
from test_andrea_web_definition_context import extracted, html_entry

ROOT = Path(__file__).resolve().parents[1]


def observed():
    return json.loads((ROOT/'docs/andrea/web-question-focus-v7-mac-2026-10-06.json').read_text())


def validate(raw, bank, selection):
    result = candidate.context.validate(raw, bank, True, heading_ranges=[], contract=candidate.baseline, selection=selection)
    result = candidate.rule_budget.validate_cardinality(result, selection['outputPolicy'])
    for adapter in (candidate.source_labels, candidate.native_identifiers, candidate.capability_evidence,
                    candidate.performance_scope, candidate.question_focus, candidate.operation_scope):
        result = adapter.validate_generation(result, selection)
    return result


class SubmittedV7Tests(unittest.TestCase):
    def test_all_automatic_results_and_separate_unfavorable_meaning_are_preserved(self):
        report = observed()
        self.assertEqual(report['originalAutomaticReport']['completedTransports'], 6)
        self.assertEqual(report['originalAutomaticReport']['performanceOutcome'], 'measured_gates_met_pending_semantic_review')
        self.assertTrue(all(pair['performanceGateMet'] for pair in report['originalAutomaticReport']['pairs']))
        self.assertEqual(report['originalTechnicalShapeCounts'], {'met':6, 'notMet':0})
        self.assertEqual(report['manualReviewCounts'], {'favorable':5, 'unfavorable':1})
        self.assertEqual(report['compactManualReviewCounts'], {'favorable':3, 'unfavorable':0})
        self.assertEqual(report['overallReview'], 'not_passed_no_adoption')
        self.assertNotIn('/Users/', json.dumps(report))
        self.assertNotIn('Last login:', json.dumps(report))

    def test_actual_added_command_example_is_rejected_without_output_repair(self):
        row = observed()['rows'][0]
        original = copy.deepcopy(row['checks'])
        self.assertEqual(original['outcome'], 'accepted_pending_semantic_review')
        self.assertEqual(original['claims'][1]['quote'], 'control subprocesses;\n')
        checked = scope.validate_generation(original, {'sourceOperationScopePolicy':{'active':True}})
        self.assertEqual(checked['outcome'], 'rejected')
        self.assertEqual(checked['reason'], 'operation_example_not_in_own_passage')
        self.assertEqual(checked['details']['claimIndex'], 2)
        self.assertEqual(checked['details']['unsupportedOperationTerms'], ['commands', 'execution', 'external_commands'])
        self.assertEqual(original, row['checks'])
        self.assertEqual(checked['details']['text'], json.loads(row['result']['modelAnswer'])['claims'][1]['text'])

    def test_other_five_actual_answers_keep_original_outcomes(self):
        for row in observed()['rows'][1:]:
            active = row['case']=='asyncio_scope'
            self.assertEqual(scope.validate_generation(row['checks'], {'sourceOperationScopePolicy':{'active':active}}), row['checks'])
        for row in observed()['rows'][4:]:
            self.assertEqual(json.loads(row['result']['modelAnswer']), {'claims':[]})
            self.assertEqual(row['checks']['outcome'], 'abstained')

    def test_neighboring_command_evidence_does_not_license_the_control_passage(self):
        text = json.loads(observed()['rows'][0]['result']['modelAnswer'])['claims'][1]['text']
        error = scope.operation_scope_error(text, 'control subprocesses;\n')
        self.assertEqual(error['reason'], 'operation_example_not_in_own_passage')
        self.assertIsNone(scope.operation_scope_error(text, 'run external commands;\n'))


class OperationScopeTests(unittest.TestCase):
    def test_control_paraphrases_are_still_allowed(self):
        for text in ('asyncio permette di controllare i sottoprocessi.',
                     'asyncio controls subprocesses.', 'asyncio gestisce i subprocessi.'):
            self.assertIsNone(scope.operation_scope_error(text, 'control subprocesses;\n'))
        self.assertIsNone(scope.operation_scope_error('asyncio esegue I/O di rete.', 'perform network IO and IPC;\n'))
        self.assertEqual(scope.operation_scope_error('asyncio esegue sottoprocessi.', 'control subprocesses;\n')['unsupportedOperationTerms'], ['execution'])
        self.assertIsNone(scope.operation_scope_error('asyncio esegue sottoprocessi.', 'run subprocesses;\n'))

    def test_commands_external_qualification_and_shell_stay_distinct(self):
        self.assertEqual(scope.operation_terms('run external commands in a shell;'), {'commands','execution','external_commands','shell'})
        self.assertEqual(scope.operation_terms('eseguire comandi esterni con una shell.'), {'commands','execution','external_commands','shell'})
        error = scope.operation_scope_error('asyncio esegue comandi esterni.', 'run commands;\n')
        self.assertEqual(error['unsupportedOperationTerms'], ['external_commands'])
        error = scope.operation_scope_error('asyncio usa una shell per comandi esterni.', 'run external commands;\n')
        self.assertEqual(error['unsupportedOperationTerms'], ['shell'])
        self.assertIsNone(scope.operation_scope_error('asyncio esegue comandi esterni con una shell.', 'run external commands in a shell;\n'))

    def test_vocabulary_presence_does_not_certify_negation_or_entailment(self):
        self.assertIsNone(scope.operation_scope_error('Execute external commands.', 'Do not execute external commands.'))
        _,_,_,selection = candidate.prepared(page(), candidate.baseline.CASES[0], 'compact')
        self.assertFalse(selection['sourceOperationScopePolicy']['semanticEntailmentCertified'])

    def test_all_schemas_and_question_values_remain_exact_and_other_case_prompts_unchanged(self):
        cp = extracted('<h1>csv</h1>'+html_entry('csv.reader','<p>'+CSV_RULE+'</p>'))
        for index, variant in candidate.baseline.ORDER:
            p = page() if index==0 else cp
            before = previous.prepared(p, previous.baseline.CASES[index], variant)
            after = candidate.prepared(p, candidate.baseline.CASES[index], variant)
            self.assertEqual(after[0], before[0])
            self.assertEqual(after[2], before[2])
            self.assertEqual(after[3]['selectedRefs'], before[3]['selectedRefs'])
            self.assertEqual(after[3]['outputPolicy'], before[3]['outputPolicy'])
            self.assertEqual([m['role'] for m in after[1]], ['system','user'])
            new = json.loads(after[1][1]['content']); old = json.loads(before[1][1]['content'])
            self.assertEqual(list(new)[-1], 'question')
            self.assertEqual(new['question'], candidate.baseline.CASES[index]['question'])
            self.assertEqual({k:v for k,v in new.items() if k!='sourceOperationTerms'}, old)
            if index!=0:
                self.assertEqual(after[1], before[1])
                self.assertFalse(after[3]['sourceOperationScopePolicy']['active'])
            else:
                self.assertTrue(after[3]['sourceOperationScopePolicy']['active'])
                self.assertIn(scope.INSTRUCTION, after[1][0]['content'])

    def test_inventory_is_owned_by_each_source_and_never_added_to_neighbors(self):
        p = extracted('<p>control subprocesses;</p><p>run external commands in a shell;</p>')
        bank, messages, _, selection = candidate.prepared(p, candidate.baseline.CASES[0], 'compact')
        inventory = json.loads(messages[1]['content'])['sourceOperationTerms']
        control = next(i+1 for i,q in enumerate(bank) if q.startswith('control'))
        command = next(i+1 for i,q in enumerate(bank) if q.startswith('run'))
        self.assertNotIn(str(control), inventory)
        self.assertEqual(inventory[str(command)], ['commands','execution','external_commands','shell'])
        self.assertEqual(''.join(bank), p['text'])
        self.assertFalse(selection['sourceOperationScopePolicy']['nativeSchemaChanged'])

    def test_missing_price_is_not_forced_and_prior_refusals_are_preserved(self):
        p = extracted('<h1>csv</h1>'+html_entry('csv.reader','<p>'+CSV_RULE+'</p>'))
        bank, _, schema, selection = candidate.prepared(p, candidate.baseline.CASES[2], 'compact')
        self.assertEqual(schema['properties']['claims']['maxItems'], 2)
        self.assertFalse(selection['sourceOperationScopePolicy']['active'])
        self.assertEqual(validate('{"claims":[]}', bank, selection)['outcome'], 'abstained')
        for result in ({'outcome':'abstained','claims':[]},
                       {'outcome':'rejected','reason':'stream_incomplete','claims':[]},
                       {'outcome':'rejected','reason':'converted_field_type_not_preserved','claims':[]}):
            self.assertIs(scope.validate_generation(result, {}), result)

    def test_alignment_repeated_application_and_input_mutation_are_checked(self):
        values = previous.prepared(page(), previous.baseline.CASES[0], 'compact')
        snapshot = copy.deepcopy(values)
        revised = scope.apply(*values, contract=candidate.baseline)
        self.assertEqual(values, snapshot)
        with self.assertRaisesRegex(ValueError, 'already_applied'):
            scope.apply(*revised, contract=candidate.baseline)
        changed = copy.deepcopy(values); changed[0][1]='Changed source bytes.\n'
        with self.assertRaisesRegex(ValueError, 'source_alignment_failed'):
            scope.apply(*changed, contract=candidate.baseline)


class FrozenProtocolTests(unittest.TestCase):
    def test_eleven_prior_sources_transport_workers_and_all_bounds_are_frozen(self):
        for name in ('BASELINE_SOURCE','RESOURCE_SOURCE','CONTEXT_SOURCE','RULE_BUDGET_SOURCE','NETWORKING_SOURCE',
                     'NATIVE_IDENTIFIER_SOURCE','PREFIX_IDENTIFIER_SOURCE','SOURCE_LABEL_SCOPE_SOURCE',
                     'CAPABILITY_EVIDENCE_SOURCE','PERFORMANCE_SCOPE_SOURCE','QUESTION_FOCUS_SOURCE'):
            self.assertEqual(getattr(candidate,name), getattr(previous,name))
        self.assertEqual(candidate.OPERATION_SCOPE_SOURCE, (ROOT/'scripts/andrea/web_operation_predicate_scope.py').read_text())
        self.assertEqual(candidate.baseline.CASES, previous.baseline.CASES)
        self.assertEqual(candidate.baseline.ORDER, previous.baseline.ORDER)
        self.assertEqual(candidate.baseline.EXPECTED, previous.baseline.EXPECTED)
        for name in ('MAX_CACHED_TOKENS','MIN_UNCACHED_FRACTION','MIN_INPUT_REDUCTION_PERCENT','MIN_PREFILL_REDUCTION_PERCENT'):
            self.assertEqual(getattr(candidate.baseline,name), getattr(previous.baseline,name))
        def functions(name):
            return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse((ROOT/'scripts/andrea'/name).read_text()).body if isinstance(n,ast.FunctionDef)}
        old=functions('web_question_focus_probe_body.py'); new=functions('web_operation_predicate_probe_body.py')
        for name in ('collect','model_worker','read_page','page_worker','thermal_sample','checked_worker'):
            self.assertEqual(new[name], old[name], name)

    def test_single_native_call_and_two_role_cache_isolation_are_unchanged(self):
        _, messages, schema, _ = candidate.prepared(page(), candidate.baseline.CASES[0], 'compact')
        isolated=candidate.baseline.isolated_messages(messages, 'A'+'a'*32)
        self.assertEqual(isolated[1], messages[1])
        calls=[]
        class Opener:
            def open(self, request, timeout):
                calls.append((json.loads(request.data),timeout))
                return io.BytesIO(b'{"message":{"content":"{\\"claims\\":[]}"},"done":true,"done_reason":"stop"}\n')
        candidate.baseline.stream_probe(Opener(), isolated, schema)
        self.assertEqual(len(calls),1)
        body, timeout=calls[0]
        self.assertEqual(body['messages'], isolated)
        self.assertEqual(body['format'], schema)
        self.assertEqual(body['options'], {'temperature':.4,'num_predict':512,'num_ctx':4096})
        self.assertEqual(body['keep_alive'], '15m')
        self.assertEqual(timeout,90)
        self.assertFalse(body['think'])

    def test_preparation_does_not_write_installed_sources(self):
        paths=[ROOT/p for p in candidate.baseline.EXPECTED if (ROOT/p).exists()]
        before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        for variant in ('production','compact'):
            candidate.prepared(page(), candidate.baseline.CASES[0], variant)
        self.assertEqual(before, {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})

    def mock_series(self, *, wrong_operation=False, wrong_missing=False, timeout=False):
        ap=page(); ap['url']=candidate.baseline.CASES[0]['url']
        cp=extracted('<h1>csv</h1>'+html_entry('csv.reader','<p>'+CSV_RULE+'</p>')); cp['url']=candidate.baseline.CASES[1]['url']
        pages={ap['url']:ap, cp['url']:cp}; calls=[]; emitted=[]
        class Reader:
            def get(self,path):
                return {'version':candidate.EXPECTED_OLLAMA_VERSION} if path=='/api/version' else {'models':[]}
        def collect(project,p,index,variant):
            calls.append((index,variant))
            if timeout and len(calls)==2:
                return {'result':{'status':'error','errorKind':'timeout','modelAnswer':'','native':candidate.baseline.native_metrics({})}},[],[],True
            bank=candidate.baseline.sentence_bank(p['text'])
            if index==0:
                text=json.loads(observed()['rows'][0]['result']['modelAnswer'])['claims'][1]['text'] if wrong_operation and variant=='production' else 'asyncio controlla i sottoprocessi.'
                claims=[{'passage':next(i+1 for i,q in enumerate(bank) if q==NETWORK),'text':'I/O di rete e IPC: asyncio permette queste operazioni.'},
                        {'passage':next(i+1 for i,q in enumerate(bank) if q==CONTROL),'text':text}]
            elif index==1 or (wrong_missing and variant=='compact'):
                claims=[{'passage':next(i+1 for i,q in enumerate(bank) if 'No automatic data type conversion' in q),
                         'text':json.loads(observed()['rows'][2]['result']['modelAnswer'])['claims'][0]['text']}]
            else:
                claims=[]
            metrics={'prompt_eval_count':2800 if variant=='production' else 1400,'prompt_eval_cached_count':0,
                     'prompt_evalMs':50000 if variant=='production' else 25000}
            return {'result':{'status':'completed','modelAnswer':json.dumps({'claims':claims}),'native':metrics}},[],[],True
        with patch.object(candidate.platform,'system',return_value='Darwin'), patch.object(candidate.baseline,'verify_project'), \
                patch.object(candidate.resources,'Reader',Reader), patch.object(candidate,'read_page',side_effect=lambda project,url:copy.deepcopy(pages[url])), \
                patch.object(candidate,'thermal_sample',return_value={}), patch.object(candidate,'collect',side_effect=collect):
            if timeout:
                with self.assertRaisesRegex(ValueError,'series_stopped_after_incomplete_request_no_retry'):
                    candidate.run(ROOT,emit=emitted.append)
                report=json.loads(next(value for value in reversed(emitted) if value.startswith('{')))
            else:
                report=candidate.run(ROOT,emit=emitted.append)
        return calls, report, emitted

    def test_mock_six_complete_requests_still_require_review_before_adoption(self):
        calls, report, _=self.mock_series()
        self.assertEqual(calls,list(candidate.baseline.ORDER))
        self.assertEqual(report['completedTransports'],6)
        self.assertTrue(report['technicalCaseShapesMet'])
        self.assertTrue(report['previousV7MeasurementsNotReused'])
        self.assertFalse(report['nativeOperationSchemaChanged'])
        self.assertFalse(report['modelOutputRewritten'])
        self.assertFalse(report['integrationAllowedByThisAutomaticReport'])
        self.assertEqual(report['qualityVerdict'],'pending_review')

    def test_added_example_refuses_whole_answer_and_keeps_series_failed(self):
        _, report, emitted=self.mock_series(wrong_operation=True)
        self.assertFalse(report['technicalCaseShapesMet'])
        self.assertEqual(report['performanceOutcome'],'gates_not_met')
        rows=[json.loads(value) for value in emitted if value.startswith('{') and '"variant"' in value and '"case"' in value]
        self.assertEqual(rows[0]['preOperationPredicateChecks']['outcome'],'accepted_pending_semantic_review')
        self.assertEqual(rows[0]['checks']['reason'],'operation_example_not_in_own_passage')
        self.assertEqual(len(json.loads(rows[0]['result']['modelAnswer'])['claims']),2)

    def test_wrong_missing_answer_is_not_relabeled_as_successful_abstention(self):
        _, report, emitted=self.mock_series(wrong_missing=True)
        self.assertFalse(report['technicalCaseShapesMet'])
        self.assertEqual(report['performanceOutcome'],'gates_not_met')
        rows=[json.loads(value) for value in emitted if value.startswith('{') and '"variant"' in value and '"case"' in value]
        self.assertEqual(rows[-1]['checks']['outcome'],'rejected')
        self.assertNotEqual(json.loads(rows[-1]['result']['modelAnswer']),{'claims':[]})
        self.assertFalse(rows[-1]['operationPredicateScopeApplied'])

    def test_timeout_stops_without_retry_or_more_requests(self):
        calls, report, _=self.mock_series(timeout=True)
        self.assertEqual(calls,list(candidate.baseline.ORDER)[:2])
        self.assertEqual(report['completedTransports'],1)
        self.assertEqual(report['notExecutedRequests'],4)


if __name__=='__main__':
    unittest.main()
