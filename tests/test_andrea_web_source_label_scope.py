"""Replay observed v4 failures and test source-local native label constraints."""
import ast
import copy
import hashlib
import io
import itertools
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

import web_source_label_scope as scope
import web_source_label_scope_probe as candidate
import web_native_prefix_probe as previous
import test_andrea_web_native_identifiers as native_tests
from test_andrea_web_definition_context import extracted, html_entry

ROOT = Path(__file__).resolve().parents[1]
NETWORK = native_tests.NETWORK
CATALOGUE = native_tests.CATALOGUE
OFTEN = 'asyncio is often a perfect fit for IO-bound and high-level structured network code.\n'
CSV_RULE = ('Each row read from the csv file is returned as a list of strings. '
            'No automatic data type conversion is performed unless the QUOTE_NONNUMERIC format option '
            'is specified (in which case unquoted fields are transformed into floats).\n')


def report():
    return json.loads((ROOT/'docs/andrea/web-native-prefix-v4-mac-2026-10-06.json').read_text())


def page():
    return extracted('<h1>asyncio</h1><p>'+OFTEN+'</p><p>'+NETWORK+'</p><p>'+CATALOGUE+'</p>')


def validate(raw, bank, selection, *, original=False):
    contract = candidate.original_baseline if original else candidate.baseline
    value = candidate.context.validate(raw, bank, True, heading_ranges=[], contract=contract, selection=selection)
    value = candidate.rule_budget.validate_cardinality(value, selection['outputPolicy'])
    if not original:
        value = scope.validate_generation(value, selection)
        value = candidate.native_identifiers.validate_generation(value, selection)
    return value


class SubmittedV4Tests(unittest.TestCase):
    def test_raw_complete_series_and_its_failed_overall_outcome_are_preserved(self):
        observed = report()
        self.assertEqual(observed['originalAutomaticReport']['completedTransports'], 6)
        self.assertTrue(all(row['result']['status'] == 'completed' for row in observed['rows']))
        self.assertEqual(observed['originalTechnicalShapeCounts'], {'met': 4, 'notMet': 2})
        self.assertEqual(observed['manualReviewCounts'], {'favorable': 4, 'unfavorable': 2})
        self.assertEqual(observed['overallReview'], 'not_passed_no_adoption')
        self.assertEqual(observed['originalAutomaticReport']['performanceOutcome'], 'gates_not_met')
        self.assertTrue(all(pair['performanceGateMet'] for pair in observed['originalAutomaticReport']['pairs']))
        self.assertNotIn('/Users/', json.dumps(observed))
        self.assertNotIn('Last login:', json.dumps(observed))

    def test_the_separate_user_interrupted_run_is_not_counted_as_a_complete_series(self):
        observed = json.loads((ROOT/'docs/andrea/web-native-prefix-v4-partial-mac-2026-10-06.json').read_text())
        self.assertEqual(observed['observedStartedRequests'], 5)
        self.assertEqual(observed['completedReportedTransports'], 4)
        self.assertIsNone(observed['originalAutomaticReport'])
        self.assertTrue(observed['missingCompletionMetricsRemainUnknown'])
        self.assertEqual(observed['notExecutedRequests'], 1)

    def test_actual_foreign_label_is_excluded_in_the_native_branch_before_inference(self):
        row = report()['rows'][1]
        text = row['checks']['details']['text']
        _, _, schema, selection = candidate.prepared(page(), candidate.baseline.CASES[0], 'compact')
        self.assertFalse(native_tests.pattern_allows(schema, 4, text))
        for label in ('I/O: ', 'I/O di rete e IPC: '):
            self.assertFalse(native_tests.pattern_allows(schema, 4, label+'asyncio gestisce event loop.'))
        self.assertTrue(native_tests.pattern_allows(schema, 4, 'asyncio gestisce sottoprocessi tramite event loop.'))
        self.assertNotIn('4', json.loads(candidate.prepared(page(), candidate.baseline.CASES[0], 'compact')[1][1]['content'])['requiredStarts'])

    def test_actual_wrong_repl_attribution_is_also_excluded_when_repl_is_in_inventory(self):
        partial = json.loads((ROOT/'docs/andrea/web-native-prefix-v4-partial-mac-2026-10-06.json').read_text())
        row = partial['rows'][0]
        labels = [rule['requiredStart'].rstrip() for rule in row['selection']['nativeIdentifierPolicy']['rules']]
        pattern = scope.not_label_start_pattern(labels)
        text = row['checks']['details']['text']
        self.assertIsNone(re.fullmatch(pattern, text))
        self.assertEqual(row['checks']['details']['addedIdentifiers'], ['REPL'])

    def test_csv_false_positive_is_corrected_without_rewriting_or_short_circuiting_any_point(self):
        row = report()['rows'][2]
        bank = ['Unused unrelated source.\n']*24
        bank[23] = row['checks']['details']['quote']
        selection = {**row['selection'], 'sourceLabelScopePolicy': {'guardBranches': []}}
        original = validate(row['result']['modelAnswer'], bank, selection, original=True)
        self.assertEqual(original, row['checks'])
        checked = validate(row['result']['modelAnswer'], bank, selection)
        self.assertEqual(checked['outcome'], 'accepted_pending_semantic_review')
        self.assertEqual(checked['claims'][0]['text'], json.loads(row['result']['modelAnswer'])['claims'][0]['text'])
        self.assertEqual(checked['claims'][0]['quote'], CSV_RULE)

    def test_technical_acceptance_does_not_hide_the_lost_frequency_in_the_reference(self):
        row = report()['rows'][0]
        claim = json.loads(row['result']['modelAnswer'])['claims'][0]
        self.assertEqual(row['checks']['outcome'], 'accepted_pending_semantic_review')
        self.assertEqual(scope.frequency_scope_error(claim['text'], row['checks']['claims'][0]['quote']),
                         'source_frequency_not_preserved')


class FiniteAliasTests(unittest.TestCase):
    def test_only_the_selected_format_noun_licenses_csv(self):
        for quote in ('Each row read from the csv file is returned.', 'The file csv is read.', CSV_RULE):
            self.assertEqual(scope.csv_file_aliases(quote), {'CSV'})
        for quote in ('csv.reader returns rows.', 'scsv file is read.', 'file csv.reader is opened.',
                      'a.csv file is opened.', 'file csvwriter is opened.', 'SQL file is read.',
                      'Each row is a list of strings.'):
            self.assertEqual(scope.csv_file_aliases(quote), set(), quote)

    def test_original_contract_is_preserved_and_existing_api_alias_remains(self):
        self.assertEqual(candidate.original_baseline.source_identifier_aliases(CSV_RULE), set())
        self.assertEqual(candidate.baseline.source_identifier_aliases(CSV_RULE), {'CSV'})
        self.assertEqual(candidate.baseline.source_identifier_aliases('asynchronous APIs for networking.'), {'API'})
        self.assertEqual(previous.baseline.source_identifier_aliases(CSV_RULE), set())

    def test_same_quote_alias_does_not_license_neighbor_ids_or_wrong_conditions(self):
        good = ('Il file CSV restituisce stringhe, salvo QUOTE_NONNUMERIC, '
                'che converte i campi non racchiusi tra virgolette in float.')
        selection = {'selectedRefs': [1], 'outputPolicy': {'maxClaims': 2},
                     'nativeIdentifierPolicy': {'rules': []}, 'sourceLabelScopePolicy': {'guardBranches': []}}
        for bad in (good.replace('file CSV', 'file SQL'),
                    good.replace('QUOTE_NONNUMERIC', 'QUOTE_MINIMAL'),
                    good.replace('non racchiusi tra virgolette', 'tutti'),
                    good.replace('in float', 'in interi')):
            raw = json.dumps({'claims': [{'passage': 1, 'text': bad}]})
            result = validate(raw, [CSV_RULE], selection)
            self.assertEqual(result['outcome'], 'rejected', bad)
            self.assertEqual(result['claims'], [])

    def test_csv_elsewhere_does_not_license_csv_in_an_unrelated_selected_source(self):
        bank = ['Each row is returned as a list of strings.\n', CSV_RULE]
        selection = {'selectedRefs': [1, 2], 'outputPolicy': {'maxClaims': 2},
                     'nativeIdentifierPolicy': {'rules': []}, 'sourceLabelScopePolicy': {'guardBranches': []}}
        raw = json.dumps({'claims': [{'passage': 1, 'text': 'Il file CSV restituisce una lista di stringhe.'}]})
        self.assertEqual(validate(raw, bank, selection)['reason'], 'source_identifiers_not_preserved')


class GuardLanguageTests(unittest.TestCase):
    def test_finite_prefix_guard_equals_the_startswith_policy(self):
        labels = ['I/O:', 'I/O di rete e IPC:', 'API:', 'REPL:', 'CSV e RFC:']
        expression = scope.not_label_start_pattern(labels)
        specimens = ['Un punto ordinario completo.', 'asyncio gestisce event loop.', 'I/Olo è una parola diversa.',
                     'Il testo termina.', 'APIche ha una grafia diversa.', 'Una frase contiene I/O: dentro il corpo.',
                     'CSV: questo è un diverso prefisso.', 'REPLICA è un nome diverso.', 'REPL: fatto.']
        for label in labels:
            specimens += [label+' un fatto completo.', label+'\u00e8 un fatto completo.', '  '+label+' un fatto completo.']
            specimens += [label[:i]+'.' for i in range(len(label))]
        for text in specimens:
            self.assertEqual(bool(re.fullmatch(expression, text)), not any(text.lstrip(' ').startswith(x) for x in labels), text)

    def test_shared_prefixes_shorter_labels_and_character_class_boundaries(self):
        for labels in (['API:', 'API e CSV:'], ['I/O:', 'IPC:'], ['CSV:'], ['API e CSV e PEP:', 'CSV e RFC:']):
            expression = scope.not_label_start_pattern(labels)
            for prefix in itertools.product('AIP/O: x\u00e8', repeat=3):
                text = ''.join(prefix)+' una frase completa.'
                self.assertEqual(bool(re.fullmatch(expression, text)), not any(text.lstrip(' ').startswith(x) for x in labels))
            for text in ('Una frase "con quote".', 'Una frase\ncon righe.', 'Una frase\\con escape.', 'Una frase\x7f.'):
                self.assertIsNone(re.fullmatch(expression, text))

    def test_no_lookahead_hard_string_cap_or_deferred_identifier_obligation(self):
        expression = scope.not_label_start_pattern(['I/O:', 'REPL:'])
        self.assertNotIn('(?!', expression)
        self.assertNotIn('(?=', expression)
        self.assertNotIn('{', expression)
        self.assertIsNotNone(re.fullmatch(expression, 'asyncio gestisce questi sottoprocessi.'))
        self.assertIsNone(re.fullmatch(expression, 'I/O: testo ripetuto.'*40+' REPL: fine.'))

    def test_invalid_or_unbounded_inventories_fail_before_generation(self):
        for labels in ([], [''], ['.*:'], ['I/O'], ['API\n:']):
            with self.assertRaises(ValueError):
                scope.not_label_start_pattern(labels)
        with self.assertRaises(ValueError):
            scope.not_label_start_pattern(['API e '+('A'*300)+':'])


class SourceQualifiedBranchTests(unittest.TestCase):
    def test_native_positive_names_and_negative_foreign_labels_remain_separate(self):
        bank, messages, schema, selection = candidate.prepared(page(), candidate.baseline.CASES[0], 'compact')
        payload = json.loads(messages[1]['content'])
        self.assertEqual(payload['requiredStarts']['2'], 'I/O: spesso ')
        self.assertEqual(payload['requiredStarts']['3'], 'I/O di rete e IPC: ')
        self.assertEqual(payload['sourceFrequencyQualifiers'], {'2': 'often'})
        self.assertTrue(native_tests.pattern_allows(schema, 2, 'I/O: spesso asyncio è perfetto per codice IO-bound e di rete.'))
        self.assertFalse(native_tests.pattern_allows(schema, 2, 'I/O: asyncio è perfetto per codice IO-bound e di rete.'))
        self.assertTrue(native_tests.pattern_allows(schema, 4, 'asyncio gestisce sottoprocessi tramite event loop.'))
        self.assertFalse(native_tests.pattern_allows(schema, 4, 'I/O: asyncio gestisce sottoprocessi tramite event loop.'))
        self.assertNotIn('maxLength', json.dumps(schema))
        self.assertEqual(payload['passages'], [[ref, bank[ref-1]] for ref in selection['selectedRefs']])
        self.assertEqual(payload['question'], candidate.baseline.CASES[0]['question'])

    def test_both_comparison_variants_use_the_same_own_source_policy_without_changing_evidence(self):
        for variant in ('production', 'compact'):
            old = previous.prepared(page(), previous.baseline.CASES[0], variant)
            snapshot = copy.deepcopy(old)
            revised = scope.apply(*old, contract=candidate.baseline, native_contract=candidate.native_identifiers)
            self.assertEqual(old, snapshot)
            self.assertEqual(revised[0], old[0])
            self.assertEqual(revised[3]['selectedRefs'], old[3]['selectedRefs'])
            self.assertEqual(revised[3]['outputPolicy'], old[3]['outputPolicy'])
            self.assertEqual(revised[2]['properties']['claims']['maxItems'], old[2]['properties']['claims']['maxItems'])
            self.assertEqual(json.loads(revised[1][1]['content'])['passages'], json.loads(old[1][1]['content'])['passages'])

    def test_missing_csv_uppercase_is_optional_and_is_not_forced_from_a_neighbor(self):
        p = extracted('<h1>csv</h1>'+html_entry('csv.reader', '<p>'+CSV_RULE+'</p>'))
        bank, messages, schema, selection = candidate.prepared(p, candidate.baseline.CASES[1], 'compact')
        ref = next(i+1 for i, quote in enumerate(bank) if 'No automatic data type conversion' in quote)
        payload = json.loads(messages[1]['content'])
        self.assertIn(ref, selection['sourceLabelScopePolicy']['sourceCsvFileAliasRefs'])
        self.assertNotIn(str(ref), payload.get('requiredStarts', {}))
        text = 'Il file CSV restituisce stringhe salvo QUOTE_NONNUMERIC, che converte i campi senza virgolette in float.'
        self.assertTrue(native_tests.pattern_allows(schema, ref, text))
        self.assertEqual(validate(json.dumps({'claims': [{'passage': ref, 'text': text}]}), bank, selection)['outcome'],
                         'accepted_pending_semantic_review')

    def test_a_correct_label_does_not_license_a_wrong_predicate_or_later_foreign_identifier(self):
        bank, _, _, selection = candidate.prepared(page(), candidate.baseline.CASES[0], 'compact')
        for text in ('I/O di rete e IPC: asyncio esegue calcoli sulla CPU.',
                     'I/O: spesso asyncio è sempre perfetto per codice IO-bound e di rete.'):
            ref = 3 if 'IPC' in text else 2
            result = validate(json.dumps({'claims': [{'passage': ref, 'text': text}]}), bank, selection)
            self.assertEqual(result['outcome'], 'rejected')
            self.assertEqual(result['claims'], [])

    def test_frequency_does_not_become_a_universal_claim_or_change_an_unqualified_source(self):
        self.assertEqual(scope.frequency_scope_error('I/O: spesso è sempre perfetto.', OFTEN), 'source_frequency_strengthened')
        self.assertEqual(scope.frequency_scope_error('I/O: è perfetto per codice IO-bound.', OFTEN), 'source_frequency_not_preserved')
        self.assertIsNone(scope.frequency_scope_error('I/O: spesso è perfetto per codice IO-bound.', OFTEN))
        self.assertIsNone(scope.frequency_scope_error('asyncio controlla i sottoprocessi.', 'control subprocesses;\n'))


class PinnedNegativePrefixConversionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        native_tests.PinnedNativePatternTests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        native_tests.PinnedNativePatternTests.tearDownClass.__func__(cls)

    def test_all_actual_v4_label_inventories_compile_in_the_pinned_pattern_converter(self):
        for row in report()['rows']:
            labels = [rule['requiredStart'].rstrip() for rule in row['selection']['nativeIdentifierPolicy']['rules']]
            expression = scope.not_label_start_pattern(labels)
            converted = native_tests.PinnedNativePatternTests.convert(self, expression)
            self.assertEqual(converted.returncode, 0, converted.stderr)
            self.assertNotIn('accepting any string', converted.stderr)
            self.assertIn('[^', converted.stdout)

    def test_each_new_source_branch_pattern_compiles_and_frequency_precedes_free_text(self):
        for variant in ('production', 'compact'):
            _, _, schema, _ = candidate.prepared(page(), candidate.baseline.CASES[0], variant)
            for branch in schema['properties']['claims']['items']['oneOf']:
                expression = branch['properties']['text'].get('pattern')
                if expression:
                    converted = native_tests.PinnedNativePatternTests.convert(self, expression)
                    self.assertEqual(converted.returncode, 0, converted.stderr)
                    if 'spesso ' in expression:
                        self.assertIn('"I/O: spesso "', converted.stdout)
                        self.assertLess(converted.stdout.index('"I/O: spesso "'), converted.stdout.index('[^'))


class FrozenProtocolTests(unittest.TestCase):
    def test_old_sources_request_fields_transport_and_gates_are_preserved(self):
        for name in ('BASELINE_SOURCE', 'RESOURCE_SOURCE', 'CONTEXT_SOURCE', 'RULE_BUDGET_SOURCE',
                     'NETWORKING_SOURCE', 'NATIVE_IDENTIFIER_SOURCE', 'PREFIX_IDENTIFIER_SOURCE'):
            self.assertEqual(getattr(candidate, name), getattr(previous, name))
        self.assertEqual(candidate.SOURCE_LABEL_SCOPE_SOURCE, (ROOT/'scripts/andrea/web_source_label_scope.py').read_text())
        self.assertEqual(candidate.baseline.CASES, previous.baseline.CASES)
        self.assertEqual(candidate.baseline.ORDER, previous.baseline.ORDER)
        for name in ('MODEL', 'BASE', 'API', 'LIMIT', 'MAX_RESPONSE', 'MAX_CLAIM_CHARS',
                     'EXPECTED', 'MAX_CACHED_TOKENS', 'MIN_UNCACHED_FRACTION',
                     'MIN_INPUT_REDUCTION_PERCENT', 'MIN_PREFILL_REDUCTION_PERCENT'):
            self.assertEqual(getattr(candidate.baseline, name), getattr(previous.baseline, name))
        def functions(filename):
            tree = ast.parse((ROOT/'scripts/andrea'/filename).read_text())
            return {node.name: ast.dump(node, include_attributes=False) for node in tree.body if isinstance(node, ast.FunctionDef)}
        before, after = functions('web_native_prefix_probe_body.py'), functions('web_source_label_scope_probe_body.py')
        for name in ('collect', 'model_worker', 'read_page', 'page_worker'):
            self.assertEqual(after[name], before[name])

    def test_no_current_installed_source_is_modified_by_isolated_preparation(self):
        paths = [ROOT/path for path in previous.baseline.EXPECTED if (ROOT/path).exists()]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        for variant in ('production', 'compact'):
            candidate.prepared(page(), candidate.baseline.CASES[0], variant)
        self.assertEqual(before, {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths})

    def test_case_arrays_and_empty_missing_price_branch_stay_available(self):
        p = extracted('<h1>csv</h1>'+html_entry('csv.reader', '<p>'+CSV_RULE+'</p>'))
        budgets = []
        for case_index, variant in candidate.baseline.ORDER:
            selected = page() if case_index == 0 else p
            bank, _, schema, selection = candidate.prepared(selected, candidate.baseline.CASES[case_index], variant)
            budgets.append(schema['properties']['claims']['maxItems'])
            self.assertEqual(schema['properties']['claims'].get('minItems', 0), 0)
            if case_index == 2:
                self.assertEqual(candidate.context.validate('{"claims":[]}', bank, True, heading_ranges=selected['headingRanges'],
                    contract=candidate.baseline, selection=selection)['outcome'], 'abstained')
        self.assertEqual(budgets, [2, 2, 1, 2, 2, 2])

    def test_native_request_is_one_post_with_same_options_and_explicit_new_schema(self):
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
        self.assertFalse(payload['think'])
        self.assertEqual(payload['keep_alive'], '15m')
        self.assertEqual(timeout, 90)

    def mock_run(self, *, interrupt=False):
        ap = page(); ap['url'] = candidate.baseline.CASES[0]['url']
        cp = extracted('<h1>csv</h1>'+html_entry('csv.reader', '<p>'+CSV_RULE+'</p>'))
        cp['url'] = candidate.baseline.CASES[1]['url']
        pages = {ap['url']: ap, cp['url']: cp}
        calls, emitted = [], []
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
                claims = [{'passage': next(i+1 for i, q in enumerate(bank) if 'network IO' in q),
                           'text': 'I/O di rete e IPC: asyncio permette queste operazioni.'},
                          {'passage': next(i+1 for i, q in enumerate(bank) if 'running subprocesses' in q),
                           'text': 'asyncio controlla i sottoprocessi tramite event loop.'}]
            elif index == 1:
                claims = [{'passage': next(i+1 for i, q in enumerate(bank) if 'No automatic data type conversion' in q),
                           'text': json.loads(report()['rows'][2]['result']['modelAnswer'])['claims'][0]['text']}]
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
        rows = [json.loads(text) for text in emitted if text.startswith('{') and '"case"' in text and '"result"' in text]
        return calls, final, rows

    def test_mocked_comparison_keeps_all_six_cases_and_preserves_original_csv_refusal(self):
        calls, final, rows = self.mock_run()
        self.assertEqual(calls, list(candidate.baseline.ORDER))
        self.assertEqual((final['attemptedRequests'], final['completedTransports'], final['notExecutedRequests']), (6, 6, 0))
        self.assertEqual([row['nativeClaimArrayLimit'] for row in rows], [2, 2, 1, 2, 2, 2])
        self.assertTrue(final['technicalCaseShapesMet'])
        self.assertTrue(final['finiteCsvFileAliasChangedExplicitly'])
        self.assertTrue(final['nativeForeignLeadingLabelGuardAddedExplicitly'])
        self.assertTrue(final['sourceFrequencyQualifierPreservedExplicitly'])
        self.assertEqual(final['qualityVerdict'], 'pending_review')
        self.assertFalse(final['integrationAllowedByThisAutomaticReport'])
        self.assertTrue(final['previousV4MeasurementsNotReused'])
        self.assertEqual(rows[2]['originalApplicationChecks']['reason'], 'source_identifiers_not_preserved')
        self.assertEqual(rows[2]['checks']['outcome'], 'accepted_pending_semantic_review')

    def test_mocked_interruption_does_not_run_four_remaining_requests_or_claim_completion(self):
        calls, final, _ = self.mock_run(interrupt=True)
        self.assertEqual(calls, [(0, 'production'), (0, 'compact')])
        self.assertEqual((final['attemptedRequests'], final['completedTransports'], final['notExecutedRequests']), (2, 1, 4))
        self.assertFalse(final['integrationAllowedByThisAutomaticReport'])
        self.assertEqual(final['performanceOutcome'], 'inconclusive_cache_or_metrics')


if __name__ == '__main__':
    unittest.main()
