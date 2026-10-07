"""Finite native compatibility/defect check, independent rejection and no writes."""
import copy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch

import qualification_clause_fix_probe as probe
import qualification_clause_guard as guard
from test_andrea_qualification_clause_guard import response

from andrea_qualification_baseline import source as baseline_source

ROOT = Path(__file__).resolve().parents[1]
TRANSPORT = ROOT/'scripts/andrea/concise_qualification_text_probe.py'


class Transport:
    def __init__(self, bundle, fault=None):
        self.requests = []
        self.fault = fault
        self.canary = json.dumps({'text': bundle['qualificationClause']['source_prefix']+' verifica'})
        self.raw = response(bundle)
        if fault == 'omission':
            self.raw = response(bundle, text='I valori sono DATO NON VERIFICATO; consultare dashboard o report indicando periodo, titolo e marketplace.')
        elif fault == 'meaning':
            value = json.loads(self.raw)
            value['records']['F2']['text'] = 'Vendite e royalty NON variano per periodo.'
            self.raw = json.dumps(value)

    def wire(self, index):
        raw = self.canary if index == 1 else self.raw
        if index == 1 and self.fault == 'canary':
            raw = '{"text":"NON_CONFORME"}'
        elif index == 1 and self.fault == 'duplicate':
            raw = '{"text":"NON_CONFORME","text":"NON_CONFORME"}'
        events = [{'message': {'content': raw[:17]}, 'done': False},
                  {'message': {'content': raw[17:]}, 'done': False},
                  {'message': {'content': ''}, 'done': True, 'done_reason': 'stop',
                   'eval_duration': 10_000_000, 'eval_count': 20}]
        if self.fault == 'length' or (index == 2 and self.fault == 'second_length'):
            events[-1]['done_reason'] = 'length'
        if self.fault == 'eof':
            events.pop()
        return b''.join(json.dumps(e).encode()+b'\n' for e in events)

    def open(self, request, timeout):
        self.requests.append(json.loads(request.data))
        assert request.full_url == 'http://127.0.0.1:11434/api/chat' and timeout == 90
        return io.BytesIO(self.wire(len(self.requests)))


class QualificationClauseFixProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.p = probe.verified_probe(TRANSPORT)
        for relative in self.p.EXPECTED:
            target = self.project/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(baseline_source(relative), target)
        self.modules = self.p.load_modules(self.project)
        self.guard = probe.guard_module()
        self.original = self.modules.bridge.prepare(self.p.synthetic_note('adversarial'))
        self.bundle = self.guard.protect(self.original)

    def run_report(self, fault=None):
        transport = Transport(self.bundle, fault)
        return probe.run_check(transport, self.modules, self.p, self.guard), transport

    def test_exact_embedded_guard_two_requests_unchanged_options_and_no_project_writes(self):
        self.assertEqual(probe.GUARD_SOURCE, (ROOT/'scripts/andrea/qualification_clause_guard.py').read_text())
        self.assertEqual(probe.GUARD_SHA256, hashlib.sha256(probe.GUARD_SOURCE.encode()).hexdigest())
        before = {str(f.relative_to(self.project)): f.read_bytes() for f in self.project.rglob('*') if f.is_file()}
        original = copy.deepcopy(self.original)
        report, transport = self.run_report()
        self.assertEqual(len(transport.requests), 2)
        self.assertEqual(report['attemptedRequests'], 2)
        self.assertTrue(report['canary']['nativeConformanceObserved'])
        self.assertIn('NON_CONFORME', transport.requests[0]['messages'][1]['content'])
        self.assertEqual(transport.requests[1]['messages'], self.bundle['messages'])
        self.assertEqual(transport.requests[1]['format'], self.bundle['plan']['schema'])
        for request in transport.requests:
            self.assertEqual(request['options'], {'temperature': 0.4, 'num_predict': 512, 'num_ctx': 4096})
            self.assertEqual(request['model'], self.p.MODEL)
            self.assertEqual(request['keep_alive'], '15m')
            self.assertIs(request['think'], False)
            self.assertNotIn(self.p.CANDIDATE_INSTRUCTION, str(request))
            self.assertNotIn('1000 euro', str(request))
        self.assertEqual(report['technicalOutcome'], 'valid_structure_pending_semantic_review')
        self.assertEqual(report['qualityVerdict'], 'pending_review')
        self.assertEqual(report['previousPerformanceExperiment'], 'failed_not_reclassified')
        self.assertFalse(report['productionChangeAdopted'])
        self.assertFalse(report['productionFilesChanged'])
        self.assertFalse(report['vaultRead'])
        self.assertEqual(report['automaticRetries'], 0)
        self.assertTrue(report['defectCase']['clausePreserved'])
        self.assertEqual(report['defectCase']['diagnosticModelJson'], transport.raw)
        self.assertFalse(report['defectCase']['generatedTextRepaired'])
        for source in report['defectCase']['sourcePassages']:
            self.assertEqual(source['passage'], next(f['quote'] for f in original['plan']['facts'] if f['id'] == source['factId']))
        self.assertEqual(self.original, original)
        after = {str(f.relative_to(self.project)): f.read_bytes() for f in self.project.rglob('*') if f.is_file()}
        self.assertEqual(before, after)

    def test_failed_canary_invalid_json_transport_or_interrupt_aborts_without_retry(self):
        for fault in ('canary', 'duplicate', 'length', 'eof'):
            with self.subTest(fault=fault):
                report, transport = self.run_report(fault)
                self.assertEqual(len(transport.requests), 1)
                self.assertEqual(report['attemptedRequests'], 1)
                self.assertFalse(report['canary']['nativeConformanceObserved'])
                self.assertIsNone(report['defectCase'])
                self.assertEqual(report['technicalOutcome'], 'native_pattern_canary_failed')
                self.assertEqual(report['automaticRetries'], 0)
        class Broken:
            calls = 0
            def open(self, *_args, **_kwargs):
                self.calls += 1
                raise OSError('PRIVATE_ERROR')
        broken = Broken()
        report = probe.run_check(broken, self.modules, self.p, self.guard)
        self.assertEqual(broken.calls, 1)
        self.assertNotIn('PRIVATE_ERROR', json.dumps(report))
        with patch.object(self.p, 'stream_probe', side_effect=KeyboardInterrupt) as calls:
            report = probe.run_check(broken, self.modules, self.p, self.guard)
        self.assertEqual(calls.call_count, 1)
        self.assertTrue(report['interrupted'])
        self.assertEqual(report['canary']['status'], 'cancelled')

    def test_schema_nonconformance_is_independently_rejected_with_raw_preserved_not_repaired(self):
        report, transport = self.run_report('omission')
        self.assertEqual(len(transport.requests), 2)
        row = report['defectCase']
        self.assertEqual(row['technicalOutcome'], 'rejected')
        self.assertEqual(row['technicalReason'], 'qualification_clause_missing_or_changed')
        self.assertEqual(row['diagnosticModelJson'], transport.raw)
        self.assertIsNone(row['syntheticAnswer'])
        self.assertFalse(row['clausePreserved'])
        self.assertFalse(row['generatedTextRepaired'])
        self.assertEqual(report['automaticRetries'], 0)
        report, transport = self.run_report('second_length')
        self.assertEqual(len(transport.requests), 2)
        self.assertEqual(report['defectCase']['technicalReason'], 'stream_not_completed')
        self.assertIsNone(report['defectCase']['syntheticAnswer'])

    def test_clause_preserved_does_not_certify_free_text_meaning(self):
        report, transport = self.run_report('meaning')
        self.assertEqual(len(transport.requests), 2)
        self.assertEqual(report['technicalOutcome'], 'valid_structure_pending_semantic_review')
        self.assertTrue(report['defectCase']['clausePreserved'])
        self.assertEqual(report['qualityVerdict'], 'pending_review')

    def test_unverified_dependency_baseline_or_embedded_code_stops_before_network(self):
        file = self.project/'probe.py'
        file.write_bytes(TRANSPORT.read_bytes()+b'\nraise RuntimeError("MUST_NOT_EXECUTE")\n')
        with self.assertRaisesRegex(ValueError, 'probe_hash_mismatch'):
            probe.verified_probe(file)
        file.unlink(); file.symlink_to(TRANSPORT)
        with self.assertRaisesRegex(ValueError, 'invalid_probe_path'):
            probe.verified_probe(file)
        with patch.object(probe, 'GUARD_SOURCE', probe.GUARD_SOURCE+'\n'):
            with self.assertRaisesRegex(ValueError, 'embedded_guard_hash_mismatch'):
                probe.guard_module()
        file = self.project/'scripts/andrea/qualification_prompt.py'
        file.write_bytes(file.read_bytes()+b'\n')
        with patch.object(sys, 'argv', ['probe', str(self.project), '--probe-script', str(TRANSPORT)]), \
                patch.object(probe, 'run_check') as network, patch('sys.stdout', new_callable=io.StringIO) as output:
            self.assertEqual(probe.main(), 1)
        network.assert_not_called()
        self.assertIn('Nessuna richiesta inviata', output.getvalue())

    def test_actual_http_stream_two_requests_and_complete_answer_with_exact_prefix(self):
        transport = Transport(self.bundle)
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                transport.requests.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(200)
                self.send_header('Content-Type', 'application/x-ndjson')
                self.end_headers()
                self.wfile.write(transport.wire(len(transport.requests)))
            def log_message(self, *_args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch.object(self.p, 'BASE', f'http://127.0.0.1:{server.server_port}'):
                opener = self.p.build_opener(self.p.ProxyHandler({}), self.p.NoRedirect())
                report = probe.run_check(opener, self.modules, self.p, self.guard)
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)
        self.assertEqual(len(transport.requests), 2)
        self.assertTrue(report['canary']['nativeConformanceObserved'])
        self.assertTrue(report['defectCase']['clausePreserved'])
        text = json.loads(report['defectCase']['diagnosticModelJson'])['records']['F3']['text']
        self.assertIsNotNone(re.fullmatch(guard.source_clause(self.original)['pattern'], text))


if __name__ == '__main__':
    unittest.main()
