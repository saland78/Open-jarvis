"""Complete source entry selection, real prior failures and unchanged gates."""
import ast
import copy
import io
import json
from pathlib import Path
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import web_definition_context as context
import web_definition_latency_probe as probe
import web_heading_evidence as headings
import web_mechanism_latency_candidate as mechanism
import web_page_fetch as fetch
import web_type_latency_probe as baseline
from test_andrea_web_type_latency import CSV, OBSERVED_DECIMAL
from test_andrea_web_heading_latency import GOOD_CSV, IO, SUBPROCESS, GOOD_IO, GOOD_SUBPROCESS
from test_andrea_web_request_resources import Child, worker_value, StubObserver

ROOT = Path(__file__).resolve().parents[1]


def extracted(html):
    instances = []
    instrumented = context.parser_with_definition_roles(headings.parser_with_heading_roles(fetch.TextParser))
    class Captured(instrumented):
        def __init__(self):
            super().__init__()
            instances.append(self)
    original = fetch.extract(html.encode(), 'text/html')
    with patch.object(fetch, 'TextParser', Captured):
        result = fetch.extract(html.encode(), 'text/html')
    if result != original:
        raise AssertionError('original source changed')
    return {'url': baseline.CASES[1]['url'], 'title': result[0], 'text': result[1],
            'partial': result[2], 'redirects': 0, 'readMs': 1,
            'headingRanges': headings.normalized_heading_ranges(instances[-1], result[1], fetch.MAX_TEXT),
            'definitionRanges': context.normalized_definition_ranges(instances[-1], result[1], fetch.MAX_TEXT)}


def html_entry(name='csv.reader', rule=CSV, close=True, suffix=''):
    return ('<h1>csv — CSV File Reading and Writing</h1><p>Unrelated context about documents.</p>'
            '<dl class="py function"><dt id="'+name+'"><span>'+name+'</span>(file)</dt><dd>'
            '<p>Return a reader object. Inputs must be strings in the defined format.</p>'
            '<p>'+rule+'</p>'+suffix+'</dd>'+('</dl>' if close else ''))


def prepare(page, question=None):
    return context.prepare(page['text'], question or baseline.CASES[1]['question'],
                           heading_ranges=page['headingRanges'], definition_ranges=page['definitionRanges'], contract=baseline)


def raw(ref, text):
    return json.dumps({'claims': [{'passage': ref, 'text': text}]})


class ReaderTests(unittest.TestCase):
    def test_main_unicode_inline_whitespace_code_and_excluded_chrome_keep_source_exact(self):
        html = ('<nav>private navigation</nav><p>Outside main.</p><main>'+html_entry(
            suffix='<pre>first code line\nsecond code line</pre><p>Una condizione 🧪 finale.</p>')+
            '<footer>private footer</footer><div hidden>private data</div></main>')
        page = extracted(html)
        self.assertNotIn('private', page['text'])
        self.assertNotIn('Outside main', page['text'])
        self.assertEqual(len(page['definitionRanges']), 1)
        entry = page['definitionRanges'][0]
        self.assertTrue(entry['complete'])
        self.assertEqual(entry['anchors'], ['csv.reader'])
        own = page['text'][slice(*entry['range'])]
        self.assertIn('first code line\nsecond code line', own)
        self.assertIn('Una condizione 🧪 finale.', own)
        self.assertIn('QUOTE_NONNUMERIC', own)

    def test_complete_reader_and_6000_clipped_writer_are_distinct(self):
        page = extracted(html_entry()+'<dl><dt id="csv.writer">csv.writer(file)</dt><dd><p>'+ 'Long writer context. '*400+'</p></dd></dl>')
        self.assertEqual(len(page['text']), 6000)
        reader, writer = page['definitionRanges']
        self.assertTrue(reader['complete']); self.assertFalse(writer['complete'])
        self.assertEqual(prepare(page)[3]['mode'], 'complete_api_entries')
        self.assertEqual(prepare(page, 'Descrivi csv.writer.')[3]['reason'], 'definition_incomplete_or_mixed')

    def test_unclosed_malformed_mixed_and_hidden_anchor_cannot_narrow(self):
        cases = [html_entry(close=False),
                 '<div>'+html_entry(close=False)+'</div>',
                 '<p>Outside prose</p><dl><dt id="csv.reader">csv.reader</dt></dl> Mixed outer prose.' ]
        for html in cases:
            with self.subTest(html=html[:40]):
                self.assertEqual(prepare(extracted(html))[3]['mode'], 'full_context')
        page = extracted('<dl><dt hidden id="csv.reader">Hidden API name</dt><dd><p>'+CSV+'</p></dd></dl>')
        self.assertEqual(page['definitionRanges'], [])
        self.assertEqual(prepare(page)[3]['mode'], 'full_context')

    def test_nested_entries_have_whole_parent_coverage(self):
        page = extracted(html_entry(name='sample.Parent', suffix=(
            '<dl><dt id="sample.Parent.child">sample.Parent.child()</dt><dd>'
            '<p>Child operations have an independent condition.</p></dd></dl>')))
        self.assertEqual(len(page['definitionRanges']), 2)
        selected = prepare(page, 'Descrivi sample.Parent.')[3]
        self.assertEqual(selected['mode'], 'complete_api_entries')
        bank = baseline.sentence_bank(page['text'])
        self.assertIn('Child operations have an independent condition.', ''.join(bank[r-1] for r in selected['selectedRefs']))

    def test_hidden_outside_main_and_non_dt_ids_are_not_api_roles(self):
        html = ('<dl><dt id="hidden.api">hidden.api</dt><dd>Outside main text</dd></dl>'
                '<main><p id="csv.reader">This paragraph is ordinary prose.</p>'+html_entry()+'</main>')
        page = extracted(html)
        self.assertEqual([item['anchors'] for item in page['definitionRanges']], [['csv.reader']])
        page = extracted('<p id="csv.reader">Ordinary prose contains no API definition.</p><p>'+CSV+'</p>')
        self.assertEqual(page['definitionRanges'], [])

    def test_alignment_failure_is_not_guessed_and_all_source_remains_unchanged(self):
        parser = context.parser_with_definition_roles(fetch.TextParser)()
        parser.feed(html_entry())
        with self.assertRaisesRegex(ValueError, 'alignment'):
            context.normalized_definition_ranges(parser, 'different source', 6000)


class SelectionTests(unittest.TestCase):
    def test_same_bank_question_and_original_numbering_with_complete_conditions(self):
        page = extracted(html_entry(suffix='<p>Unless the special mode is selected, that conversion never occurs.</p>')+
                         '<p>Other module APIs and unrelated definitions remain in the audit source.</p>')
        bank, messages, schema, selected = prepare(page)
        self.assertEqual(bank, baseline.sentence_bank(page['text']))
        self.assertEqual(''.join(bank), page['text'])
        payload = json.loads(messages[1]['content'])
        self.assertEqual(payload['question'], baseline.CASES[1]['question'])
        self.assertEqual(payload['passages'], [[ref, bank[ref-1]] for ref in selected['selectedRefs']])
        self.assertIn('Unless the special mode is selected', ''.join(unit for _, unit in payload['passages']))
        self.assertLess(selected['modelSourceCharacters'], selected['sourceCharacters'])
        refs = schema['properties']['claims']['items']['properties']['passage']['enum']
        self.assertNotIn(1, refs)  # heading remains context, not evidence
        for ref in refs: self.assertIn(ref, selected['selectedRefs'])
        quote_ref = next(ref for ref in refs if 'No automatic data type conversion' in bank[ref-1])
        result = context.validate(raw(quote_ref, GOOD_CSV), bank, True,
                                  heading_ranges=page['headingRanges'], contract=baseline, selection=selected)
        self.assertEqual(result['outcome'], 'accepted_pending_semantic_review')
        self.assertEqual(result['claims'][0]['text'], GOOD_CSV)

    def test_general_missing_unmatched_and_multiple_api_questions_keep_full_context(self):
        page = extracted(html_entry()+'<p>Other full source text is kept.</p>')
        for question in ('Sintetizza questa pagina.', baseline.CASES[2]['question'],
                         'Confronta csv.reader e csv.writer.', 'Descrivi csv.Reader.'):
            with self.subTest(question=question):
                bank, messages, _, selected = prepare(page, question)
                self.assertEqual(selected['mode'], 'full_context')
                self.assertEqual(json.loads(messages[1]['content'])['passages'], [[i+1, p] for i, p in enumerate(bank)])
                self.assertEqual(selected['omittedSourceCharacters'], 0)
                self.assertEqual(messages[0]['content'], context.SHORT_SYSTEM + context.MECHANISM_INSTRUCTION)
                self.assertLess(len(messages[0]['content']), len(baseline.SHORT_SYSTEM))

    def test_all_matching_duplicate_entries_preserve_conflicting_or_later_conditions(self):
        second = '<dl><dt id="csv.reader">csv.reader(file)</dt><dd><p>A later warning changes the applicable scope.</p></dd></dl>'
        page = extracted(html_entry()+second+'<p>Outside unrelated text.</p>')
        bank, _, _, selected = prepare(page)
        self.assertEqual(selected['mode'], 'complete_api_entries')
        self.assertIn('A later warning changes', ''.join(bank[r-1] for r in selected['selectedRefs']))
        changed = copy.deepcopy(page); changed['definitionRanges'][1]['complete'] = False
        self.assertEqual(prepare(changed)[3]['mode'], 'full_context')

    def test_budget_cannot_cut_off_an_exception_or_tail(self):
        page = extracted(html_entry(suffix='<p>'+'Filler context. '*240+'A final exception applies to the whole operation.</p>'))
        bank, messages, _, selected = prepare(page)
        self.assertEqual(selected['reason'], 'whole_definition_exceeds_budget_or_no_reduction')
        self.assertIn('A final exception applies', ''.join(unit for _, unit in json.loads(messages[1]['content'])['passages']))
        self.assertEqual(''.join(bank), page['text'])

    def test_long_units_split_at_sentences_are_all_preserved_without_rewriting(self):
        page = extracted(html_entry(rule='A long source statement retains its condition. '*30)+ '<p>Additional module context.</p>')
        bank, messages, _, selected = prepare(page)
        self.assertEqual(selected['mode'], 'complete_api_entries')
        self.assertEqual(''.join(bank), page['text'])
        own = page['text'][slice(*page['definitionRanges'][0]['range'])]
        sent = ''.join(unit for ref, unit in json.loads(messages[1]['content'])['passages'] if ref not in baseline.context_only_refs(bank, page['headingRanges']))
        self.assertEqual(sent.rstrip('\n'), own)

    def test_malformed_unaligned_bool_and_unsorted_metadata_fail_closed(self):
        page = extracted(html_entry())
        invalid = (None, (), [{'anchors': ['csv.reader'], 'range': [True, 20], 'complete': True}],
                   [{'anchors': ['csv.reader'], 'range': [1, 20], 'complete': True}],
                   [{'anchors': ['invalid'], 'range': [0, 20], 'complete': True}],
                   [{'anchors': ['csv.reader'], 'range': [0, 20000], 'complete': True}])
        for ranges in invalid:
            changed = copy.deepcopy(page); changed['definitionRanges'] = ranges
            with self.subTest(ranges=ranges), self.assertRaisesRegex(ValueError, 'metadata'):
                prepare(changed)

    def test_generated_reference_to_an_omitted_passage_is_rejected_without_repair(self):
        page = extracted(html_entry()+'<p>control subprocesses;</p>')
        bank, _, _, selected = prepare(page)
        ref = next(i+1 for i, unit in enumerate(bank) if unit.strip() == 'control subprocesses;')
        result = context.validate(raw(ref, GOOD_SUBPROCESS), bank, True,
                                  heading_ranges=page['headingRanges'], contract=baseline, selection=selected)
        self.assertEqual(result['reason'], 'evidence_not_supplied_to_model')
        self.assertEqual(result['details']['text'], GOOD_SUBPROCESS)

    def test_prior_observed_failures_and_scope_type_identifier_guards_are_identical(self):
        cases = ((OBSERVED_DECIMAL, CSV), (GOOD_CSV, CSV),
                 ('asyncio consente di gestire sottoprocessi attraverso un’interfaccia specifica.', SUBPROCESS),
                 (GOOD_IO, IO), (GOOD_SUBPROCESS, SUBPROCESS),
                 ('csv.reader converte sempre i campi non quotati in float.', CSV),
                 ('La funzione controlla 500 sottoprocessi.', SUBPROCESS))
        for text, quote in cases:
            answer = raw(1, text)
            with self.subTest(text=text):
                self.assertEqual(context.validate(answer, [quote], True, heading_ranges=[], contract=baseline),
                                 mechanism.validate(answer, [quote], True, heading_ranges=[]))


class ObservedMacTermTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((ROOT/'docs/andrea/web-complete-api-context-mac-2026-10-06.json').read_text())
        cls.rows = cls.report['rows']

    def source_bank(self, case):
        # Actual public source quotations from the unchanged six-case report.
        # Missing units are not evidence in these regression tests.
        quotes = {}
        for row in self.rows:
            if row['case'] != case:
                continue
            for claim in row['checks']['claims']:
                quotes[claim['passage']] = claim['quote']
            details = row['checks'].get('details', {})
            if 'quote' in details:
                quotes[details['passage']] = details['quote']
        bank = ['Unused source unit for this regression.\n']*max(quotes)
        for ref, quote in quotes.items():
            bank[ref-1] = quote
        return bank

    def test_actual_process_and_encapsulated_translations_remain_rejected_without_repair(self):
        for position, reason in ((1, 'source_technical_terms_not_preserved'),
                                 (2, 'unquoted_field_scope_not_preserved')):
            row = self.rows[position]
            bank = self.source_bank(row['case'])
            answer, original_bank = row['result']['modelAnswer'], list(bank)
            result = context.validate(answer, bank, True, heading_ranges=[], contract=baseline)
            self.assertEqual(result['reason'], reason)
            self.assertEqual(result['claims'], [])
            self.assertEqual(result['details']['text'], row['checks']['details']['text'])
            self.assertEqual(bank, original_bank)
            self.assertEqual(row['result']['modelAnswer'], answer)

    def test_source_subprocess_equivalent_and_existing_io_claim_are_supported(self):
        bank = self.source_bank('asyncio_scope')
        data = json.loads(self.rows[1]['result']['modelAnswer'])
        data['claims'][1]['text'] = 'asyncio consente di creare e gestire event loop per rete, sottoprocessi e segnali dell’OS.'
        counterexample = json.dumps(data, ensure_ascii=False)
        result = context.validate(counterexample, bank, True, heading_ranges=[], contract=baseline)
        self.assertEqual(result['outcome'], 'accepted_pending_semantic_review')
        self.assertEqual([claim['text'] for claim in result['claims']], [claim['text'] for claim in data['claims']])
        self.assertEqual(self.report['overallReview'], 'not_passed_no_adoption')

    def test_actual_single_complete_csv_rule_is_preserved(self):
        row = self.rows[3]
        result = context.validate(row['result']['modelAnswer'], self.source_bank(row['case']), True,
                                  heading_ranges=[], contract=baseline)
        self.assertEqual(result['outcome'], 'accepted_pending_semantic_review')
        self.assertEqual(result['claims'], row['checks']['claims'])

    def test_correct_technical_terms_do_not_make_two_copies_of_a_rule_distinct(self):
        row = self.rows[2]
        data = json.loads(row['result']['modelAnswer'])
        for claim in data['claims']:
            claim['text'] = claim['text'].replace('non incapsulati', 'non racchiusi tra virgolette')
        answer = json.dumps(data, ensure_ascii=False)
        bank = self.source_bank(row['case'])
        original = list(bank)
        self.assertEqual(baseline.validate(answer, bank, True, heading_ranges=[])['outcome'],
                         'accepted_pending_semantic_review')
        result = context.validate(answer, bank, True, heading_ranges=[], contract=baseline)
        self.assertEqual(result['reason'], 'csv_conversion_rule_repeated')
        self.assertEqual(result['details']['earlierClaimIndex'], 1)
        self.assertEqual(result['details']['claimIndex'], 2)
        self.assertEqual(result['details']['text'], data['claims'][1]['text'])
        self.assertEqual(result['claims'], [])
        self.assertEqual(bank, original)

    def test_same_passage_can_support_two_distinct_facts(self):
        quote = 'Network operations exchange data while callbacks schedule independent work.\n'
        claims = [{'passage': 1, 'text': 'Le operazioni di rete scambiano dati.'},
                  {'passage': 1, 'text': 'I callback pianificano lavoro indipendente.'}]
        result = context.validate(json.dumps({'claims': claims}), [quote], True,
                                  heading_ranges=[], contract=baseline)
        self.assertEqual(result['outcome'], 'accepted_pending_semantic_review')
        self.assertEqual(len(result['claims']), 2)

    def test_actual_performance_pairs_pass_but_failed_answers_cannot_close_the_gate(self):
        report = baseline.comparison(self.rows)
        self.assertEqual(report['pairs'], self.report['originalAutomaticReport']['pairs'])
        self.assertTrue(all(pair['performanceGateMet'] for pair in report['pairs']))
        self.assertFalse(report['technicalCaseShapesMet'])
        self.assertEqual(report['performanceOutcome'], 'gates_not_met')
        self.assertFalse(report['integrationAllowedByThisAutomaticReport'])


class ProtocolTests(unittest.TestCase):
    def test_exact_embedded_sources_and_body(self):
        folder = ROOT/'scripts/andrea'
        for name, filename in (('BASELINE_SOURCE', 'web_type_latency_probe.py'),
                               ('RESOURCE_SOURCE', 'latency_resource_diagnostic.py'),
                               ('CONTEXT_SOURCE', 'web_definition_context.py')):
            self.assertEqual(getattr(probe, name), (folder/filename).read_text())
        body = (folder/'web_definition_latency_probe_body.py').read_text().replace('from __future__ import annotations\n', '')
        self.assertTrue((folder/'web_definition_latency_probe.py').read_text().endswith(body))
        self.assertEqual(probe.baseline.ORDER, baseline.ORDER)
        self.assertEqual(probe.baseline.CASES, baseline.CASES)
        self.assertEqual(probe.baseline.EXPECTED, baseline.EXPECTED)
        self.assertEqual((probe.baseline.MIN_INPUT_REDUCTION_PERCENT, probe.baseline.MIN_PREFILL_REDUCTION_PERCENT), (10, 10))
        self.assertEqual((probe.baseline.MAX_CACHED_TOKENS, probe.baseline.MIN_UNCACHED_FRACTION), (8, .98))

    def test_production_messages_bank_schema_question_exactly_match_installed_input(self):
        page = extracted(html_entry())
        bank, messages, schema, selection = probe.prepared(page, baseline.CASES[1], 'production')
        self.assertEqual((bank, messages, schema), baseline.baseline_prepare(page['text'], baseline.CASES[1]['question']))
        self.assertEqual(selection['mode'], 'full_context')

    def test_preflight_refuses_missing_complete_definition_before_model_calls(self):
        page = extracted('<p>'+CSV+'</p>')
        with self.assertRaisesRegex(ValueError, 'complete_csv_definition'):
            probe.prepared(page, baseline.CASES[1], 'compact')

    def test_owned_child_is_bounded_one_request_no_shell_retry_or_stderr_leak(self):
        child = Child()
        observers = []
        def observer_factory(worker):
            observer = StubObserver(worker); observer.errors = []
            observers.append(observer)
            return observer
        with patch.object(probe.subprocess, 'Popen', return_value=child) as create:
            value, rows, errors, cleaned = probe.collect(Path('project'), extracted(html_entry()), 1, 'compact',
                                               popen=create, observer_factory=observer_factory)
        self.assertEqual(create.call_count, 1)
        self.assertNotIn('shell', create.call_args.kwargs)
        self.assertEqual(create.call_args.args[0][-1], '--model-worker')
        self.assertEqual(child.calls[0][1], 95)
        self.assertEqual(child.kills, 0); self.assertTrue(cleaned)
        self.assertEqual(value, worker_value()); self.assertTrue(rows)
        self.assertEqual(errors, [])
        self.assertNotIn('secret', json.dumps(value))

    def test_deadline_and_interrupt_cleanup_only_owned_child(self):
        child = Child(timeout=True)
        observer = StubObserver(child); observer.errors = []
        value, _, _, cleaned = probe.collect(Path('project'), extracted(html_entry()), 1, 'compact',
                                         popen=lambda *a, **k: child, observer_factory=lambda _: observer)
        self.assertEqual(child.kills, 1); self.assertTrue(cleaned)
        self.assertEqual(value['result']['errorKind'], 'owned_worker_deadline_no_retry')
        child = Child(); original = child.communicate; calls = []
        def interrupted(*a, **kw):
            calls.append(1)
            if len(calls) == 1: raise KeyboardInterrupt()
            return original(*a, **kw)
        child.communicate = interrupted; observer = StubObserver(child); observer.errors = []
        with self.assertRaises(KeyboardInterrupt):
            probe.collect(Path('project'), extracted(html_entry()), 1, 'compact', popen=lambda *a, **k: child,
                          observer_factory=lambda _: observer)
        self.assertEqual(child.kills, 1); self.assertTrue(observer.closed)

    def test_worker_duplicate_json_oversize_and_nonfinite_timing_are_refused(self):
        for raw_bytes in (b'invalid', b'x'*65537, b'{"result":{},"result":{}}'):
            child = Child(raw=raw_bytes)
            observer = StubObserver(child); observer.errors = []
            value, _, _, _ = probe.collect(Path('project'), extracted(html_entry()), 1, 'compact',
                                       popen=lambda *a, **k: child, observer_factory=lambda _: observer)
            self.assertEqual(value['result']['status'], 'error')
            self.assertEqual(len(child.calls), 1)
        for value in (True, float('inf'), float('nan'), -1):
            changed = worker_value(); changed['requestStartedMonotonic'] = value
            with self.assertRaises(ValueError): probe.checked_worker(changed)

    def test_small_thermal_read_only_no_cpu_process_scan_or_settings_mutation(self):
        calls = []
        class Reader:
            issues = []
            def command(self, label, command):
                calls.append(command)
                return 'CPU_Speed_Limit = 62\nCPU_Scheduler_Limit = 100\nCPU_Available_CPUs = 16'
        with patch.object(probe.resources, 'Reader', Reader):
            result = probe.thermal_sample()
        self.assertEqual(calls, [['/usr/bin/pmset', '-g', 'therm']])
        self.assertEqual(result['thermalLimits']['CPU_Speed_Limit'], 62)

    def test_original_gates_failure_cannot_be_relabelled_as_success(self):
        from test_andrea_web_heading_latency import HeadingCacheTests
        rows = HeadingCacheTests().rows()
        rows[1]['result']['native']['prompt_evalMs'] = rows[0]['result']['native']['prompt_evalMs']*.95
        result = probe.baseline.comparison(rows)
        self.assertEqual(result['performanceOutcome'], 'gates_not_met')
        self.assertEqual(result['fixedGates']['minPrefillReductionPercent'], 10)
        self.assertFalse(result['integrationAllowedByThisAutomaticReport'])

    def test_six_original_calls_once_balanced_order_unchanged_sources_and_explicit_selection(self):
        csv_page = extracted(html_entry()+'<p>Other unrelated source text.</p>')
        async_page = extracted('<h1>asyncio — Asynchronous I/O</h1><p>'+IO+'</p><p>'+SUBPROCESS+'</p>')
        async_page['url'] = baseline.CASES[0]['url']
        calls, emitted = [], []
        def read_page(project, url):
            return copy.deepcopy(csv_page if url == csv_page['url'] else async_page)
        def collect(project, page, index, variant):
            calls.append((index, variant))
            bank, _, _, selected = probe.prepared(page, baseline.CASES[index], variant)
            if index == 0:
                claims = [{'passage': i+1, 'text': GOOD_IO if 'IPC' in unit else GOOD_SUBPROCESS}
                          for i, unit in enumerate(bank) if 'IPC' in unit or unit.strip() == 'control subprocesses;']
            elif index == 1:
                ref = next(i+1 for i, unit in enumerate(bank) if 'No automatic data type conversion' in unit)
                claims = [{'passage': ref, 'text': GOOD_CSV}]
            else:
                claims = []
            ms = 1000 if variant == 'production' else 700
            value = worker_value()
            value['result'].update({'modelAnswer': json.dumps({'claims': claims}),
                'native': {'prompt_eval_count': ms, 'prompt_eval_cached_count': 0, 'prompt_evalMs': ms}})
            observation = {'thermalLimits': {'CPU_Speed_Limit': 62}, 'nativePrefillPhaseProven': False}
            return value, [observation], [], True
        with patch.object(probe.platform, 'system', return_value='Darwin'), patch.object(probe.baseline, 'verify_project'), \
                patch.object(probe.resources.Reader, 'get', side_effect=lambda path:
                             {'version': '0.35.1'} if path == '/api/version' else {'models': []}), \
                patch.object(probe, 'read_page', side_effect=read_page), patch.object(probe, 'collect', side_effect=collect), \
                patch.object(probe, 'thermal_sample', return_value={'thermalLimits': {'CPU_Speed_Limit': 100}}):
            report = probe.run(Path('project'), emit=emitted.append)
        self.assertEqual(calls, list(baseline.ORDER))
        self.assertEqual(report['fixedGates']['minPrefillReductionPercent'], 10)
        self.assertEqual(report['qualityVerdict'], 'pending_review')
        self.assertFalse(report['integrationAllowedByThisAutomaticReport'])
        self.assertTrue(report['noCoolingWaitsOrThermalBasedExclusions'])
        self.assertEqual(report['performanceOutcome'], 'measured_gates_met_pending_semantic_review')
        rows = [json.loads(item) for item in emitted if item.startswith('{') and '"selection"' in item]
        self.assertEqual(len(rows), 6)
        self.assertEqual([row['fullSourceSuppliedToModel'] for row in rows], [True, True, False, True, True, True])
        self.assertEqual(rows[2]['sourceTextSha256'], rows[3]['sourceTextSha256'])
        self.assertTrue(all(row['sameSourceAnchoredTypeScopeAndMechanismChecks'] for row in rows))

    def test_thermal_observer_stops_and_sanitizes_sample_failure_without_extra_inference(self):
        child = Child(); child.returncode = 0
        observer = probe.ThermalObserver(child, sampler=lambda: self.fail('sample after completion'))
        with patch.object(probe, 'THERMAL_SAMPLE_SECONDS', (0, 0, 0)):
            observer.start(); self.assertTrue(observer.close())
        self.assertEqual(observer.rows, [])
        child = Child()
        def fail(): raise OSError('/Users/private/secret')
        with patch.object(probe, 'THERMAL_SAMPLE_SECONDS', (0, 0, 0)):
            observer = probe.ThermalObserver(child, sampler=fail)
            observer.start(); observer.thread.join(timeout=1)
        self.assertEqual(len(observer.errors), 3)
        self.assertNotIn('private', json.dumps(observer.errors))


if __name__ == '__main__':
    unittest.main()
