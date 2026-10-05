"""Replay actual term/type failures and preserve the finite latency protocol."""
import ast
import copy
import json
import unittest
from unittest.mock import patch

import test_andrea_web_heading_latency as heading_tests
import test_andrea_web_short_instructions as archived
import web_heading_latency_candidate as preceding
import web_heading_latency_probe as preceding_probe
import web_sentence_contract as installed
import web_type_fidelity as fidelity
import web_type_latency_candidate as candidate
import web_type_latency_probe as probe

CSV = ('Each row read from the csv file is returned as a list of strings. '
       'No automatic data type conversion is performed unless the QUOTE_NONNUMERIC '
       'format option is specified (in which case unquoted fields are transformed into floats).\n')
OBSERVED_IO = ('asyncio permette di eseguire operazioni di input/output '
               'e comunicazione tra processi (IPC).')
OBSERVED_SUBPROCESS = 'asyncio consente di gestire sottoprocessi.'
OBSERVED_DECIMAL = ('csv.reader restituisce ogni riga come lista di stringhe, senza effettuare '
                    "conversione automatica dei tipi, a meno che non sia specificato l'opzione "
                    'QUOTE_NONNUMERIC, in cui i campi non virgolettati vengono trasformati in numeri decimali.')


def raw(claims):
    return heading_tests.raw(claims)


def checked(text, quote=CSV):
    return candidate.validate(raw([(1, text)]), [quote], True, heading_ranges=[])


class TypeRegressionTests(unittest.TestCase):
    def test_exact_observed_io_expansion_preserves_both_answer_and_own_quotes(self):
        bank = ([heading_tests.HEADING] + ['Other retained context line.\n'] * 8
                + [heading_tests.IO, heading_tests.SUBPROCESS])
        answer = raw([(10, OBSERVED_IO), (11, OBSERVED_SUBPROCESS)])
        self.assertEqual(preceding.validate(answer, bank, True,
                         heading_ranges=heading_tests.RANGES)['reason'], 'source_identifiers_not_preserved')
        result = candidate.validate(answer, bank, True, heading_ranges=heading_tests.RANGES)
        self.assertEqual(result['outcome'], 'accepted_pending_semantic_review')
        self.assertEqual(result['claims'], [
            {'text': OBSERVED_IO, 'quote': heading_tests.IO, 'passage': 10},
            {'text': OBSERVED_SUBPROCESS, 'quote': heading_tests.SUBPROCESS, 'passage': 11}])
        self.assertEqual(result, probe.validate(answer, bank, True, heading_ranges=heading_tests.RANGES))
        self.assertEqual(probe.installed_validate(answer, bank, True)['reason'], 'source_identifiers_not_preserved')

    def test_exact_observed_decimal_target_fails_without_text_repair_or_hidden_history(self):
        answer = raw([(1, OBSERVED_DECIMAL)])
        self.assertEqual(preceding.validate(answer, [CSV], True, heading_ranges=[])['outcome'],
                         'accepted_pending_semantic_review')
        self.assertEqual(probe.installed_validate(answer, [CSV], True)['outcome'],
                         'accepted_pending_semantic_review')
        result = checked(OBSERVED_DECIMAL)
        self.assertEqual(result['reason'], 'converted_field_type_not_preserved')
        self.assertEqual(result['claims'], [])
        self.assertEqual(result['details']['text'], OBSERVED_DECIMAL)
        self.assertEqual(result['details']['quote'], CSV)
        self.assertTrue(result['details']['diagnosticOnly'])
        self.assertEqual(result, probe.validate(answer, [CSV], True, heading_ranges=[]))

    def test_input_output_has_finite_case_equivalence_but_no_broad_synonyms(self):
        for spelling in ('input/output', 'Input/Output', 'INPUT/OUTPUT'):
            with self.subTest(spelling=spelling):
                text = OBSERVED_IO.replace('input/output', spelling)
                result = checked(text, heading_tests.IO)
                self.assertEqual(result['outcome'], 'accepted_pending_semantic_review')
                self.assertEqual(result['claims'][0]['text'], text)
        for spelling in ('input', 'output', 'dati', 'input / output', 'input/outputary', 'myinput/output'):
            with self.subTest(spelling=spelling):
                self.assertEqual(checked(OBSERVED_IO.replace('input/output', spelling), heading_tests.IO)['reason'],
                                 'source_identifiers_not_preserved')

    def test_expansion_is_symmetric_and_keeps_other_identifiers_protected(self):
        source = 'perform network input/output and IPC;\n'
        result = checked(heading_tests.GOOD_IO, source)
        self.assertEqual(result['outcome'], 'accepted_pending_semantic_review')
        self.assertEqual(result['claims'][0]['quote'], source)
        source = 'perform network input/output, IPC and INPUT;\n'
        self.assertEqual(checked(heading_tests.GOOD_IO, source)['details']['missingIdentifiers'], ['INPUT'])
        text = OBSERVED_IO.replace(' (IPC)', ' (IPC) con GPU')
        self.assertEqual(checked(text, heading_tests.IO)['details']['addedIdentifiers'], ['GPU'])

    def test_another_passage_never_licenses_io_or_a_missing_ipc_fact(self):
        text = 'asyncio consente di gestire sottoprocessi e input/output.'
        result = candidate.validate(raw([(2, text)]), [heading_tests.IO, heading_tests.SUBPROCESS],
                                    True, heading_ranges=[])
        self.assertEqual(result['details']['addedIdentifiers'], ['I/O'])
        text = 'asyncio gestisce operazioni di input/output.'
        self.assertEqual(checked(text, heading_tests.IO)['details']['missingIdentifiers'], ['IPC'])

    def test_correct_result_type_forms_are_scoped_to_the_converted_fields(self):
        for target in ('float', 'floats', 'numeri a virgola mobile', 'floating-point numbers'):
            text = ('csv.reader, con QUOTE_NONNUMERIC, trasforma i campi non quotati in ' + target + '.')
            with self.subTest(target=target):
                result = checked(text)
                self.assertEqual(result['outcome'], 'accepted_pending_semantic_review')
                self.assertEqual(result['claims'][0]['text'], text)

    def test_wrong_target_types_and_float_elsewhere_do_not_pass(self):
        for target in ('numeri decimali', 'Decimal', 'int', 'stringhe', 'bool', 'valori numerici', 'float o Decimal'):
            text = ('csv.reader considera float; con QUOTE_NONNUMERIC, i campi non quotati '
                    'vengono trasformati in ' + target + '.')
            with self.subTest(target=target):
                self.assertEqual(checked(text)['reason'], 'converted_field_type_not_preserved')

    def test_common_positive_conversion_predicates_keep_the_float_type(self):
        for predicate in ('vengono trasformati in', 'vengono convertiti in', 'diventano', 'are converted to'):
            text = 'Con QUOTE_NONNUMERIC i campi non quotati ' + predicate + ' Decimal.'
            with self.subTest(predicate=predicate):
                self.assertEqual(checked(text)['reason'], 'converted_field_type_not_preserved')

    def test_default_only_summary_is_not_forced_to_invent_an_exception(self):
        text = 'csv.reader non effettua conversione automatica dei tipi.'
        self.assertEqual(checked(text)['outcome'], 'accepted_pending_semantic_review')
        self.assertEqual(fidelity.converted_field_targets('I campi non vengono convertiti in float.'), [])
        self.assertEqual(fidelity.converted_field_targets('Fields are not converted to float.'), [])

    def test_float_inventory_requires_the_explicit_source_rule_in_its_own_passage(self):
        self.assertEqual(fidelity.csv_converted_source_types(CSV), {'float'})
        for quote in ('QUOTE_NONNUMERIC is an option. A float is a number.\n',
                      'Unquoted fields are converted to strings with QUOTE_NONNUMERIC.\n',
                      'Unquoted fields are transformed into floats.\n'):
            with self.subTest(quote=quote):
                self.assertEqual(fidelity.csv_converted_source_types(quote), set())
        payload = json.loads(candidate.prepare(CSV + 'Other unrelated Decimal context.\n',
                             'Conversione?', heading_ranges=[])[1][1]['content'])
        self.assertEqual(payload['protectedIdentifiers'], {'1': ['QUOTE_NONNUMERIC', 'float']})

    def test_only_source_float_inventory_is_added_no_text_question_or_schema_rewrite(self):
        question = 'Conversione e condizioni?'
        before = installed.prepare(CSV, question)
        after = candidate.prepare(CSV, question, heading_ranges=[])
        self.assertEqual(after[0], before[0]); self.assertEqual(''.join(after[0]), CSV)
        self.assertEqual(after[2], before[2])
        payload = json.loads(after[1][1]['content']); self.assertEqual(payload.pop('contextOnly'), [])
        payload['protectedIdentifiers']['1'].remove('float')
        self.assertEqual(payload, json.loads(before[1][1]['content']))
        self.assertEqual(after[1][0], preceding.prepare(CSV, question, heading_ranges=[])[1][0])
        self.assertEqual(after, probe.compact_prepare(CSV, question, heading_ranges=[]))
        page = {'text': CSV, 'headingRanges': []}
        probe.preflight_pair(before, after, page)
        for identifiers in (['QUOTE_NONNUMERIC'], ['QUOTE_NONNUMERIC', 'float', 'Decimal'], ['float']):
            changed = copy.deepcopy(after); data = json.loads(changed[1][1]['content'])
            data['protectedIdentifiers']['1'] = identifiers
            changed[1][1]['content'] = json.dumps(data)
            with self.subTest(identifiers=identifiers), self.assertRaises(probe.CheckError):
                probe.preflight_pair(before, changed, page)

    def test_legacy_validator_and_transport_are_exact_and_new_helpers_are_standalone(self):
        old, new = map(archived.functions, (preceding_probe, probe))
        for name in ('baseline_prepare', 'installed_validate', 'installed_technical_terms',
                     'stream_probe', 'native_metrics', 'case_shape', 'cache_qualification',
                     'isolated_messages', 'read_heading_page', 'page_worker'):
            self.assertEqual(ast.dump(new[name]), ast.dump(old[name]), name)
        for name, node in archived.functions(fidelity).items():
            self.assertEqual(ast.dump(node), ast.dump(new[name]), name)

    def test_program_replay_does_not_relabel_original_mac_run_as_a_pass(self):
        rows = heading_tests.HeadingCacheTests().rows()
        rows[1]['caseShapeMet'] = False
        report = probe.comparison(rows)
        self.assertEqual(report['performanceOutcome'], 'gates_not_met')
        self.assertEqual(report['qualityVerdict'], 'pending_review')
        self.assertFalse(report['integrationAllowedByThisAutomaticReport'])


class WithTypeCandidate:
    """Run unchanged heading/cache/finite-transport regressions on this candidate."""
    def setUp(self):
        for name, module in (('candidate', candidate), ('probe', probe)):
            patcher = patch.object(heading_tests, name, module)
            patcher.start(); self.addCleanup(patcher.stop)
        super().setUp()


class TypeHtmlTests(WithTypeCandidate, heading_tests.HtmlRoleTests):
    pass


class TypeContractTests(WithTypeCandidate, heading_tests.HeadingContractTests):
    pass


class TypeCacheTests(WithTypeCandidate, heading_tests.HeadingCacheTests):
    pass


class TypeProbeTests(WithTypeCandidate, heading_tests.HeadingProbeTests):
    pass


if __name__ == '__main__':
    unittest.main()
