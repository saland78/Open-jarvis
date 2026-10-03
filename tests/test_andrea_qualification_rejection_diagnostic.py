"""Single diagnostic request: preserve evidence without accepting or repairing it."""
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PROBE_FILE = ROOT/'scripts/andrea/concise_qualification_text_probe.py'
spec = importlib.util.spec_from_file_location(
    'qualification_rejection_diagnostic', ROOT/'scripts/andrea/diagnose_qualification_rejection.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


class Response(io.BytesIO):
    pass


class Transport:
    def __init__(self, bundle, fault=None):
        self.requests = []
        texts = ['I libri pubblicati sono 17.', 'Vendite e royalty variano per periodo.',
                 'I valori aggiornati restano DATO NON VERIFICATO soltanto in questa nota; consultare dashboard o report indicando periodo, titolo e marketplace.',
                 'Copie e royalty: DATO ASSENTE nella fotografia storica.']
        self.records = {f['id']: {'text': text} | (
            {'contextDate': f['contextDate']} if 'contextDate' in f else {})
            for f, text in zip(bundle['plan']['facts'], texts)}
        self.fault = fault
        if fault == 'predicate':
            self.records['F3']['text'] = self.records['F3']['text'].replace('restano', 'sono')
        elif fault == 'meaning':
            self.records['F2']['text'] = 'Vendite e royalty NON variano per periodo.'
        elif fault == 'date':
            self.records['F3']['contextDate'] = '2030-12-31'
        self.raw = json.dumps({'records': self.records}, ensure_ascii=False)
        if fault == 'duplicate':
            self.raw = '{"records":{},"records":{}}'
        elif fault == 'invalid':
            self.raw = 'not JSON'

    def wire(self):
        events = [{'message': {'content': self.raw[:17]}, 'done': False},
                  {'message': {'content': self.raw[17:]}, 'done': False},
                  {'message': {'content': ''}, 'done': True, 'done_reason': 'stop',
                   'total_duration': 20_000_000, 'eval_duration': 12_000_000, 'eval_count': 131}]
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
        return Response(self.wire())


class QualificationRejectionDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.p = d.verified_probe(PROBE_FILE)
        for relative in self.p.EXPECTED:
            target = self.project/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/relative, target)
        self.modules = self.p.load_modules(self.project)
        self.bundle = self.modules.bridge.prepare(self.p.synthetic_note('adversarial'))

    def test_rejected_json_and_exact_failing_predicate_preserved_with_no_repair_or_writes(self):
        before = {str(f.relative_to(self.project)): f.read_bytes()
                  for f in self.project.rglob('*') if f.is_file()}
        bundle_before = copy.deepcopy(self.bundle)
        transport = Transport(self.bundle, 'predicate')
        report = d.diagnose(transport, self.modules, self.p)
        self.assertEqual(len(transport.requests), 1)
        body = transport.requests[0]
        self.assertEqual(body['messages'], self.bundle['messages'])
        self.assertEqual(body['format'], self.bundle['plan']['schema'])
        self.assertEqual(body['options'], {'temperature': 0.4, 'num_predict': 512, 'num_ctx': 4096})
        self.assertEqual(body['model'], self.p.MODEL)
        self.assertEqual(body['keep_alive'], '15m')
        self.assertIs(body['think'], False)
        self.assertNotIn('1000 euro', str(body))
        self.assertNotIn('99999', str(body))
        self.assertNotIn(self.p.CANDIDATE_INSTRUCTION, str(body))
        self.assertEqual(report['row']['technicalReason'], 'unsupported_value_update')
        self.assertEqual(report['diagnosticModelJson'], transport.raw)
        self.assertIsNone(report['row']['syntheticAnswer'])
        checks = report['predicateInspection']['records']
        self.assertEqual([(r['factId'], r['predicateGuardRejected']) for r in checks], [('F3', True), ('F4', False)])
        self.assertIn('restano', checks[0]['sourcePassage'])
        self.assertIn('sono', checks[0]['generatedText'])
        self.assertFalse(report['diagnosticTextIsAcceptedAnswer'])
        self.assertFalse(report['productionChangeAdopted'])
        self.assertEqual(report['previousPerformanceExperiment'], 'failed_not_reclassified')
        self.assertEqual(report['automaticRetries'], 0)
        self.assertEqual(self.bundle, bundle_before)
        after = {str(f.relative_to(self.project)): f.read_bytes()
                 for f in self.project.rglob('*') if f.is_file()}
        self.assertEqual(after, before)

    def test_accepted_new_sample_does_not_reclassify_old_failure_or_certify_meaning(self):
        for fault in (None, 'meaning'):
            with self.subTest(fault=fault):
                transport = Transport(self.bundle, fault)
                report = d.diagnose(transport, self.modules, self.p)
                self.assertEqual(len(transport.requests), 1)
                self.assertEqual(report['row']['technicalOutcome'], 'valid_structure_pending_semantic_review')
                self.assertEqual(report['row']['qualityVerdict'], 'pending_review')
                self.assertFalse(report['productionChangeAdopted'])
                self.assertEqual(report['previousPerformanceExperiment'], 'failed_not_reclassified')
                self.assertFalse(report['diagnosticTextIsAcceptedAnswer'])

    def test_invalid_json_and_other_guard_failure_are_distinct_from_predicate_inspection(self):
        for fault in ('duplicate', 'invalid', 'date'):
            with self.subTest(fault=fault):
                transport = Transport(self.bundle, fault)
                report = d.diagnose(transport, self.modules, self.p)
                self.assertEqual(len(transport.requests), 1)
                self.assertEqual(report['row']['technicalOutcome'], 'rejected')
                self.assertEqual(report['diagnosticModelJson'], transport.raw)
                if fault == 'date':
                    self.assertNotEqual(report['row']['technicalReason'], 'unsupported_value_update')
                    self.assertTrue(all(r['predicateGuardRejected'] is False for r in report['predicateInspection']['records']))
                else:
                    self.assertEqual(report['predicateInspection']['inspectionStatus'], 'invalid_json_or_records')

    def test_transport_errors_truncation_and_interrupt_cannot_trigger_second_request(self):
        for fault in ('length', 'eof', 'tools'):
            with self.subTest(fault=fault):
                transport = Transport(self.bundle, fault)
                report = d.diagnose(transport, self.modules, self.p)
                self.assertEqual(len(transport.requests), 1)
                self.assertEqual(report['row']['technicalOutcome'], 'rejected')
                self.assertIsNone(report['row']['syntheticAnswer'])
                self.assertEqual(report['automaticRetries'], 0)
        class Broken:
            calls = 0
            def open(self, request, timeout):
                self.calls += 1
                raise OSError('PRIVATE_ERROR_CONTENT')
        transport = Broken()
        report = d.diagnose(transport, self.modules, self.p)
        self.assertEqual(transport.calls, 1)
        self.assertIsNone(report['diagnosticModelJson'])
        self.assertNotIn('PRIVATE_ERROR_CONTENT', json.dumps(report))
        with patch.object(self.p, 'stream_probe', side_effect=KeyboardInterrupt) as call:
            report = d.diagnose(transport, self.modules, self.p)
        self.assertEqual(call.call_count, 1)
        self.assertTrue(report['interrupted'])
        self.assertEqual(report['row']['status'], 'cancelled')
        self.assertIsNone(report['diagnosticModelJson'])

    def test_unverified_dependency_or_production_baseline_stops_before_any_network(self):
        probe = self.project/'probe.py'
        probe.write_bytes(PROBE_FILE.read_bytes()+b'\nraise RuntimeError("UNVERIFIED_EXEC")\n')
        with self.assertRaisesRegex(ValueError, 'probe_hash_mismatch'):
            d.verified_probe(probe)
        probe.unlink()
        probe.symlink_to(PROBE_FILE)
        with self.assertRaisesRegex(ValueError, 'invalid_probe_path'):
            d.verified_probe(probe)
        file = self.project/'scripts/andrea/qualification_prompt.py'
        file.write_bytes(file.read_bytes()+b'\n')
        with patch.object(sys, 'argv', ['diagnose', str(self.project), '--probe-script', str(PROBE_FILE)]), \
                patch.object(d, 'diagnose') as request, patch('sys.stdout', new_callable=io.StringIO) as output:
            self.assertEqual(d.main(), 1)
        request.assert_not_called()
        self.assertIn('Nessuna richiesta inviata', output.getvalue())

    def test_real_http_stream_one_request_with_rejected_raw_kept(self):
        transport = Transport(self.bundle, 'predicate')
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers['Content-Length'])
                transport.requests.append(json.loads(self.rfile.read(length)))
                self.send_response(200)
                self.send_header('Content-Type', 'application/x-ndjson')
                self.end_headers()
                self.wfile.write(transport.wire())
            def log_message(self, *_):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch.object(self.p, 'BASE', f'http://127.0.0.1:{server.server_port}'):
                opener = self.p.build_opener(self.p.ProxyHandler({}), self.p.NoRedirect())
                report = d.diagnose(opener, self.modules, self.p)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertEqual(len(transport.requests), 1)
        self.assertEqual(report['row']['status'], 'completed')
        self.assertEqual(report['row']['technicalReason'], 'unsupported_value_update')
        self.assertEqual(report['diagnosticModelJson'], transport.raw)


if __name__ == '__main__':
    unittest.main()
