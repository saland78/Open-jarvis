import ast
from contextlib import redirect_stdout
from hashlib import sha256
import io
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError

import web_concurrency_synthesis_probe as candidate
import web_sentence_contract as installed

PAGE = ('La programmazione asincrona gestisce più attività contemporaneamente durante le attese.\n'
        'await sospende una coroutine, lasciando procedere altro codice durante le attese.\n')

ROOT = Path(__file__).resolve().parents[1]

def installed_source(relative):
    # The isolated probe intentionally targets the pre-integration installed
    # version. Preserve that baseline when the repository advances.
    if relative == 'scripts/andrea/web_sentence_contract.py':
        return (ROOT / 'tests/fixtures/andrea/web_sentence_contract.py_before_concurrency_prompt').read_bytes()
    if relative in {'scripts/andrea/web_page_fetch.py', 'scripts/andrea/web_page_local.py'}:
        return (ROOT / ('tests/fixtures/andrea/'+Path(relative).name+'_before_read_diagnostics')).read_bytes()
    return (ROOT / relative).read_bytes()

def baseline(root):
    for relative in candidate.EXPECTED:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(installed_source(relative))


class ConcurrencyProbeTests(unittest.TestCase):
    def test_acceptance_contract_is_unchanged(self):
        def functions(module, path=None):
            tree = ast.parse((path or Path(module.__file__)).read_text())
            return {node.name: ast.dump(node) for node in tree.body if isinstance(node, ast.FunctionDef)}
        before, after = functions(installed, ROOT/'tests/fixtures/andrea/web_sentence_contract.py_before_english_alias'), functions(candidate)
        for name in ('sentence_bank', 'technical_terms', 'unique_pairs', 'normalized', 'validate'):
            self.assertEqual(before[name], after[name], name)
        bank, messages, schema = candidate.prepare(PAGE, 'Sintetizza.')
        path = ROOT/'tests/fixtures/andrea/web_sentence_contract.py_before_english_alias'
        loader = importlib.machinery.SourceFileLoader('historical_contract', str(path))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        historical = importlib.util.module_from_spec(spec); loader.exec_module(historical)
        old_bank, old_messages, old_schema = historical.prepare(PAGE, 'Sintetizza.')
        self.assertEqual(bank, old_bank)
        self.assertEqual(schema, old_schema)
        self.assertEqual(messages[1], old_messages[1])
        self.assertTrue(messages[0]['content'].startswith(old_messages[0]['content']))

    def test_observed_parallel_inference_stays_rejected(self):
        raw = json.dumps({'claims': [{'passage': 1,
            'text': "L'asincrono permette di eseguire attività in parallelo mentre si aspetta."}]})
        verdict = candidate.validate(raw, candidate.sentence_bank(PAGE), True)
        self.assertEqual(verdict['outcome'], 'rejected')
        self.assertEqual(verdict['claims'], [])
        self.assertEqual(verdict['details']['missingConcepts'], ['parallel_execution'])
        self.assertEqual(verdict['details']['quote'], PAGE.splitlines(keepends=True)[0])

    def test_supported_concurrent_paraphrase_remains_unmodified(self):
        text = 'Durante le attese il codice asincrono gestisce più attività contemporaneamente.'
        raw = json.dumps({'claims': [{'passage': 1, 'text': text}]})
        verdict = candidate.validate(raw, candidate.sentence_bank(PAGE), True)
        self.assertEqual(verdict['outcome'], 'accepted_pending_semantic_review')
        self.assertEqual(verdict['claims'][0]['text'], text)
        self.assertEqual(verdict['claims'][0]['quote'], PAGE.splitlines(keepends=True)[0])

    def test_a_term_elsewhere_does_not_ground_selected_passage(self):
        bank = candidate.sentence_bank(PAGE + 'Un sistema diverso lavora in parallelo con più processi.\n')
        raw = json.dumps({'claims': [{'passage': 1,
            'text': 'Il codice asincrono svolge le attività in parallelo.'}]})
        self.assertEqual(candidate.validate(raw, bank, True)['outcome'], 'rejected')

    def test_expected_files_match_and_local_changes_abort_before_network(self):
        class NeverOpen:
            def open(self, *args, **kwargs):
                raise AssertionError('Unexpected network request')
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            baseline(temporary)
            candidate.verify_project(temporary)
            first = temporary / next(iter(candidate.EXPECTED))
            first.write_bytes(first.read_bytes() + b'\n# local change\n')
            with self.assertRaisesRegex(ValueError, 'installed_version_mismatch'):
                candidate.run(temporary, NeverOpen())

    def test_single_read_single_inference_without_file_mutations(self):
        requests = []
        test = self
        answer = json.dumps({'claims': [{'passage': 1,
            'text': 'Durante le attese il codice asincrono gestisce più attività contemporaneamente.'}]})
        class Response(io.BytesIO):
            status = 200
        class Opener:
            def open(self, request, timeout):
                requests.append(request)
                if request.full_url.endswith('/api/andrea/web/read'):
                    test.assertEqual(json.loads(request.data), {'url': candidate.URL})
                    return Response(json.dumps({'url': candidate.URL, 'sourceId': 'W1',
                                                'text': PAGE, 'readMs': 10}).encode())
                test.assertEqual(request.full_url, candidate.BASE + '/api/chat')
                payload = json.loads(request.data)
                test.assertEqual(payload['options'], {'temperature': .4, 'num_predict': 512, 'num_ctx': 4096})
                test.assertFalse(payload['think'])
                test.assertNotIn('tools', payload)
                return Response((json.dumps({'message': {'content': answer}, 'done': True,
                                             'done_reason': 'stop'}) + '\n').encode())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline(root)
            before = {path: sha256((root / path).read_bytes()).hexdigest() for path in candidate.EXPECTED}
            with redirect_stdout(io.StringIO()):
                result = candidate.run(root, Opener())
            self.assertEqual(before, {path: sha256((root / path).read_bytes()).hexdigest() for path in candidate.EXPECTED})
        self.assertEqual(len(requests), 2)
        self.assertFalse(result['productionModified'])
        self.assertEqual(result['automaticRetries'], 0)
        self.assertEqual(result['checks']['outcome'], 'accepted_pending_semantic_review')
        self.assertEqual(result['qualityVerdict'], 'pending_review')

    def test_read_failure_exposes_detail_without_inference(self):
        calls = []
        class Opener:
            def open(self, request, timeout):
                calls.append(request)
                raise HTTPError(request.full_url, 503, 'Unavailable', {},
                                io.BytesIO(b'{"detail":"Pagina non letta (network_error)."}'))
        with self.assertRaisesRegex(ValueError, 'page_read_http_503: Pagina non letta'):
            candidate.read_page(Opener())
        self.assertEqual(len(calls), 1)
