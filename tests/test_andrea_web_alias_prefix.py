"""Regressions for actual alias false rejection and native length word clipping."""
import ast
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import web_alias_prefix_contract_candidate as candidate
import web_alias_prefix_probe as probe
import web_literal_prefix_contract_candidate as previous
from test_andrea_web_literal_prefix import LOOPS, BAD, GOOD_LOOPS
from test_andrea_web_identifier_probe import Opener, ASYNC, CSV, GOOD, CONCURRENT, CONDITION, raw

ROOT = Path(__file__).resolve().parents[1]
OBSERVED_LOOPS = "asyncio consente di creare e gestire loop di eventi per networking, esecuzione di subprocessi, e gestione di segnali dell'OS."
OBSERVED_CUT = ('csv.reader restituisce ogni riga come lista di stringhe, senza conversione automatica dei tipi, '
                'a meno che non sia specificato il formato QUOTE_NONNUMERIC, in cui i campi non quotati vengono trasformi')
COMPLETE_CSV = ('csv.reader restituisce ogni riga come lista di stringhe, senza conversione automatica dei tipi, '
                'a meno che non sia specificato il formato QUOTE_NONNUMERIC, in cui i campi non quotati vengono trasformati in float.')


class AliasContractTests(unittest.TestCase):
    def test_actual_correct_italian_translation_no_longer_false_rejected_or_repaired(self):
        self.assertEqual(previous.validate(raw(OBSERVED_LOOPS), [LOOPS], True)['reason'], 'source_technical_terms_not_preserved')
        result = candidate.validate(raw(OBSERVED_LOOPS), [LOOPS], True)
        self.assertEqual(result['outcome'], 'accepted_pending_semantic_review')
        self.assertEqual(result['claims'], [{'text': OBSERVED_LOOPS, 'quote': LOOPS, 'passage': 1}])

    def test_finite_equivalents_only_and_actual_wrong_subprojects_still_refused(self):
        for term in ('subprocess', 'subprocesses', 'subprocesso', 'subprocessi', 'sottoprocesso', 'sottoprocessi'):
            answer = 'asyncio gestisce i ' + term + ' mediante le API e i segnali OS.'
            self.assertEqual(candidate.validate(raw(answer), [LOOPS], True)['outcome'], 'accepted_pending_semantic_review', term)
        for term in ('sottoprogetti', 'processori', 'sottoprocessione', 'subprocessXYZ'):
            self.assertEqual(candidate.subprocess_terms(term), set(), term)
        result = candidate.validate(raw(BAD), [LOOPS], True)
        self.assertEqual(result['reason'], 'source_technical_terms_not_preserved')
        self.assertEqual(result['details']['missingTechnicalConcepts'], ['subprocess'])
        self.assertEqual(result['claims'], [])

    def test_equivalents_require_their_own_selected_source_unit(self):
        source = 'The library controls concurrent activities.\n'
        for term in ('subprocessi', 'sottoprocessi', 'subprocesses'):
            result = candidate.validate(raw('La libreria controlla i ' + term + ' durante le attese.'), [source, LOOPS], True)
            self.assertEqual(result['reason'], 'source_technical_terms_not_preserved')
            self.assertEqual(result['details']['addedTechnicalConcepts'], ['subprocess'])
        result = candidate.validate(raw('La libreria offre API per gestire le attività.'), [source, LOOPS], True)
        self.assertEqual(result['details']['addedIdentifiers'], ['API'])

    def test_actual_word_clipped_output_is_still_rejected_despite_completed_transport(self):
        self.assertEqual(len(OBSERVED_CUT), 200)
        result = candidate.validate(raw(OBSERVED_CUT), [CSV], True)
        self.assertEqual(result['reason'], 'sentence_not_complete')
        self.assertEqual(result['claims'], [])

    def test_completion_space_preserves_entire_csv_condition_and_field_scope(self):
        self.assertGreater(len(COMPLETE_CSV), 200)
        self.assertLess(len(COMPLETE_CSV), 320)
        self.assertEqual(previous.validate(raw(COMPLETE_CSV), [CSV], True)['outcome'], 'rejected')
        result = candidate.validate(raw(COMPLETE_CSV), [CSV], True)
        self.assertEqual(result['outcome'], 'accepted_pending_semantic_review')
        self.assertEqual(result['claims'][0]['text'], COMPLETE_CSV)
        self.assertEqual(result['claims'][0]['quote'], CSV)
        # Structural acceptance does not automatically judge omitted conditions.
        self.assertEqual(candidate.validate('{"claims":[]}', [CSV], True)['outcome'], 'abstained')

    def test_application_bound_and_stream_completion_still_reject_without_trimming(self):
        excessive = 'La libreria ' + 'gestisce ' * 35 + 'le operazioni.'
        self.assertGreater(len(excessive), 320)
        for text, complete, reason in ((excessive, True, 'invalid_structure'),
                                       (GOOD, False, 'stream_incomplete'),
                                       (COMPLETE_CSV[:-1], True, 'sentence_not_complete')):
            result = candidate.validate(raw(text), [CSV], complete)
            self.assertEqual(result['reason'], reason)
            self.assertEqual(result['claims'], [])

    def test_schema_no_native_cap_but_two_claims_and_source_selection_remain_bounded(self):
        page = ASYNC + LOOPS + CSV
        bank, messages, schema = candidate.prepare(page, 'Sintesi')
        old_bank, old_messages, old_schema = previous.prepare(page, 'Sintesi')
        self.assertEqual(bank, old_bank)
        expected = json.loads(json.dumps(old_schema))
        del expected['properties']['claims']['items']['properties']['text']['maxLength']
        self.assertEqual(schema, expected)
        payload = json.loads(messages[1]['content'])
        self.assertEqual(payload['passages'], json.loads(old_messages[1]['content'])['passages'])
        self.assertEqual(payload['sourceTechnicalTerms'], {'3': ['subprocess']})
        self.assertEqual(list(payload)[-1], 'question')
        self.assertIn('condizioni, eccezioni, negazioni e limiti hanno precedenza', messages[0]['content'])
        self.assertEqual(candidate.MAX_CLAIM_CHARS, 320)
        self.assertEqual(candidate.TARGET_CLAIM_CHARS, 100)

    def test_page_prefix_and_system_and_schema_are_stable_for_distinct_questions(self):
        a, b = [candidate.prepare(CSV, question) for question in ('Come converte?', 'Qual è il prezzo?')]
        self.assertEqual(a[0], b[0])
        self.assertEqual(a[1][0], b[1][0])
        self.assertEqual(a[2], b[2])
        prefix = probe.common_prefix_characters(a[1][1]['content'], b[1][1]['content'])
        self.assertGreater(prefix, len(CSV))

    def test_numbers_concurrency_duplicates_and_original_guards_still_fail(self):
        for answer, source, reason in ((raw('asyncio gestisce 100 operazioni IO e IPC.'), [ASYNC.splitlines(keepends=True)[1]], 'unsupported_number'),
                                       (raw('Le coroutine eseguono operazioni in parallelo.'), [ASYNC.splitlines(keepends=True)[0]], 'technical_term_missing_from_passage'),
                                       ('{"claims":[],"claims":[]}', [CSV], 'invalid_structure')):
            result = candidate.validate(answer, source, True)
            self.assertEqual(result['reason'], reason)
            self.assertEqual(result['claims'], [])

    def test_failed_second_claim_discards_all_without_silent_repair(self):
        answer = json.dumps({'claims': [{'passage': 1, 'text': GOOD}, {'passage': 2, 'text': BAD}]})
        result = candidate.validate(answer, [ASYNC.splitlines(keepends=True)[1], LOOPS], True)
        self.assertEqual(result['claims'], [])
        self.assertEqual(result['details']['claimIndex'], 2)

    def test_standalone_and_pure_functions_are_identical(self):
        def functions(module):
            return {n.name: ast.dump(n) for n in ast.parse(Path(module.__file__).read_text()).body if isinstance(n, ast.FunctionDef)}
        pure, standalone = functions(candidate), functions(probe)
        for name, body in pure.items(): self.assertEqual(body, standalone[name], name)


class AliasProbeTests(unittest.TestCase):
    def project(self, directory):
        root = Path(directory)
        for relative, digest in probe.EXPECTED.items():
            data = (ROOT/relative).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), digest)
            target = root/relative; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
        return root

    def test_two_reads_three_original_cases_no_writes_or_setting_changes(self):
        answers = [json.dumps({'claims': [{'passage': 1, 'text': CONCURRENT}, {'passage': 2, 'text': GOOD}]}), raw(COMPLETE_CSV), '{"claims":[]}']
        with tempfile.TemporaryDirectory() as directory:
            root = self.project(directory)
            before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
            opener = Opener(answers); rows = probe.run(root, opener, lambda _: None)
            self.assertEqual(before, {p: p.read_bytes() for p in root.rglob('*') if p.is_file()})
        self.assertEqual((opener.read_count, opener.infer_count), (2, 3))
        self.assertEqual([r['case'] for r in rows], [c['id'] for c in probe.CASES])
        self.assertEqual([r['checks']['outcome'] for r in rows], ['accepted_pending_semantic_review', 'accepted_pending_semantic_review', 'abstained'])
        for row in rows:
            self.assertEqual(row['qualityVerdict'], 'pending_review')
            self.assertEqual(row['automaticRetries'], 0)
            self.assertFalse(row['productionModified'])
            self.assertEqual(row['claimLengthPolicy']['nativeStringMaxLength'], None)
        for url, request, _ in opener.calls:
            if url.endswith('/api/chat'):
                self.assertEqual(request['options'], {'temperature': .4, 'num_predict': 512, 'num_ctx': 4096})
                self.assertEqual(request['keep_alive'], '15m'); self.assertFalse(request['think'])

    def test_failed_read_missing_context_and_local_edits_stop_before_inference(self):
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

    def test_incomplete_stream_stops_without_retry_or_partial_acceptance(self):
        output = []
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(probe, 'stream_probe', return_value={'status': 'incomplete', 'modelAnswer': ''}) as call:
                with self.assertRaises(probe.CheckError): probe.run(self.project(directory), Opener(), output.append)
            self.assertEqual(call.call_count, 1)
        row = next(json.loads(x) for x in output if x.startswith('{'))
        self.assertEqual(row['checks']['reason'], 'stream_incomplete')
        self.assertEqual(row['qualityVerdict'], 'pending_review')


if __name__ == '__main__': unittest.main()
