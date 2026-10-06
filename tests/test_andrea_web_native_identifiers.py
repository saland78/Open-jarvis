"""Real refused outputs, own-source grammar and the pinned native converter."""
import ast
import copy
import hashlib
import io
import itertools
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import web_native_identifier_schema as native
import web_native_identifier_probe as candidate
import web_networking_scope_probe as previous
import web_page_context_contract as live
import web_page_fidelity as fidelity
from test_andrea_web_definition_context import extracted, html_entry
from test_andrea_web_request_resources import Child, StubObserver

ROOT = Path(__file__).resolve().parents[1]
NETWORK = 'perform network IO and IPC;\n'
CATALOGUE = ('create and manage event loops, which provide asynchronous APIs for networking, '
             'running subprocesses, handling OS signals, etc;\n')
ONE_SOURCE_SELECTION = {'selectedRefs': [1], 'outputPolicy': {'maxClaims': 2}}


def page():
    return extracted('<h1>asyncio</h1><p>'+NETWORK+'</p><p>'+CATALOGUE+'</p>')


def branch_for(schema, ref):
    item = schema['properties']['claims']['items']
    branches = item.get('oneOf', [item])
    found = [branch for branch in branches if ref in branch['properties']['passage']['enum']]
    if len(found) != 1:
        raise AssertionError('Own reference must select exactly one native branch')
    return found[0]


def pattern_allows(schema, ref, text):
    field = branch_for(schema, ref)['properties']['text']
    return len(text) >= field['minLength'] and (
        'pattern' not in field or re.fullmatch(field['pattern'], text) is not None)


class ObservedFailureTests(unittest.TestCase):
    def test_both_original_refusals_remain_refused_and_the_whole_answer_is_preserved(self):
        for series in (1, 2):
            report = json.loads((ROOT/f'docs/andrea/web-networking-scope-v2-mac-series-{series}-2026-10-06.json').read_text())
            row = report['rows'][1]
            details = row['checks']['details']
            bank = ['Unused unrelated source passage.\n']*18
            bank[9] = details['quote']
            second = json.loads(row['result']['modelAnswer'])['claims'][1]
            bank[second['passage']-1] = CATALOGUE if second['passage'] == 18 else 'control subprocesses;\n'
            raw = row['result']['modelAnswer']
            result = live.validate(raw, bank, True, {'headingRanges': []}, row['selection'])
            with self.subTest(series=series):
                self.assertEqual(result, row['checks'])
                self.assertEqual(result['claims'], [])
                self.assertEqual(json.loads(raw)['claims'][0]['text'], details['text'])
                self.assertFalse(re.fullmatch(native.pattern(['I/O', 'IPC'], network_io=True), details['text']))
                self.assertEqual(report['manualReviewCounts'], {'favorable': 4, 'unfavorable': 2})
                self.assertEqual(report['overallReview'], 'not_passed_no_adoption')
                self.assertFalse(report['originalAutomaticReport']['technicalCaseShapesMet'])
                self.assertNotIn('/Users/', json.dumps(report))
                self.assertNotIn('Last login:', json.dumps(report))

    def test_original_reference_acceptance_is_not_relabelled_but_lost_network_qualifier_is_excluded_upfront(self):
        report = json.loads((ROOT/'docs/andrea/web-networking-scope-v2-mac-series-1-2026-10-06.json').read_text())
        row = report['rows'][0]
        self.assertEqual(row['checks']['outcome'], 'accepted_pending_semantic_review')
        self.assertFalse(re.fullmatch(native.pattern(['I/O', 'IPC'], network_io=True), row['checks']['claims'][0]['text']))
        self.assertTrue(report['originalAutomaticChecksPreserved'])

    def test_presence_does_not_bypass_the_existing_identifier_boundary_or_meaning_checks(self):
        bank = [NETWORK]
        for text in ('asyncio gestisce I/O di rete e IPCfalse.',
                     'asyncio gestisce I/O di rete, IPC e CPU.'):
            with self.subTest(text=text):
                self.assertIsNotNone(re.fullmatch(native.pattern(['I/O', 'IPC'], network_io=True), text))
                raw = json.dumps({'claims': [{'passage': 1, 'text': text}]})
                result = live.validate(raw, bank, True, {'headingRanges': []}, ONE_SOURCE_SELECTION)
                self.assertEqual(result['reason'], 'source_identifiers_not_preserved')
                self.assertEqual(result['claims'], [])


class NativeBranchTests(unittest.TestCase):
    def test_source_number_selects_its_own_pattern_and_heading_remains_ineligible(self):
        before = previous.prepared(page(), previous.baseline.CASES[0], 'compact')
        snapshot = copy.deepcopy(before)
        bank, messages, schema, selection = native.apply(*before, contract=fidelity)
        self.assertEqual(before, snapshot)
        self.assertEqual(bank, before[0])
        old, new = json.loads(before[1][1]['content']), json.loads(messages[1]['content'])
        for field in ('question', 'passages', 'protectedIdentifiers', 'contextOnly'):
            self.assertEqual(new[field], old[field])
        self.assertNotIn(1, [ref for branch in schema['properties']['claims']['items']['oneOf']
                             for ref in branch['properties']['passage']['enum']])
        self.assertTrue(pattern_allows(schema, 2, 'asyncio esegue I/O di rete e IPC.'))
        self.assertFalse(pattern_allows(schema, 2, 'asyncio esegue operazioni di rete e IPC.'))
        self.assertNotIn('pattern', branch_for(schema, 3)['properties']['text'])
        self.assertEqual(new['sourceTechnicalTerms']['2'], ['network IO'])
        self.assertEqual(selection['nativeIdentifierPolicy']['rules'][0]['passage'], 2)
        self.assertEqual(list(branch_for(schema, 2)['properties']), ['passage', 'text'])
        self.assertNotIn('properties', schema['properties']['claims']['items'])

    def test_faithful_native_spellings_and_both_orders_keep_original_source_checks(self):
        expression = native.pattern(['I/O', 'IPC'], network_io=True)
        for text in ('asyncio esegue I/O di rete e IPC.',
                     'asyncio permette IPC e IO in rete.',
                     'asyncio consente input/output di rete e IPC.',
                     'asyncio permette network IO e IPC.'):
            with self.subTest(text=text):
                self.assertIsNotNone(re.fullmatch(expression, text))
                raw = json.dumps({'claims': [{'passage': 1, 'text': text}]})
                result = live.validate(raw, [NETWORK], True, {'headingRanges': []}, ONE_SOURCE_SELECTION)
                self.assertEqual(result['outcome'], 'accepted_pending_semantic_review')
                self.assertEqual(result['claims'][0]['text'], text)

    def test_network_qualifier_is_required_only_when_its_own_source_proves_it(self):
        plain = extracted('<p>perform IO and IPC without another qualifier;</p>')
        before = previous.prepared(plain, previous.baseline.CASES[0], 'compact')
        _, _, schema, selection = native.apply(*before, contract=fidelity)
        self.assertTrue(pattern_allows(schema, 1, 'Il modulo permette I/O e IPC.'))
        self.assertFalse(selection['nativeIdentifierPolicy']['rules'][0]['networkIOQualifierRequired'])

    def test_multisentence_or_neighboring_signal_identifiers_are_not_made_unconditional(self):
        self.assertEqual(native.unconditional_identifiers(CATALOGUE, contract=fidelity), [])
        self.assertEqual(native.unconditional_identifiers('API controls requests. CPU performs other work.', contract=fidelity), [])
        self.assertEqual(native.unconditional_identifiers('handle OS signals;', contract=fidelity), ['OS'])
        raw = json.dumps({'claims': [{'passage': 1, 'text': 'asyncio controlla sottoprocessi tramite event loop.'}]})
        result = live.validate(raw, [CATALOGUE], True, {'headingRanges': []}, ONE_SOURCE_SELECTION)
        self.assertEqual(result['outcome'], 'accepted_pending_semantic_review')

    def test_same_pattern_groups_only_its_own_references_and_large_inventory_is_reported(self):
        p = extracted('<p>perform network IO and IPC;</p><p>send network IO and IPC;</p>'
                      '<p>API and CPU and GPU and RAM are distinct names;</p>')
        bank, messages, schema, selection = native.apply(*previous.prepared(p, previous.baseline.CASES[0], 'compact'), contract=fidelity)
        self.assertEqual(branch_for(schema, 1)['properties']['passage']['enum'], [1, 2])
        self.assertEqual(branch_for(schema, 3)['properties']['passage']['enum'], [3])
        self.assertEqual(selection['nativeIdentifierPolicy']['notEncodedNativeRefs'], [3])
        self.assertTrue(selection['nativeIdentifierPolicy']['unmodifiedApplicationValidationRequired'])

    def test_new_native_constraint_preserves_native_budgets_and_genuine_abstention(self):
        p = extracted(html_entry())
        for index in (1, 2):
            before = previous.prepared(p, previous.baseline.CASES[index], 'compact')
            after = native.apply(*before, contract=fidelity)
            self.assertEqual(after[2]['properties']['claims']['maxItems'], 1 if index == 1 else 2)
            self.assertNotIn('minItems', after[2]['properties']['claims'])
            result = live.validate('{"claims":[]}', after[0], True, p, after[3])
            self.assertEqual(result['outcome'], 'abstained')
            self.assertFalse(candidate.baseline.case_shape('asyncio_scope', result))
            self.assertNotIn('maxLength', json.dumps(after[2]))

    def test_misaligned_bytes_invalid_refs_and_unknown_schema_fail_before_model_work(self):
        for kind in ('bytes', 'ref', 'schema'):
            before = copy.deepcopy(previous.prepared(page(), previous.baseline.CASES[0], 'compact'))
            if kind == 'bytes':
                value = json.loads(before[1][1]['content'])
                value['passages'][0][1] += 'changed'
                before[1][1]['content'] = json.dumps(value)
            elif kind == 'ref':
                before[2]['properties']['claims']['items']['properties']['passage']['enum'] = [True, 2]
            else:
                before[2]['properties']['claims']['items']['properties']['text']['maxLength'] = 100
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                native.apply(*before, contract=fidelity)

    def test_no_identifier_does_not_inject_guidance_or_change_wire_schema(self):
        p = extracted('<p>control subprocesses without another acronym;</p>')
        before = previous.prepared(p, previous.baseline.CASES[0], 'compact')
        after = native.apply(*before, contract=fidelity)
        self.assertEqual(after[:3], before[:3])
        self.assertEqual(after[3]['nativeIdentifierPolicy']['rules'], [])

    def test_repetition_cap_is_finite_without_a_string_length_cap(self):
        expression = native.pattern(['API', 'CPU', 'GPU'])
        for order in itertools.permutations(['API', 'CPU', 'GPU']):
            self.assertIsNotNone(re.fullmatch(expression, 'Il sistema usa '+' e '.join(order)+'.'))
        for ids in ([], ['CPU', 'API'], ['API', 'CPU', 'GPU', 'RAM'], ['api'], ['API', 'API']):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                native.pattern(ids)

    def test_ignored_native_constraint_cannot_turn_into_a_successful_claim(self):
        _, _, _, selection = candidate.prepared(page(), candidate.baseline.CASES[0], 'compact')
        claim = {'passage': 2, 'text': 'asyncio permette I/O e IPC.', 'quote': NETWORK}
        original = {'outcome': 'accepted_pending_semantic_review', 'claims': [claim]}
        snapshot = copy.deepcopy(original)
        result = native.validate_generation(original, selection)
        self.assertEqual(result['reason'], 'native_identifier_constraint_not_observed')
        self.assertEqual(result['details']['text'], claim['text'])
        self.assertEqual(result['claims'], [])
        self.assertEqual(original, snapshot)
        refused = {'outcome': 'rejected', 'reason': 'source_identifiers_not_preserved', 'claims': []}
        self.assertIs(native.validate_generation(refused, selection), refused)
        empty = {'outcome': 'abstained', 'claims': []}
        self.assertIs(native.validate_generation(empty, selection), empty)

    def test_valid_native_constraint_keeps_all_original_generated_claims_verbatim(self):
        _, _, _, selection = candidate.prepared(page(), candidate.baseline.CASES[0], 'compact')
        original = {'outcome': 'accepted_pending_semantic_review', 'claims': [
            {'passage': 2, 'text': 'asyncio permette I/O di rete e IPC.', 'quote': NETWORK},
            {'passage': 3, 'text': 'asyncio controlla sottoprocessi con event loop.', 'quote': CATALOGUE}]}
        self.assertIs(native.validate_generation(original, selection), original)


class PinnedNativePatternTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('g++') or shutil.which('clang++')
        if compiler is None:
            raise RuntimeError('A C++ compiler is required for the pinned native pattern tests')
        cls.temporary = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.temporary.name)/'native-pattern'
        subprocess.run([compiler, '-std=c++17', '-O0', str(ROOT/'tests/fixtures/andrea/llama_native_pattern_b11232.cpp'),
                        '-o', str(cls.binary)], check=True, capture_output=True, timeout=45)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def convert(self, expression):
        return subprocess.run([str(self.binary)], input=expression, text=True, capture_output=True, timeout=3)

    def test_every_pattern_in_both_variant_schemas_compiles_in_the_pinned_converter(self):
        for p, case in ((page(), candidate.baseline.CASES[0]), (extracted(html_entry()), candidate.baseline.CASES[1])):
            for variant in ('production', 'compact'):
                _, _, _, selection = candidate.prepared(p, case, variant)
                for rule in selection['nativeIdentifierPolicy']['rules']:
                    with self.subTest(variant=variant, ref=rule['passage']):
                        result = self.convert(rule['pattern'])
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertIn('root ::=', result.stdout)
                        for token in rule['mandatoryIdentifiers']:
                            self.assertIn('"'+token+'"', result.stdout)

    def test_unsupported_lookahead_is_exposed_instead_of_counted_as_a_constraint(self):
        result = self.convert('^(?=.*IPC).*I/O.*$')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('root ::=', result.stdout)

    def test_generated_grammar_contains_the_network_qualifier_and_all_finite_orders(self):
        result = self.convert(native.pattern(['I/O', 'IPC'], network_io=True))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"rete"', result.stdout)
        self.assertEqual(result.stdout.count('"IPC"'), 2)
        result = self.convert(native.pattern(['API', 'CPU', 'GPU']))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count('"GPU"'), 6)

    def test_native_source_excerpts_and_license_match_the_recorded_primary_sources(self):
        fixture = (ROOT/'tests/fixtures/andrea/llama_native_pattern_b11232.cpp').read_text()
        metadata = json.loads((ROOT/'tests/fixtures/andrea/llama_native_pattern_b11232.json').read_text())
        self.assertEqual(metadata['ollamaVersion'], '0.35.1')
        self.assertEqual(metadata['llamaCppTag'], 'b11232')
        self.assertFalse(metadata['fullSchemaDecoderOrInferenceMeasured'])
        self.assertIn('MIT License', fixture)
        for excerpt in metadata['excerpts']:
            start = fixture.index(excerpt['start'])
            text = fixture[start:start+excerpt['characters']]
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), excerpt['sha256'])


class IsolatedRunnerTests(unittest.TestCase):
    def test_original_sources_and_native_request_boundaries_remain_frozen(self):
        for name in ('BASELINE_SOURCE', 'RESOURCE_SOURCE', 'CONTEXT_SOURCE', 'RULE_BUDGET_SOURCE', 'NETWORKING_SOURCE'):
            self.assertEqual(getattr(candidate, name), getattr(previous, name))
        self.assertEqual(candidate.NATIVE_IDENTIFIER_SOURCE, (ROOT/'scripts/andrea/web_native_identifier_schema.py').read_text())
        self.assertEqual(candidate.baseline.CASES, previous.baseline.CASES)
        self.assertEqual(candidate.baseline.ORDER, previous.baseline.ORDER)
        self.assertEqual(candidate.baseline.EXPECTED, previous.baseline.EXPECTED)
        def functions(filename):
            tree = ast.parse((ROOT/'scripts/andrea'/filename).read_text())
            return {node.name: ast.dump(node, include_attributes=False) for node in tree.body if isinstance(node, ast.FunctionDef)}
        old = functions('web_networking_scope_probe_body.py')
        new = functions('web_native_identifier_probe_body.py')
        for name in ('checked_page', 'page_worker', 'read_page', 'thermal_sample', 'worker_error', 'checked_worker', 'collect', 'model_worker'):
            self.assertEqual(new[name], old[name])

    def test_both_variants_receive_the_same_own_source_policy_without_reusing_old_timings(self):
        for variant in ('production', 'compact'):
            before = previous.prepared(page(), previous.baseline.CASES[0], variant)
            after = candidate.prepared(page(), candidate.baseline.CASES[0], variant)
            self.assertEqual(after[0], before[0])
            self.assertEqual(after[1][0]['content'], before[1][0]['content']+native.INSTRUCTION)
            self.assertEqual(after[3]['nativeIdentifierPolicy']['rules'][0]['mandatoryIdentifiers'], ['I/O', 'IPC'])
            self.assertEqual(after[2]['properties']['claims']['maxItems'], before[2]['properties']['claims']['maxItems'])
        self.assertEqual(candidate.CANDIDATE_REVISION, 'own_passage_native_identifier_v3')

    def test_schema_reaches_ollama_once_without_changing_any_model_option(self):
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
        self.assertEqual(payload['messages'], messages)
        self.assertEqual(payload['options'], {'temperature': .4, 'num_predict': 512, 'num_ctx': 4096})
        self.assertFalse(payload['think'])
        self.assertEqual(timeout, 90)

    def test_timeout_closes_only_the_owned_worker_without_retry(self):
        child = Child(timeout=True)
        observer = StubObserver(child)
        value, _, _, cleaned = candidate.collect(Path('project'), page(), 0, 'compact',
            popen=lambda *a, **k: child, observer_factory=lambda _: observer)
        self.assertTrue(cleaned)
        self.assertEqual(child.kills, 1)
        self.assertEqual(value['result']['errorKind'], 'owned_worker_deadline_no_retry')

    def test_actual_failed_series_still_fail_original_gates(self):
        for series in (1, 2):
            report = json.loads((ROOT/f'docs/andrea/web-networking-scope-v2-mac-series-{series}-2026-10-06.json').read_text())
            automatic = candidate.baseline.comparison(report['rows'])
            self.assertFalse(automatic['technicalCaseShapesMet'])
            self.assertEqual(automatic['performanceOutcome'], 'gates_not_met')
            self.assertEqual(automatic['pairs'], report['originalAutomaticReport']['pairs'])
            self.assertFalse(automatic['integrationAllowedByThisAutomaticReport'])

    def test_balanced_series_preserves_original_checks_and_records_failed_native_scope(self):
        async_page = page()
        async_page['url'] = candidate.baseline.CASES[0]['url']
        csv_page = extracted(html_entry())
        pages = {async_page['url']: async_page, csv_page['url']: csv_page}
        installed = json.loads((ROOT/'docs/andrea/web-api-context-installed-mac-2026-10-06.json').read_text())
        good_csv = installed['rows'][1]['claims'][0]['text']
        class Reader:
            def get(self, path):
                return {'version': candidate.EXPECTED_OLLAMA_VERSION} if path == '/api/version' else {'models': []}
        for omit_network in (False, True):
            calls = []
            def collect(project, p, index, variant):
                calls.append((index, variant))
                bank = candidate.baseline.sentence_bank(p['text'])
                if index == 0:
                    network_ref = bank.index(NETWORK)+1
                    catalogue_ref = next(i+1 for i, unit in enumerate(bank) if 'handling OS signals' in unit)
                    text = 'asyncio permette I/O e IPC.' if omit_network and variant == 'compact' else 'asyncio permette I/O di rete e IPC.'
                    claims = [{'passage': network_ref, 'text': text},
                              {'passage': catalogue_ref, 'text': 'asyncio controlla sottoprocessi con event loop.'}]
                elif index == 1:
                    ref = next(i+1 for i, p in enumerate(bank) if 'No automatic data type conversion' in p)
                    claims = [{'passage': ref, 'text': good_csv}]
                else:
                    claims = []
                native_metrics = {'prompt_eval_count': 3000 if variant == 'production' else 1400,
                                  'prompt_eval_cached_count': 0,
                                  'prompt_evalMs': 50000 if variant == 'production' else 25000}
                return {'result': {'status': 'completed', 'modelAnswer': json.dumps({'claims': claims}),
                                   'native': native_metrics, 'doneReason': 'stop'}}, [], [], True
            output = []
            with self.subTest(omit_network=omit_network), \
                    patch.object(candidate.platform, 'system', return_value='Darwin'), \
                    patch.object(candidate.baseline, 'verify_project'), \
                    patch.object(candidate.resources, 'Reader', Reader), \
                    patch.object(candidate, 'read_page', side_effect=lambda project, url: copy.deepcopy(pages[url])), \
                    patch.object(candidate, 'thermal_sample', return_value={}), \
                    patch.object(candidate, 'collect', side_effect=collect):
                automatic = candidate.run(ROOT, emit=output.append)
            self.assertEqual(calls, list(candidate.baseline.ORDER))
            self.assertEqual(automatic['completed'], 6)
            self.assertEqual(automatic['technicalCaseShapesMet'], not omit_network)
            self.assertEqual(automatic['qualityVerdict'], 'pending_review')
            self.assertFalse(automatic['integrationAllowedByThisAutomaticReport'])
            self.assertTrue(automatic['previousV2MeasurementsNotReused'])
            self.assertTrue(automatic['nativeIdentifierPolicySharedByBothVariants'])
            self.assertTrue(automatic['nativeIdentifierChecksAddedExplicitly'])
            records = [json.loads(text) for text in output if text.startswith('{')]
            rows = [record for record in records if 'case' in record]
            self.assertEqual([row['nativeClaimArrayLimit'] for row in rows], [2, 2, 1, 2, 2, 2])
            if omit_network:
                self.assertEqual(rows[1]['originalApplicationChecks']['outcome'], 'accepted_pending_semantic_review')
                self.assertEqual(rows[1]['checks']['reason'], 'native_identifier_constraint_not_observed')
                self.assertFalse(rows[1]['caseShapeMet'])


if __name__ == '__main__':
    unittest.main()
