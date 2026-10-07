"""Source-first refinement addresses the observed technical mistranslation."""
import ast
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import web_literal_prefix_contract_candidate as candidate
import web_literal_prefix_probe as probe
import web_prefix_contract_candidate as previous
from web_prefix_baseline import contract as installed
from test_andrea_web_identifier_probe import Opener, ASYNC, CSV, GOOD, CONCURRENT, CONDITION, raw

from web_prefix_baseline import source as baseline_source

ROOT = Path(__file__).resolve().parents[1]
LOOPS = ('create and manage event loops, which provide asynchronous APIs for '
         'networking, running subprocesses, handling OS signals, etc;\n')
BAD = "asyncio offre API asincrone per networking, esecuzione di sottoprogetti e gestione di segnali dell'OS."
GOOD_LOOPS = "asyncio offre API asincrone per networking, esecuzione di subprocesses e gestione dei segnali dell'OS."


class LiteralContractTests(unittest.TestCase):
    def test_observed_bad_subprojects_claim_is_rejected_even_after_api_false_rejection_fix(self):
        result = candidate.validate(raw(BAD), [LOOPS], True)
        self.assertEqual(result['reason'], 'source_technical_terms_not_preserved')
        self.assertEqual(result['claims'], [])
        self.assertEqual(result['details']['missingLiteralTerms'], ['subprocesses'])
        self.assertEqual(result['details']['text'], BAD)
        self.assertEqual(result['details']['quote'], LOOPS)

    def test_literal_subprocesses_and_api_plural_anchor_accept_precise_candidate_not_repaired_text(self):
        self.assertEqual(previous.validate(raw(GOOD_LOOPS), [LOOPS], True)['details']['addedIdentifiers'], ['API'])
        result = candidate.validate(raw(GOOD_LOOPS), [LOOPS], True)
        self.assertEqual(result['outcome'], 'accepted_pending_semantic_review')
        self.assertEqual(result['claims'], [{'text': GOOD_LOOPS, 'quote': LOOPS, 'passage': 1}])
        self.assertEqual(candidate.source_identifier_aliases('APIs'), {'API'})
        self.assertEqual(candidate.source_identifier_aliases('apis'), set())

    def test_api_alias_is_anchored_to_selected_unit_not_elsewhere_in_page(self):
        result = candidate.validate(raw('La libreria offre API per gestire le attività.'),
            ['The library controls concurrent activities.\n', LOOPS], True)
        self.assertEqual(result['reason'], 'source_identifiers_not_preserved')
        self.assertEqual(result['details']['addedIdentifiers'], ['API'])

    def test_source_literal_terms_cannot_be_added_to_an_unrelated_unit(self):
        result = candidate.validate(raw('La libreria controlla i subprocesses durante le attese.'),
                                    ['The library controls concurrent activities.\n'], True)
        self.assertEqual(result['reason'], 'source_technical_terms_not_preserved')
        self.assertEqual(result['details']['addedLiteralTerms'], ['subprocesses'])

    def test_false_second_claim_drops_all_claims_without_repair(self):
        claims = [{'passage': 1, 'text': GOOD}, {'passage': 2, 'text': BAD}]
        result = candidate.validate(json.dumps({'claims': claims}), [ASYNC.splitlines(keepends=True)[1], LOOPS], True)
        self.assertEqual(result['claims'], [])
        self.assertEqual(result['details']['claimIndex'], 2)

    def test_full_source_schema_and_conditions_preserved_without_acronym_definition(self):
        page = ASYNC + LOOPS + CSV
        bank, messages, schema = candidate.prepare(page, 'Sintesi')
        self.assertEqual(''.join(bank), page)
        self.assertEqual(schema, installed.prepare(page, 'Sintesi')[2])
        payload = json.loads(messages[1]['content'])
        self.assertEqual(payload['literalTechnicalTerms'], {'3': ['subprocesses']})
        self.assertEqual(payload['passages'], json.loads(installed.prepare(page, 'Sintesi')[1][1]['content'])['passages'])
        self.assertEqual(list(payload)[-1], 'question')
        self.assertNotIn('sottoprogetti', json.dumps(payload))
        self.assertEqual(candidate.validate(raw(CONDITION), [CSV], True), installed.validate(raw(CONDITION), [CSV], True))
        self.assertEqual(candidate.validate('{"claims":[]}', [CSV], True)['outcome'], 'abstained')

    def test_standalone_and_pure_refinement_functions_are_identical(self):
        def functions(module):
            return {n.name: ast.dump(n) for n in ast.parse(Path(module.__file__).read_text()).body if isinstance(n, ast.FunctionDef)}
        pure, standalone = functions(candidate), functions(probe)
        for name, body in pure.items(): self.assertEqual(body, standalone[name], name)


class LiteralProbeTests(unittest.TestCase):
    def project(self, directory):
        root = Path(directory)
        for relative, digest in probe.EXPECTED.items():
            data = baseline_source(relative)
            self.assertEqual(hashlib.sha256(data).hexdigest(), digest)
            target = root/relative; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
        return root

    def test_two_reads_three_candidate_calls_unchanged_files_settings_pending_quality(self):
        answers = [json.dumps({'claims': [{'passage': 1, 'text': CONCURRENT}, {'passage': 2, 'text': GOOD}]}),
                   raw(CONDITION), '{"claims":[]}']
        with tempfile.TemporaryDirectory() as directory:
            root = self.project(directory)
            before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
            opener = Opener(answers); rows = probe.run(root, opener, lambda _: None)
            self.assertEqual(before, {p: p.read_bytes() for p in root.rglob('*') if p.is_file()})
        self.assertEqual((opener.read_count, opener.infer_count), (2, 3))
        self.assertEqual(len(opener.calls), 5)
        self.assertTrue(all(r['qualityVerdict'] == 'pending_review' and r['automaticRetries'] == 0 for r in rows))
        self.assertEqual([r['case'] for r in rows], [c['id'] for c in probe.CASES])
        for url, request, _ in opener.calls:
            if url.endswith('/api/chat'):
                self.assertEqual(request['options'], {'temperature': .4, 'num_predict': 512, 'num_ctx': 4096})
                self.assertEqual(request['keep_alive'], '15m'); self.assertFalse(request['think'])
                self.assertEqual(list(json.loads(request['messages'][1]['content']))[-1], 'question')
        self.assertGreater(rows[2]['serializedUserCommonPrefixCharacters'], 100)

    def test_failed_read_missing_context_and_local_edits_do_not_start_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.project(directory); opener = Opener(read_fail=True)
            with self.assertRaises(probe.CheckError): probe.run(root, opener, lambda _: None)
            self.assertEqual(opener.infer_count, 0)
            cases = tuple({**c, 'requiredContext': 'ABSENT CONDITION'} if i == 1 else c for i, c in enumerate(probe.CASES))
            opener = Opener()
            with patch.object(probe, 'CASES', cases):
                with self.assertRaises(probe.CheckError): probe.run(root, opener, lambda _: None)
            self.assertEqual(opener.infer_count, 0)
            (root/next(iter(probe.EXPECTED))).write_text('local change'); opener = Opener()
            with self.assertRaises(probe.CheckError): probe.run(root, opener, lambda _: None)
            self.assertEqual(opener.calls, [])

    def test_incomplete_stream_stops_after_one_diagnostic_without_retry(self):
        output = []
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(probe, 'stream_probe', return_value={'status': 'incomplete', 'modelAnswer': ''}) as call:
                with self.assertRaises(probe.CheckError): probe.run(self.project(directory), Opener(), output.append)
            self.assertEqual(call.call_count, 1)
        row = next(json.loads(x) for x in output if x.startswith('{'))
        self.assertEqual(row['checks']['reason'], 'stream_incomplete')
        self.assertEqual(row['qualityVerdict'], 'pending_review')


if __name__ == '__main__': unittest.main()
