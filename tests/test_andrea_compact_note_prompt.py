"""Synthetic notes and simulated local HTTP; no live model or private vault."""
from contextlib import redirect_stdout
import copy
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from urllib.parse import urlsplit, parse_qs

from test_andrea_real_notes_synthesis import BOOK, QUALIFICATIONS, answer, note

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / 'scripts/andrea/compact_note_prompt_probe.py'
BASELINE_NOTE_FACTS = ROOT / 'tests/fixtures/andrea/note_facts_before_qualification.py'
spec = importlib.util.spec_from_file_location('compact_probe', FILE)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
VAULT = '/example/vault'
PATHS = ['Books/book.md', 'Numbers/metrics.md']


def copy_probe_baseline(root):
    # Old diagnostics intentionally retain their installed-version pins.
    # Exercise their original public baseline, not the later production bridge.
    for relative in p.EXPECTED:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        original = BASELINE_NOTE_FACTS if relative == 'scripts/andrea/note_facts.py' else ROOT/relative
        shutil.copyfile(original, destination)


class Response(io.BytesIO):
    status = 200


class LocalHTTP:
    def __init__(self, modules):
        self.modules = modules
        self.notes = dict(zip(PATHS, (note(BOOK, PATHS[0]), note(QUALIFICATIONS, PATHS[1]))))
        self.requests = []
        self.after = None
        self.reason = 'stop'
        self.tools = None
        self.mode = 'read-only'
        self.duplicate_event = False

    def open(self, request, timeout):
        url = urlsplit(request.full_url)
        self.requests.append(request)
        if url.netloc == '127.0.0.1:8008':
            assert request.get_method() == 'GET'
            if url.path.endswith('/status'):
                value = {'configured': True, 'available': True, 'mode': self.mode, 'vault': VAULT}
            elif url.path.endswith('/read'):
                value = self.notes[parse_qs(url.query)['path'][0]]
            else:
                raise AssertionError('Search or other endpoint must not be called')
            return Response(json.dumps(value).encode())
        assert url.netloc == '127.0.0.1:11434' and url.path == '/api/chat'
        assert request.get_method() == 'POST' and timeout == 90
        body = json.loads(request.data)
        mandatory = json.loads(body['messages'][1]['content'])['informazioni_obbligatorie']
        kind = 'book' if mandatory[0]['kind'] == 'book_description' else 'qualifications'
        path = PATHS[0] if kind == 'book' else PATHS[1]
        bundle = self.modules.bridge.prepare(self.notes[path])
        value = answer(bundle['plan'])
        events = [{'message': {'content': value[:10], 'tool_calls': self.tools}, 'done': False},
                  {'message': {'content': value[10:]}, 'done': False},
                  {'message': {'content': None}, 'done': True, 'done_reason': self.reason,
                   'total_duration': 20_000_000, 'load_duration': 1_000_000,
                   'prompt_eval_duration': 7_000_000, 'eval_duration': 10_000_000,
                   'prompt_eval_count': 101, 'prompt_eval_cached_count': 11, 'eval_count': 5}]
        wire = b''.join(json.dumps(e).encode() + b'\n' for e in events)
        if self.duplicate_event:
            wire = b'{"message":{"content":"x"},"done":false,"done":true}\n'
        if self.after:
            self.after(self)
        return Response(wire)

    def posts(self):
        return [json.loads(r.data) for r in self.requests if r.get_method() == 'POST']


class CompactTests(unittest.TestCase):
    def setUp(self):
        self.baseline_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.baseline_dir.cleanup)
        self.project = Path(self.baseline_dir.name)
        copy_probe_baseline(self.project)
        self.modules = p.load_modules(self.project)

    def bundle(self, kind):
        return self.modules.bridge.prepare(note(
            BOOK if kind == 'book' else QUALIFICATIONS, PATHS[0 if kind == 'book' else 1]))

    def test_embedded_candidate_exactly_matches_module(self):
        self.assertEqual(p.COMPACT_CODE, (ROOT/'scripts/andrea/compact_note_prompt.py').read_text())

    def test_both_kinds_preserve_all_facts_schema_and_instructions_and_shorten_message(self):
        for kind in ('book', 'qualifications'):
            bundle = self.bundle(kind)
            before = copy.deepcopy(bundle)
            compact = p.compact.messages(bundle['case'], bundle['plan'], self.modules.synthesis)
            original = bundle['messages']
            original_body = json.loads(original[1]['content'])
            compact_body = json.loads(compact[1]['content'])
            self.assertEqual(compact_body['informazioni_obbligatorie'], original_body['informazioni_obbligatorie'])
            self.assertEqual(compact_body['richiesta'], original_body['richiesta'])
            expected_instruction = original[0]['content'].replace(
                p.compact.SCHEMA_INSTRUCTION, p.compact.SHAPE_INSTRUCTION)
            if kind == 'book':
                expected_instruction += p.compact.BOOK_ROLE_INSTRUCTION
            self.assertEqual(compact[0]['content'], expected_instruction)
            self.assertEqual(bundle, before)
            self.assertNotIn('response_schema', compact_body)
            for fact in bundle['plan']['facts']:
                expected = {'text': ''} | ({'contextDate': fact['contextDate']} if 'contextDate' in fact else {})
                self.assertEqual(compact_body['response_shape']['records'][fact['id']], expected)
            self.assertLess(p.message_chars(compact), p.message_chars(original))
            self.assertNotIn('2030-12-31', str(compact))
            self.assertNotIn('1000 euro', str(compact))

    def test_wrong_year_count_qualification_and_predicate_still_refuse(self):
        fixtures = [
            ('book', lambda records: records['F3'].update(text='Edizione digitale disponibile dal 16 marzo 2027.')),
            ('book', lambda records: records['F4'].update(text='Nuova edizione online dal 21 aprile.')),
            ('qualifications', lambda records: records['F1'].update(text='I libri pubblicati sono 4.')),
            ('qualifications', lambda records: records['F3'].update(contextDate='2027-03-01')),
            ('qualifications', lambda records: records['F3'].update(text='Vendite e royalty sono DATO ASSENTE nella nota.')),
            ('qualifications', lambda records: records['F3'].update(text='Vendite e royalty sono state aggiornate: DATO NON VERIFICATO.')),
        ]
        for kind, mutate in fixtures:
            bundle = self.bundle(kind)
            p.compact.messages(bundle['case'], bundle['plan'], self.modules.synthesis)
            value = json.loads(answer(bundle['plan']))
            mutate(value['records'])
            result = self.modules.adapter.validate(json.dumps(value), bundle['case'], bundle['plan'],
                                                    self.modules.synthesis, self.modules.validator, completed=True)
            self.assertEqual(result['status'], 'rejected')

    def test_book_revision_only_adds_role_guidance_and_preserves_kpi_wire(self):
        for kind in ('book', 'qualifications'):
            bundle = self.bundle(kind)
            messages = p.compact.messages(bundle['case'], bundle['plan'], self.modules.synthesis)
            first_version_system = bundle['messages'][0]['content'].replace(
                p.compact.SCHEMA_INSTRUCTION, p.compact.SHAPE_INSTRUCTION)
            first_version_body = json.loads(bundle['messages'][1]['content'])
            first_version_body.pop('response_schema')
            first_version_body['response_shape'] = {'records': {
                fact['id']: {'text': ''} | ({'contextDate': fact['contextDate']} if 'contextDate' in fact else {})
                for fact in bundle['plan']['facts']}}
            self.assertEqual(messages[1]['content'], json.dumps(first_version_body, ensure_ascii=False))
            if kind == 'qualifications':
                self.assertEqual(messages[0]['content'], first_version_system)
            else:
                self.assertEqual(messages[0]['content'], first_version_system + p.compact.BOOK_ROLE_INSTRUCTION)
                # Generic instructions, not an authored answer or specimen text.
                for data in ('11 capitoli', '8.500', '4 marzo', '21 aprile', 'Romanzo di avventura'):
                    self.assertNotIn(data, p.compact.BOOK_ROLE_INSTRUCTION)

    def test_generic_classification_and_ambiguous_start_need_semantic_review(self):
        bundle = self.bundle('book')
        value = json.loads(answer(bundle['plan']))
        value['records']['F1']['text'] = 'Libro di avventura in italiano, 11 capitoli e circa 8.500 parole.'
        value['records']['F2']['text'] = 'Edizione cartacea iniziata il 4 marzo 2027.'
        result = self.modules.adapter.validate(json.dumps(value), bundle['case'], bundle['plan'],
                                                self.modules.synthesis, self.modules.validator, completed=True)
        self.assertEqual(result['status'], 'valid_structure_pending_semantic_review')
        self.assertEqual(result['semanticVerdict'], 'pending_review')
        self.assertFalse(result['externalTruthVerified'])

    def test_technical_acceptance_is_not_semantic_success(self):
        bundle = self.bundle('qualifications')
        value = json.loads(answer(bundle['plan']))
        value['records']['F2']['text'] = 'Vendite e royalty NON variano per periodo.'
        result = self.modules.adapter.validate(json.dumps(value), bundle['case'], bundle['plan'],
                                                self.modules.synthesis, self.modules.validator, completed=True)
        self.assertEqual(result['status'], 'valid_structure_pending_semantic_review')
        self.assertEqual(result['semanticVerdict'], 'pending_review')
        self.assertFalse(result['externalTruthVerified'])

    def test_actual_payloads_four_calls_same_native_schema_and_options_read_only(self):
        http = LocalHTTP(self.modules)
        with redirect_stdout(io.StringIO()):
            report = p.collect(http, self.modules, self.project, VAULT, PATHS)
        self.assertEqual(report['inferenceRequests'], 4)
        self.assertEqual([r['variant'] for r in report['rows']], ['original', 'compact']*2)
        self.assertEqual(report['qualityVerdict'], 'pending_review')
        self.assertEqual(report['candidateRevision'], 2)
        self.assertFalse(report['productionAdoption'])
        posts = http.posts()
        for i in (0, 2):
            for key in ('model', 'stream', 'think', 'keep_alive', 'format', 'options'):
                self.assertEqual(posts[i][key], posts[i+1][key])
            self.assertEqual(posts[i]['options'], {'temperature': 0.4, 'num_predict': 512, 'num_ctx': 4096})
            self.assertEqual(posts[i]['model'], 'qwen3:4b-instruct-2507-q4_K_M')
            self.assertEqual(posts[i]['format'], self.bundle('book' if i == 0 else 'qualifications')['plan']['schema'])
            self.assertLess(report['rows'][i+1]['messageCharacters'], report['rows'][i]['messageCharacters'])
            for row in report['rows'][i:i+2]:
                self.assertTrue(row['sourceUnchanged'])
                self.assertEqual(row['native']['prompt_eval_count'], 101)
                self.assertEqual(row['native']['prompt_eval_cached_count'], 11)
                self.assertEqual(row['native']['evalMs'], 10)
                self.assertEqual(row['contract']['semanticVerdict'], 'pending_review')
                self.assertIsNotNone(row['renderedAnswer'])
                self.assertIsNotNone(row['acceptedTextReadyClientMs'])

    def test_invalid_selection_never_sends_http(self):
        selections = [[], PATHS + ['Other/note.md'], [PATHS[0]]*2,
                      ['/absolute.md'], ['../outside.md'], ['.private/note.md'], ['a//note.md']]
        for paths in selections:
            http = LocalHTTP(self.modules)
            with self.assertRaises(ValueError):
                p.collect(http, self.modules, self.project, VAULT, paths)
            self.assertFalse(http.requests)

    def test_unsupported_second_note_prevents_any_inference(self):
        http = LocalHTTP(self.modules)
        http.notes[PATHS[1]] = note('---\nstatus: active\n---\n# Not a supported note\n', PATHS[1])
        with self.assertRaises(ValueError):
            p.collect(http, self.modules, self.project, VAULT, PATHS)
        self.assertFalse(http.posts())

    def test_changed_source_or_timestamp_or_vault_mode_refuses_and_stops_pair(self):
        mutations = [lambda h: h.notes[PATHS[0]].update(text=BOOK+'\nChanged'),
                     lambda h: h.notes[PATHS[0]].update(modifiedAt='2031-01-01'),
                     lambda h: setattr(h, 'mode', 'write')]
        for mutate in mutations:
            http = LocalHTTP(self.modules); http.after = mutate
            with redirect_stdout(io.StringIO()):
                report = p.collect(http, self.modules, self.project, VAULT, [PATHS[0]])
            self.assertEqual(report['inferenceRequests'], 1)
            self.assertEqual(report['rows'][0]['contract']['reason'], 'note_changed_or_unavailable')
            self.assertIsNone(report['rows'][0]['renderedAnswer'])
            self.assertIsNone(report['rows'][0]['acceptedTextReadyClientMs'])
            self.assertIn('stoppedReason', report)

    def test_truncated_output_not_accepted_no_retry_and_missing_metrics_not_zero(self):
        http = LocalHTTP(self.modules); http.reason = 'length'
        with redirect_stdout(io.StringIO()):
            report = p.collect(http, self.modules, self.project, VAULT, [PATHS[0]])
        self.assertEqual(report['inferenceRequests'], 2)
        self.assertEqual(report['automaticRetries'], 0)
        for row in report['rows']:
            self.assertEqual(row['status'], 'truncated')
            self.assertEqual(row['contract']['status'], 'rejected')
            self.assertIsNone(row['renderedAnswer'])
        self.assertTrue(all(v is None for v in p.native_metrics({}).values()))

    def test_tools_or_duplicate_terminal_keys_refuse_transport(self):
        for tools, duplicate in ([{'function': {'name': 'anything'}}], False), (None, True):
            http = LocalHTTP(self.modules); http.tools = tools; http.duplicate_event = duplicate
            with redirect_stdout(io.StringIO()):
                report = p.collect(http, self.modules, self.project, VAULT, [PATHS[0]])
            self.assertEqual(report['inferenceRequests'], 1)
            self.assertEqual(report['rows'][0]['status'], 'error')
            self.assertIsNone(report['rows'][0]['renderedAnswer'])

    def test_baseline_verified_before_loading_and_no_files_written(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            copy_probe_baseline(root)
            before = {str(f.relative_to(root)): f.read_bytes() for f in root.rglob('*') if f.is_file()}
            original_modules = {name: sys.modules.get(name) for name in p.LOAD_ORDER}
            modules = p.load_modules(root)
            self.assertEqual(original_modules, {name: sys.modules.get(name) for name in p.LOAD_ORDER})
            http = LocalHTTP(modules)
            with redirect_stdout(io.StringIO()):
                p.collect(http, modules, root, VAULT, [PATHS[0]])
            after = {str(f.relative_to(root)): f.read_bytes() for f in root.rglob('*') if f.is_file()}
            self.assertEqual(before, after)
            file = root / 'scripts/andrea/runtime.py'
            file.write_text('raise RuntimeError("Unverified code must not execute")')
            with self.assertRaisesRegex(ValueError, 'baseline_mismatch'):
                p.load_modules(root)

    def test_baseline_change_during_inference_rejects_accepted_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            copy_probe_baseline(root)
            modules = p.load_modules(root)
            http = LocalHTTP(modules)
            http.after = lambda h: (root/'scripts/andrea/runtime.py').write_text('# changed')
            with redirect_stdout(io.StringIO()):
                report = p.collect(http, modules, root, VAULT, [PATHS[0]])
            self.assertEqual(report['inferenceRequests'], 1)
            self.assertFalse(report['baselineUnchanged'])
            self.assertEqual(report['rows'][0]['contract']['reason'], 'baseline_changed_during_request')
            self.assertIsNone(report['rows'][0]['renderedAnswer'])


if __name__ == '__main__':
    unittest.main()
