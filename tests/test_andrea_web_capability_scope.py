"""Replay the submitted v5 series and test operation/performance grounding."""
import ast
import copy
import hashlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import web_capability_evidence as capability
import web_source_performance_scope as performance
import web_capability_scope_probe as candidate
import web_source_label_scope_probe as previous
import test_andrea_web_native_identifiers as native_tests
from test_andrea_web_definition_context import extracted, html_entry
from test_andrea_web_source_label_scope import CSV_RULE, OFTEN, NETWORK

ROOT = Path(__file__).resolve().parents[1]
CONTROL = 'control subprocesses;\n'
EFFICIENT = 'implement efficient protocols using transports;\n'


def observed():
    return json.loads((ROOT/'docs/andrea/web-source-label-scope-v5-mac-2026-10-06.json').read_text())


def page():
    return extracted('<h1>asyncio</h1><p>'+OFTEN+'</p><p>'+NETWORK+'</p><p>'+CONTROL+'</p><p>'+EFFICIENT+'</p>')


def validate(raw, bank, selection):
    result = candidate.context.validate(raw, bank, True, heading_ranges=[], contract=candidate.baseline, selection=selection)
    result = candidate.rule_budget.validate_cardinality(result, selection['outputPolicy'])
    result = candidate.source_labels.validate_generation(result, selection)
    result = candidate.native_identifiers.validate_generation(result, selection)
    result = capability.validate_generation(result, selection)
    return performance.validate_generation(result, selection)


def references(schema):
    items = schema['properties']['claims']['items']
    return {ref for branch in items.get('oneOf', [items]) for ref in branch['properties']['passage']['enum']}


class SubmittedV5Tests(unittest.TestCase):
    def test_automatic_success_and_unfavorable_meaning_are_both_preserved(self):
        report = observed()
        self.assertEqual(report['originalAutomaticReport']['completedTransports'], 6)
        self.assertTrue(report['originalAutomaticReport']['technicalCaseShapesMet'])
        self.assertTrue(all(pair['performanceGateMet'] for pair in report['originalAutomaticReport']['pairs']))
        self.assertEqual(report['manualReviewCounts'], {'favorable': 4, 'unfavorable': 2})
        self.assertEqual(report['overallReview'], 'not_passed_no_adoption')
        self.assertTrue(all(row['checks']['outcome'] in ('accepted_pending_semantic_review', 'abstained')
                            for row in report['rows']))
        self.assertNotIn('/Users/', json.dumps(report))
        self.assertNotIn('Last login:', json.dumps(report))

    def test_actual_added_efficiency_is_rejected_without_rewriting_or_dropping_one_point(self):
        row = observed()['rows'][1]
        original = copy.deepcopy(row['checks'])
        result = performance.validate_generation(original, {'sourcePerformanceScopePolicy': {}})
        self.assertEqual(result['reason'], 'performance_attribute_not_in_own_passage')
        self.assertEqual(result['claims'], [])
        self.assertEqual(result['details']['claimIndex'], 2)
        self.assertEqual(result['details']['quote'], NETWORK)
        self.assertIn('efficiency', result['details']['unsupportedPerformanceTerms'])
        self.assertEqual(original, row['checks'])

    def test_the_actual_suitability_refs_are_not_operation_evidence(self):
        for row in observed()['rows'][:2]:
            claim = row['checks']['claims'][0]
            self.assertEqual(claim['passage'], 4)
            self.assertEqual(claim['quote'], OFTEN)
            self.assertFalse(capability.action_statement(claim['quote']))
            selection = {'sourceCapabilityScopePolicy': {'active': True, 'eligibleOperationRefs': [10]}}
            self.assertEqual(capability.validate_generation(row['checks'], selection)['reason'],
                             'capability_not_supported_by_operation_statement')

    def test_the_favorable_csv_and_genuine_abstention_outputs_remain_unchanged(self):
        for row in observed()['rows'][2:]:
            value = copy.deepcopy(row['checks'])
            selection = {'sourcePerformanceScopePolicy': {},
                         'sourceCapabilityScopePolicy': {'active': False, 'eligibleOperationRefs': []}}
            self.assertEqual(capability.validate_generation(value, selection), row['checks'])
            self.assertEqual(performance.validate_generation(value, selection), row['checks'])


class PerformanceVocabularyTests(unittest.TestCase):
    def test_attributes_are_distinct_and_have_finite_language_forms(self):
        self.assertEqual(performance.performance_terms('gestione efficiente; efficiency; efficiently'), {'efficiency'})
        self.assertEqual(performance.performance_terms('Un server ad alte prestazioni.'), {'high_performance'})
        self.assertEqual(performance.performance_terms('Esecuzione più veloce e rapidamente.'), {'speed'})
        self.assertEqual(performance.performance_terms('Lower-latency and latenza ridotta.'), {'low_latency'})
        self.assertEqual(performance.performance_terms('La fonte documenta soltanto I/O di rete e IPC.'), set())

    def test_support_for_an_operation_does_not_license_performance_properties(self):
        for text in ('I/O di rete e IPC: operazioni efficienti.', 'I/O di rete e IPC: operazioni più veloci.',
                     'I/O di rete e IPC: consentono alte prestazioni.', 'I/O di rete e IPC: hanno bassa latenza.'):
            self.assertEqual(performance.performance_scope_error(text, NETWORK)['reason'],
                             'performance_attribute_not_in_own_passage')
        self.assertIsNone(performance.performance_scope_error('I/O di rete e IPC: asyncio permette queste operazioni.', NETWORK))

    def test_same_source_efficiency_is_licensed_without_licensing_speed_or_latency(self):
        self.assertIsNone(performance.performance_scope_error('asyncio implementa protocolli efficienti.', EFFICIENT))
        self.assertIsNotNone(performance.performance_scope_error('asyncio implementa protocolli più veloci.', EFFICIENT))
        self.assertIsNotNone(performance.performance_scope_error('asyncio implementa protocolli a bassa latenza.', EFFICIENT))
        self.assertIsNotNone(performance.performance_scope_error('Connessioni efficienti.', 'high-performance network servers.'))

    def test_vocabulary_presence_does_not_claim_to_resolve_negation_or_certify_meaning(self):
        # Identical vocabulary can still reverse a negation. The module does
        # not claim otherwise: manual review remains required in the report.
        self.assertIsNone(performance.performance_scope_error('Operazioni efficienti.', 'not efficient operations.'))
        _, _, _, selection = candidate.prepared(page(), candidate.baseline.CASES[0], 'compact')
        self.assertFalse(selection['sourcePerformanceScopePolicy']['semanticEntailmentCertified'])

    def test_other_passage_vocabulary_is_not_borrowed(self):
        bank, _, _, selection = candidate.prepared(page(), candidate.baseline.CASES[0], 'compact')
        ref = next(i+1 for i, quote in enumerate(bank) if quote == NETWORK)
        raw = json.dumps({'claims': [{'passage': ref, 'text': 'I/O di rete e IPC: asyncio permette operazioni efficienti.'}]})
        result = validate(raw, bank, selection)
        self.assertEqual(result['reason'], 'performance_attribute_not_in_own_passage')
        self.assertEqual(result['claims'], [])

    def test_existing_refusals_and_abstentions_are_preserved(self):
        for value in ({'outcome': 'abstained', 'claims': []},
                      {'outcome': 'rejected', 'reason': 'csv_conversion_type_not_preserved', 'claims': []}):
            self.assertIs(performance.validate_generation(value, {}), value)
            self.assertIs(capability.validate_generation(value, {}), value)


class CapabilityPreparationTests(unittest.TestCase):
    def test_action_recognition_excludes_suitability_headings_and_incomplete_units(self):
        for quote in (NETWORK, CONTROL, EFFICIENT, 'distribute tasks via queues;\n',
                      'create and manage event loops, which provide asynchronous APIs for networking;\n'):
            self.assertTrue(capability.action_statement(quote), quote)
        for quote in (OFTEN, 'High-level APIs\n', 'run these operations',
                      'RUN this command;\n', 'asyncio is used for efficient networking.\n', 'Run tasks;\n'):
            self.assertFalse(capability.action_statement(quote), quote)

    def test_capability_branches_use_operations_while_all_source_bytes_remain_in_context(self):
        for variant in ('production', 'compact'):
            before = previous.prepared(page(), previous.baseline.CASES[0], variant)
            bank, messages, schema, selection = candidate.prepared(page(), candidate.baseline.CASES[0], variant)
            fit = next(i+1 for i, quote in enumerate(bank) if quote == OFTEN)
            expected = {i+1 for i, quote in enumerate(bank)
                        if quote.strip() in (NETWORK.strip(), CONTROL.strip(), EFFICIENT.strip())}
            self.assertEqual(references(schema), expected)
            self.assertNotIn(fit, references(schema))
            self.assertEqual(bank, before[0])
            self.assertEqual(selection['selectedRefs'], before[3]['selectedRefs'])
            self.assertEqual(selection['outputPolicy'], before[3]['outputPolicy'])
            payload = json.loads(messages[1]['content'])
            old_payload = json.loads(before[1][1]['content'])
            self.assertEqual(payload['passages'], old_payload['passages'])
            self.assertEqual(payload['question'], old_payload['question'])
            self.assertEqual(set(payload['capabilityEvidenceRefs']), expected)
            self.assertNotIn(str(fit), payload.get('requiredStarts', {}))
            self.assertNotIn('maxLength', json.dumps(schema))
            self.assertEqual(schema['properties']['claims'].get('minItems', 0), 0)

    def test_no_new_native_patterns_or_schema_word_bans_are_added(self):
        for variant in ('production', 'compact'):
            old = previous.prepared(page(), previous.baseline.CASES[0], variant)[2]
            revised = candidate.prepared(page(), candidate.baseline.CASES[0], variant)[2]
            old_patterns = {branch['properties']['text'].get('pattern') for branch in old['properties']['claims']['items']['oneOf']}
            new_patterns = {branch['properties']['text'].get('pattern') for branch in revised['properties']['claims']['items']['oneOf']}
            self.assertLessEqual(new_patterns, old_patterns)

    def test_source_qualified_labels_remain_bound_to_their_own_operation(self):
        bank, _, schema, selection = candidate.prepared(page(), candidate.baseline.CASES[0], 'compact')
        network = next(i+1 for i, quote in enumerate(bank) if quote == NETWORK)
        control = next(i+1 for i, quote in enumerate(bank) if quote == CONTROL)
        self.assertTrue(native_tests.pattern_allows(schema, network, 'I/O di rete e IPC: asyncio permette queste operazioni.'))
        self.assertFalse(native_tests.pattern_allows(schema, control, 'I/O: asyncio controlla i sottoprocessi.'))
        self.assertTrue(native_tests.pattern_allows(schema, control, 'asyncio controlla i sottoprocessi.'))
        good = json.dumps({'claims': [{'passage': network, 'text': 'I/O di rete e IPC: asyncio permette queste operazioni.'},
                                      {'passage': control, 'text': 'asyncio controlla i sottoprocessi.'}]})
        self.assertEqual(validate(good, bank, selection)['outcome'], 'accepted_pending_semantic_review')

    def test_csv_and_missing_price_questions_keep_evidence_and_array_budgets(self):
        p = extracted('<h1>csv</h1>'+html_entry('csv.reader', '<p>'+CSV_RULE+'</p>'))
        budgets = []
        for index, variant in candidate.baseline.ORDER:
            selected = page() if index == 0 else p
            bank, messages, schema, selection = candidate.prepared(selected, candidate.baseline.CASES[index], variant)
            budgets.append(schema['properties']['claims']['maxItems'])
            if index != 0:
                old = previous.prepared(selected, previous.baseline.CASES[index], variant)
                self.assertEqual(schema, old[2])
                self.assertFalse(selection['sourceCapabilityScopePolicy']['active'])
                self.assertNotIn('capabilityEvidenceRefs', json.loads(messages[1]['content']))
            if index == 2:
                self.assertEqual(validate('{"claims":[]}', bank, selection)['outcome'], 'abstained')
        self.assertEqual(budgets, [2, 2, 1, 2, 2, 2])

    def test_insufficient_action_evidence_does_not_force_an_answer_or_minimum(self):
        p = extracted('<h1>asyncio</h1><p>'+OFTEN+'</p><p>'+NETWORK+'</p>')
        before = previous.prepared(p, previous.baseline.CASES[0], 'compact')
        after = candidate.prepared(p, candidate.baseline.CASES[0], 'compact')
        self.assertFalse(after[3]['sourceCapabilityScopePolicy']['active'])
        self.assertEqual(after[2], before[2])
        self.assertEqual(validate('{"claims":[]}', after[0], after[3])['outcome'], 'abstained')

    def test_adapters_are_pure_and_fail_before_inference_on_source_misalignment(self):
        original = previous.prepared(page(), previous.baseline.CASES[0], 'compact')
        saved = copy.deepcopy(original)
        revised = capability.apply(*original, contract=candidate.baseline)
        performance.apply(*revised, contract=candidate.baseline)
        self.assertEqual(original, saved)
        bad = copy.deepcopy(original)
        bad[0][1] = 'An unrelated changed source statement.\n'
        for adapter in (capability, performance):
            with self.assertRaisesRegex(ValueError, 'source_alignment_failed'):
                adapter.apply(*bad, contract=candidate.baseline)


class FrozenProtocolTests(unittest.TestCase):
    def test_all_previous_embedded_sources_and_original_questions_are_preserved(self):
        for name in ('BASELINE_SOURCE', 'RESOURCE_SOURCE', 'CONTEXT_SOURCE', 'RULE_BUDGET_SOURCE',
                     'NETWORKING_SOURCE', 'NATIVE_IDENTIFIER_SOURCE', 'PREFIX_IDENTIFIER_SOURCE', 'SOURCE_LABEL_SCOPE_SOURCE'):
            self.assertEqual(getattr(candidate, name), getattr(previous, name))
        self.assertEqual(candidate.CAPABILITY_EVIDENCE_SOURCE, (ROOT/'scripts/andrea/web_capability_evidence.py').read_text())
        self.assertEqual(candidate.PERFORMANCE_SCOPE_SOURCE, (ROOT/'scripts/andrea/web_source_performance_scope.py').read_text())
        self.assertEqual(candidate.baseline.CASES, previous.baseline.CASES)
        self.assertEqual(candidate.baseline.ORDER, previous.baseline.ORDER)
        self.assertEqual(candidate.baseline.EXPECTED, previous.baseline.EXPECTED)
        for name in ('MODEL', 'MAX_CLAIM_CHARS', 'MAX_CACHED_TOKENS', 'MIN_UNCACHED_FRACTION',
                     'MIN_INPUT_REDUCTION_PERCENT', 'MIN_PREFILL_REDUCTION_PERCENT'):
            self.assertEqual(getattr(candidate.baseline, name), getattr(previous.baseline, name))

    def test_worker_transport_and_page_reader_functions_are_unchanged(self):
        def functions(filename):
            tree = ast.parse((ROOT/'scripts/andrea'/filename).read_text())
            return {node.name: ast.dump(node, include_attributes=False) for node in tree.body if isinstance(node, ast.FunctionDef)}
        old = functions('web_source_label_scope_probe_body.py')
        new = functions('web_capability_scope_probe_body.py')
        for name in ('collect', 'model_worker', 'page_worker', 'read_page', 'thermal_sample', 'checked_worker'):
            self.assertEqual(new[name], old[name], name)

    def test_no_installed_sources_are_written_during_preparation(self):
        paths = [ROOT/path for path in previous.baseline.EXPECTED if (ROOT/path).exists()]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        for variant in ('production', 'compact'):
            candidate.prepared(page(), candidate.baseline.CASES[0], variant)
        self.assertEqual(before, {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths})

    def test_native_post_keeps_format_deadline_options_and_one_generation(self):
        _, messages, schema, _ = candidate.prepared(page(), candidate.baseline.CASES[0], 'compact')
        calls = []
        class Opener:
            def open(self, request, timeout):
                calls.append((json.loads(request.data), timeout))
                return io.BytesIO(b'{"message":{"content":"{\\"claims\\":[]}"},"done":true,"done_reason":"stop"}\n')
        candidate.baseline.stream_probe(Opener(), messages, schema)
        self.assertEqual(len(calls), 1)
        payload, timeout = calls[0]
        self.assertEqual(payload['format'], schema)
        self.assertEqual(payload['options'], {'temperature': .4, 'num_predict': 512, 'num_ctx': 4096})
        self.assertEqual(payload['model'], candidate.baseline.MODEL)
        self.assertEqual(payload['keep_alive'], '15m')
        self.assertFalse(payload['think'])
        self.assertEqual(timeout, 90)

    def mock_series(self, *, interrupt=False):
        ap = page(); ap['url'] = candidate.baseline.CASES[0]['url']
        cp = extracted('<h1>csv</h1>'+html_entry('csv.reader', '<p>'+CSV_RULE+'</p>'))
        cp['url'] = candidate.baseline.CASES[1]['url']
        pages, calls, emitted = {ap['url']: ap, cp['url']: cp}, [], []
        class Reader:
            def get(self, path):
                return {'version': candidate.EXPECTED_OLLAMA_VERSION} if path == '/api/version' else {'models': []}
        def collect(project, p, index, variant):
            calls.append((index, variant))
            if interrupt and len(calls) == 2:
                return {'result': {'status': 'error', 'errorKind': 'timeout', 'modelAnswer': '',
                                  'native': candidate.baseline.native_metrics({})}}, [], [], True
            bank = candidate.baseline.sentence_bank(p['text'])
            if index == 0:
                claims = [{'passage': next(i+1 for i, q in enumerate(bank) if q == NETWORK),
                           'text': 'I/O di rete e IPC: asyncio permette queste operazioni.'},
                          {'passage': next(i+1 for i, q in enumerate(bank) if q == CONTROL),
                           'text': 'asyncio controlla i sottoprocessi.'}]
            elif index == 1:
                claims = [{'passage': next(i+1 for i, q in enumerate(bank) if 'No automatic data type conversion' in q),
                           'text': json.loads(observed()['rows'][2]['result']['modelAnswer'])['claims'][0]['text']}]
            else:
                claims = []
            native = {'prompt_eval_count': 2800 if variant == 'production' else 1400,
                      'prompt_eval_cached_count': 0, 'prompt_evalMs': 50000 if variant == 'production' else 25000}
            return {'result': {'status': 'completed', 'modelAnswer': json.dumps({'claims': claims}), 'native': native}}, [], [], True
        with patch.object(candidate.platform, 'system', return_value='Darwin'), \
                patch.object(candidate.baseline, 'verify_project'), patch.object(candidate.resources, 'Reader', Reader), \
                patch.object(candidate, 'read_page', side_effect=lambda project, url: copy.deepcopy(pages[url])), \
                patch.object(candidate, 'thermal_sample', return_value={}), patch.object(candidate, 'collect', side_effect=collect):
            if interrupt:
                with self.assertRaisesRegex(ValueError, 'series_stopped_after_incomplete_request_no_retry'):
                    candidate.run(ROOT, emit=emitted.append)
                final = json.loads(next(text for text in reversed(emitted) if text.startswith('{')))
            else:
                final = candidate.run(ROOT, emit=emitted.append)
        return calls, final, emitted

    def test_balanced_six_requests_leave_automatic_integration_disabled(self):
        calls, report, emitted = self.mock_series()
        self.assertEqual(calls, list(candidate.baseline.ORDER))
        self.assertEqual(report['completedTransports'], 6)
        self.assertEqual(report['notExecutedRequests'], 0)
        self.assertEqual(report['qualityVerdict'], 'pending_review')
        self.assertFalse(report['integrationAllowedByThisAutomaticReport'])
        self.assertFalse(report['referenceIsCurrentInstalledPrompt'])
        self.assertTrue(report['previousV5MeasurementsNotReused'])
        self.assertTrue(report['technicalCaseShapesMet'])
        self.assertFalse(report['nativePerformanceVocabularyConstraintApplied'])
        self.assertTrue(all('preCapabilityPerformanceChecks' in json.loads(item) for item in emitted if item.startswith('{') and '"case"' in item and '"variant"' in item))

    def test_incomplete_transport_stops_without_retry_or_fabricated_metrics(self):
        calls, report, _ = self.mock_series(interrupt=True)
        self.assertEqual(calls, list(candidate.baseline.ORDER)[:2])
        self.assertEqual(report['attemptedRequests'], 2)
        self.assertEqual(report['completedTransports'], 1)
        self.assertEqual(report['notExecutedRequests'], 4)
        self.assertTrue(report['seriesStoppedAfterIncompleteTransport'])


if __name__ == '__main__':
    unittest.main()
