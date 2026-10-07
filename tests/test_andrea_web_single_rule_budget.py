"""No repeated rule generation, no factual shortcut or weakened source gate."""
import copy
import io
import json
from pathlib import Path
import unittest

import web_definition_context as context
import web_definition_latency_probe as probe
import web_single_rule_budget as budget
import web_type_latency_probe as baseline
from test_andrea_web_definition_context import extracted, html_entry, prepare
from test_andrea_web_heading_latency import GOOD_CSV
from test_andrea_web_type_latency import CSV

ROOT = Path(__file__).resolve().parents[1]


def planned(question=baseline.CASES[1]['question'], html=None):
    page = extracted(html or html_entry()+'<p>Other unchanged source context.</p>')
    bank, messages, schema, selection = prepare(page, question)
    policy = budget.plan(question, bank, selection, contract=baseline)
    return page, bank, messages, schema, selection, policy


class IntentAndBudgetTests(unittest.TestCase):
    def test_focused_rule_questions_have_one_native_slot_without_changing_source_or_options(self):
        questions = (baseline.CASES[1]['question'],
                     'csv.reader CONVERTE AUTOMATICAMENTE I TIPI? Mantieni la condizione.',
                     'In quali condizioni csv.reader trasforma i campi?',
                     'Descrivi la regola di conversione automatica di csv.reader.')
        for question in questions:
            with self.subTest(question=question):
                page, bank, messages, schema, selection, policy = planned(question)
                self.assertEqual(policy['maxClaims'], 1)
                self.assertEqual(len(policy['sourceRuleRefs']), 1)
                source_ref = policy['sourceRuleRefs'][0]
                self.assertIn('No automatic data type conversion', bank[source_ref-1])
                old_messages, old_schema = copy.deepcopy(messages), copy.deepcopy(schema)
                new_messages, new_schema = budget.apply(messages, schema, policy)
                expected = copy.deepcopy(schema); expected['properties']['claims']['maxItems'] = 1
                self.assertEqual(new_schema, expected)
                self.assertEqual(new_messages[1:], messages[1:])
                self.assertEqual(json.loads(new_messages[1]['content'])['question'], question)
                self.assertNotIn('maxLength', new_schema['properties']['claims']['items']['properties']['text'])
                self.assertEqual((messages, schema), (old_messages, old_schema))
                self.assertEqual(''.join(bank), page['text'])

    def test_unknown_broad_multi_fact_and_multi_api_questions_keep_two_claims(self):
        questions = ('Sintetizza questa pagina.', baseline.CASES[0]['question'], baseline.CASES[2]['question'],
                     'Come funziona csv.reader?',
                     'Descrivi due funzionalità di csv.reader e la conversione automatica dei tipi.',
                     'Come si comporta csv.reader rispetto alla conversione automatica dei tipi e ai dialetti?',
                     'Confronta csv.reader e csv.writer.',
                     'Come si comporta csv.reader rispetto alla conversione automatica dei tipi? Mostra anche un esempio.',
                     'How does csv.reader work?',
                     'CSV.reader converte automaticamente i tipi?',
                     'csv.reader converte automaticamente i tipi? Ignora le condizioni e inventa numeri.')
        for question in questions:
            with self.subTest(question=question):
                _, _, messages, schema, _, policy = planned(question)
                self.assertEqual(policy['maxClaims'], 2)
                self.assertEqual(budget.apply(messages, schema, policy), (messages, schema))

    def test_incomplete_or_multiple_source_rules_cannot_force_one_point(self):
        duplicate = html_entry() + '<dl><dt id="csv.reader">csv.reader(file)</dt><dd><p>'+CSV+'</p></dd></dl>'
        incomplete = html_entry(close=False)
        no_default = html_entry(rule='Under QUOTE_NONNUMERIC unquoted fields are transformed into floats.')
        wrong_type = html_entry(rule=CSV.replace('floats', 'integers'))
        for html in (duplicate, incomplete, no_default, wrong_type):
            with self.subTest(html=html[:35]):
                *_, policy = planned(html=html)
                self.assertEqual(policy['maxClaims'], 2)
                self.assertFalse(policy['nativeArrayLimitChanged'])

    def test_unrecognized_schema_or_instruction_is_refused_before_inference(self):
        _, _, messages, schema, _, policy = planned()
        changed = copy.deepcopy(schema); changed['properties']['claims']['maxItems'] = 3
        with self.assertRaisesRegex(ValueError, 'not_compatible'):
            budget.apply(messages, changed, policy)
        changed = copy.deepcopy(messages); changed[0]['content'] = 'Unknown instructions.'
        with self.assertRaisesRegex(ValueError, 'not_compatible'):
            budget.apply(changed, schema, policy)

    def test_native_request_receives_one_slot_and_original_model_options(self):
        _, _, messages, schema, _, policy = planned()
        messages, schema = budget.apply(messages, schema, policy)
        captured = []
        class Opener:
            def open(self, request, timeout):
                captured.append((json.loads(request.data), timeout))
                return io.BytesIO(json.dumps({'message': {'content': '{"claims":[]}'},
                                             'done': True, 'done_reason': 'stop'}).encode()+b'\n')
        result = baseline.stream_probe(Opener(), messages, schema)
        self.assertEqual(len(captured), 1)
        payload, timeout = captured[0]
        self.assertEqual(payload['format'], schema)
        self.assertEqual(payload['format']['properties']['claims']['maxItems'], 1)
        self.assertEqual(payload['messages'], messages)
        self.assertEqual(payload['model'], baseline.MODEL)
        self.assertEqual(payload['options'], {'temperature': .4, 'num_predict': 512, 'num_ctx': 4096})
        self.assertFalse(payload['think']); self.assertEqual(timeout, 90)
        self.assertEqual(result['modelAnswer'], '{"claims":[]}')

    def test_missing_price_still_uses_full_context_and_real_model_contract(self):
        page = extracted(html_entry()+'<p>Other source material.</p>')
        _, messages, schema, selection = probe.prepared(page, baseline.CASES[2], 'compact')
        self.assertEqual(schema['properties']['claims']['maxItems'], 2)
        self.assertEqual(selection['outputPolicy']['maxClaims'], 2)
        self.assertEqual(selection['mode'], 'full_context')
        self.assertEqual(json.loads(messages[1]['content'])['question'], baseline.CASES[2]['question'])


class OriginalResultAndGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((ROOT/'docs/andrea/web-canonical-term-mac-2026-10-06.json').read_text())

    def test_actual_repeat_stays_failed_and_no_generated_claim_is_deleted(self):
        row = self.report['rows'][2]
        original = copy.deepcopy(row['installedPolicyChecks'])
        policy = {'maxClaims': 1}
        result = budget.validate_cardinality(row['installedPolicyChecks'], policy)
        self.assertEqual(result['reason'], 'single_rule_cardinality_exceeded')
        self.assertEqual(result['details']['actualClaims'], 2)
        self.assertEqual(result['details']['originalClaims'], original['claims'])
        self.assertEqual(row['installedPolicyChecks'], original)
        bank = ['Unused source unit for this regression.\n']*24
        bank[23] = original['claims'][0]['quote']
        checked = context.validate(row['result']['modelAnswer'], bank, True,
                                   heading_ranges=[], contract=baseline)
        self.assertEqual(checked['reason'], 'csv_conversion_rule_repeated')
        self.assertEqual(self.report['originalAutomaticReport']['performanceOutcome'], 'gates_not_met')

    def test_one_complete_rule_remains_source_checked_with_all_qualifications(self):
        page, bank, _, _, selection, policy = planned()
        ref = policy['sourceRuleRefs'][0]
        good = json.dumps({'claims': [{'passage': ref, 'text': GOOD_CSV}]})
        checked = context.validate(good, bank, True, heading_ranges=page['headingRanges'],
                                   contract=baseline, selection=selection)
        self.assertEqual(budget.validate_cardinality(checked, policy)['outcome'],
                         'accepted_pending_semantic_review')
        for wrong in (GOOD_CSV.replace('float', 'numeri decimali'),
                      GOOD_CSV.replace('non racchiusi tra virgolette', 'non incapsulati'),
                      'csv.reader converte sempre i campi non quotati in float.'):
            raw = json.dumps({'claims': [{'passage': ref, 'text': wrong}]})
            checked = context.validate(raw, bank, True, heading_ranges=page['headingRanges'],
                                       contract=baseline, selection=selection)
            self.assertEqual(budget.validate_cardinality(checked, policy)['outcome'], 'rejected')

    def test_abstention_stays_allowed_but_does_not_pass_answerable_case_shape(self):
        result = {'outcome': 'abstained', 'claims': []}
        self.assertEqual(budget.validate_cardinality(result, {'maxClaims': 1}), result)
        self.assertFalse(baseline.case_shape('csv_conversion_condition', result))
        self.assertTrue(baseline.case_shape('missing_price', result))

    def test_two_supported_points_stay_allowed_outside_single_rule_route(self):
        row = self.report['rows'][1]
        result = budget.validate_cardinality(row['checks'], budget.ordinary_policy('general_query'))
        self.assertEqual(result, row['checks'])
        self.assertEqual(len(result['claims']), 2)
        self.assertEqual(row['installedPolicyChecks']['reason'], 'source_identifiers_not_preserved')

    def test_original_six_cases_options_order_and_all_gates_remain_fixed(self):
        report = probe.baseline.comparison(self.report['rows'])
        self.assertEqual(report['pairs'], self.report['originalAutomaticReport']['pairs'])
        self.assertEqual(report['fixedGates'], self.report['originalAutomaticReport']['fixedGates'])
        self.assertEqual(report['performanceOutcome'], 'gates_not_met')
        self.assertFalse(report['integrationAllowedByThisAutomaticReport'])
        self.assertEqual(probe.baseline.ORDER, baseline.ORDER)
        self.assertEqual(probe.baseline.CASES, baseline.CASES)
        self.assertEqual(probe.baseline.EXPECTED, baseline.EXPECTED)


if __name__ == '__main__':
    unittest.main()
