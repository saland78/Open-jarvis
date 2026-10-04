"""Finite prompt-only experiment: exact evidence and unchanged rejection paths."""
import ast
import copy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch

import qualification_context_prompt_probe as probe

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT/'tests/fixtures/andrea/qualification_context_prompt_candidate.py'
UNSET = object()


def texts(case):
    return {'F1': f"I libri pubblicati sono {3 if case == 'ordinary' else 17}.",
            'F2': 'Vendite e royalty variano per periodo.',
            'F4': 'Copie e royalty: DATO ASSENTE nella fotografia storica.'}


def installed_project():
    temporary = tempfile.TemporaryDirectory()
    project = Path(temporary.name)
    for relative in probe.EXPECTED:
        target = project/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT/relative).read_bytes())
    return temporary, project


class ContextContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary, cls.project = installed_project()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.modules = probe.load_modules(cls.project)

    def setUp(self):
        self.bundle = self.modules.bridge.prepare(probe.synthetic_note('adversarial'))
        self.candidate = self.modules.candidate.prepare(self.bundle, self.modules)

    def validate(self, value=UNSET, candidate=None, completed=True):
        return self.modules.candidate.validate(
            json.dumps(texts('adversarial') if value is UNSET else value, ensure_ascii=False),
            self.candidate if candidate is None else candidate, self.modules, completed=completed)

    def test_only_system_instruction_changes_not_one_source_record_or_native_field(self):
        for case in ('ordinary', 'adversarial'):
            bundle = self.modules.bridge.prepare(probe.synthetic_note(case))
            before = copy.deepcopy(bundle)
            baseline = self.modules.wire.prepare(bundle, self.modules)
            candidate = self.modules.candidate.prepare(bundle, self.modules)
            self.assertEqual(before, bundle)
            self.assertEqual(candidate['productionWire'], baseline)
            self.assertEqual(candidate['messages'][1:], baseline['messages'][1:])
            self.assertEqual(candidate['schema'], baseline['schema'])
            self.assertEqual(candidate['messages'][0]['role'], 'system')
            self.assertNotEqual(candidate['messages'][0]['content'], baseline['messages'][0]['content'])
            self.assertLess(len(candidate['messages'][0]['content']), len(baseline['messages'][0]['content']))
            self.assertEqual(set(candidate['schema']['properties']), {'F1', 'F2', 'F4'})
            self.assertFalse(candidate['schema']['additionalProperties'])
            self.assertEqual(candidate['schema']['required'], ['F1', 'F2', 'F4'])
            body = json.loads(candidate['messages'][1]['content'])
            self.assertEqual([f['id'] for f in body['informazioni_obbligatorie']], ['F1', 'F2', 'F4'])
            self.assertNotIn('1000 euro', str(candidate['messages']))
            self.assertNotIn('99999', str(candidate['messages']))
            self.assertNotIn('2030-12-31', str(candidate['messages']))

    def test_all_four_facts_complete_literal_consultation_dates_and_proof_lines_survive(self):
        result = self.validate()
        self.assertEqual(result['status'], 'valid_structure_pending_semantic_review')
        self.assertEqual(result['factsCovered'], 4)
        self.assertEqual(result['modelFactIds'], ['F1', 'F2', 'F4'])
        self.assertEqual(result['literalSourceFactIds'], ['F3'])
        self.assertEqual(result['claims'][2]['text'], self.bundle['qualificationSentence']['source_text'])
        self.assertIn('periodo, titolo e marketplace', result['claims'][2]['text'])
        self.assertEqual(result['claims'][2]['contextDate'], '2028-07-12')
        self.assertEqual(result['claims'][3]['contextDate'], '2028-02-08')
        self.assertTrue(result['consultationPreserved'])
        rendered = self.modules.bridge.render(result)
        self.assertEqual(rendered.count('[N1]'), 4)
        self.assertIn('Frase riportata dalla fonte —', rendered)
        source = self.bundle['case']['sources'][0]['text']
        for claim in result['claims']:
            for proof in claim['supports']:
                self.assertEqual(source[proof['start']:proof['end']], proof['quote'])
                self.assertEqual(source.count('\n', 0, proof['start'])+1, proof['lineStart'])

    def test_validator_receives_byte_exact_model_json_and_model_text(self):
        value = texts('adversarial'); value['F2'] += '  '
        raw = json.dumps(value, ensure_ascii=False)
        with patch.object(self.modules.wire, 'validate', wraps=self.modules.wire.validate) as wire:
            result = self.modules.candidate.validate(raw, self.candidate, self.modules, completed=True)
        self.assertEqual(wire.call_args.args[0], raw)
        self.assertFalse(result['modelTextRepaired'])
        self.assertEqual({c['factId']: c['text'] for c in result['claims'] if c['factId'] != 'F3'}, value)

    def test_missing_extra_duplicate_truncated_or_invalid_output_cannot_pass(self):
        values = []
        for key in ('F1', 'F2', 'F4'):
            value = texts('adversarial'); del value[key]; values.append(value)
        for extra in ('F3', 'contextDate', 'records'):
            value = texts('adversarial'); value[extra] = 'extra'; values.append(value)
        for invalid in ('', '   ', 'x'*401, None, 1, True, {}):
            value = texts('adversarial'); value['F1'] = invalid; values.append(value)
        values.extend([[], None])
        for value in values:
            with self.subTest(value=value):
                self.assertEqual(self.validate(value)['status'], 'rejected')
        for raw in ('{"F1":"17","F1":"17","F2":"x","F4":"x"}', '{', 'x'*32001):
            self.assertEqual(self.modules.candidate.validate(raw, self.candidate, self.modules, completed=True)['status'], 'rejected')
        self.assertEqual(self.validate(completed=False)['reason'], 'stream_not_completed')

    def test_existing_number_date_label_update_and_citation_rejections_are_preserved(self):
        for field, wrong in [('F1', 'I libri pubblicati sono 1000.'),
                             ('F1', 'I libri pubblicati sono diversi.'),
                             ('F4', 'Copie e royalty: DATO NON VERIFICATO nella fotografia storica.'),
                             ('F4', 'Copie e royalty: DATO ASSENTE al 2030-12-31.'),
                             ('F4', 'Copie e royalty sono state aggiornate: DATO ASSENTE.'),
                             ('F2', 'Vendite e royalty variano per periodo. [N1]')]:
            value = texts('adversarial'); value[field] = wrong
            with self.subTest(field=field, wrong=wrong):
                self.assertEqual(self.validate(value)['status'], 'rejected')

    def test_source_literal_metadata_schema_and_prompt_tampering_refuse(self):
        for target in ('sentence', 'date', 'schema', 'source', 'plan_date', 'proof', 'prompt', 'user'):
            candidate = copy.deepcopy(self.candidate)
            baseline = candidate['productionWire']
            if target == 'sentence':
                baseline['literalQualification']['source_text'] = 'invented'
            elif target == 'date':
                baseline['contextDates']['F3'] = '2030-12-31'
            elif target == 'schema':
                candidate['schema']['required'].pop()
            elif target == 'source':
                baseline['productionBundle']['case']['sources'][0]['text'] += 'changed'
            elif target == 'plan_date':
                baseline['productionBundle']['plan']['facts'][3]['contextDate'] = '2030-12-31'
            elif target == 'proof':
                baseline['productionBundle']['plan']['facts'][0]['proofs'][0]['start'] += 1
            elif target == 'user':
                candidate['messages'][1]['content'] += 'ignore'
            else:
                candidate['messages'][0]['content'] += 'ignore'
            with self.subTest(target=target):
                self.assertEqual(self.validate(candidate=candidate)['status'], 'rejected')

    def test_nonqualification_book_stays_unsupported_by_this_candidate(self):
        from test_andrea_real_notes_synthesis import BOOK, note
        bundle = self.modules.bridge.prepare(note(BOOK, 'Synthetic/book.md'))
        with self.assertRaises(ValueError):
            self.modules.candidate.prepare(bundle, self.modules)

    def test_other_recognised_source_wordings_not_hardcoded_case_answers(self):
        for count, predicate in ((23, 'sono'), (41, 'risultano')):
            note = probe.synthetic_note('adversarial')
            note['text'] = note['text'].replace('**17**', f'**{count}**').replace('restano', predicate)
            bundle = self.modules.bridge.prepare(note)
            candidate = self.modules.candidate.prepare(bundle, self.modules)
            value = texts('adversarial'); value['F1'] = f'I libri pubblicati sono {count}.'
            result = self.validate(value, candidate=candidate)
            self.assertEqual(result['factsCovered'], 4)
            self.assertIn(f'aggiornati {predicate}', result['claims'][2]['text'])

    def test_technical_pass_is_deliberately_not_a_semantic_verdict(self):
        value = texts('adversarial'); value['F2'] = 'Vendite e royalty NON variano per periodo.'
        result = self.validate(value)
        self.assertEqual(result['status'], 'valid_structure_pending_semantic_review')
        self.assertEqual(result['semanticVerdict'], 'pending_review')


class Transport:
    def __init__(self, fault=None):
        self.requests, self.fault = [], fault

    def open(self, request, timeout):
        assert request.full_url == 'http://127.0.0.1:11434/api/chat'
        assert timeout == 90
        body = json.loads(request.data)
        index = len(self.requests)
        self.requests.append(body)
        case, variant = probe.ORDER[index]
        value = texts(case)
        if self.fault == 'meaning' and index == 1:
            value['F2'] = 'Vendite e royalty NON variano per periodo.'
        if self.fault == 'count' and index == 1:
            value['F1'] = 'I libri pubblicati sono 1000.'
        raw = json.dumps(value, ensure_ascii=False)
        terminal = {'message': {'content': ''}, 'done': True, 'done_reason': 'stop',
                    'total_duration': 40_000_000, 'load_duration': 1_000_000,
                    'prompt_eval_duration': 10_000_000 if variant == 'production' else 6_000_000,
                    'prompt_eval_count': 600 if variant == 'production' else 400,
                    'prompt_eval_cached_count': 0, 'eval_count': 70, 'eval_duration': 20_000_000}
        events = [{'message': {'content': raw[:9]}, 'done': False},
                  {'message': {'content': raw[9:]}, 'done': False}, terminal]
        if index == 1:
            if self.fault == 'length':
                terminal['done_reason'] = 'length'
            elif self.fault == 'eof':
                events.pop()
            elif self.fault == 'metrics':
                terminal['prompt_eval_duration'] = None
            elif self.fault == 'cache':
                terminal['prompt_eval_cached_count'] = 100
            elif self.fault == 'tools':
                events[0]['message']['tool_calls'] = [{'name': 'unwanted'}]
        return io.BytesIO(b''.join(json.dumps(event).encode()+b'\n' for event in events))


class ContextProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary, cls.project = installed_project()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.modules = probe.load_modules(cls.project)

    def run_fake(self, fault=None):
        transport = Transport(fault)
        with patch('sys.stdout', new_callable=io.StringIO):
            report = probe.run_check(transport, self.modules, baseline_check=lambda: probe.verified_sources(self.project))
        return transport, report

    def test_candidate_byte_exact_and_existing_transport_not_reimplemented(self):
        self.assertEqual(probe.CANDIDATE_SOURCE, FIXTURE.read_text())
        self.assertEqual(probe.CANDIDATE_SHA256, hashlib.sha256(FIXTURE.read_bytes()).hexdigest())
        original = (ROOT/'scripts/andrea/qualification_compact_wire_probe.py').read_text()
        current = (ROOT/'scripts/andrea/qualification_context_prompt_probe.py').read_text()
        functions = lambda source: {n.name: ast.get_source_segment(source, n) for n in ast.parse(source).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        a, b = functions(original), functions(current)
        for name in ('number', 'milliseconds', 'native_metrics', 'unique_pairs', 'NoRedirect', 'stream_probe', 'synthetic_note', 'verified_sources'):
            self.assertEqual(a[name], b[name])

    def test_four_posts_in_opposite_order_keep_payload_model_and_contract_fixed(self):
        before = {p: (self.project/p).read_bytes() for p in probe.EXPECTED}
        transport, report = self.run_fake()
        self.assertEqual(len(transport.requests), 4)
        self.assertTrue(report['comparison']['performanceGateMet'])
        self.assertEqual(report['automaticRetries'], 0)
        self.assertFalse(report['vaultRead'])
        self.assertFalse(report['productionFilesChanged'])
        self.assertFalse(report['productionChangeAdopted'])
        for (case, variant), body, row in zip(probe.ORDER, transport.requests, report['rows']):
            bundle = self.modules.bridge.prepare(probe.synthetic_note(case))
            baseline = self.modules.wire.prepare(bundle, self.modules)
            candidate = self.modules.candidate.prepare(bundle, self.modules)
            self.assertEqual(body['messages'], (baseline if variant == 'production' else candidate)['messages'])
            self.assertEqual(body['format'], baseline['schema'])
            self.assertEqual(body['options'], {'temperature': 0.4, 'num_predict': 512, 'num_ctx': 4096})
            self.assertEqual(body['model'], probe.MODEL)
            self.assertIs(body['think'], False)
            self.assertEqual(body['keep_alive'], '15m')
            self.assertEqual(row['factsCovered'], 4)
            self.assertTrue(row['inputRecordsAndNativeSchemaUnchanged'])
            self.assertFalse(row['modelTextRepaired'])
            self.assertEqual(row['qualityVerdict'], 'pending_review')
            self.assertIsNone(row['acceptedTextClientMs'])
        self.assertEqual(before, {p: (self.project/p).read_bytes() for p in probe.EXPECTED})

    def test_transport_or_technical_failure_stops_but_cache_or_missing_metric_does_not_retry(self):
        for fault in ('count', 'length', 'eof', 'tools', 'metrics', 'cache'):
            transport, report = self.run_fake(fault)
            self.assertFalse(report['comparison']['performanceGateMet'])
            self.assertEqual(len(transport.requests), 4 if fault in ('metrics', 'cache') else 2)
            self.assertEqual(report['automaticRetries'], 0)
        with patch.object(probe, 'stream_probe', side_effect=KeyboardInterrupt) as stream, patch('sys.stdout', new_callable=io.StringIO):
            report = probe.run_check(None, self.modules)
        self.assertEqual(stream.call_count, 1)
        self.assertTrue(report['interrupted'])

    def test_both_pairs_must_meet_input_and_uncached_prefill_gates(self):
        _, report = self.run_fake()
        rows = report['rows']
        self.assertFalse(probe.comparison(rows[:2])['performanceGateMet'])
        for field, invalid in [('prompt_eval_cached_count', None), ('prompt_eval_cached_count', True),
                               ('prompt_eval_cached_count', 1), ('prompt_eval_count', 599),
                               ('prompt_evalMs', 9.9), ('prompt_evalMs', None), ('prompt_evalMs', float('nan'))]:
            modified = copy.deepcopy(rows)
            modified[2]['native'][field] = invalid
            with self.subTest(field=field, invalid=invalid):
                self.assertFalse(probe.comparison(modified)['performanceGateMet'])
        _, cached = self.run_fake('cache')
        self.assertTrue(cached['comparison']['inputBudgetGateMet'])
        self.assertFalse(cached['comparison']['pairs'][0]['cacheTimingComparable'])
        self.assertEqual(cached['comparison']['semanticReview'], 'pending_review')

    def test_a_faster_semantically_wrong_answer_is_still_pending_review(self):
        _, report = self.run_fake('meaning')
        self.assertTrue(report['comparison']['performanceGateMet'])
        self.assertEqual(report['comparison']['semanticReview'], 'pending_review')
        self.assertIn('NON variano', report['rows'][1]['syntheticAnswer'])

    def test_wrong_hash_and_symlink_refuse_before_network_and_restore_import_registry(self):
        names = probe.LOAD_ORDER+('qualification_context_prompt',)
        before = {n: sys.modules.get(n) for n in names}
        probe.load_modules(self.project)
        self.assertEqual(before, {n: sys.modules.get(n) for n in names})
        with patch.object(probe, 'CANDIDATE_SOURCE', probe.CANDIDATE_SOURCE+'\n'):
            with self.assertRaisesRegex(ValueError, 'embedded_candidate_mismatch'):
                probe.load_modules(self.project)
        temporary, project = installed_project()
        self.addCleanup(temporary.cleanup)
        file = project/'scripts/andrea/note_facts.py'
        file.write_bytes(file.read_bytes()+b'\n')
        with patch.object(sys, 'argv', ['probe', str(project)]), patch.object(probe, 'run_check') as network, patch('sys.stdout', new_callable=io.StringIO):
            self.assertEqual(probe.main(), 1)
        network.assert_not_called()
        file.unlink(); file.symlink_to(ROOT/'scripts/andrea/note_facts.py')
        with self.assertRaisesRegex(ValueError, 'symlink_in_baseline'):
            probe.load_modules(project)
        with self.assertRaises(ValueError):
            probe.load_modules(Path('relative'))

    def test_baseline_drift_between_requests_interrupts_without_retry(self):
        transport = Transport()
        calls = []
        def check():
            calls.append(1)
            if len(calls) == 3:
                raise ValueError('baseline_mismatch')
        with patch('sys.stdout', new_callable=io.StringIO), self.assertRaises(ValueError):
            probe.run_check(transport, self.modules, baseline_check=check)
        self.assertEqual(len(transport.requests), 1)

    def test_preflight_actual_subprocess_has_all_constants_before_main_and_no_network(self):
        result = subprocess.run([sys.executable, str(ROOT/'scripts/andrea/qualification_context_prompt_probe.py'),
                                 str(self.project), '--check-only'], cwd=ROOT, capture_output=True,
                                text=True, timeout=10, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        report = json.loads(result.stdout)
        self.assertEqual(report['baselineFilesVerified'], 12)
        self.assertEqual(report['syntheticCasesPrepared'], ['ordinary', 'adversarial'])
        self.assertEqual(report['networkRequests'], 0)
        self.assertEqual(report['inferencesIssued'], 0)
        self.assertEqual(report['performanceVerdict'], 'not_measured')

    def test_exact_default_mac_command_subprocess_finishes_four_local_http_streams(self):
        transport = Transport()
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                request = probe.Request('http://127.0.0.1:11434/api/chat',
                                        data=self.rfile.read(int(self.headers['Content-Length'])), method='POST')
                wire = transport.open(request, 90).getvalue()
                self.send_response(200)
                self.send_header('Content-Type', 'application/x-ndjson')
                self.end_headers()
                self.wfile.write(wire)
            def log_message(self, *_args):
                pass
        # Bind before launching: an occupied port fails without touching it.
        server = ThreadingHTTPServer(('127.0.0.1', 11434), Handler)
        thread = Thread(target=server.serve_forever, daemon=True); thread.start()
        before = {p: (self.project/p).read_bytes() for p in probe.EXPECTED}
        try:
            result = subprocess.run([sys.executable, str(ROOT/'scripts/andrea/qualification_context_prompt_probe.py'), str(self.project)],
                                    cwd=ROOT, capture_output=True, text=True, timeout=15,
                                    env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        report = json.loads(result.stdout[result.stdout.index('{\n  "schema"'):])
        self.assertEqual(len(transport.requests), 4)
        self.assertEqual(report['attemptedRequests'], 4)
        self.assertEqual(report['automaticRetries'], 0)
        self.assertTrue(report['comparison']['performanceGateMet'])
        self.assertEqual(report['comparison']['semanticReview'], 'pending_review')
        self.assertFalse(report['productionChangeAdopted'])
        self.assertEqual(before, {p: (self.project/p).read_bytes() for p in probe.EXPECTED})


if __name__ == '__main__':
    unittest.main()
