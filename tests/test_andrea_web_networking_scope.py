"""Observed installed rejection, own-passage guidance and unchanged gates."""
import ast
import copy
import hashlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import web_networking_scope as networking
import web_networking_scope_probe as candidate
import web_definition_latency_probe as archived
from frozen_web_context import contract as live
import web_page_fidelity as fidelity
from test_andrea_web_definition_context import extracted, html_entry
from test_andrea_web_request_resources import Child, StubObserver

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ('create and manage event loops, which provide asynchronous APIs for networking, '
             'running subprocesses, handling OS signals, etc;\n')


def raw(ref, text):
    return json.dumps({'claims': [{'passage': ref, 'text': text}]}, ensure_ascii=False)


def prepared(page, question=None):
    return live.prepare(page, question or archived.baseline.CASES[0]['question'])


def guided(page, question=None):
    return networking.apply(*prepared(page, question), contract=fidelity)


class ActualInstalledRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((ROOT/'docs/andrea/web-api-context-installed-mac-2026-10-06.json').read_text())

    def test_actual_io_substitution_remains_rejected_by_the_unmodified_live_validator(self):
        row = self.report['rows'][0]
        detail = row['rejectionDetails']
        bank = ['Unused source unit for regression.\n']*detail['passage']
        bank[detail['passage']-1] = detail['quote']
        answer = raw(detail['passage'], detail['text'])
        original = list(bank)
        result = live.validate(answer, bank, True, {'headingRanges': []}, row['contextSelection'])
        self.assertEqual(result['reason'], row['reason'])
        self.assertEqual(result['details']['text'], detail['text'])
        self.assertEqual(result['details']['quote'], detail['quote'])
        self.assertEqual(result['details']['addedIdentifiers'], ['I/O'])
        self.assertEqual(result['claims'], [])
        self.assertEqual(bank, original)
        # Only the refused second point was reported: no first point is fabricated.
        self.assertEqual(detail['claimIndex'], 2)
        self.assertEqual(json.loads(answer)['claims'][0]['text'], detail['text'])

    def test_other_page_io_mentions_cannot_license_the_observed_networking_claim(self):
        detail = self.report['rows'][0]['rejectionDetails']
        bank = ['asyncio supports I/O and IPC.\n', detail['quote']]
        page = {'headingRanges': []}
        selection = {'selectedRefs': [1, 2], 'outputPolicy': {'maxClaims': 2}}
        result = live.validate(raw(2, detail['text']), bank, True, page, selection)
        self.assertEqual(result['reason'], 'source_identifiers_not_preserved')
        self.assertEqual(result['details']['addedIdentifiers'], ['I/O'])

    def test_csv_and_actual_empty_price_answer_still_pass_without_repair(self):
        for row in self.report['rows'][1:]:
            bank = ['Unused source unit for regression.\n']*max([p['passage'] for p in row['claims']], default=1)
            for claim in row['claims']:
                bank[claim['passage']-1] = claim['quote']
            answer = json.dumps({'claims': [{'passage': p['passage'], 'text': p['text']} for p in row['claims']]})
            with self.subTest(case=row['case']):
                result = live.validate(answer, bank, True, {'headingRanges': []}, row['contextSelection'])
                self.assertEqual(result['outcome'], row['outcome'])
                self.assertEqual(result['claims'], row['claims'])

    def test_previous_finite_success_and_current_installed_failure_stay_separate(self):
        self.assertEqual(self.report['manualReviewCounts'], {'favorable': 2, 'unfavorable': 1})
        self.assertEqual(self.report['overallReview'], 'not_passed_asyncio_own_passage_identifier')
        self.assertFalse(self.report['newBalancedPerformanceComparison'])
        previous = json.loads((ROOT/'docs/andrea/web-signal-scope-mac-2026-10-06.json').read_text())
        self.assertEqual(previous['manualReviewCounts'], {'favorable': 6, 'unfavorable': 0})
        self.assertFalse(previous['originalAutomaticReport']['integrationAllowedByThisAutomaticReport'])
        public = json.dumps(self.report)
        self.assertNotIn('/Users/', public)
        self.assertNotIn('Last login:', public)


class OwnPassagePromptTests(unittest.TestCase):
    def test_networking_inventory_is_added_before_inference_without_changing_source_or_schema(self):
        page = extracted('<h1>asyncio — Asynchronous I/O</h1><p>'+CATALOGUE+'</p>')
        before = prepared(page)
        original = copy.deepcopy(before)
        bank, messages, schema, selection = networking.apply(*before, contract=fidelity)
        self.assertEqual(before, original)
        old, new = json.loads(before[1][1]['content']), json.loads(messages[1]['content'])
        for field in ('question', 'passages', 'contextOnly', 'protectedIdentifiers'):
            self.assertEqual(new[field], old[field])
        self.assertEqual(schema, before[2])
        self.assertEqual(bank, before[0])
        self.assertEqual(''.join(bank), page['text'])
        self.assertEqual(messages[0]['content'], before[1][0]['content']+networking.NETWORKING_SCOPE_INSTRUCTION)
        refs = selection['sourceNetworkingScopeRefs']
        self.assertEqual(len(refs), 1)
        ref = refs[0]
        self.assertEqual(new['sourceTechnicalTerms'][str(ref)],
                         sorted(set(old['sourceTechnicalTerms'][str(ref)]) | {'networking'}))
        self.assertNotIn('I/O', new['protectedIdentifiers'][str(ref)])
        self.assertLess(len(messages[0]['content']), len(archived.baseline.baseline_prepare(page['text'], old['question'])[1][0]['content']))

    def test_omitted_networking_source_adds_no_terms_to_a_selected_csv_entry(self):
        page = extracted(html_entry()+'<p>'+CATALOGUE+'</p>')
        question = archived.baseline.CASES[1]['question']
        before = prepared(page, question)
        after = guided(page, question)
        self.assertEqual(after[:3], before[:3])
        self.assertEqual(after[3]['sourceNetworkingScopeRefs'], [])
        self.assertEqual(after[3]['mode'], 'complete_api_entries')
        self.assertEqual(after[3]['outputPolicy']['maxClaims'], 1)
        self.assertIn(CATALOGUE.rstrip(), page['text'])
        self.assertNotIn(networking.NETWORKING_SCOPE_INSTRUCTION, after[1][0]['content'])

    def test_heading_is_context_not_a_networking_inventory_source(self):
        page = extracted('<h1>networking without I/O evidence</h1><p>Readers return strings according to their format.</p>')
        before, after = prepared(page), guided(page)
        self.assertEqual(before[:3], after[:3])
        self.assertEqual(after[3]['sourceNetworkingScopeRefs'], [])

    def test_literal_networking_with_own_io_identifier_does_not_receive_the_narrow_guidance(self):
        for own in ('networking and I/O are separate source items.',
                    'networking and IO are separate source items.',
                    'networking and input/output are separate source items.'):
            with self.subTest(own=own):
                page = extracted('<p>'+own+'</p>')
                before, after = prepared(page), guided(page)
                self.assertEqual(before[:3], after[:3])
                self.assertEqual(after[3]['sourceNetworkingScopeRefs'], [])

    def test_activation_is_not_tied_to_asyncio_url_question_or_passage_number(self):
        page = extracted('<p>Other preceding details in a different document.</p>'
                         '<p>NETWORKING operations use distinct protocols.</p>')
        page['url'] = 'https://example.com/unrelated'
        bank, messages, _, selection = guided(page, 'Descrivi le operazioni secondo questo testo.')
        self.assertEqual(selection['sourceNetworkingScopeRefs'], [2])
        self.assertEqual(json.loads(messages[1]['content'])['sourceTechnicalTerms']['2'], ['networking'])
        self.assertIn('NETWORKING', bank[1])

    def test_csv_and_price_input_are_exactly_unchanged_when_no_networking_evidence_is_present(self):
        page = extracted(html_entry()+'<p>Additional unrelated material remains available.</p>')
        for case in archived.baseline.CASES[1:]:
            with self.subTest(case=case['id']):
                before, after = prepared(page, case['question']), guided(page, case['question'])
                self.assertEqual(before[:3], after[:3])
                self.assertEqual(after[3]['sourceNetworkingScopeRefs'], [])

    def test_mismatched_source_bytes_or_numbers_are_refused_before_guidance(self):
        page = extracted('<p>'+CATALOGUE+'</p>')
        before = prepared(page)
        for mutate in ('bytes', 'reference'):
            changed = copy.deepcopy(before)
            payload = json.loads(changed[1][1]['content'])
            if mutate == 'bytes':
                payload['passages'][0][1] += ' Different text.'
            else:
                payload['passages'][0][0] = 99
            changed[1][1]['content'] = json.dumps(payload)
            with self.subTest(mutate=mutate), self.assertRaisesRegex(ValueError, 'alignment'):
                networking.apply(*changed, contract=fidelity)

    def test_valid_networking_or_rete_and_subprocess_only_claims_remain_valid(self):
        for text in ('asyncio gestisce event loop per networking, sottoprocessi e segnali dell’OS.',
                     'asyncio gestisce event loop per rete, sottoprocessi e segnali dell’OS.',
                     'asyncio consente di creare event loop per eseguire sottoprocessi.'):
            with self.subTest(text=text):
                result = live.validate(raw(1, text), [CATALOGUE], True, {'headingRanges': []},
                                       {'selectedRefs': [1], 'outputPolicy': {'maxClaims': 2}})
                self.assertEqual(result['outcome'], 'accepted_pending_semantic_review')
                self.assertEqual(result['claims'][0]['text'], text)


class IsolatedProbeTests(unittest.TestCase):
    def test_embedded_baseline_resources_context_and_budget_are_frozen_exactly(self):
        for name in ('BASELINE_SOURCE', 'RESOURCE_SOURCE', 'CONTEXT_SOURCE', 'RULE_BUDGET_SOURCE'):
            self.assertEqual(getattr(candidate, name), getattr(archived, name))
        self.assertEqual(candidate.NETWORKING_SOURCE, (ROOT/'scripts/andrea/web_networking_scope.py').read_text())
        body = (ROOT/'scripts/andrea/web_networking_scope_probe_body.py').read_text().replace('from __future__ import annotations\n', '')
        self.assertTrue((ROOT/'scripts/andrea/web_networking_scope_probe.py').read_text().endswith(body))

    def test_runner_fingerprints_current_installed_code_without_relabeling_its_archived_reference(self):
        self.assertEqual(candidate.INSTALLED_PROJECT_REVISION, live.CONTRACT_REVISION)
        self.assertEqual(candidate.ARCHIVED_BASELINE_REVISION, 'full_context_before_api_context_integration')
        for path, fingerprint in candidate.baseline.EXPECTED.items():
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256(((ROOT/'tests/fixtures/andrea/web_page_context_contract.py_before_compact_v9') if path == 'scripts/andrea/web_page_context_contract.py' else ROOT/path).read_bytes()).hexdigest(), fingerprint)
        self.assertNotEqual(candidate.baseline.EXPECTED['scripts/andrea/web_page_local.py'],
                            archived.baseline.EXPECTED['scripts/andrea/web_page_local.py'])

    def test_original_questions_order_options_cache_and_latency_gates_are_unchanged(self):
        self.assertEqual(candidate.baseline.CASES, archived.baseline.CASES)
        self.assertEqual(candidate.baseline.ORDER, archived.baseline.ORDER)
        self.assertEqual((candidate.baseline.MIN_INPUT_REDUCTION_PERCENT, candidate.baseline.MIN_PREFILL_REDUCTION_PERCENT), (10, 10))
        self.assertEqual((candidate.baseline.MAX_CACHED_TOKENS, candidate.baseline.MIN_UNCACHED_FRACTION), (8, .98))
        self.assertEqual(candidate.EXPECTED_OLLAMA_VERSION, archived.EXPECTED_OLLAMA_VERSION)
        self.assertEqual(candidate.WORKER_SECONDS, 95)
        self.assertEqual(candidate.THERMAL_SAMPLE_SECONDS, (6, 18, 36))

    def test_archived_reference_wire_and_csv_and_price_candidate_wire_are_preserved(self):
        page = extracted(html_entry()+'<p>Additional unrelated material.</p>')
        for case in candidate.baseline.CASES:
            before = archived.prepared(page, case, 'production')
            after = candidate.prepared(page, case, 'production')
            self.assertEqual(after[:3], before[:3])
            self.assertEqual(after[3]['reason'], candidate.ARCHIVED_BASELINE_REVISION)
        for case in candidate.baseline.CASES[1:]:
            before = archived.prepared(page, case, 'compact')
            after = candidate.prepared(page, case, 'compact')
            self.assertEqual(after[:3], before[:3])
            self.assertEqual(after[3], {**before[3], 'sourceNetworkingScopeRefs': []})

    def test_candidate_native_call_has_the_full_original_schema_once_and_no_model_option_change(self):
        page = extracted('<h1>asyncio — Asynchronous I/O</h1><p>'+CATALOGUE+'</p>')
        _, messages, schema, _ = candidate.prepared(page, candidate.baseline.CASES[0], 'compact')
        calls = []
        class Opener:
            def open(self, request, timeout):
                calls.append((json.loads(request.data), timeout))
                return io.BytesIO(b'{"message":{"content":"{\\"claims\\":[]}"},"done":true,"done_reason":"stop"}\n')
        candidate.baseline.stream_probe(Opener(), messages, schema)
        self.assertEqual(len(calls), 1)
        payload, timeout = calls[0]
        self.assertEqual(payload['messages'], messages)
        self.assertEqual(payload['format'], schema)
        self.assertEqual(payload['options'], {'temperature': .4, 'num_predict': 512, 'num_ctx': 4096})
        self.assertEqual(payload['model'], candidate.baseline.MODEL)
        self.assertFalse(payload['think'])
        self.assertEqual(timeout, 90)

    def test_owned_worker_timeout_cleans_its_child_and_does_not_retry(self):
        child = Child(timeout=True)
        observer = StubObserver(child)
        value, _, errors, cleaned = candidate.collect(Path('project'), extracted(html_entry()), 1, 'compact',
            popen=lambda *a, **k: child, observer_factory=lambda _: observer)
        self.assertEqual(child.kills, 1)
        self.assertTrue(cleaned)
        self.assertTrue(observer.closed)
        self.assertEqual(errors, [])
        self.assertEqual(value['result']['errorKind'], 'owned_worker_deadline_no_retry')

    def test_owned_network_and_worker_boundaries_are_identical_to_the_tested_previous_runner(self):
        def functions(filename):
            tree = ast.parse((ROOT/'scripts/andrea'/filename).read_text())
            return {node.name: ast.dump(node, include_attributes=False) for node in tree.body if isinstance(node, ast.FunctionDef)}
        previous = functions('web_definition_latency_probe_body.py')
        current = functions('web_networking_scope_probe_body.py')
        for name in ('checked_page', 'page_worker', 'read_page', 'thermal_sample', 'worker_error',
                     'checked_worker', 'collect', 'model_worker'):
            with self.subTest(function=name):
                self.assertEqual(current[name], previous[name])

    def test_old_refusals_still_close_the_original_gates(self):
        report = json.loads((ROOT/'docs/andrea/web-single-rule-cardinality-mac-2026-10-06.json').read_text())
        rows = copy.deepcopy(report['rows'])
        quotes = {}
        for row in rows:
            quotes.setdefault(row['case'], {}).update({p['passage']: p['quote'] for p in row['checks']['claims']})
        for row in rows:
            own = quotes[row['case']]
            bank = ['Unused source unit for regression.\n']*max(own, default=1)
            for ref, quote in own.items():
                bank[ref-1] = quote
            row['checks'] = candidate.context.validate(row['result']['modelAnswer'], bank, True,
                                                      heading_ranges=[], contract=candidate.baseline)
            row['caseShapeMet'] = candidate.baseline.case_shape(row['case'], row['checks'])
        automatic = candidate.baseline.comparison(rows)
        self.assertFalse(automatic['technicalCaseShapesMet'])
        self.assertFalse(automatic['integrationAllowedByThisAutomaticReport'])

    def test_six_request_runner_keeps_balanced_order_and_records_any_refusal_as_failed(self):
        async_page = extracted('<h1>asyncio</h1><p>perform network IO and IPC;</p><p>'+CATALOGUE+'</p>')
        async_page['url'] = candidate.baseline.CASES[0]['url']
        csv_page = extracted(html_entry()+'<p>Unrelated source details remain available.</p>')
        pages = {async_page['url']: async_page, csv_page['url']: csv_page}
        report = self.report_fixture()
        bad = report['rows'][0]['rejectionDetails']['text']
        good_csv = report['rows'][1]['claims'][0]['text']
        class Reader:
            def get(self, path):
                return {'version': candidate.EXPECTED_OLLAMA_VERSION} if path == '/api/version' else {'models': []}
        for inject_refusal in (False, True):
            calls = []
            def collect(project, page, index, variant):
                calls.append((index, variant))
                bank = candidate.baseline.sentence_bank(page['text'])
                if index == 0:
                    io_ref = next(i+1 for i, unit in enumerate(bank) if 'network IO' in unit)
                    catalogue_ref = next(i+1 for i, unit in enumerate(bank) if 'handling OS signals' in unit)
                    text = bad if inject_refusal and variant == 'compact' else 'asyncio gestisce event loop per rete, sottoprocessi e segnali dell’OS.'
                    points = [{'passage': io_ref, 'text': 'asyncio permette IO di rete e IPC.'},
                              {'passage': catalogue_ref, 'text': text}]
                elif index == 1:
                    ref = next(i+1 for i, unit in enumerate(bank) if 'No automatic data type conversion' in unit)
                    points = [{'passage': ref, 'text': good_csv}]
                else:
                    points = []
                native = {'prompt_eval_count': 3000 if variant == 'production' else 1400,
                          'prompt_eval_cached_count': 0, 'prompt_evalMs': 50000 if variant == 'production' else 25000}
                result = {'status': 'completed', 'modelAnswer': json.dumps({'claims': points}),
                          'native': native, 'doneReason': 'stop'}
                return {'result': result}, [], [], True
            output = []
            with self.subTest(inject_refusal=inject_refusal), \
                    patch.object(candidate.platform, 'system', return_value='Darwin'), \
                    patch.object(candidate.baseline, 'verify_project'), \
                    patch.object(candidate.resources, 'Reader', Reader), \
                    patch.object(candidate, 'read_page', side_effect=lambda project, url: copy.deepcopy(pages[url])), \
                    patch.object(candidate, 'thermal_sample', return_value={}), \
                    patch.object(candidate, 'collect', side_effect=collect):
                automatic = candidate.run(ROOT, emit=output.append)
            self.assertEqual(calls, list(candidate.baseline.ORDER))
            self.assertEqual(automatic['technicalCaseShapesMet'], not inject_refusal)
            self.assertEqual(automatic['performanceOutcome'],
                             'gates_not_met' if inject_refusal else 'measured_gates_met_pending_semantic_review')
            self.assertEqual(automatic['referencePromptRevision'], candidate.ARCHIVED_BASELINE_REVISION)
            self.assertFalse(automatic['referenceIsCurrentInstalledPrompt'])
            self.assertFalse(automatic['integrationAllowedByThisAutomaticReport'])
            self.assertEqual(automatic['qualityVerdict'], 'pending_review')
            self.assertEqual(automatic['completed'], 6)
            rows = [json.loads(value) for value in output if isinstance(value, str) and value.startswith('{')]
            limits = [value['nativeClaimArrayLimit'] for value in rows if 'case' in value]
            self.assertEqual(limits, [2, 2, 1, 2, 2, 2])

    def report_fixture(self):
        return json.loads((ROOT/'docs/andrea/web-api-context-installed-mac-2026-10-06.json').read_text())


if __name__ == '__main__':
    unittest.main()
