"""One native request, exact complete clause, retained failures and no writes."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch

import qualification_sentence_fix_probe as probe
from test_andrea_qualification_clause_guard import response
from test_andrea_qualification_sentence_guard import OBSERVED

from andrea_qualification_baseline import source as baseline_source

ROOT = Path(__file__).resolve().parents[1]
TRANSPORT = ROOT/'scripts/andrea/concise_qualification_text_probe.py'


class Transport:
    def __init__(self, bundle, fault=None):
        self.requests = []
        self.fault = fault
        self.raw = response(bundle, text=bundle['qualificationSentence']['source_text'])
        if fault == 'omission':
            self.raw = response(bundle, text=OBSERVED)
        elif fault == 'meaning':
            value = json.loads(self.raw)
            value['records']['F2']['text'] = 'Vendite e royalty NON variano per periodo.'
            self.raw = json.dumps(value)
        elif fault == 'duplicate':
            self.raw = '{"records":{},"records":{}}'

    def wire(self):
        events = [{'message': {'content': self.raw[:17]}, 'done': False},
                  {'message': {'content': self.raw[17:]}, 'done': False},
                  {'message': {'content': ''}, 'done': True, 'done_reason': 'stop',
                   'eval_duration': 10_000_000, 'eval_count': 20}]
        if self.fault == 'length':
            events[-1]['done_reason'] = 'length'
        elif self.fault == 'eof':
            events.pop()
        elif self.fault == 'tools':
            events[0]['message']['tool_calls'] = [{'name': 'unwanted'}]
        return b''.join(json.dumps(e).encode()+b'\n' for e in events)

    def open(self, request, timeout):
        self.requests.append(json.loads(request.data))
        assert request.full_url == 'http://127.0.0.1:11434/api/chat' and timeout == 90
        return io.BytesIO(self.wire())


class QualificationSentenceFixProbeTests(unittest.TestCase):
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
        self.bundle = self.guard.protect(self.modules.bridge.prepare(self.p.synthetic_note('adversarial')))

    def run_report(self, fault=None):
        transport = Transport(self.bundle, fault)
        return probe.run_check(transport, self.modules, self.p, self.guard), transport

    def test_embedded_source_matches_native_const_one_request_and_no_project_writes(self):
        for name, code, checksum, file in [('prefix', probe.PREFIX_SOURCE, probe.PREFIX_SHA256, 'qualification_clause_guard.py'),
                                          ('sentence', probe.SENTENCE_SOURCE, probe.SENTENCE_SHA256, 'qualification_sentence_guard.py')]:
            with self.subTest(name=name):
                self.assertEqual(code, (ROOT/'scripts/andrea'/file).read_text())
                self.assertEqual(checksum, hashlib.sha256(code.encode()).hexdigest())
        prior = sys.modules.get('qualification_clause_guard')
        probe.guard_module()
        self.assertIs(sys.modules.get('qualification_clause_guard'), prior)
        before = {str(f.relative_to(self.project)): f.read_bytes() for f in self.project.rglob('*') if f.is_file()}
        report, transport = self.run_report()
        self.assertEqual(len(transport.requests), 1)
        self.assertEqual(report['plannedRequests'], 1)
        self.assertEqual(report['attemptedRequests'], 1)
        self.assertEqual(report['automaticRetries'], 0)
        request = transport.requests[0]
        self.assertEqual(request['format'], self.bundle['plan']['schema'])
        field = request['format']['properties']['records']['properties']['F3']['properties']['text']
        self.assertEqual(field['const'], self.bundle['qualificationSentence']['source_text'])
        self.assertNotIn('pattern', field)
        self.assertEqual(request['messages'], self.bundle['messages'])
        self.assertNotIn(self.p.CANDIDATE_INSTRUCTION, str(request))
        self.assertNotIn('1000 euro', str(request))
        self.assertNotIn('99999', str(request))
        self.assertEqual(request['options'], {'temperature': 0.4, 'num_predict': 512, 'num_ctx': 4096})
        self.assertEqual(request['model'], self.p.MODEL)
        self.assertEqual(request['keep_alive'], '15m')
        self.assertIs(request['think'], False)
        self.assertEqual(report['technicalOutcome'], 'valid_structure_pending_semantic_review')
        self.assertEqual(report['qualityVerdict'], 'pending_review')
        self.assertEqual(report['literalField'], 'F3')
        self.assertEqual(report['modelSynthesisFields'], ['F1', 'F2', 'F4'])
        self.assertTrue(report['row']['consultationPreserved'])
        self.assertTrue(report['row']['sentencePreserved'])
        self.assertEqual(report['row']['literalSourceFactIds'], ['F3'])
        self.assertEqual(report['row']['diagnosticModelJson'], transport.raw)
        self.assertFalse(report['row']['generatedTextRepaired'])
        self.assertFalse(report['productionChangeAdopted'])
        self.assertFalse(report['productionFilesChanged'])
        self.assertFalse(report['vaultRead'])
        self.assertEqual(report['previousPrefixExperiment'], 'semantic_failure_consultation_omitted')
        after = {str(f.relative_to(self.project)): f.read_bytes() for f in self.project.rglob('*') if f.is_file()}
        self.assertEqual(before, after)

    def test_observed_failed_sample_retained_and_independently_rejected_without_second_request(self):
        report, transport = self.run_report('omission')
        self.assertEqual(len(transport.requests), 1)
        row = report['row']
        self.assertEqual(row['technicalOutcome'], 'rejected')
        self.assertEqual(row['technicalReason'], 'qualification_sentence_missing_or_changed')
        self.assertEqual(row['diagnosticModelJson'], transport.raw)
        self.assertIsNone(row['syntheticAnswer'])
        self.assertFalse(row['sentencePreserved'])
        self.assertFalse(row['consultationPreserved'])
        self.assertFalse(row['generatedTextRepaired'])

    def test_other_meaning_not_certified_by_the_literal_field(self):
        report, transport = self.run_report('meaning')
        self.assertEqual(len(transport.requests), 1)
        self.assertTrue(report['row']['sentencePreserved'])
        self.assertTrue(report['row']['consultationPreserved'])
        self.assertEqual(report['qualityVerdict'], 'pending_review')

    def test_protocol_errors_partial_stream_and_interrupt_do_not_retry_or_repair(self):
        for fault in ('duplicate', 'length', 'eof', 'tools'):
            with self.subTest(fault=fault):
                report, transport = self.run_report(fault)
                self.assertEqual(len(transport.requests), 1)
                self.assertEqual(report['technicalOutcome'], 'rejected')
                self.assertIsNone(report['row']['syntheticAnswer'])
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
        self.assertEqual(report['row']['status'], 'cancelled')

    def test_hashes_registry_restoration_and_baseline_mismatch_stop_before_network(self):
        file = self.project/'probe.py'
        file.write_bytes(TRANSPORT.read_bytes()+b'\nraise RuntimeError("MUST_NOT_EXECUTE")\n')
        with self.assertRaisesRegex(ValueError, 'probe_hash_mismatch'):
            probe.verified_probe(file)
        file.unlink(); file.symlink_to(TRANSPORT)
        with self.assertRaisesRegex(ValueError, 'invalid_probe_path'):
            probe.verified_probe(file)
        for field in ('PREFIX_SOURCE', 'SENTENCE_SOURCE'):
            with patch.object(probe, field, getattr(probe, field)+'\n'):
                with self.assertRaisesRegex(ValueError, 'embedded_guard_hash_mismatch'):
                    probe.guard_module()
        original = self.project/'scripts/andrea/qualification_prompt.py'
        original.write_bytes(original.read_bytes()+b'\n')
        with patch.object(sys, 'argv', ['probe', str(self.project), '--probe-script', str(TRANSPORT)]), \
                patch.object(probe, 'run_check') as network, patch('sys.stdout', new_callable=io.StringIO) as output:
            self.assertEqual(probe.main(), 1)
        network.assert_not_called()
        self.assertIn('Nessuna richiesta inviata', output.getvalue())

    def test_actual_http_stream_single_request_retains_complete_source_qualification(self):
        transport = Transport(self.bundle)
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                transport.requests.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(200)
                self.send_header('Content-Type', 'application/x-ndjson')
                self.end_headers()
                self.wfile.write(transport.wire())
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
        self.assertEqual(len(transport.requests), 1)
        self.assertEqual(report['technicalOutcome'], 'valid_structure_pending_semantic_review')
        self.assertTrue(report['row']['consultationPreserved'])
        self.assertEqual(json.loads(report['row']['diagnosticModelJson'])['records']['F3']['text'], self.bundle['qualificationSentence']['source_text'])


if __name__ == '__main__':
    unittest.main()
