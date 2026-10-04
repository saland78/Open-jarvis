"""Persistence and local ASGI boundaries; no real model or personal notes."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import multiprocessing
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/andrea'))
from manual_memory import ManualMemory, MemoryError
from runtime import LocalMode


def record(text='Rispondi in italiano.', topic='Lingua', active=True, kind='preference'):
    return dict(text=text, topic=topic, active=active, kind=kind)


def add(store, value):
    return store.mutate(dict(action='create', revision=store.snapshot()['revision'], record=value))


def process_write(state, revision, topic, queue):
    try:
        ManualMemory(Path(state)).mutate(dict(action='create', revision=revision, record=record(topic=topic, active=False)))
        queue.put('saved')
    except MemoryError as exc:
        queue.put(exc.status)


class MemoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name)/'state'
        self.store = ManualMemory(self.state)

    def tearDown(self):
        self.tmp.cleanup()

    def test_empty_read_does_not_create_files(self):
        self.assertEqual(self.store.snapshot()['records'], [])
        self.assertFalse(self.state.exists())

    def test_persistence_update_id_delete_and_private_permissions(self):
        first = add(self.store, record())
        row = first['records'][0]
        reload = ManualMemory(self.state)
        self.assertEqual(reload.snapshot()['records'][0], row)
        changed = reload.mutate(dict(action='update', revision=1, id=row['id'], record=record('Rispondi in francese.', kind='correction')))
        self.assertEqual(changed['records'][0]['id'], row['id'])
        self.assertEqual(changed['records'][0]['createdAt'], row['createdAt'])
        self.assertNotIn('italiano', str(self.store.messages([])))
        self.assertIn('francese', str(self.store.messages([])))
        self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o600)
        reload.mutate(dict(action='delete', revision=2, id=row['id']))
        self.assertEqual(self.store.messages([{'role': 'user', 'content': 'Ciao'}]), [{'role': 'user', 'content': 'Ciao'}])
        self.assertEqual(ManualMemory(self.state).snapshot()['records'], [])

    def test_stale_edit_and_replaced_record_cannot_resurrect(self):
        row = add(self.store, record())['records'][0]
        self.store.mutate(dict(action='delete', revision=1, id=row['id']))
        with self.assertRaises(MemoryError) as error:
            self.store.mutate(dict(action='update', revision=1, id=row['id'], record=record()))
        self.assertEqual(error.exception.status, 409)
        with self.assertRaises(MemoryError):
            self.store.mutate(dict(action='update', revision=2, id=row['id'], record=record()))
        self.assertEqual(self.store.snapshot()['records'], [])

    def test_two_processes_same_revision_only_one_write(self):
        ctx = multiprocessing.get_context('spawn')
        queue = ctx.Queue()
        workers = [ctx.Process(target=process_write, args=(str(self.state), 0, topic, queue)) for topic in ('A', 'B')]
        for worker in workers: worker.start()
        for worker in workers:
            worker.join(15)
            self.assertEqual(worker.exitcode, 0)
        self.assertCountEqual([queue.get(timeout=2), queue.get(timeout=2)], ['saved', 409])
        self.assertEqual(len(self.store.snapshot()['records']), 1)
        self.assertEqual(self.store.snapshot()['revision'], 1)

    def test_corruption_fails_closed_without_rewriting(self):
        add(self.store, record())
        for bad in (b'{broken', b'{"schema":1,"revision":0,"records":[{}]}', b'{"schema":1,"revision":0,"revision":1,"records":[]}'):
            self.store.path.write_bytes(bad)
            with self.assertRaises(MemoryError): self.store.messages([])
            with self.assertRaises(MemoryError): add(self.store, record())
            self.assertEqual(self.store.path.read_bytes(), bad)

    def test_file_and_lock_links_rejected(self):
        self.state.mkdir()
        other = Path(self.tmp.name)/'private'
        other.write_text('untouched')
        for name in ('manual-memory.json', 'manual-memory.lock'):
            link = self.state/name
            link.unlink(missing_ok=True)
            link.symlink_to(other)
            with self.assertRaises((MemoryError, OSError)):
                self.store.mutate(dict(action='create', revision=0, record=record()))
            self.assertEqual(other.read_text(), 'untouched')
            link.unlink()
        os.link(other, self.store.path)
        with self.assertRaises(MemoryError): self.store.snapshot()
        self.assertEqual(other.read_text(), 'untouched')

    def test_state_symlink_rejected_for_read_and_write(self):
        target = Path(self.tmp.name)/'elsewhere'
        target.mkdir()
        self.state.symlink_to(target, target_is_directory=True)
        with self.assertRaises(MemoryError): self.store.snapshot()
        with self.assertRaises(MemoryError): add(self.store, record())
        self.assertEqual(list(target.iterdir()), [])

    def test_inactive_and_conflicting_topic(self):
        add(self.store, record(active=False))
        self.assertEqual(self.store.messages([]), [])
        add(self.store, record())
        before = self.store.path.read_bytes()
        with self.assertRaises(MemoryError): add(self.store, record(topic=' lingua ', text='Valore diverso'))
        self.assertEqual(self.store.path.read_bytes(), before)

    def test_limits_do_not_evict_or_truncate(self):
        for i in range(8): add(self.store, record(topic=str(i)))
        before = self.store.path.read_bytes()
        with self.assertRaises(MemoryError): add(self.store, record(topic='9'))
        self.assertEqual(self.store.path.read_bytes(), before)
        row = self.store.snapshot()['records'][0]
        self.store.mutate(dict(action='update', revision=8, id=row['id'], record=record(active=False)))
        add(self.store, record(topic='9'))
        self.assertEqual(len(self.store.snapshot()['records']), 9)
        self.assertEqual(len([r for r in self.store.snapshot()['records'] if r['active']]), 8)

    def test_invalid_inputs_do_not_save(self):
        for value in (record(active=1), record(text=''), record(text='x'*501), record(kind=[]), record(topic='x'*81), {**record(), 'verified': True}):
            with self.assertRaises(MemoryError): add(self.store, value)
        self.assertFalse(self.store.path.exists())

    def test_context_size_cap_and_saved_cap_preserve_previous_file(self):
        for i in range(4): add(self.store, record(topic=str(i), text='a'*400))
        before = self.store.path.read_bytes()
        with self.assertRaises(MemoryError): add(self.store, record(topic='extra', text='b'*500))
        self.assertEqual(self.store.path.read_bytes(), before)
        for row in self.store.snapshot()['records']:
            self.store.mutate(dict(action='update', revision=self.store.snapshot()['revision'], id=row['id'], record=record(topic=row['topic'], active=False)))
        for i in range(96): add(self.store, record(topic=f'saved-{i}', active=False))
        before = self.store.path.read_bytes()
        with self.assertRaises(MemoryError): add(self.store, record(topic='over-cap', active=False))
        self.assertEqual(self.store.path.read_bytes(), before)


class MemoryBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ManualMemory(Path(self.tmp.name)/'state')
        self.calls = []
        async def sink(scope, receive, send):
            self.calls.append(json.loads((await receive())['body']))
            await send({'type': 'http.response.start', 'status': 200, 'headers': []})
            await send({'type': 'http.response.body', 'body': b'data: [DONE]\n\n'})
        self.app = LocalMode(sink, 'model', 8008, memory=self.store)

    async def asyncTearDown(self): self.tmp.cleanup()

    async def call(self, payload=None, *, path='/api/andrea/memory', method='POST', origin='http://localhost:8008'):
        events = []
        scope = {'type': 'http', 'method': method, 'path': path, 'headers': [(b'host', b'localhost:8008'), (b'content-type', b'application/json')]}
        if origin is not None: scope['headers'].append((b'origin', origin.encode()))
        async def receive(): return {'type': 'http.request', 'body': json.dumps(payload).encode()}
        async def send(event): events.append(event)
        await self.app(scope, receive, send)
        return events[0]['status'], b''.join(e.get('body', b'') for e in events)

    async def test_same_origin_and_no_tools(self):
        payload = dict(action='create', revision=0, record=record())
        for origin in (None, 'https://evil.test'):
            self.assertEqual((await self.call(payload, origin=origin))[0], 403)
        self.assertFalse(self.store.path.exists())
        self.assertEqual((await self.call(payload))[0], 200)
        self.assertEqual((await self.call({}, path='/v1/memory', method='DELETE'))[0], 403)
        self.assertEqual(self.calls, [])

    async def test_chat_context_corrected_and_deleted_without_extra_inference(self):
        chat = {'model': 'model', 'stream': True, 'messages': [{'role': 'user', 'content': 'Quale lingua preferisco?'}]}
        await self.call(chat, path='/v1/chat/completions')
        self.assertEqual(self.calls[-1]['messages'], chat['messages'])
        self.assertFalse(self.store.path.exists())
        row = add(self.store, record())['records'][0]
        await self.call(chat, path='/v1/chat/completions')
        self.assertIn('italiano', self.calls[-1]['messages'][1]['content'])
        self.store.mutate(dict(action='update', revision=1, id=row['id'], record=record('Preferisco francese.', kind='correction')))
        await self.call(chat, path='/v1/chat/completions')
        self.assertNotIn('italiano', str(self.calls[-1]))
        self.assertIn('francese', str(self.calls[-1]))
        self.store.mutate(dict(action='delete', revision=2, id=row['id']))
        await self.call(chat, path='/v1/chat/completions')
        self.assertEqual(self.calls[-1]['messages'], chat['messages'])
        self.assertEqual(len(self.calls), 4)
        self.assertTrue(all(c['max_tokens'] == 512 and not c.get('tools') for c in self.calls))

    async def test_notes_context_unchanged(self):
        add(self.store, record(text='Preferisco contenuti estranei alla nota.'))
        chat = {'model': 'model', 'stream': True, 'messages': [{'role': 'user', 'content': 'Ciao'}], 'notes_query': 'colore', 'notes_sources': [{'id': 'N1', 'title': 'Test', 'text': 'Il colore è rosso.'}]}
        status, _ = await self.call(chat, path='/v1/chat/completions')
        self.assertEqual(status, 200)
        self.assertNotIn('Preferisco contenuti estranei', str(self.calls))
        self.assertIn('rosso', str(self.calls))

    async def test_busy_and_corruption_do_not_mutate_or_infer(self):
        self.app.busy = True
        self.assertEqual((await self.call(dict(action='create', revision=0, record=record())))[0], 409)
        self.app.busy = False
        add(self.store, record())
        self.store.path.write_text('{broken')
        self.assertEqual((await self.call(method='GET'))[0], 503)
        chat = {'model': 'model', 'stream': True, 'messages': [{'role': 'user', 'content': 'Ciao'}]}
        self.assertEqual((await self.call(chat, path='/v1/chat/completions'))[0], 503)
        self.assertFalse(self.app.busy)
        self.assertEqual(self.calls, [])


if __name__ == '__main__': unittest.main()
