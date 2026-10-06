"""Replay the actual accepted-but-unfaithful OS paraphrase without repair."""
import copy
import io
import json
from pathlib import Path
import unittest

import web_definition_context as context
import web_definition_latency_probe as probe
import web_type_latency_probe as baseline
from test_andrea_web_definition_context import extracted, html_entry, prepare

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ('create and manage event loops, which provide asynchronous APIs for networking, '
             'running subprocesses, handling OS signals, etc;\n')


def answer(text, ref=1):
    return json.dumps({'claims': [{'passage': ref, 'text': text}]}, ensure_ascii=False)


def validate(text, bank=None, ref=1):
    return context.validate(answer(text, ref), bank or [CATALOGUE], True,
                            heading_ranges=[], contract=baseline)


class ObservedSignalScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((ROOT/'docs/andrea/web-single-rule-cardinality-mac-2026-10-06.json').read_text())
        cls.rows = cls.report['rows']

    def bank(self, case):
        quotes = {claim['passage']: claim['quote'] for row in self.rows if row['case'] == case
                  for claim in row['checks']['claims']}
        result = ['Unused source unit for this regression.\n']*max(quotes, default=1)
        for ref, quote in quotes.items():
            result[ref-1] = quote
        return result

    def test_actual_answer_keeps_os_token_but_loses_signal_scope_and_is_not_repaired(self):
        row = self.rows[1]
        bank = self.bank(row['case'])
        original_bank, raw = list(bank), row['result']['modelAnswer']
        self.assertEqual(baseline.validate(raw, bank, True, heading_ranges=[])['outcome'],
                         'accepted_pending_semantic_review')
        result = context.validate(raw, bank, True, heading_ranges=[], contract=baseline)
        self.assertEqual(result['reason'], 'os_signal_scope_not_preserved')
        self.assertEqual(result['claims'], [])
        self.assertEqual(result['details']['claimIndex'], 2)
        self.assertEqual(result['details']['text'], json.loads(raw)['claims'][1]['text'])
        self.assertEqual(result['details']['quote'], CATALOGUE)
        self.assertEqual(row['result']['modelAnswer'], raw)
        self.assertEqual(bank, original_bank)

    def test_all_six_actual_responses_are_replayed_and_only_os_broadening_fails(self):
        reviewed = copy.deepcopy(self.rows)
        for row in reviewed:
            row['checks'] = context.validate(row['result']['modelAnswer'], self.bank(row['case']), True,
                                             heading_ranges=[], contract=baseline)
            row['caseShapeMet'] = baseline.case_shape(row['case'], row['checks'])
        self.assertEqual([r['checks']['outcome'] for r in reviewed],
                         ['accepted_pending_semantic_review', 'rejected',
                          'accepted_pending_semantic_review', 'accepted_pending_semantic_review',
                          'abstained', 'abstained'])
        self.assertEqual(len(reviewed[2]['checks']['claims']), 1)
        self.assertEqual(reviewed[2]['checks']['claims'], self.rows[2]['checks']['claims'])
        result = baseline.comparison(reviewed)
        self.assertTrue(all(pair['performanceGateMet'] for pair in result['pairs']))
        self.assertFalse(result['technicalCaseShapesMet'])
        self.assertFalse(result['integrationAllowedByThisAutomaticReport'])

    def test_original_automatic_report_remains_accepted_and_manual_refusal_is_separate(self):
        original = self.report['originalAutomaticReport']
        self.assertEqual(original['performanceOutcome'], 'measured_gates_met_pending_semantic_review')
        self.assertTrue(original['technicalCaseShapesMet'])
        self.assertEqual(original['pairs'], baseline.comparison(self.rows)['pairs'])
        self.assertEqual(self.report['manualReviewCounts'], {'favorable': 5, 'unfavorable': 1})
        self.assertEqual(self.report['overallReview'], 'not_passed_no_adoption')
        self.assertTrue(self.report['originalAutomaticChecksPreserved'])
        self.assertFalse(original['integrationAllowedByThisAutomaticReport'])


class QualifierAttachmentTests(unittest.TestCase):
    def test_finite_signal_equivalents_preserve_the_os_relationship(self):
        for form in ('segnali dell’OS', "segnali dell'OS", 'segnali del OS',
                     'segnali OS', 'OS signals', 'signals from OS'):
            text = 'asyncio consente di gestire event loop, sottoprocessi e '+form+'.'
            with self.subTest(form=form):
                result = validate(text)
                self.assertEqual(result['outcome'], 'accepted_pending_semantic_review')
                self.assertEqual(result['claims'][0]['text'], text)

    def test_signals_elsewhere_cannot_license_another_unqualified_os_mention(self):
        text = 'asyncio gestisce sottoprocessi e segnali dell’OS e permette comunicazione con l’OS.'
        result = validate(text)
        self.assertEqual(result['reason'], 'os_signal_scope_not_preserved')
        self.assertEqual(result['details']['text'], text)

    def test_broad_os_translations_and_alternative_qualifiers_are_not_signal_equivalents(self):
        for form in ('comunicazione con l’OS', 'interazioni con il sistema operativo',
                     'eventi dell’OS', 'messaggi dell’OS', 'segnalazioni all’OS'):
            text = 'asyncio gestisce sottoprocessi e '+form+'.'
            with self.subTest(form=form):
                self.assertEqual(context.os_signal_scope_error(text, CATALOGUE), 'os_signal_scope_not_preserved')

    def test_existing_partial_subprocess_fact_does_not_select_the_signal_item(self):
        text = 'asyncio consente di creare event loop per eseguire sottoprocessi.'
        result = validate(text)
        self.assertEqual(result['outcome'], 'accepted_pending_semantic_review')
        self.assertEqual(context.os_signal_scope_error(text, CATALOGUE), None)

    def test_other_os_relationships_in_the_source_are_not_assumed_to_be_signals_only(self):
        for quote in ('OS communication is provided by a separate mechanism.',
                      CATALOGUE.rstrip()+' A separate API communicates with OS.',
                      'OS events are handled by the application.'):
            with self.subTest(quote=quote):
                self.assertFalse(context.os_signals_only_scope(quote))
                self.assertIsNone(context.os_signal_scope_error('Comunicazione con OS.', quote))

    def test_scope_comes_from_the_claims_own_passage_not_neighboring_evidence(self):
        other = 'Communication with OS is supported by a distinct interface.\n'
        text = 'La libreria consente comunicazione con OS tramite un’interfaccia.'
        result = validate(text, [CATALOGUE, other], ref=2)
        self.assertEqual(result['outcome'], 'accepted_pending_semantic_review')
        self.assertEqual(result['claims'][0]['quote'], other)
        wrong_ref = validate('asyncio gestisce sottoprocessi e comunicazione con OS.', [CATALOGUE, other])
        self.assertEqual(wrong_ref['reason'], 'os_signal_scope_not_preserved')


class SignalPromptTests(unittest.TestCase):
    def test_inventory_and_instruction_are_source_anchored_without_changing_question_or_passages(self):
        page = extracted('<h1>asyncio — Asynchronous I/O</h1><p>'+CATALOGUE+'</p>')
        question = baseline.CASES[0]['question']
        bank, messages, schema, selected = prepare(page, question)
        original_bank, original_messages, original_schema = baseline.compact_prepare(
            page['text'], question, heading_ranges=page['headingRanges'])
        payload, original_payload = json.loads(messages[1]['content']), json.loads(original_messages[1]['content'])
        refs = selected['sourceSignalScopeRefs']
        self.assertEqual(len(refs), 1)
        self.assertIn('OS signals', payload['sourceTechnicalTerms'][str(refs[0])])
        self.assertIn(context.SIGNAL_SCOPE_INSTRUCTION, messages[0]['content'])
        for field in ('question', 'passages', 'protectedIdentifiers', 'contextOnly'):
            self.assertEqual(payload[field], original_payload[field])
        self.assertEqual(bank, original_bank)
        self.assertEqual(schema, original_schema)
        self.assertLess(len(messages[0]['content']), len(baseline.baseline_prepare(page['text'], question)[1][0]['content']))

    def test_omitted_unrelated_os_passage_adds_no_inventory_or_instruction_to_csv(self):
        page = extracted(html_entry()+'<p>'+CATALOGUE+'</p>')
        bank, messages, _, selected = prepare(page)
        self.assertEqual(selected['mode'], 'complete_api_entries')
        self.assertEqual(selected['sourceSignalScopeRefs'], [])
        self.assertNotIn(context.SIGNAL_SCOPE_INSTRUCTION, messages[0]['content'])
        payload = json.loads(messages[1]['content'])
        self.assertNotIn('OS signals', json.dumps(payload['sourceTechnicalTerms']))
        self.assertIn(CATALOGUE.rstrip(), ''.join(bank))

    def test_signal_contract_reaches_the_native_request_once_with_original_options(self):
        page = extracted('<h1>asyncio — Asynchronous I/O</h1><p>'+CATALOGUE+'</p>')
        _, messages, schema, _ = probe.prepared(page, baseline.CASES[0], 'compact')
        requests = []
        class Opener:
            def open(self, request, timeout):
                requests.append((json.loads(request.data), timeout))
                return io.BytesIO(b'{"message":{"content":"{\\"claims\\":[]}"},"done":true,"done_reason":"stop"}\n')
        baseline.stream_probe(Opener(), messages, schema)
        self.assertEqual(len(requests), 1)
        payload, timeout = requests[0]
        self.assertEqual(payload['messages'], messages)
        self.assertEqual(payload['format'], schema)
        self.assertEqual(payload['format']['properties']['claims']['maxItems'], 2)
        self.assertEqual(payload['options'], {'temperature': .4, 'num_predict': 512, 'num_ctx': 4096})
        self.assertFalse(payload['think'])
        self.assertEqual(timeout, 90)


if __name__ == '__main__':
    unittest.main()
