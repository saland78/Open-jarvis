"""Finite HTTP probes and unchanged production guards; synthetic sources only."""
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.request import build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'concise_probe', ROOT/'scripts/andrea/concise_qualification_text_probe.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class Response(io.BytesIO):
    status = 200


class Transport:
    def __init__(self, modules, fault=None):
        self.modules, self.fault, self.requests = modules, fault, []

    def wire(self, body):
        self.requests.append(body)
        number = len(self.requests)
        case, variant = p.ORDER[number-1]
        bundle = self.modules.bridge.prepare(p.synthetic_note(case))
        amount = '3' if case == 'ordinary' else '17'
        predicate = 'sono' if case == 'ordinary' else 'restano'
        texts = [f'I libri pubblicati sono {amount}.',
                 'Vendite e royalty variano per periodo.',
                 f'I valori aggiornati {predicate} DATO NON VERIFICATO in questa nota; consultare dashboard o report indicando periodo, titolo e marketplace.',
                 'Copie e royalty sono DATO ASSENTE nella fotografia storica.']
        records = {fact['id']: {'text': text} | (
            {'contextDate': fact['contextDate']} if 'contextDate' in fact else {})
            for fact, text in zip(bundle['plan']['facts'], texts)}
        if self.fault == 'date' and number == 2:
            records['F3']['contextDate'] = '2030-12-31'
        if self.fault == 'meaning' and number == 2:
            records['F2']['text'] = 'Vendite e royalty NON variano per periodo.'
        if self.fault == 'count' and number == 2:
            records['F1']['text'] = 'I libri pubblicati sono 1000.'
        if self.fault == 'missing_fact' and number == 2:
            del records['F4']
        if self.fault == 'qualification' and number == 2:
            records['F3']['text'] = 'I valori aggiornati sono DATO ASSENTE nella dashboard.'
        if self.fault == 'predicate' and number == 2:
            records['F3']['text'] = 'Vendite e royalty sono state aggiornate: DATO NON VERIFICATO.'
        raw = json.dumps({'records': records}, ensure_ascii=False)
        events = [{'message': {'content': raw[:11]}, 'done': False},
                  {'message': {'content': raw[11:]}, 'done': False},
                  {'message': {'content': ''}, 'done': True, 'done_reason': 'stop',
                   'total_duration': 30_000_000, 'load_duration': 1_000_000,
                   'prompt_eval_duration': 4_000_000,
                   'eval_duration': 20_000_000 if variant == 'production' else 15_000_000,
                   'prompt_eval_count': 800, 'prompt_eval_cached_count': 0,
                   'eval_count': 120 if variant == 'production' else 100}]
        if number == 2:
            if self.fault == 'length':
                events[-1]['done_reason'] = 'length'
            elif self.fault == 'eof':
                events.pop()
            elif self.fault == 'tools':
                events[0]['message']['tool_calls'] = [{'name': 'fake'}]
            elif self.fault == 'metrics':
                events[-1]['eval_count'] = None
            elif self.fault == 'duplicate':
                return b'{"done":false,"done":true}\n'
        return b''.join(json.dumps(event).encode()+b'\n' for event in events)

    def open(self, request, timeout):
        assert request.full_url == 'http://127.0.0.1:11434/api/chat'
        assert request.get_method() == 'POST' and timeout == 90
        return Response(self.wire(json.loads(request.data)))


class ConciseQualificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        for relative in p.EXPECTED:
            target = self.project/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/relative, target)
        self.modules = p.load_modules(self.project)

    def test_candidate_changes_only_system_style_not_any_fact_schema_or_route(self):
        for case in ('ordinary', 'adversarial'):
            bundle = self.modules.bridge.prepare(p.synthetic_note(case))
            before = copy.deepcopy(bundle)
            candidate = p.candidate_messages(bundle)
            self.assertEqual(candidate[1], bundle['messages'][1])
            self.assertEqual(candidate[0]['content'],
                             bundle['messages'][0]['content']+p.CANDIDATE_INSTRUCTION)
            self.assertEqual(bundle, before)
            self.assertNotIn('1000 euro', str(candidate))
            self.assertNotIn('2030-12-31', str(candidate))
            self.assertNotIn('DATO ASSENTE', p.CANDIDATE_INSTRUCTION)
            for alteration in ('wrong_kind', 'reordered', 'missing'):
                bad = copy.deepcopy(bundle)
                if alteration == 'wrong_kind':
                    bad['kind'] = 'book'
                elif alteration == 'reordered':
                    bad['plan']['facts'].reverse()
                else:
                    bad['plan']['facts'].pop()
                with self.assertRaises(ValueError):
                    p.candidate_messages(bad)

    def test_exactly_four_posts_same_full_schema_budget_and_no_files_written(self):
        before = {path.relative_to(self.project): path.read_bytes()
                  for path in self.project.rglob('*') if path.is_file()}
        transport = Transport(self.modules)
        report = p.collect(transport, self.modules)
        self.assertEqual(len(transport.requests), 4)
        self.assertEqual([(r['case'], r['variant']) for r in report['rows']], list(p.ORDER))
        for body, (case, variant) in zip(transport.requests, p.ORDER):
            bundle = self.modules.bridge.prepare(p.synthetic_note(case))
            self.assertEqual(body['format'], bundle['plan']['schema'])
            self.assertEqual(body['model'], p.MODEL)
            self.assertEqual(body['keep_alive'], '15m')
            self.assertIs(body['think'], False)
            self.assertEqual(body['options'],
                             {'temperature': 0.4, 'num_predict': 512, 'num_ctx': 4096})
            self.assertNotIn('tools', body)
        self.assertTrue(report['comparison']['allExploratoryGatesMet'])
        self.assertEqual(report['comparison']['qualityVerdict'], 'pending_review')
        self.assertTrue(report['comparison']['decision'].startswith('not_adopted'))
        self.assertFalse(report['vaultRead'])
        self.assertFalse(report['serverPathMeasured'])
        after = {path.relative_to(self.project): path.read_bytes()
                 for path in self.project.rglob('*') if path.is_file()}
        self.assertEqual(before, after)
        self.assertTrue(all('modelAnswer' not in row for row in report['rows']))
        self.assertTrue(all('[N1]' in row['syntheticAnswer'] for row in report['rows']))

    def test_existing_guard_failures_are_kept_and_never_retried(self):
        for fault in ('date', 'count', 'missing_fact', 'qualification', 'predicate'):
            with self.subTest(fault=fault):
                transport = Transport(self.modules, fault)
                report = p.collect(transport, self.modules)
                self.assertEqual(len(transport.requests), 4)
                self.assertEqual(report['rows'][1]['technicalOutcome'], 'rejected')
                self.assertIsNone(report['rows'][1]['syntheticAnswer'])
                self.assertFalse(report['comparison']['allExploratoryGatesMet'])

    def test_technical_acceptance_can_still_be_semantically_wrong(self):
        report = p.collect(Transport(self.modules, 'meaning'), self.modules)
        row = report['rows'][1]
        self.assertEqual(row['technicalOutcome'], 'valid_structure_pending_semantic_review')
        self.assertIn('NON variano', row['syntheticAnswer'])
        self.assertEqual(row['qualityVerdict'], 'pending_review')
        self.assertTrue(report['comparison']['decision'].startswith('not_adopted'))

    def test_transport_faults_and_missing_counters_do_not_pass_exploratory_gate(self):
        for fault in ('length', 'eof', 'tools', 'duplicate', 'metrics'):
            with self.subTest(fault=fault):
                transport = Transport(self.modules, fault)
                report = p.collect(transport, self.modules)
                self.assertEqual(len(transport.requests), 4)
                self.assertFalse(report['comparison']['allExploratoryGatesMet'])
                self.assertEqual(report['automaticRetries'], 0)

    def test_failed_connection_does_not_issue_retries(self):
        class Broken:
            calls = 0
            def open(self, request, timeout):
                self.calls += 1
                raise OSError('arbitrary private error')
        transport = Broken()
        report = p.collect(transport, self.modules)
        self.assertEqual(transport.calls, 4)
        self.assertTrue(all(row['status'] == 'error' for row in report['rows']))
        self.assertNotIn('arbitrary private error', json.dumps(report))
        self.assertFalse(report['comparison']['allExploratoryGatesMet'])

    def test_rounding_cannot_turn_a_failed_threshold_into_a_pass(self):
        report = p.collect(Transport(self.modules), self.modules)
        candidate = report['rows'][1]
        candidate['native']['eval_count'] = 108.0001
        comparison = p.comparison(report['rows'])
        self.assertEqual(comparison['pairs'][0]['nativeTokenReductionPercent'], 10.0)
        self.assertFalse(comparison['pairs'][0]['exploratoryGateMet'])

    def test_native_fields_reject_booleans_floats_and_unsafe_integer_counters(self):
        for bad in (True, 1.5, -1, 2**53):
            native = p.native_metrics({'eval_count': bad, 'eval_duration': bad})
            self.assertIsNone(native['eval_count'])
            self.assertIsNone(native['evalMs'])
            self.assertIsNone(native['evalTokensPerSecond'])
        native = p.native_metrics({'eval_count': 0, 'eval_duration': 0})
        self.assertEqual(native['eval_count'], 0)
        self.assertEqual(native['evalMs'], 0)
        self.assertIsNone(native['evalTokensPerSecond'])

    def test_stream_limits_deadline_and_malformed_content_fail_without_text(self):
        class Raw:
            def __init__(self, data):
                self.data = data
            def open(self, request, timeout):
                return Response(self.data)
        bundle = self.modules.bridge.prepare(p.synthetic_note('ordinary'))
        for wire in (b'x'*262145,
                     b'{"message":{"content":42},"done":true,"done_reason":"stop"}\n',
                     (b'['*1200+b']'*1200+b'\n')):
            row = p.stream_probe(Raw(wire), bundle['messages'], bundle['plan']['schema'])
            self.assertEqual(row['status'], 'error')
            self.assertIsNone(row['modelAnswer'])
        ticks = iter((0, 91, 92))
        row = p.stream_probe(Raw(b''), bundle['messages'], bundle['plan']['schema'],
                             clock=lambda: next(ticks))
        self.assertEqual(row['status'], 'error')

    def test_interrupt_keeps_partial_results_and_stops_without_retry(self):
        transport = Transport(self.modules)
        calls = []
        def interrupted(opener, messages, schema):
            calls.append(1)
            if len(calls) == 2:
                raise KeyboardInterrupt
            return p.stream_probe(opener, messages, schema)
        report = p.collect(transport, self.modules, probe=interrupted)
        self.assertEqual(len(calls), 2)
        self.assertTrue(report['interrupted'])
        self.assertEqual(report['rows'][-1]['status'], 'cancelled')
        self.assertFalse(report['comparison']['allExploratoryGatesMet'])

    def test_baseline_hashes_and_symlinks_refuse_before_transport(self):
        file = self.project/'scripts/andrea/qualification_prompt.py'
        file.write_bytes(file.read_bytes()+b'\n')
        with self.assertRaisesRegex(ValueError, 'baseline_mismatch'):
            p.load_modules(self.project)
        shutil.copyfile(ROOT/'scripts/andrea/qualification_prompt.py', file)
        file.unlink()
        file.symlink_to(ROOT/'scripts/andrea/qualification_prompt.py')
        with self.assertRaisesRegex(ValueError, 'symlink_in_baseline'):
            p.load_modules(self.project)

    def test_real_local_ndjson_http_series_uses_production_modules(self):
        transport = Transport(self.modules)
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.assert_path = self.path
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                wire = transport.wire(body)
                self.send_response(200)
                self.send_header('Content-Type', 'application/x-ndjson')
                self.send_header('Content-Length', str(len(wire)))
                self.end_headers()
                self.wfile.write(wire)
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            opener = build_opener(ProxyHandler({}), p.NoRedirect())
            with patch.object(p, 'BASE', f'http://127.0.0.1:{server.server_port}'):
                report = p.collect(opener, self.modules)
            self.assertEqual(len(transport.requests), 4)
            self.assertTrue(all(row['status'] == 'completed' for row in report['rows']))
            self.assertTrue(report['comparison']['allExploratoryGatesMet'])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(2)


if __name__ == '__main__':
    unittest.main()
