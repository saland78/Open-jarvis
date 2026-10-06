"""The actual uncompleted string must not postpone its source names forever."""
import ast
import copy
import hashlib
import io
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

import web_native_identifier_prefix as prefix
import web_native_identifier_probe as v3
import web_native_prefix_probe as candidate
import test_andrea_web_native_identifiers as previous_tests
from test_andrea_web_definition_context import extracted, html_entry

ROOT = Path(__file__).resolve().parents[1]
NETWORK = previous_tests.NETWORK
CATALOGUE = previous_tests.CATALOGUE


def report():
    return json.loads((ROOT/'docs/andrea/web-native-identifier-v3-interrupted-mac-2026-10-06.json').read_text())


class ActualPostponementRegressionTests(unittest.TestCase):
    def test_preserved_actual_run_has_one_completed_transport_and_four_unexecuted_cases(self):
        observed = report()
        self.assertEqual(observed['originalAutomaticReport']['completed'], 2)
        self.assertEqual([row['result']['status'] for row in observed['rows']], ['completed', 'error'])
        self.assertEqual(observed['manualReviewCounts'], {'favorable': 1, 'failedIncomplete': 1, 'notExecuted': 4})
        self.assertEqual(observed['rows'][1]['result']['errorKind'], 'timeout')
        self.assertEqual(observed['rows'][1]['result']['totalClientMs'], 90117.091)
        self.assertIsNone(observed['rows'][1]['result']['native']['prompt_evalMs'])
        self.assertEqual(observed['rows'][1]['checks']['reason'], 'stream_incomplete')
        self.assertTrue(observed['originalAutomaticChecksPreserved'])
        self.assertNotIn('/Users/', json.dumps(observed))
        self.assertNotIn('Last login:', json.dumps(observed))

    def test_actual_repetitive_tail_has_a_completion_witness_in_the_old_pattern_but_not_the_new_one(self):
        row = report()['rows'][1]
        value = row['result']['modelAnswer'].split('"text":"', 1)[1]
        rule = next(rule for rule in row['selection']['nativeIdentifierPolicy']['rules'] if rule['passage'] == 10)
        self.assertEqual(len(value), 768)
        self.assertNotIn('I/O', value)
        witness = value+' I/O di rete IPC'
        self.assertIsNotNone(re.fullmatch(rule['pattern'], witness))
        revised = prefix.prefix_pattern(prefix.source_prefix(rule), native_contract=v3.native_identifiers)
        self.assertIsNone(re.fullmatch(revised, witness+'.'))
        for suffix in (' I/O di rete e IPC: nuova frase.', ' IPC poi I/O di rete.', '**.'*30+' I/O di rete e IPC.'):
            self.assertIsNone(re.fullmatch(revised, value+suffix))
        # This is a language/prefix witness, not a model-performance assertion.

    def test_the_favorable_v3_reference_answer_is_kept_as_a_distinct_result(self):
        row = report()['rows'][0]
        self.assertTrue(row['caseShapeMet'])
        self.assertEqual(row['checks'], row['originalApplicationChecks'])
        self.assertEqual(row['checks']['claims'][0]['quote'], NETWORK)
        self.assertIn('I/O di rete', row['checks']['claims'][0]['text'])
        self.assertEqual(report()['overallReview'], 'not_passed_no_adoption')
        self.assertFalse(report()['originalAutomaticReport']['integrationAllowedByThisAutomaticReport'])


class PrefixContractTests(unittest.TestCase):
    def test_names_have_a_finite_fixed_order_before_the_free_predicate(self):
        bank, messages, schema, selection = candidate.prepared(previous_tests.page(), candidate.baseline.CASES[0], 'compact')
        rule = selection['nativeIdentifierPolicy']['rules'][0]
        self.assertEqual(rule['requiredStart'], 'I/O di rete e IPC: ')
        good = 'I/O di rete e IPC: asyncio consente queste operazioni.'
        self.assertIsNotNone(re.fullmatch(rule['pattern'], good))
        for bad in ('asyncio consente I/O di rete e IPC.',
                    'I/O e IPC: asyncio consente operazioni di rete.',
                    'I/O di rete e IPC: asyncio consente queste operazioni',
                    'IPC e I/O di rete: asyncio consente queste operazioni.'):
            self.assertIsNone(re.fullmatch(rule['pattern'], bad))
        payload = json.loads(messages[1]['content'])
        self.assertEqual(payload['requiredStarts']['2'], rule['requiredStart'])
        self.assertEqual(schema['properties']['claims']['maxItems'], 2)
        self.assertFalse(selection['nativeIdentifierPolicy']['unboundedTextBeforeMandatoryNames'])

    def test_sources_questions_conditions_and_original_inventories_stay_exact(self):
        page = previous_tests.page()
        for variant in ('production', 'compact'):
            before = v3.prepared(page, v3.baseline.CASES[0], variant)
            snapshot = copy.deepcopy(before)
            after = prefix.apply(*before, native_contract=v3.native_identifiers)
            self.assertEqual(before, snapshot)
            self.assertEqual(after[0], before[0])
            old, new = json.loads(before[1][1]['content']), json.loads(after[1][1]['content'])
            for field in old:
                self.assertEqual(new[field], old[field])
            self.assertEqual(after[3]['selectedRefs'], before[3]['selectedRefs'])
            self.assertEqual(after[3]['outputPolicy'], before[3]['outputPolicy'])
            self.assertEqual(after[2]['properties']['claims']['maxItems'], before[2]['properties']['claims']['maxItems'])
            self.assertNotIn('maxLength', json.dumps(after[2]))

    def test_conditional_and_subprocess_only_facts_receive_no_forced_neighboring_names(self):
        _, messages, schema, selection = candidate.prepared(previous_tests.page(), candidate.baseline.CASES[0], 'compact')
        self.assertNotIn('3', json.loads(messages[1]['content'])['requiredStarts'])
        self.assertNotIn('pattern', previous_tests.branch_for(schema, 3)['properties']['text'])
        raw = json.dumps({'claims': [{'passage': 3, 'text': 'asyncio gestisce sottoprocessi tramite event loop.'}]})
        bank = candidate.baseline.sentence_bank(previous_tests.page()['text'])
        checked = candidate.context.validate(raw, bank, True, heading_ranges=[ [0, 7] ],
                                               contract=candidate.baseline, selection=selection)
        self.assertEqual(checked['outcome'], 'accepted_pending_semantic_review')

    def test_label_does_not_satisfy_an_unsupported_or_wrong_predicate(self):
        p = previous_tests.page()
        bank, _, _, selection = candidate.prepared(p, candidate.baseline.CASES[0], 'compact')
        text = 'I/O di rete e IPC: asyncio esegue calcoli sulla CPU.'
        raw = json.dumps({'claims': [{'passage': 2, 'text': text}]})
        checked = candidate.context.validate(raw, bank, True, heading_ranges=p['headingRanges'],
                                               contract=candidate.baseline, selection=selection)
        checked = candidate.native_identifiers.validate_generation(checked, selection)
        self.assertEqual(checked['reason'], 'source_identifiers_not_preserved')
        self.assertEqual(checked['claims'], [])
        self.assertEqual(checked['details']['text'], text)

    def test_a_complete_own_source_predicate_remains_original_model_text(self):
        p = previous_tests.page()
        bank, _, _, selection = candidate.prepared(p, candidate.baseline.CASES[0], 'compact')
        text = 'I/O di rete e IPC: asyncio permette di effettuare queste operazioni.'
        raw = json.dumps({'claims': [{'passage': 2, 'text': text}]})
        original = candidate.context.validate(raw, bank, True, heading_ranges=p['headingRanges'],
                                                contract=candidate.baseline, selection=selection)
        result = candidate.native_identifiers.validate_generation(original, selection)
        self.assertEqual(result['outcome'], 'accepted_pending_semantic_review')
        self.assertEqual(result['claims'][0]['text'], text)
        self.assertEqual(result['claims'][0]['quote'], NETWORK)
        self.assertIs(result, original)

    def test_inconsistent_sources_or_native_branches_are_refused_before_inference(self):
        for kind in ('source', 'branch', 'instruction'):
            before = copy.deepcopy(v3.prepared(previous_tests.page(), v3.baseline.CASES[0], 'compact'))
            if kind == 'source':
                payload = json.loads(before[1][1]['content'])
                payload['passages'][0][1] += 'changed'
                before[1][1]['content'] = json.dumps(payload)
            elif kind == 'branch':
                before[2]['properties']['claims']['items']['oneOf'][0]['properties']['text']['pattern'] = '^unknown$'
            else:
                before[1][0]['content'] = before[1][0]['content'].replace(v3.native_identifiers.INSTRUCTION, '')
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                prefix.apply(*before, native_contract=v3.native_identifiers)

    def test_no_required_names_preserves_the_exact_native_wire(self):
        p = extracted('<p>control subprocesses without another acronym;</p>')
        before = v3.prepared(p, v3.baseline.CASES[0], 'compact')
        self.assertEqual(prefix.apply(*before, native_contract=v3.native_identifiers), before)


class PinnedNativePrefixConversionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous_tests.PinnedNativePatternTests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        previous_tests.PinnedNativePatternTests.tearDownClass.__func__(cls)

    def test_each_converted_pattern_requires_its_entire_literal_prefix_before_the_first_repetition(self):
        for variant in ('production', 'compact'):
            _, _, _, selection = candidate.prepared(previous_tests.page(), candidate.baseline.CASES[0], variant)
            for rule in selection['nativeIdentifierPolicy']['rules']:
                converted = previous_tests.PinnedNativePatternTests.convert(self, rule['pattern'])
                self.assertEqual(converted.returncode, 0, converted.stderr)
                grammar = converted.stdout
                literal = '"'+rule['requiredStart']+'"'
                self.assertIn(literal, grammar)
                self.assertLess(grammar.index(literal), grammar.index('[^'))
                self.assertIn('[.]', grammar)
                # Pattern conversion is tested; Mac inference is still pending.

    def test_every_actual_v3_source_inventory_has_a_literal_native_prefix(self):
        for row in report()['rows']:
            for rule in row['selection']['nativeIdentifierPolicy']['rules']:
                label = prefix.source_prefix(rule)
                expression = prefix.prefix_pattern(label, native_contract=v3.native_identifiers)
                converted = previous_tests.PinnedNativePatternTests.convert(self, expression)
                self.assertEqual(converted.returncode, 0, converted.stderr)
                self.assertIn('"'+label+'"', converted.stdout)


class IsolatedComparisonTests(unittest.TestCase):
    def test_all_previous_embedding_and_request_gates_are_frozen(self):
        for name in ('BASELINE_SOURCE', 'RESOURCE_SOURCE', 'CONTEXT_SOURCE', 'RULE_BUDGET_SOURCE', 'NETWORKING_SOURCE', 'NATIVE_IDENTIFIER_SOURCE'):
            self.assertEqual(getattr(candidate, name), getattr(v3, name))
        self.assertEqual(candidate.PREFIX_IDENTIFIER_SOURCE, (ROOT/'scripts/andrea/web_native_identifier_prefix.py').read_text())
        self.assertEqual(candidate.baseline.CASES, v3.baseline.CASES)
        self.assertEqual(candidate.baseline.ORDER, v3.baseline.ORDER)
        self.assertEqual(candidate.baseline.EXPECTED, v3.baseline.EXPECTED)
        for relative, checksum in candidate.baseline.EXPECTED.items():
            self.assertEqual(hashlib.sha256((ROOT/relative).read_bytes()).hexdigest(), checksum)
        self.assertEqual((candidate.baseline.MIN_INPUT_REDUCTION_PERCENT, candidate.baseline.MIN_PREFILL_REDUCTION_PERCENT), (10, 10))
        self.assertEqual(candidate.WORKER_SECONDS, 95)
        def functions(filename):
            tree = ast.parse((ROOT/'scripts/andrea'/filename).read_text())
            return {node.name: ast.dump(node, include_attributes=False) for node in tree.body if isinstance(node, ast.FunctionDef)}
        old, new = functions('web_native_identifier_probe_body.py'), functions('web_native_prefix_probe_body.py')
        for name in ('checked_page', 'page_worker', 'read_page', 'model_worker', 'collect', 'checked_worker'):
            self.assertEqual(old[name], new[name])

    def test_transmitted_native_format_has_the_prefix_once_and_the_original_options(self):
        _, messages, schema, _ = candidate.prepared(previous_tests.page(), candidate.baseline.CASES[0], 'compact')
        calls = []
        class Opener:
            def open(self, request, timeout):
                calls.append((json.loads(request.data), timeout))
                return io.BytesIO(b'{"message":{"content":"{\\"claims\\":[]}"},"done":true,"done_reason":"stop"}\n')
        candidate.baseline.stream_probe(Opener(), messages, schema)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0]['format'], schema)
        self.assertEqual(calls[0][0]['options'], {'temperature': .4, 'num_predict': 512, 'num_ctx': 4096})
        self.assertEqual(calls[0][1], 90)

    def test_interrupted_series_reports_attempted_and_completed_counts_separately(self):
        asyncio_page = previous_tests.page()
        asyncio_page['url'] = candidate.baseline.CASES[0]['url']
        csv_page = extracted(html_entry())
        pages = {asyncio_page['url']: asyncio_page, csv_page['url']: csv_page}
        calls = []
        class Reader:
            def get(self, path):
                return {'version': candidate.EXPECTED_OLLAMA_VERSION} if path == '/api/version' else {'models': []}
        def collect(project, p, index, variant):
            calls.append((index, variant))
            if variant == 'compact':
                return {'result': report()['rows'][1]['result']}, [], [], True
            bank = candidate.baseline.sentence_bank(p['text'])
            claims = [{'passage': next(i+1 for i, unit in enumerate(bank) if 'network IO' in unit),
                       'text': 'I/O di rete e IPC: asyncio supporta queste operazioni.'},
                      {'passage': next(i+1 for i, unit in enumerate(bank) if 'handling OS signals' in unit),
                       'text': 'asyncio permette di controllare sottoprocessi con event loop.'}]
            return {'result': {'status': 'completed', 'modelAnswer': json.dumps({'claims': claims}),
                              'native': report()['rows'][0]['result']['native']}}, [], [], True
        output = []
        with patch.object(candidate.platform, 'system', return_value='Darwin'), \
                patch.object(candidate.baseline, 'verify_project'), patch.object(candidate.resources, 'Reader', Reader), \
                patch.object(candidate, 'read_page', side_effect=lambda project, url: copy.deepcopy(pages[url])), \
                patch.object(candidate, 'thermal_sample', return_value={}), patch.object(candidate, 'collect', side_effect=collect), \
                self.assertRaisesRegex(ValueError, 'series_stopped_after_incomplete_request_no_retry'):
            candidate.run(ROOT, emit=output.append)
        self.assertEqual(calls, [(0, 'production'), (0, 'compact')])
        final = json.loads(next(text for text in reversed(output) if text.startswith('{')))
        self.assertEqual((final['attemptedRequests'], final['completedTransports'], final['notExecutedRequests']), (2, 1, 4))
        self.assertFalse(final['integrationAllowedByThisAutomaticReport'])
        self.assertEqual(final['performanceOutcome'], 'inconclusive_cache_or_metrics')

    def test_six_balanced_original_cases_keep_their_budgets_and_semantic_review_pending(self):
        asyncio_page = previous_tests.page()
        asyncio_page['url'] = candidate.baseline.CASES[0]['url']
        csv_page = extracted(html_entry())
        pages = {asyncio_page['url']: asyncio_page, csv_page['url']: csv_page}
        installed = json.loads((ROOT/'docs/andrea/web-api-context-installed-mac-2026-10-06.json').read_text())
        good_csv = installed['rows'][1]['claims'][0]['text']
        calls = []
        class Reader:
            def get(self, path):
                return {'version': candidate.EXPECTED_OLLAMA_VERSION} if path == '/api/version' else {'models': []}
        def collect(project, p, index, variant):
            calls.append((index, variant))
            bank = candidate.baseline.sentence_bank(p['text'])
            if index == 0:
                claims = [{'passage': next(i+1 for i, unit in enumerate(bank) if 'network IO' in unit),
                           'text': 'I/O di rete e IPC: asyncio consente queste operazioni.'},
                          {'passage': next(i+1 for i, unit in enumerate(bank) if 'handling OS signals' in unit),
                           'text': 'asyncio gestisce sottoprocessi tramite event loop.'}]
            elif index == 1:
                claims = [{'passage': next(i+1 for i, unit in enumerate(bank) if 'No automatic data type conversion' in unit),
                           'text': good_csv}]
            else:
                claims = []
            native = {'prompt_eval_count': 2800 if variant == 'production' else 1400,
                      'prompt_eval_cached_count': 0, 'prompt_evalMs': 50000 if variant == 'production' else 25000}
            return {'result': {'status': 'completed', 'modelAnswer': json.dumps({'claims': claims}),
                              'native': native}}, [], [], True
        output = []
        with patch.object(candidate.platform, 'system', return_value='Darwin'), \
                patch.object(candidate.baseline, 'verify_project'), patch.object(candidate.resources, 'Reader', Reader), \
                patch.object(candidate, 'read_page', side_effect=lambda project, url: copy.deepcopy(pages[url])), \
                patch.object(candidate, 'thermal_sample', return_value={}), patch.object(candidate, 'collect', side_effect=collect):
            final = candidate.run(ROOT, emit=output.append)
        self.assertEqual(calls, list(candidate.baseline.ORDER))
        self.assertEqual((final['attemptedRequests'], final['completedTransports'], final['notExecutedRequests']), (6, 6, 0))
        self.assertEqual(final['performanceOutcome'], 'measured_gates_met_pending_semantic_review')
        self.assertEqual(final['qualityVerdict'], 'pending_review')
        self.assertFalse(final['integrationAllowedByThisAutomaticReport'])
        self.assertTrue(final['previousV3MeasurementsNotReused'])
        self.assertTrue(final['mandatoryNamesBeforeFreeTextChangedExplicitly'])
        records = [json.loads(text) for text in output if text.startswith('{')]
        rows = [row for row in records if 'case' in row]
        self.assertEqual([row['nativeClaimArrayLimit'] for row in rows], [2, 2, 1, 2, 2, 2])


if __name__ == '__main__':
    unittest.main()
