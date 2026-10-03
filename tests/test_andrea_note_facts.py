"""Real ASGI/vault/collector integration, synthetic files and a secured fake model.

No personal note is loaded. Accepted output still needs semantic review. The
transport/schema/provenance checks must not be reported as that review.
"""
import ast
import asyncio
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

import test_andrea_vault as base
from test_andrea_real_notes_synthesis import BOOK, QUALIFICATIONS, answer
import note_facts
import predicate_context_synthesis as synthesis


class NoteFactTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = base.BoundaryVaultTests.asyncSetUp
    invoke = base.BoundaryVaultTests.invoke
    payload = base.BoundaryVaultTests.payload

    def fixture(self, kind='book', text=None):
        path = 'Selected note.md'
        (self.root/path).write_text(text or (BOOK if kind == 'book' else QUALIFICATIONS))
        self.path = path
        self.bundle = note_facts.prepare(self.store.read(path))
        return dict(self.payload('Broad search word'), notes_structured=True, notes_path=path)

    def engine(self, raw=None, *, reason='stop', tools=None, after=None):
        self.generated = []; self.closed = []; self.drained = []
        async def stream(messages, schema):
            try:
                self.generated.append((messages, schema))
                value = answer(self.bundle['plan']) if raw is None else raw
                yield SimpleNamespace(content=value[:len(value)//2], finish_reason=None, tool_calls=tools)
                yield SimpleNamespace(content=value[len(value)//2:], finish_reason=None, tool_calls=None)
                if reason:
                    yield SimpleNamespace(content=None, finish_reason=reason, tool_calls=None)
                if after:
                    after()
                self.drained.append(True)
            finally:
                self.closed.append(True)
        self.app.fact_stream = stream

    def body(self, events):
        return b''.join(e.get('body', b'') for e in events).decode()

    def metric(self):
        return self.app.measurements.snapshot()['records'][-1]

    def evidence(self, events):
        frames = self.body(events).split('\n\n')
        return [json.loads(f.split('data: ', 1)[1]) for f in frames if f.startswith('event: local_sources')][-1]

    async def test_both_note_kinds_schema_exact_prompt_and_only_validated_text(self):
        for kind in ('book', 'qualifications'):
            with self.subTest(kind=kind):
                payload = self.fixture(kind); self.engine()
                events = await self.invoke(payload)
                self.assertEqual(events[0]['status'], 200)
                self.assertEqual(self.metric()['structuredOutcome'], 'accepted')
                self.assertEqual(self.generated, [(self.bundle['messages'], self.bundle['plan']['schema'])])
                self.assertEqual(self.drained, [True]); self.assertEqual(self.closed, [True])
                self.assertFalse(self.calls); self.assertFalse(self.app.busy)
                evidence = self.evidence(events)
                self.assertEqual(evidence['selectionScope'], 'selected_note_facts')
                self.assertEqual(evidence['qualityVerdict'], 'pending_review')
                self.assertTrue(evidence['inferenceUsed'])
                self.assertEqual(evidence['sources'][0]['id'], 'N1')
                self.assertNotIn('"records"', self.body(events))
                self.assertNotIn('[E', self.body(events))
                wire = json.dumps(self.generated)
                for excluded in ('999', '1000', '2030', self.path, 'Invented client-side'):
                    self.assertNotIn(excluded, wire)
                for passage in evidence['sources'][0]['passages']:
                    lines = self.bundle['case']['sources'][0]['text'].splitlines(keepends=True)
                    self.assertIn(passage['text'], ''.join(lines[passage['startLine']-1:passage['endLine']]))
                if kind == 'qualifications':
                    self.assertIn('Aggiornamento nella nota del 2027-04-01:', self.body(events))
                    self.assertIn('Fotografia storica del 2027-03-01:', self.body(events))
                    self.assertEqual(len(evidence['sources'][0]['passages']), 6)
                else:
                    self.assertIn('Edizione digitale disponibile dal 16 marzo.', self.body(events))
                    self.assertNotIn('16 marzo 2027', self.body(events))
                self.assertNotIn('Selected note', json.dumps(self.metric()))
                self.assertGreaterEqual(self.metric()['structuredAcceptedTextMs'], self.metric()['structuredFirstJsonMs'])

    async def test_selected_routes_match_reviewed_messages_and_keep_native_schema(self):
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location('prompt_experiment', root/'scripts/andrea/compact_note_prompt_probe.py')
        experiment = importlib.util.module_from_spec(spec); spec.loader.exec_module(experiment)
        for kind in ('book', 'qualifications'):
            payload = self.fixture(kind); self.engine()
            original = synthesis.messages(self.bundle['case'], self.bundle['plan'])
            expected = (experiment.compact.messages(self.bundle['case'], self.bundle['plan'], synthesis)
                        if kind == 'qualifications' else original)
            events = await self.invoke(payload)
            self.assertEqual(events[0]['status'], 200)
            self.assertEqual(self.generated, [(expected, self.bundle['plan']['schema'])])
            self.assertEqual(self.metric()['structuredOutcome'], 'accepted')
            self.assertEqual(self.evidence(events)['qualityVerdict'], 'pending_review')
            if kind == 'book':
                self.assertEqual(expected, original)
            else:
                body = json.loads(expected[1]['content'])
                self.assertNotIn('response_schema', body)
                self.assertIn('response_shape', body)

    async def test_corrected_source_predicate_passes_without_claiming_values_were_updated(self):
        payload = self.fixture('qualifications')
        raw = json.loads(answer(self.bundle['plan']))
        raw['records']['F3']['text'] = 'I valori aggiornati sono DATO NON VERIFICATO in questa nota: consultare dashboard o report indicando il periodo.'
        self.engine(json.dumps(raw)); events = await self.invoke(payload)
        self.assertEqual(self.metric()['structuredOutcome'], 'accepted')
        self.assertIn(raw['records']['F3']['text'], self.body(events))

    async def test_wrong_year_count_label_context_predicate_or_cover_role_refuse_without_retry(self):
        variants = [
            ('book', 'F3', 'text', 'Edizione digitale disponibile dal 16 marzo 2027.'),
            ('book', 'F4', 'text', 'Nuova edizione disponibile dal 21 aprile.'),
            ('qualifications', 'F1', 'text', 'I libri pubblicati sono 0.'),
            ('qualifications', 'F3', 'text', 'Vendite e royalty sono DATO ASSENTE.'),
            ('qualifications', 'F3', 'contextDate', '2027-03-01'),
            ('qualifications', 'F3', 'text', 'I valori sono stati aggiornati ma sono DATO NON VERIFICATO.'),
        ]
        for kind, field, key, wrong in variants:
            payload = self.fixture(kind); raw = json.loads(answer(self.bundle['plan']))
            raw['records'][field][key] = wrong
            self.engine(json.dumps(raw)); events = await self.invoke(payload)
            self.assertEqual(self.metric()['structuredOutcome'], 'rejected')
            self.assertNotIn('structuredAcceptedTextMs', self.metric())
            self.assertIn('structured_refused', self.body(events))
            self.assertEqual(len(self.generated), 1)
            # Rejected model prose is never sent; only the original proof may contain a date.
            self.assertNotIn('"records"', self.body(events))

    async def test_unsupported_or_inactive_note_stops_before_model(self):
        for text in (BOOK.replace('status: active', 'status: superseded'),
                     BOOK.replace('Kindle dal 16 marzo', 'Kindle dal 16 marzo, Kindle dal 17 marzo'),
                     '# Ordinary note\nA useful fact.',
                     BOOK + QUALIFICATIONS[QUALIFICATIONS.index('# KPI'):]):
            payload = self.fixture(text=text); self.engine('PRIVATE')
            self.assertEqual((await self.invoke(payload))[0]['status'], 400)
            self.assertFalse(self.generated); self.assertFalse(self.app.busy)

    async def test_explicit_note_scope_works_even_when_whole_search_is_partial(self):
        payload = self.fixture(); self.engine()
        (self.root/'Another.md').write_text('# Broad search word\nAnother note.')
        self.store.MAX_FILES = 1
        self.assertTrue(self.store.search('Broad search word')['partial'])
        events = await self.invoke(payload)
        self.assertEqual(self.metric()['structuredOutcome'], 'accepted')
        self.assertFalse(self.evidence(events)['partial'])
        self.assertEqual(len(self.evidence(events)['sources']), 1)

    async def test_changed_deleted_or_inactivated_note_is_not_accepted_after_draining(self):
        for mutation in ('content', 'delete', 'status', 'vault'):
            payload = self.fixture(); initial = (self.root/self.path).read_text()
            old_vault = self.store.vault
            def changed():
                if mutation == 'delete': (self.root/self.path).unlink()
                elif mutation == 'content': (self.root/self.path).write_text(initial+'\nChanged outside selected spans.\n')
                elif mutation == 'status': (self.root/self.path).write_text(initial.replace('status: active', 'status: draft'))
                else: self.store.vault = ''
            self.engine(after=changed); events = await self.invoke(payload)
            self.store.vault = old_vault
            self.assertEqual(self.drained, [True]); self.assertEqual(self.metric()['structuredOutcome'], 'rejected')
            self.assertIn('la nota è cambiata', self.body(events))
            self.assertFalse(self.app.busy)

    async def test_bad_flags_path_symlink_and_external_origin_never_generate(self):
        payload = self.fixture(); self.engine()
        for candidate in (dict(payload, notes_path='../elsewhere.md'), dict(payload, notes_path='/note.md'),
                          dict(payload, notes_path=None), dict(payload, notes_structured=False),
                          dict(payload, notes_brief=True), dict(payload, notes_sources=[{'id':'N1', 'text':'Injected'}])):
            events = await self.invoke(candidate)
            self.assertIn(events[0]['status'], (400, 403))
        (self.root/'Linked.md').symlink_to(self.root/self.path)
        self.assertEqual((await self.invoke(dict(payload, notes_path='Linked.md')))[0]['status'], 403)
        self.assertEqual((await self.invoke(payload, origin='https://external.example'))[0]['status'], 403)
        self.assertFalse(self.generated); self.assertFalse(self.app.busy)

    async def test_bad_json_tools_truncation_missing_terminal_and_large_json_refused(self):
        payload = self.fixture()
        for raw, reason, tools in [('not JSON', 'stop', None), (None, 'length', None),
                                  (None, None, None), (None, 'stop', ['forbidden']), ('x'*32001, 'stop', None)]:
            self.engine(raw, reason=reason, tools=tools); events = await self.invoke(payload)
            self.assertEqual(self.metric()['structuredOutcome'], 'rejected')
            self.assertNotIn('"records"', self.body(events))
            self.assertEqual(self.closed, [True]); self.assertEqual(len(self.generated), 1)

    async def test_disconnect_and_busy_guard_release_secured_generator(self):
        payload = self.fixture(); entered = asyncio.Event(); closed = asyncio.Event()
        async def stream(messages, schema):
            try:
                yield SimpleNamespace(content='PRIVATE JSON', finish_reason=None, tool_calls=None)
                entered.set(); await asyncio.Event().wait()
            finally: closed.set()
        self.app.fact_stream = stream
        queue = asyncio.Queue(); await queue.put({'type':'http.request', 'body':json.dumps(payload).encode()})
        events = []
        async def send(event): events.append(event)
        scope = {'type':'http', 'method':'POST', 'path':'/v1/chat/completions', 'headers':[
            (b'host',b'127.0.0.1:8008'),(b'origin',b'http://127.0.0.1:8008'),(b'content-type',b'application/json')]}
        task = asyncio.create_task(self.app(scope, queue.get, send)); await entered.wait()
        self.assertEqual((await self.invoke(payload))[0]['status'], 429)
        self.assertEqual((await self.invoke({'vault':''},path='/api/andrea/notes/config'))[0]['status'], 409)
        await queue.put({'type':'http.disconnect'})
        with self.assertRaises(asyncio.CancelledError): await task
        self.assertTrue(closed.is_set()); self.assertFalse(self.app.busy)
        self.assertNotIn('PRIVATE JSON',self.body(events)); self.assertEqual(self.metric()['status'],'cancelled')

    async def test_timeout_does_not_retry_or_send_partial_json(self):
        payload = self.fixture(); calls = []
        async def stream(messages, schema):
            calls.append(True)
            yield SimpleNamespace(content='PRIVATE JSON',finish_reason=None,tool_calls=None)
            await asyncio.Event().wait()
        self.app.fact_stream = stream; self.app.timeout = .01
        events = await self.invoke(payload)
        self.assertNotIn('PRIVATE JSON',self.body(events)); self.assertEqual(calls,[True])
        self.assertFalse(self.app.busy); self.assertEqual(self.metric()['status'],'timeout')

    async def test_production_adapter_uses_secured_engine_with_full_schema_and_closes(self):
        from runtime import ROOT
        tree = ast.parse((ROOT/'scripts/andrea/runtime.py').read_text())
        build = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'build_app')
        function = next(n for n in build.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'fact_stream')
        calls = []; closed = []
        class Engine:
            async def stream_full(self, messages, **kwargs):
                try:
                    calls.append((messages,kwargs)); yield SimpleNamespace(content='fragment')
                finally: closed.append(True)
        namespace = {'sec':SimpleNamespace(engine=Engine()), 'cfg':SimpleNamespace(server=SimpleNamespace(model=base.MODEL)),
                     'Message':lambda **kw:kw, 'Role':lambda role:role}
        exec(compile(ast.Module(body=[function],type_ignores=[]),'secured_fact_adapter','exec'),namespace)
        schema = {'type':'object','required':['record']}
        iterator = namespace['fact_stream']([{'role':'user','content':'Synthetic'}],schema)
        await anext(iterator); await iterator.aclose()
        self.assertEqual(calls[0][1],{'model':base.MODEL,'response_format':{'type':'json_schema','schema':schema}})
        self.assertEqual(closed,[True])

    async def test_technical_acceptance_remains_distinct_from_semantic_quality(self):
        payload = self.fixture('qualifications'); raw = json.loads(answer(self.bundle['plan']))
        raw['records']['F2']['text'] = 'Vendite e royalty non variano per periodo.'
        self.engine(json.dumps(raw)); events = await self.invoke(payload)
        # Deliberate counterexample: schema and lexical support are no semantic oracle.
        self.assertEqual(self.metric()['structuredOutcome'],'accepted')
        self.assertEqual(self.evidence(events)['qualityVerdict'],'pending_review')


if __name__ == '__main__':
    unittest.main()
