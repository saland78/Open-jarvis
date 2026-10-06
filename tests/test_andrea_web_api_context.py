"""Live integration of the six-case reviewed candidate, without new inference."""
import ast
import copy
import json
from pathlib import Path
from types import SimpleNamespace as Chunk
import unittest
from unittest.mock import AsyncMock, patch

import web_page_context_contract as contract
import web_page_context_fetch as worker
import web_page_fetch as fetch
import web_page_fidelity as fidelity
import web_page_local as service
import web_definition_latency_probe as probe
import web_type_latency_probe as baseline
from test_andrea_web_definition_context import extracted, html_entry
from test_andrea_web_heading_latency import GOOD_CSV
from test_andrea_web_search_local import Process
from web_search_local import SearchError

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ('create and manage event loops, which provide asynchronous APIs for networking, '
             'running subprocesses, handling OS signals, etc;\n')


def prepared_csv():
    return extracted(html_entry()+'<p>Unrelated details remain in the original page for comparison.</p>')


def claim(ref, text):
    return json.dumps({'claims': [{'passage': ref, 'text': text}]}, ensure_ascii=False)


def page_from_bytes(body, content_type):
    def fake_fetch(url):
        title, text, partial = fetch.extract(body, content_type)
        return {'url': url, 'title': title, 'text': text, 'partial': partial, 'redirects': 0}
    return fake_fetch


class CandidateParityTests(unittest.TestCase):
    def test_every_pure_fidelity_function_is_identical_to_the_reviewed_candidate(self):
        production = ast.parse((ROOT/'scripts/andrea/web_page_fidelity.py').read_text())
        candidate = ast.parse((ROOT/'scripts/andrea/web_type_latency_probe.py').read_text())
        expected = {node.name: node for node in candidate.body if isinstance(node, ast.FunctionDef)}
        functions = [node for node in production.body if isinstance(node, ast.FunctionDef)]
        self.assertEqual(len(functions), 21)
        for node in functions:
            with self.subTest(function=node.name):
                self.assertEqual(ast.dump(node, include_attributes=False),
                                 ast.dump(expected[node.name], include_attributes=False))
        imports = [node for node in production.body if isinstance(node, (ast.Import, ast.ImportFrom))]
        self.assertNotIn('probe', ast.dump(ast.Module(body=imports, type_ignores=[])))

    def test_live_messages_schema_bank_and_policy_match_reviewed_wire_candidate(self):
        cases = [(prepared_csv(), baseline.CASES[1]),
                 (extracted('<h1>asyncio</h1><p>'+CATALOGUE+'</p>'), baseline.CASES[0]),
                 (prepared_csv(), baseline.CASES[2])]
        for page, case in cases:
            original = copy.deepcopy(page)
            with self.subTest(case=case['id']):
                self.assertEqual(contract.prepare(page, case['question']),
                                 probe.prepared(page, case, 'compact'))
                self.assertEqual(page, original)

    def test_all_six_actual_mac_answers_pass_without_repair_and_prior_reports_stay_distinct(self):
        report = json.loads((ROOT/'docs/andrea/web-signal-scope-mac-2026-10-06.json').read_text())
        rows = report['rows']
        banks = {}
        for case in {row['case'] for row in rows}:
            quotes = {point['passage']: point['quote'] for row in rows if row['case'] == case
                      for point in row['checks']['claims']}
            bank = ['Unused source unit for regression.\n']*max(quotes, default=1)
            for ref, quote in quotes.items():
                bank[ref-1] = quote
            banks[case] = bank
        outcomes = []
        for row in rows:
            with self.subTest(case=row['case'], variant=row['variant']):
                raw = row['result']['modelAnswer']
                bank = banks[row['case']]
                result = contract.validate(raw, bank, True, {'headingRanges': []}, row['selection'])
                outcomes.append(result['outcome'])
                self.assertEqual(result['claims'], row['checks']['claims'])
                self.assertEqual(json.dumps(json.loads(raw), ensure_ascii=False),
                                 json.dumps({'claims': [{'passage': p['passage'], 'text': p['text']}
                                                       for p in result['claims']]}, ensure_ascii=False))
        self.assertEqual(outcomes, ['accepted_pending_semantic_review']*4+['abstained']*2)
        self.assertEqual(report['manualReviewCounts'], {'favorable': 6, 'unfavorable': 0})
        self.assertEqual(rows[1]['installedPolicyChecks']['reason'], 'technical_term_missing_from_passage')
        self.assertFalse(report['originalAutomaticReport']['integrationAllowedByThisAutomaticReport'])
        self.assertEqual(json.loads((ROOT/'docs/andrea/web-single-rule-cardinality-mac-2026-10-06.json').read_text())['overallReview'],
                         'not_passed_no_adoption')

    def test_previous_os_broadening_is_refused_with_original_diagnostic(self):
        text = 'asyncio gestisce event loop, sottoprocessi e comunicazione con OS.'
        selection = {'selectedRefs': [1], 'outputPolicy': {'maxClaims': 2}}
        result = contract.validate(claim(1, text), [CATALOGUE], True, {'headingRanges': []}, selection)
        self.assertEqual(result['reason'], 'os_signal_scope_not_preserved')
        self.assertEqual(result['claims'], [])
        self.assertEqual(result['details']['text'], text)

    def test_selected_context_cannot_cite_omitted_passage_or_heading(self):
        page = prepared_csv()
        bank, _messages, _schema, selection = contract.prepare(page, baseline.CASES[1]['question'])
        refs = set(selection['selectedRefs'])
        omitted = next(i for i in range(1, len(bank)+1) if i not in refs)
        result = contract.validate(claim(omitted, 'Il testo contiene dettagli.'), bank, True, page, selection)
        self.assertEqual(result['outcome'], 'rejected')
        result = contract.validate(claim(1, 'csv tratta i file.'), bank, True, page, selection)
        self.assertEqual(result['outcome'], 'rejected')


class ReaderWorkerTests(unittest.TestCase):
    def test_worker_preserves_original_source_bytes_and_adds_proven_roles(self):
        html = ('<nav>Excluded navigation</nav><main>'+html_entry()+'</main>').encode()
        old = fetch.extract(html, 'text/html')
        original_parser, original_extract = fetch.TextParser, fetch.extract
        with patch.object(fetch, 'fetch_page', side_effect=page_from_bytes(html, 'text/html')):
            result = worker.read_request(b'{"url":"https://example.com/page"}')
        self.assertEqual((result['title'], result['text'], result['partial']), old)
        self.assertTrue(result['headingRanges'])
        self.assertEqual(result['definitionRanges'][0]['anchors'], ['csv.reader'])
        self.assertTrue(result['definitionRanges'][0]['complete'])
        self.assertIs(fetch.TextParser, original_parser)
        self.assertIs(fetch.extract, original_extract)

    def test_plain_text_has_no_inferred_html_roles(self):
        body = ('csv.reader is ordinary text here. '+CATALOGUE).encode()
        with patch.object(fetch, 'fetch_page', side_effect=page_from_bytes(body, 'text/plain')):
            result = worker.read_request(b'{"url":"https://example.com/page"}')
        self.assertEqual(result['text'], fetch.extract(body, 'text/plain')[1])
        self.assertEqual(result['headingRanges'], [])
        self.assertEqual(result['definitionRanges'], [])

    def test_private_destination_is_blocked_by_original_fetcher_and_globals_restored(self):
        original_parser, original_extract = fetch.TextParser, fetch.extract
        with patch.object(fetch.socket, 'getaddrinfo') as dns:
            result = worker.read_request(b'{"url":"https://localhost/"}')
        self.assertEqual(result, {'error': 'private_destination'})
        dns.assert_not_called()
        self.assertIs(fetch.TextParser, original_parser)
        self.assertIs(fetch.extract, original_extract)
        with patch.object(fetch, 'read_request', side_effect=RuntimeError('synthetic error')):
            with self.assertRaises(RuntimeError):
                worker.read_request(b'{}')
        self.assertIs(fetch.TextParser, original_parser)
        self.assertIs(fetch.extract, original_extract)


class LivePageIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_service_reader_uses_new_worker_roles_and_retains_full_audit_source(self):
        page = prepared_csv()
        page.pop('readMs')
        process = Process(page)
        pages = service.LocalWebPages()
        self.addCleanup(pages.clear)
        with patch.object(service.asyncio, 'create_subprocess_exec', AsyncMock(return_value=process)) as spawn:
            result = await pages.read({'url': page['url']})
        self.assertTrue(spawn.call_args.args[1].endswith('web_page_context_fetch.py'))
        self.assertEqual(result['text'], page['text'])
        self.assertEqual(result['definitionRanges'], page['definitionRanges'])
        self.assertEqual(result['headingRanges'], page['headingRanges'])
        self.assertEqual(pages.page, result)

    async def test_invalid_worker_roles_are_not_retained(self):
        for roles in ({'headingRanges': [[False, 5]], 'definitionRanges': []},
                      {'headingRanges': [], 'definitionRanges': [{'anchors': ['csv.reader'], 'range': [0, 9000], 'complete': True}]}):
            page = {k: v for k, v in prepared_csv().items() if k != 'readMs'}
            page.update(roles)
            pages = service.LocalWebPages()
            with patch.object(service.asyncio, 'create_subprocess_exec', AsyncMock(return_value=Process(page))):
                with self.assertRaisesRegex(SearchError, 'invalid_response'):
                    await pages.read({'url': page['url']})
            self.assertIsNone(pages.page)

    async def test_one_native_call_complete_rule_original_question_and_actual_input_metrics(self):
        page = {**prepared_csv(), 'pageId': 'token'}
        original = copy.deepcopy(page)
        pages = service.LocalWebPages()
        pages.page, pages.expires = page, service.time.monotonic()+300
        bank, messages, schema, selection = contract.prepare(page, baseline.CASES[1]['question'])
        ref = selection['outputPolicy']['sourceRuleRefs'][0]
        calls, closed = [], []
        async def stream(actual_messages, actual_schema):
            calls.append((actual_messages, actual_schema))
            try:
                yield Chunk(content=claim(ref, GOOD_CSV), finish_reason='stop')
            finally:
                closed.append(True)
        result = await pages.summarize({'pageId': 'token', 'question': baseline.CASES[1]['question']}, stream)
        self.assertEqual(calls, [(messages, schema)])
        self.assertEqual(closed, [True])
        self.assertEqual(schema['properties']['claims']['maxItems'], 1)
        self.assertEqual(json.loads(messages[1]['content'])['question'], baseline.CASES[1]['question'])
        self.assertEqual(result['outcome'], 'accepted_pending_semantic_review')
        self.assertEqual(result['claims'][0]['quote'], bank[ref-1])
        self.assertEqual(result['contextSelection'], selection)
        self.assertEqual(result['contractRevision'], contract.CONTRACT_REVISION)
        self.assertEqual(result['timings']['sourceCharacters'], len(page['text']))
        self.assertEqual(result['timings']['inputCharacters'], selection['modelSourceCharacters'])
        self.assertLess(result['timings']['inputCharacters'], result['timings']['sourceCharacters'])
        self.assertEqual(result['automaticRetries'], 0)
        self.assertEqual(result['qualityVerdict'], 'pending_review')
        self.assertEqual(pages.page, original)


if __name__ == '__main__':
    unittest.main()
