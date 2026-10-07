"""Actual unsupported heading, HTML provenance and finite latency protocol."""
import ast
import copy
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import web_heading_evidence as roles
import web_heading_latency_candidate as candidate
import web_heading_latency_probe as probe
import web_page_fetch as fetch
import web_scoped_latency_candidate as preceding
import web_scoped_latency_probe as preceding_probe
import web_sentence_contract as installed
import test_andrea_web_short_instructions as archived
from test_andrea_web_scoped_latency import CATALOGUE, OBSERVED

HEADING = 'asyncio — Asynchronous I/O\n'
IO = 'perform network IO and IPC;\n'
SUBPROCESS = 'control subprocesses;\n'
ASYNC = HEADING + IO + SUBPROCESS
RANGES = [[0, len(HEADING) - 1]]
CSV = archived.CSV
BAD_HEADING = "asyncio serve per gestire l'asincrono I/O, permettendo di eseguire operazioni in modo non bloccante."
GOOD_IO = 'asyncio permette di eseguire operazioni di I/O e comunicazione tra processi (IPC).'
GOOD_SUBPROCESS = 'asyncio consente di controllare i sottoprocessi.'
GOOD_CSV = ('csv.reader restituisce ogni riga come lista di stringhe, senza conversione automatica dei tipi, '
            'salvo che quando è specificato il formato QUOTE_NONNUMERIC, in cui i campi non racchiusi '
            'tra virgolette vengono trasformati in float.')


def raw(claims):
    return json.dumps({'claims': [{'passage': ref, 'text': text} for ref, text in claims]}, ensure_ascii=False)


def extracted(body):
    instances = []
    base = roles.parser_with_heading_roles(fetch.TextParser)
    class Captured(base):
        def __init__(self):
            super().__init__(); instances.append(self)
    expected = fetch.extract(body.encode(), 'text/html')
    with patch.object(fetch, 'TextParser', Captured):
        result = fetch.extract(body.encode(), 'text/html')
    if result != expected:
        raise AssertionError('source changed')
    ranges = roles.normalized_heading_ranges(instances[-1], result[1], fetch.MAX_TEXT)
    return result[1], ranges


class HtmlRoleTests(unittest.TestCase):
    def test_exact_source_with_main_nested_inline_heading_and_excluded_chrome(self):
        html = ('<title>Browser title</title><nav>Do not include navigation</nav><p>Outside main text.</p>'
                '<main><h1>asyncio — <em>Asynchronous I/O</em></h1>'
                '<p>asyncio provides APIs for <code>network IO and IPC</code>.</p>'
                '<script>secret</script><div hidden>secret</div><footer>Footer</footer></main>')
        page, ranges = extracted(html)
        self.assertEqual(page, 'asyncio — Asynchronous I/O\nasyncio provides APIs for network IO and IPC.')
        self.assertEqual(ranges, [[0, len(HEADING) - 1]])
        self.assertEqual(roles.context_only_refs(candidate.sentence_bank(page), ranges), [1])
        self.assertNotIn('secret', page)

    def test_all_six_html_heading_elements_with_prose_boundaries(self):
        for tag in sorted(roles.HEADINGS):
            with self.subTest(tag=tag):
                page, ranges = extracted(f'<div><{tag}>An actual heading with useful context</{tag}></div>'
                                          '<p>The documented library performs network I/O.</p>')
                self.assertEqual(roles.context_only_refs(candidate.sentence_bank(page), ranges), [1])

    def test_same_words_in_prose_are_not_excluded_by_a_title_string_match(self):
        page, ranges = extracted('<h1>An actual descriptive sentence.</h1>'
                                 '<p>An actual descriptive sentence.</p>')
        self.assertEqual(page, 'An actual descriptive sentence.\nAn actual descriptive sentence.')
        self.assertEqual(roles.context_only_refs(candidate.sentence_bank(page), ranges), [1])

    def test_whitespace_unicode_source_wrapping_and_inline_code_stay_exact(self):
        page, ranges = extracted('<h2>  Un\n titolo\u00a0con emoji 🧪 </h2>'
                                 '<p>Una frase\n completa con <code>I/O</code> e IPC.</p>'
                                 '<pre>first line\nsecond line of code</pre>')
        self.assertEqual(page, 'Un titolo con emoji 🧪\nUna frase completa con I/O e IPC.\nfirst line\nsecond line of code')
        self.assertEqual(roles.context_only_refs(candidate.sentence_bank(page), ranges), [1])

    def test_mixed_heading_prose_line_is_not_labelled_heading_only(self):
        # h5/h6 have no installed BREAK boundary; retain its prose, do not invent one.
        page, ranges = extracted('<h5>Some heading text</h5> The library controls subprocesses without extra work.')
        self.assertEqual(ranges, [])
        self.assertIn('subprocesses', page)

    def test_no_headings_does_not_guess_from_punctuation_or_language(self):
        page, ranges = extracted('<p>Unpunctuated prose about running subprocesses</p>'
                                 '<p>More documentation about network communication.</p>')
        self.assertEqual(ranges, [])
        self.assertEqual(roles.context_only_refs(candidate.sentence_bank(page), ranges), [])

    def test_visible_heading_remains_when_hidden_subtree_is_excluded(self):
        page, ranges = extracted('<div hidden><h1>Hidden heading</h1></div>'
                                 '<h2>Visible documentation heading</h2>'
                                 '<p>There is enough source text to complete extraction.</p>')
        self.assertEqual(page.splitlines()[0], 'Visible documentation heading')
        self.assertEqual(roles.context_only_refs(candidate.sentence_bank(page), ranges), [1])

    def test_6000_character_cap_and_long_heading_have_exact_bounded_roles(self):
        page, ranges = extracted('<p>' + 'x' * 5960 + '</p><h1>' + 'A heading. ' * 80 + '</h1>')
        self.assertEqual(len(page), 6000)
        self.assertEqual(ranges, [[5961, 6000]])
        refs = roles.context_only_refs(candidate.sentence_bank(page), ranges)
        self.assertTrue(refs)
        self.assertEqual(''.join(candidate.sentence_bank(page)), page)
        page, ranges = extracted('<h1>' + 'A heading. ' * 80 + '</h1><p>Real prose with facts.</p>')
        bank = candidate.sentence_bank(page)
        self.assertEqual(roles.context_only_refs(bank, ranges), list(range(1, len(bank))))

    def test_metadata_must_align_with_original_extraction(self):
        parser = roles.parser_with_heading_roles(fetch.TextParser)()
        parser.feed('<h1>A heading.</h1><p>A paragraph with enough text for the extractor.</p>')
        with self.assertRaisesRegex(ValueError, 'alignment'):
            roles.normalized_heading_ranges(parser, 'altered source', 6000)

    def test_missing_malformed_overlapping_and_non_boundary_roles_fail_closed(self):
        bank = candidate.sentence_bank(ASYNC)
        bad = (None, (), {'heading': 1}, [[True, 20]], [[0, False]], [[-1, 20]],
               [[0, 999]], [[0, 3]], [[1, 25]], [[0, 25], [0, 25]],
               [[26, 51], [0, 25]], [[0, 25, 26]])
        for ranges in bad:
            with self.subTest(ranges=ranges), self.assertRaisesRegex(ValueError, 'invalid_heading_metadata'):
                roles.context_only_refs(bank, ranges)
        self.assertEqual(roles.context_only_refs(bank, RANGES), [1])


class HeadingContractTests(unittest.TestCase):
    def test_exact_observed_heading_expansion_is_rejected_without_repair_or_reanchoring(self):
        bank = [HEADING] + ['Other retained context line.\n'] * 8 + [IO]
        answer = raw([(1, BAD_HEADING), (10, GOOD_IO)])
        old = preceding.validate(answer, bank, True)
        self.assertEqual(old['outcome'], 'accepted_pending_semantic_review')
        result = candidate.validate(answer, bank, True, heading_ranges=RANGES)
        self.assertEqual(result['reason'], 'heading_only_evidence')
        self.assertEqual(result['claims'], [])
        self.assertEqual(result['details']['text'], BAD_HEADING)
        self.assertEqual(result['details']['quote'], HEADING)
        self.assertEqual(probe.validate(answer, bank, True, heading_ranges=RANGES), result)

    def test_heading_is_in_context_and_inventory_but_not_native_evidence_enum(self):
        before = installed.prepare(ASYNC, 'Due funzionalità.')
        after = candidate.prepare(ASYNC, 'Due funzionalità.', heading_ranges=RANGES)
        self.assertEqual(before[0], after[0])
        self.assertEqual(''.join(after[0]), ASYNC)
        self.assertEqual(after, probe.compact_prepare(ASYNC, 'Due funzionalità.', heading_ranges=RANGES))
        payload = json.loads(after[1][1]['content'])
        self.assertEqual(payload.pop('contextOnly'), [1])
        self.assertEqual(payload, json.loads(before[1][1]['content']))
        self.assertEqual(after[2]['properties']['claims']['items']['properties']['passage']['enum'], [2, 3])
        self.assertEqual(probe.baseline_prepare(ASYNC, 'Due funzionalità.'), before)

    def test_real_supported_points_and_finite_scope_fix_remain_unmodified(self):
        for text, quote in ((GOOD_IO, IO), (GOOD_SUBPROCESS, SUBPROCESS), (OBSERVED, CATALOGUE), (GOOD_CSV, CSV)):
            result = candidate.validate(raw([(1, text)]), [quote], True, heading_ranges=[])
            self.assertEqual(result, preceding.validate(raw([(1, text)]), [quote], True))
            self.assertEqual(result['outcome'], 'accepted_pending_semantic_review')
            self.assertEqual(result['claims'][0]['quote'], quote)
            self.assertEqual(result['claims'][0]['text'], text)

    def test_both_variants_have_the_same_stricter_role_validator(self):
        self.assertEqual(candidate.validate(raw([(2, GOOD_IO), (3, GOOD_SUBPROCESS)]),
                         candidate.sentence_bank(ASYNC), True, heading_ranges=RANGES)['outcome'],
                         'accepted_pending_semantic_review')
        self.assertEqual(candidate.validate('{"claims":[]}', [CSV], True, heading_ranges=[])['outcome'], 'abstained')
        self.assertEqual(candidate.validate('{"claims":[]}', [CSV], False, heading_ranges=None)['reason'], 'stream_incomplete')
        self.assertEqual(candidate.validate(raw([(1, GOOD_CSV)]), [CSV], True, heading_ranges=None)['reason'], 'invalid_heading_metadata')

    def test_old_condition_qualifier_identifier_number_and_word_cut_failures_stay_failed(self):
        for text, quote, reason in ((archived.OBSERVED_BAD, CSV, 'unquoted_field_scope_not_preserved'),
                                    (archived.OBSERVED_CUT, CSV, 'sentence_not_complete'),
                                    ('csv.reader converte sempre i campi non quotati in float.', CSV, 'csv_conversion_condition_not_preserved'),
                                    ('asyncio controlla 500 sottoprocessi.', SUBPROCESS, 'unsupported_number'),
                                    ('asyncio gestisce comunicazione tra processi IPC.', IO, 'source_identifiers_not_preserved')):
            self.assertEqual(candidate.validate(raw([(1, text)]), [quote], True, heading_ranges=[])['reason'], reason)

    def test_heading_only_document_is_not_sent_to_a_model_as_descriptive_evidence(self):
        page = 'A heading with more than twenty characters.'
        with self.assertRaisesRegex(ValueError, 'no_bounded_evidence'):
            candidate.prepare(page, 'Funzioni?', heading_ranges=[[0, len(page)]])

    def test_ast_parity_guard_helpers_and_exact_installed_baseline(self):
        old, new, standalone = map(archived.functions, (preceding, candidate, probe))
        for name, node in old.items():
            if name not in ('prepare', 'validate'):
                self.assertEqual(ast.dump(node), ast.dump(new[name]), name)
            if name != 'prepare':
                self.assertEqual(ast.dump(new[name]), ast.dump(standalone[name]), name)
        baseline = copy.deepcopy(standalone['baseline_prepare']); baseline.name = 'prepare'
        self.assertEqual(ast.dump(baseline), ast.dump(archived.functions(installed)['prepare']))
        for name in ('stream_probe', 'native_metrics', 'cache_qualification', 'isolated_messages', 'case_shape'):
            self.assertEqual(ast.dump(standalone[name]), ast.dump(archived.functions(preceding_probe)[name]), name)
        for name, node in archived.functions(roles).items():
            self.assertEqual(ast.dump(node), ast.dump(standalone[name]), name)


class HeadingCacheTests(archived.CacheAttributionTests):
    def setUp(self):
        patcher = patch.object(archived, 'probe', probe)
        patcher.start(); self.addCleanup(patcher.stop)


class HeadingProbeTests(unittest.TestCase):
    def pages(self):
        return [{'url': probe.CASES[0]['url'], 'title': 'asyncio', 'text': ASYNC,
                 'partial': False, 'redirects': 0, 'headingRanges': RANGES, 'readMs': 1},
                {'url': probe.CASES[1]['url'], 'title': 'csv', 'text': CSV,
                 'partial': False, 'redirects': 0, 'headingRanges': [], 'readMs': 1}]

    def result(self, answer, status='completed'):
        return {'status': status, 'modelAnswer': answer, 'native': {'prompt_eval_count': 2000,
                'prompt_eval_cached_count': 4, 'prompt_evalMs': 40000}}

    def results(self):
        async_answer = raw([(2, GOOD_IO), (3, GOOD_SUBPROCESS)])
        csv_answer = raw([(1, GOOD_CSV)])
        return [self.result(a) for a in (async_answer, async_answer, csv_answer, csv_answer, '{"claims":[]}', '{"claims":[]}')]

    def test_six_original_requests_two_reads_unchanged_sources_options_and_no_installation(self):
        output = []
        with patch.object(probe, 'verify_project') as verify, patch.object(probe, 'read_heading_page', side_effect=self.pages()) as reader, \
                patch.object(probe, 'stream_probe', side_effect=self.results()) as model:
            rows = probe.run(Path('project'), opener=object(), emit=output.append)
        self.assertEqual(model.call_count, 6); self.assertEqual(reader.call_count, 2)
        self.assertEqual(verify.call_count, 13)
        self.assertTrue(all(row['caseShapeMet'] for row in rows))
        self.assertEqual(probe.CASES, preceding_probe.CASES)
        self.assertEqual(probe.ORDER, preceding_probe.ORDER)
        self.assertEqual(probe.EXPECTED, preceding_probe.EXPECTED)
        for row in rows:
            self.assertFalse(row['productionModified']); self.assertFalse(row['modelOptionsChanged'])
            self.assertFalse(row['vaultRead']); self.assertEqual(row['automaticRetries'], 0)
            self.assertEqual(row['qualityVerdict'], 'pending_review')
            self.assertTrue(row['bothVariantsUseSameCandidateValidator'])
            self.assertTrue(row['fullSourcePreserved'])
            self.assertEqual(row['installedBaselineInputUnchanged'], row['variant'] == 'production')
        self.assertEqual(probe.comparison(rows)['fixedGates'], preceding_probe.comparison(rows)['fixedGates'])

    def test_complete_heading_rejection_is_retained_and_never_retried_or_hidden(self):
        results = self.results(); results[1] = self.result(raw([(1, BAD_HEADING), (2, GOOD_IO)]))
        with patch.object(probe, 'verify_project'), patch.object(probe, 'read_heading_page', side_effect=self.pages()), \
                patch.object(probe, 'stream_probe', side_effect=results) as model:
            rows = probe.run(Path('project'), opener=object(), emit=lambda _: None)
        self.assertEqual(model.call_count, 6)
        self.assertEqual(rows[1]['checks']['reason'], 'heading_only_evidence')
        self.assertFalse(rows[1]['caseShapeMet'])
        self.assertEqual(rows[1]['result']['modelAnswer'], results[1]['modelAnswer'])
        self.assertEqual(rows[1]['installedPolicyChecks']['outcome'], 'accepted_pending_semantic_review')
        self.assertFalse(probe.comparison(rows)['technicalCaseShapesMet'])

    def test_incomplete_first_stream_stops_without_retry(self):
        with patch.object(probe, 'verify_project'), patch.object(probe, 'read_heading_page', side_effect=self.pages()), \
                patch.object(probe, 'stream_probe', return_value=self.result('{"claims":[]}', 'incomplete')) as model:
            with self.assertRaisesRegex(probe.CheckError, 'Trasporto incompleto'):
                probe.run(Path('project'), opener=object(), emit=lambda _: None)
        self.assertEqual(model.call_count, 1)

    def test_alignment_inventory_schema_or_required_context_change_prevents_all_inference(self):
        pages = self.pages(); pages[1]['text'] = 'Not enough required context for the requested CSV rule.'
        with patch.object(probe, 'verify_project'), patch.object(probe, 'read_heading_page', side_effect=pages), \
                patch.object(probe, 'stream_probe') as model:
            with self.assertRaisesRegex(probe.CheckError, 'Contesto richiesto assente'):
                probe.run(Path('project'), opener=object(), emit=lambda _: None)
        model.assert_not_called()
        before = installed.prepare(ASYNC, 'Domanda')
        after = candidate.prepare(ASYNC, 'Domanda', heading_ranges=RANGES)
        for field in ('question', 'passages', 'protectedIdentifiers'):
            changed = copy.deepcopy(after); payload = json.loads(changed[1][1]['content']); payload[field] = 'altered'
            changed[1][1]['content'] = json.dumps(payload)
            with self.assertRaises(probe.CheckError): probe.preflight_pair(before, changed, self.pages()[0])
        changed = copy.deepcopy(after)
        changed[2]['properties']['claims']['maxItems'] = 3
        with self.assertRaises(probe.CheckError): probe.preflight_pair(before, changed, self.pages()[0])

    def test_observed_title_must_actually_be_excluded_before_collection(self):
        pages = self.pages(); pages[0]['headingRanges'] = []
        with patch.object(probe, 'verify_project'), patch.object(probe, 'read_heading_page', side_effect=pages), \
                patch.object(probe, 'stream_probe') as model:
            with self.assertRaisesRegex(probe.CheckError, 'titolo iniziale'):
                probe.run(Path('project'), opener=object(), emit=lambda _: None)
        model.assert_not_called()

    def test_reader_subprocess_is_finite_and_does_not_contact_the_model_or_api(self):
        page = self.pages()[0]; page.pop('readMs')
        completed = SimpleNamespace(returncode=0, stdout=json.dumps(page).encode())
        with patch.object(probe.subprocess, 'run', return_value=completed) as worker, patch.object(probe, 'post') as api, \
                patch.object(probe, 'stream_probe') as model:
            read = probe.read_heading_page(Path('project'), page['url'])
        self.assertEqual(read['text'], ASYNC)
        self.assertEqual(read['headingRanges'], RANGES)
        self.assertEqual(worker.call_count, 1)
        self.assertEqual(worker.call_args.kwargs['timeout'], 25)
        self.assertEqual(json.loads(worker.call_args.kwargs['input']), {'url': page['url']})
        self.assertEqual(worker.call_args.args[0][-1], '--page-worker')
        api.assert_not_called(); model.assert_not_called()
        with patch.object(probe.subprocess, 'run', side_effect=probe.subprocess.TimeoutExpired('owned-reader', 25)) as worker:
            with self.assertRaisesRegex(probe.CheckError, 'Lettura scaduta'):
                probe.read_heading_page(Path('project'), page['url'])
        self.assertEqual(worker.call_count, 1)

    def test_reader_errors_or_missing_roles_fail_before_any_model_call(self):
        for page in ({'error': 'private_destination'}, {k:v for k,v in self.pages()[0].items() if k != 'headingRanges'},
                     {**self.pages()[0], 'headingRanges': [[0, 3]]}):
            with self.subTest(page=page), self.assertRaises(ValueError): probe.checked_page(page)

    def test_worker_uses_pinned_reader_network_policy_and_exact_extract_hook(self):
        class Loader:
            def exec_module(self, module):
                for name in ('TextParser', 'extract', 'MAX_TEXT'):
                    setattr(module, name, getattr(fetch, name))
                def read_request(data):
                    self.request = json.loads(data)
                    html = ('<h1>asyncio — Asynchronous I/O</h1><p>perform network IO and IPC;</p>'
                            '<p>control subprocesses;</p>')
                    # extract's globals use the installed module; patch only its parser.
                    with patch.object(fetch, 'TextParser', module.TextParser):
                        title, text, partial = module.extract(html.encode(), 'text/html')
                    return {'url': self.request['url'], 'title': title, 'text': text, 'partial': partial, 'redirects': 0}
                module.read_request = read_request
        loader = Loader()
        spec = SimpleNamespace(loader=loader)
        fake_module = SimpleNamespace()
        stdin = SimpleNamespace(buffer=io.BytesIO(json.dumps({'url': probe.CASES[0]['url']}).encode()))
        output = io.StringIO()
        with patch.object(probe, 'verify_project') as verify, patch.object(probe.importlib.util, 'spec_from_file_location', return_value=spec) as imported, \
                patch.object(probe.importlib.util, 'module_from_spec', return_value=fake_module), patch.object(probe.sys, 'stdin', stdin), \
                patch('sys.stdout', output):
            probe.page_worker(Path('project'))
        verify.assert_called_once_with(Path('project'))
        self.assertEqual(imported.call_args.args[1], Path('project/scripts/andrea/web_page_fetch.py'))
        page = json.loads(output.getvalue())
        self.assertEqual(page['text'], ASYNC.rstrip('\n'))
        self.assertEqual(page['headingRanges'], RANGES)
        self.assertEqual(loader.request, {'url': probe.CASES[0]['url']})


if __name__ == '__main__': unittest.main()
