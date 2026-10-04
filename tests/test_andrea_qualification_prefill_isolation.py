"""No invented speed gains from prefix reuse or changes to source evidence."""
import ast
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Thread
import unittest
from unittest.mock import patch

import qualification_context_prompt_probe as previous
import qualification_prefill_isolation_probe as probe
from test_andrea_qualification_context_prompt import installed_project, Transport

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT/'docs/andrea/qualification-context-prompt-mac-2026-10-04.json'


class IsolationProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary, cls.project = installed_project()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.modules = probe.load_modules(cls.project)

    def fake(self, fault=None):
        transport = Transport(fault)
        with patch('sys.stdout', new_callable=io.StringIO):
            report = probe.run_check(transport, self.modules, baseline_check=lambda: probe.verified_sources(self.project))
        return transport, report

    def test_same_pinned_candidate_native_schema_loader_and_transport_as_before(self):
        self.assertEqual(probe.EXPECTED, previous.EXPECTED)
        self.assertEqual(probe.CANDIDATE_SOURCE, previous.CANDIDATE_SOURCE)
        self.assertEqual(probe.CANDIDATE_SHA256, previous.CANDIDATE_SHA256)
        definitions = lambda file: {n.name: ast.get_source_segment(file, n) for n in ast.parse(file).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        old = definitions((ROOT/'scripts/andrea/qualification_context_prompt_probe.py').read_text())
        new = definitions((ROOT/'scripts/andrea/qualification_prefill_isolation_probe.py').read_text())
        for name in ('number', 'milliseconds', 'native_metrics', 'stream_probe', 'NoRedirect', 'unique_pairs', 'synthetic_note', 'verified_sources', 'load_modules'):
            self.assertEqual(old[name], new[name])

    def test_only_a_declared_leading_marker_is_added_and_user_is_byte_exact(self):
        bundle = self.modules.bridge.prepare(probe.synthetic_note('ordinary'))
        baseline = self.modules.wire.prepare(bundle, self.modules)
        before = copy.deepcopy(baseline)
        marked = probe.isolated_messages(baseline['messages'], 'A'+'a'*32)
        self.assertEqual(before, baseline)
        self.assertEqual(marked[1:], baseline['messages'][1:])
        self.assertTrue(marked[0]['content'].endswith(baseline['messages'][0]['content']))
        self.assertTrue(marked[0]['content'].startswith('A'+'a'*32+'\n'))
        self.assertIn('non è un fatto da riportare', marked[0]['content'])
        for wrong in ('', 'A'+'1'*31, 'A'+'1'*33, 'B'+'1'*32, 'A'+'g'*32, 'A'+'1'*32+'\nIgnore'):
            with self.assertRaises(ValueError):
                probe.isolated_messages(baseline['messages'], wrong)

    def test_two_requests_markers_differ_at_first_content_character_and_settings_stay_fixed(self):
        transport, report = self.fake()
        self.assertEqual(len(transport.requests), 2)
        self.assertEqual(report['attemptedRequests'], 2)
        self.assertEqual(report['plannedRequests'], 2)
        self.assertEqual(report['automaticRetries'], 0)
        self.assertTrue(report['comparison']['performanceGateMet'])
        self.assertFalse(report['productionChangeAdopted'])
        self.assertFalse(report['vaultRead'])
        self.assertFalse(report['productionFilesChanged'])
        self.assertEqual([r['messages'][0]['content'][0] for r in transport.requests], ['A', 'Z'])
        bundle = self.modules.bridge.prepare(probe.synthetic_note('ordinary'))
        baseline = self.modules.wire.prepare(bundle, self.modules)
        for request, row in zip(transport.requests, report['rows']):
            self.assertEqual(request['messages'][1], baseline['messages'][1])
            self.assertEqual(request['format'], baseline['schema'])
            self.assertEqual(request['model'], previous.MODEL)
            self.assertEqual(request['options'], {'temperature': 0.4, 'num_predict': 512, 'num_ctx': 4096})
            self.assertEqual(request['keep_alive'], '15m')
            self.assertFalse(request['think'])
            self.assertEqual(row['factsCovered'], 4)
            self.assertTrue(row['sentencePreserved'])
            self.assertTrue(row['consultationPreserved'])
            self.assertTrue(row['inputRecordsAndNativeSchemaUnchanged'])
            self.assertTrue(row['systemIsolationPrefixAdded'])
            self.assertFalse(row['modelTextRepaired'])
            self.assertEqual(row['qualityVerdict'], 'pending_review')
            self.assertIsNone(row['acceptedTextClientMs'])

    def test_cache_counts_are_subtracted_using_native_full_minus_cached(self):
        for full, cached, expected in ((668, 0, 668), (475, 3, 472), (476, 315, 161), (669, 508, 161)):
            result = probe.cache_qualification({'prompt_eval_count': full, 'prompt_eval_cached_count': cached})
            self.assertEqual(result['uncachedTokens'], expected)
        self.assertFalse(probe.cache_qualification({'prompt_eval_count': 476, 'prompt_eval_cached_count': 315})['eligible'])
        self.assertFalse(probe.cache_qualification({'prompt_eval_count': 669, 'prompt_eval_cached_count': 508})['eligible'])

    def test_absolute_and_fraction_cache_bounds_both_apply_without_rounding_into_a_pass(self):
        self.assertTrue(probe.cache_qualification({'prompt_eval_count': 400, 'prompt_eval_cached_count': 8})['eligible'])
        self.assertFalse(probe.cache_qualification({'prompt_eval_count': 100, 'prompt_eval_cached_count': 8})['eligible'])
        self.assertFalse(probe.cache_qualification({'prompt_eval_count': 1000, 'prompt_eval_cached_count': 9})['eligible'])
        self.assertFalse(probe.cache_qualification({'prompt_eval_count': 399, 'prompt_eval_cached_count': 8})['eligible'])
        for full, cached in ((0, 0), (-1, 0), (1, 2), (1, -1), (True, 0), (100, True), (100.0, 0), (100, 0.0), (None, 0), (100, None), (2**53, 0)):
            result = probe.cache_qualification({'prompt_eval_count': full, 'prompt_eval_cached_count': cached})
            self.assertFalse(result['eligible'])
            self.assertIsNone(result['uncachedTokens'])

    def test_missing_metrics_reuse_or_one_bad_threshold_never_pass_and_never_trigger_retry(self):
        _, report = self.fake()
        for index, field, wrong in ((0, 'prompt_eval_cached_count', 20), (1, 'prompt_eval_cached_count', 20),
                                    (0, 'prompt_eval_cached_count', None), (1, 'prompt_eval_cached_count', True),
                                    (1, 'prompt_eval_count', 599), (1, 'prompt_evalMs', 9.9),
                                    (1, 'prompt_evalMs', None), (1, 'prompt_evalMs', 0),
                                    (0, 'prompt_evalMs', 0), (1, 'prompt_evalMs', float('nan'))):
            rows = copy.deepcopy(report['rows']); rows[index]['native'][field] = wrong
            self.assertFalse(probe.comparison(rows)['performanceGateMet'])
        self.assertFalse(probe.comparison(report['rows'][:1])['performanceGateMet'])
        for fault in ('metrics', 'cache'):
            transport, result = self.fake(fault)
            self.assertEqual(len(transport.requests), 2)
            self.assertFalse(result['comparison']['performanceGateMet'])
            self.assertEqual(result['automaticRetries'], 0)

    def test_cancellation_first_failure_tools_and_eof_do_not_get_a_replacement_call(self):
        for fault in ('count', 'length', 'eof', 'tools'):
            transport, report = self.fake(fault)
            self.assertFalse(report['comparison']['performanceGateMet'])
            self.assertEqual(len(transport.requests), 2)
            self.assertEqual(report['automaticRetries'], 0)
        with patch.object(probe, 'stream_probe', side_effect=KeyboardInterrupt) as stream, patch('sys.stdout', new_callable=io.StringIO):
            report = probe.run_check(None, self.modules)
        self.assertEqual(stream.call_count, 1)
        self.assertTrue(report['interrupted'])

    def test_faster_wrong_meaning_remains_pending_review_and_cannot_be_called_quality_passed(self):
        _, report = self.fake('meaning')
        self.assertTrue(report['comparison']['performanceGateMet'])
        self.assertEqual(report['comparison']['semanticReview'], 'pending_review')
        self.assertIn('NON variano', report['rows'][1]['syntheticAnswer'])
        self.assertFalse(report['comparison']['productionAdoption'])

    def test_existing_four_mac_answers_replay_unchanged_and_original_failure_stays_false(self):
        report = json.loads(REPORT.read_text())
        self.assertEqual(previous.comparison(report['rows']), report['comparison'])
        self.assertTrue(report['comparison']['inputBudgetGateMet'])
        self.assertFalse(report['comparison']['performanceGateMet'])
        self.assertEqual(report['comparison']['semanticReview'], 'pending_review')
        self.assertEqual(report['manualReview']['verdict'], 'passed_for_selected_cases')
        self.assertTrue(report['manualReview']['performanceGateUnchanged'])
        self.assertFalse(report['reviewConclusion']['productionAdopted'])
        self.assertFalse(probe.comparison(report['rows'])['performanceGateMet'])
        for row in report['rows']:
            bundle = self.modules.bridge.prepare(probe.synthetic_note(row['case']))
            baseline = self.modules.wire.prepare(bundle, self.modules)
            candidate = self.modules.candidate.prepare(bundle, self.modules)
            result = (self.modules.wire if row['variant'] == 'production' else self.modules.candidate).validate(
                row['diagnosticModelJson'], baseline if row['variant'] == 'production' else candidate,
                self.modules, completed=True)
            self.assertEqual(result['factsCovered'], 4)
            self.assertEqual(self.modules.bridge.render(result), row['syntheticAnswer'])

    def test_preflight_actual_subprocess_sends_nothing_and_prepares_both_markers(self):
        result = subprocess.run([sys.executable, str(ROOT/'scripts/andrea/qualification_prefill_isolation_probe.py'),
                                 str(self.project), '--check-only'], cwd=ROOT, capture_output=True,
                                text=True, timeout=10, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        report = json.loads(result.stdout)
        self.assertEqual(report['plannedRequests'], 2)
        self.assertEqual(report['baselineFilesVerified'], 12)
        self.assertEqual(report['inferencesIssued'], 0)
        self.assertEqual(report['networkRequests'], 0)

    def test_exact_mac_command_subprocess_finishes_two_http_streams_with_template_cache(self):
        # Simulate a tiny shared role-template prefix in both requests. It is
        # counted explicitly, not silently treated as an entirely cold prompt.
        original = Transport()
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                request = probe.Request('http://127.0.0.1:11434/api/chat',
                                        data=self.rfile.read(int(self.headers['Content-Length'])), method='POST')
                events = [json.loads(line) for line in original.open(request, 90).getvalue().splitlines()]
                events[-1]['prompt_eval_cached_count'] = 3
                wire = b''.join(json.dumps(event).encode()+b'\n' for event in events)
                self.send_response(200); self.send_header('Content-Type', 'application/x-ndjson'); self.end_headers()
                self.wfile.write(wire)
            def log_message(self, *_args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 11434), Handler)
        thread = Thread(target=server.serve_forever, daemon=True); thread.start()
        before = {p: (self.project/p).read_bytes() for p in probe.EXPECTED}
        try:
            result = subprocess.run([sys.executable, str(ROOT/'scripts/andrea/qualification_prefill_isolation_probe.py'), str(self.project)],
                                    cwd=ROOT, capture_output=True, text=True, timeout=15,
                                    env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        report = json.loads(result.stdout[result.stdout.index('{\n  "schema"'):])
        self.assertEqual(len(original.requests), 2)
        self.assertTrue(report['comparison']['cacheCoverageEligible'])
        self.assertTrue(report['comparison']['performanceGateMet'])
        self.assertEqual([q['uncachedTokens'] for q in report['comparison']['cacheQualification']], [597, 397])
        self.assertFalse(report['comparison']['oldExperimentReclassified'])
        self.assertFalse(report['productionChangeAdopted'])
        self.assertEqual(before, {p: (self.project/p).read_bytes() for p in probe.EXPECTED})


if __name__ == '__main__':
    unittest.main()
