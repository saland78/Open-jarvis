"""Prompt-prefix experiment preserves source, quality guards and bounded calls."""
import ast
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import check_web_reliability as production_check
import web_prefix_contract_candidate as candidate
import web_prompt_prefix_probe as probe
import web_sentence_contract as production
from test_andrea_web_identifier_probe import Opener, ASYNC, CSV, GOOD, CONCURRENT, CONDITION, BAD, raw

ROOT = Path(__file__).resolve().parents[1]


class PrefixContractTests(unittest.TestCase):
    def test_only_json_field_order_changes_full_source_question_schema_and_roles_preserved(self):
        for page in (ASYNC, CSV, 'A'*700 + '\n' + ASYNC):
            before = production.prepare(page, 'Sintesi con domanda differente.')
            after = candidate.prepare(page, 'Sintesi con domanda differente.')
            self.assertEqual(after[0], before[0])
            self.assertEqual(''.join(after[0]), page)
            self.assertEqual(after[2], before[2])
            self.assertEqual(after[1][0], before[1][0])
            self.assertEqual(after[1][1]['role'], before[1][1]['role'])
            self.assertEqual(json.loads(after[1][1]['content']), json.loads(before[1][1]['content']))
            self.assertEqual(list(json.loads(after[1][1]['content'])), ['protectedIdentifiers', 'passages', 'question'])

    def test_different_questions_keep_whole_same_page_prefix_not_answers(self):
        baseline = [production.prepare(CSV, x['question'])[1][1]['content'] for x in production_check.CASES[1:]]
        proposed = [candidate.prepare(CSV, x['question'])[1][1]['content'] for x in production_check.CASES[1:]]
        self.assertLess(probe.common_prefix_characters(*baseline), 30)
        prefix_length = probe.common_prefix_characters(*proposed)
        source_end = proposed[0].index(',"question":')
        self.assertGreaterEqual(prefix_length, source_end)
        self.assertEqual(proposed[0][:source_end], proposed[1][:source_end])
        self.assertNotEqual(proposed[0], proposed[1])

    def test_validation_identical_for_supported_condition_bad_ipc_and_abstention(self):
        examples = [(ASYNC, raw(GOOD, 2)), (ASYNC, raw(BAD, 2)),
                    (CSV, raw(CONDITION)), (CSV, '{"claims":[]}'),
                    (ASYNC, raw('Le coroutine sono eseguite in parallelo.', 1))]
        for page, answer in examples:
            for completed in (True, False):
                bank = production.sentence_bank(page)
                self.assertEqual(candidate.validate(answer, bank, completed), production.validate(answer, bank, completed))

    def test_standalone_uses_exact_candidate_and_installed_baseline_functions(self):
        def functions(module):
            return {n.name: n for n in ast.parse(Path(module.__file__).read_text()).body if isinstance(n, ast.FunctionDef)}
        pure, standalone, installed = functions(candidate), functions(probe), functions(production)
        for name, function in pure.items():
            self.assertEqual(ast.dump(function), ast.dump(standalone[name]), name)
            if name != 'prepare':
                self.assertEqual(ast.dump(function), ast.dump(installed[name]), name)
        installed['prepare'].name = 'prepare_baseline'
        self.assertEqual(ast.dump(installed['prepare']), ast.dump(standalone['prepare_baseline']))


class PrefixProbeTests(unittest.TestCase):
    def project(self, directory):
        root = Path(directory)
        for relative, digest in probe.EXPECTED.items():
            data = (ROOT/relative).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), digest)
            target = root/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (root/'private-note.md').write_text('PRIVATE CANARY')
        return root

    def opener(self):
        return Opener([json.dumps({'claims': [{'passage': 1, 'text': CONCURRENT}, {'passage': 2, 'text': GOOD}]}),
                       raw(CONDITION), '{"claims":[]}'] * 2)

    def test_exact_two_reads_six_inferences_same_sources_no_writes_options_or_warmups(self):
        self.assertEqual(probe.CASES, production_check.CASES)
        self.assertEqual(probe.EXPECTED, production_check.EXPECTED)
        with tempfile.TemporaryDirectory() as directory:
            project = self.project(directory)
            before = {p: p.read_bytes() for p in project.rglob('*') if p.is_file()}
            opener = self.opener()
            rows = probe.run(project, opener, lambda _: None)
            self.assertEqual(before, {p: p.read_bytes() for p in project.rglob('*') if p.is_file()})
        self.assertEqual((opener.read_count, opener.infer_count), (2, 6))
        self.assertEqual(len(opener.calls), 8)
        inference = [data for url, data, _ in opener.calls if url.endswith('/api/chat')]
        for request in inference:
            self.assertEqual(request['options'], {'temperature': .4, 'num_predict': 512, 'num_ctx': 4096})
            self.assertEqual(request['model'], probe.MODEL)
            self.assertEqual(request['keep_alive'], '15m')
            self.assertFalse(request['think'])
            self.assertNotIn('tools', request)
            self.assertNotIn('PRIVATE CANARY', json.dumps(request))
        for i in range(3):
            self.assertEqual(json.loads(inference[i]['messages'][1]['content']), json.loads(inference[i+3]['messages'][1]['content']))
            self.assertEqual(inference[i]['format'], inference[i+3]['format'])
            self.assertEqual(rows[i]['sourceTextSha256'], rows[i+3]['sourceTextSha256'])
        self.assertTrue(all(r['qualityVerdict'] == 'pending_review' for r in rows))
        self.assertTrue(all(r['automaticRetries'] == 0 and not r['productionModified'] for r in rows))
        self.assertLess(rows[2]['serializedUserCommonPrefixCharacters'], rows[5]['serializedUserCommonPrefixCharacters'])

    def test_bad_semantic_guard_result_is_retained_not_retried_or_repaired(self):
        opener = self.opener(); opener.answers[0] = raw(BAD, 2)
        with tempfile.TemporaryDirectory() as directory:
            rows = probe.run(self.project(directory), opener, lambda _: None)
        self.assertEqual(opener.infer_count, 6)
        self.assertEqual(rows[0]['checks']['outcome'], 'rejected')
        self.assertEqual(rows[0]['checks']['claims'], [])
        self.assertEqual(json.loads(rows[0]['result']['modelAnswer'])['claims'][0]['text'], BAD)

    def test_read_failure_or_missing_condition_prevents_all_inferences(self):
        with tempfile.TemporaryDirectory() as directory:
            project = self.project(directory)
            opener = Opener(read_fail=True)
            with self.assertRaises(probe.CheckError): probe.run(project, opener, lambda _: None)
            self.assertEqual(opener.infer_count, 0)
            opener = self.opener()
            cases = tuple({**case, 'requiredContext': 'NOT IN SOURCE'} if i == 1 else case for i, case in enumerate(probe.CASES))
            with patch.object(probe, 'CASES', cases):
                with self.assertRaises(probe.CheckError): probe.run(project, opener, lambda _: None)
            self.assertEqual((opener.read_count, opener.infer_count), (2, 0))

    def test_changed_installed_file_refused_before_any_request(self):
        with tempfile.TemporaryDirectory() as directory:
            project = self.project(directory)
            (project/next(iter(probe.EXPECTED))).write_text('changed')
            opener = self.opener()
            with self.assertRaises(probe.CheckError): probe.run(project, opener, lambda _: None)
        self.assertEqual(opener.calls, [])

    def test_incomplete_model_transport_stops_after_exposing_failure(self):
        output = []
        with tempfile.TemporaryDirectory() as directory:
            opener = self.opener()
            with patch.object(probe, 'stream_probe', return_value={'status': 'incomplete', 'modelAnswer': ''}) as call:
                with self.assertRaises(probe.CheckError): probe.run(self.project(directory), opener, output.append)
            self.assertEqual(call.call_count, 1)
        row = next(json.loads(x) for x in output if x.startswith('{'))
        self.assertEqual(row['checks']['reason'], 'stream_incomplete')
        self.assertEqual(row['qualityVerdict'], 'pending_review')

    def test_proxy_redirect_isolation_and_missing_native_cache_measurements(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(probe.urllib.request, 'build_opener', return_value=self.opener()) as build:
                probe.run(self.project(directory), emit=lambda _: None)
        self.assertEqual(build.call_args.args[0].proxies, {})
        with self.assertRaises(probe.CheckError): build.call_args.args[1].redirect_request(None, None, 302, 'redirect', {}, 'https://example.com')
        self.assertIsNone(probe.native_metrics({})['prompt_eval_cached_count'])
        self.assertEqual(probe.native_metrics({'prompt_eval_count': 2239, 'prompt_eval_cached_count': 2200,
                         'prompt_eval_duration': 200000000})['prompt_evalMs'], 200)


if __name__ == '__main__': unittest.main()
