import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('baseline', ROOT/'scripts/andrea/baseline.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
spec = importlib.util.spec_from_file_location('evidence', ROOT/'scripts/andrea/evidence.py')
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)


def result(payload):
    notes = 'notes_sources' in payload
    direct = notes and e.explicit_count_answer(payload['notes_query'], payload['notes_sources']) is not None
    return {'requestId': 'PRIVATE_ID', 'answer': 'PRIVATE_ANSWER', 'done': True, 'finishReason': 'stop',
            'firstTextClientMs': 5, 'totalClientMs': 10,
            'server': {'kind': 'notes' if notes else 'chat', 'status': 'completed',
                       'answerMode': ('explicit_fields' if direct else 'model_synthesis') if notes else None,
                       'inferenceUsed': not direct if notes else None, 'generationMs': None if direct else 8,
                       'privatePath': 'PRIVATE_PATH', 'usage': {'total_tokens': 10, 'text': 'PRIVATE_TEXT'}}}


class BaselineTests(unittest.TestCase):
    def test_exact_nine_interleaved_calls_and_no_private_fields(self):
        calls = []
        def run(payload, *, keep_answer):
            self.assertFalse(keep_answer); calls.append(payload)
            return result(payload)
        with redirect_stdout(io.StringIO()): report = b.collect(run)
        self.assertEqual(len(calls), 9)
        self.assertEqual([r['kind'] for r in report['rows']], list(b.KINDS)*3)
        self.assertEqual(sum(r['firstInBatch'] for r in report['rows']), 1)
        self.assertTrue(all(s['included'] == 3 for s in report['summary'].values()))
        self.assertNotIn('PRIVATE', json.dumps(report))

    def test_fixture_routes_and_no_vault_queries(self):
        generated = b.payload_for('notes_generated'); direct = b.payload_for('notes_direct')
        self.assertIsNone(e.explicit_count_answer(generated['notes_query'], generated['notes_sources']))
        self.assertIsNotNone(e.explicit_count_answer(direct['notes_query'], direct['notes_sources']))
        for payload in (generated, direct):
            self.assertEqual(e.supplied_sources(payload['notes_sources']), payload['notes_sources'])
        self.assertNotIn('notes_query', b.payload_for('chat'))
        self.assertNotIn('notes_brief', direct)

    def test_failed_slots_preserved_without_retry_or_false_zero(self):
        calls = 0
        def run(payload, **kwargs):
            nonlocal calls; calls += 1
            if calls == 1: raise HTTPError('http://127.0.0.1:8008', 429, 'PRIVATE', {}, None)
            return result(payload)
        with redirect_stdout(io.StringIO()): report = b.collect(run)
        self.assertEqual(calls, 9); self.assertEqual(report['summary']['chat']['included'], 2)
        self.assertIsNone(report['rows'][0]['firstTextClientMs'])
        self.assertEqual(report['rows'][0]['httpStatus'], 429)
        self.assertNotIn('PRIVATE', json.dumps(report))

    def test_wrong_path_truncation_missing_done_and_missing_server_excluded(self):
        base = result(b.payload_for('notes_generated'))
        for patch in ({'done': False}, {'finishReason': 'length'}, {'server': None},
                      {'server': {'kind': 'notes', 'status': 'completed', 'answerMode': 'explicit_fields', 'inferenceUsed': False}}):
            row = b.sanitize('notes_generated', {**base, **patch})
            self.assertFalse(row['includedInSummary'])
        self.assertFalse(b.sanitize('chat', {**base, 'firstTextClientMs': float('nan')})['includedInSummary'])

    def test_all_errors_return_report_without_median_or_retry(self):
        with redirect_stdout(io.StringIO()):
            report = b.collect(lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('PRIVATE')))
        self.assertEqual(len(report['rows']), 9)
        self.assertTrue(all(s['included'] == 0 and s['firstTextClientMs'] is None for s in report['summary'].values()))
        self.assertNotIn('PRIVATE', json.dumps(report))

    def test_unverified_client_is_not_imported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); file = root/'scripts/andrea/collaudo.py'
            file.parent.mkdir(parents=True); file.write_text('raise AssertionError("must not execute")')
            with self.assertRaisesRegex(ValueError, 'versione verificata'): b.load_client(root)


if __name__ == '__main__': unittest.main()
