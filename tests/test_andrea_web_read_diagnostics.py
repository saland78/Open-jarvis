"""Failure injection: exact operation, cleanup, no retry and no stale summary."""
import asyncio
import http.client
import json
import ssl
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import web_page_fetch as fetch
import web_page_local as local
from web_search_local import SearchError
from test_andrea_web_search_local import Process
from test_andrea_web_pages import PAGE
from test_andrea_web_search_local import RouteTests


class FetchDiagnosticsTests(unittest.TestCase):
    def test_connection_errors_do_not_retry_or_expose_details(self):
        for exc, code in [(TimeoutError('PRIVATE'), 'connection_timeout'),
                          (ConnectionRefusedError('PRIVATE'), 'connection_refused'),
                          (OSError('PRIVATE'), 'connection_network_error')]:
            with self.subTest(code=code), patch.object(fetch.socket, 'create_connection', side_effect=exc) as connect:
                with self.assertRaisesRegex(fetch.PageError, '^'+code+'$'):
                    fetch.PinnedHTTPS('example.com', '8.8.8.8').connect()
                self.assertEqual(connect.call_count, 1)

    def test_tls_failures_close_socket_without_disabling_verification(self):
        for exc, code in [(ssl.SSLCertVerificationError('PRIVATE'), 'tls_certificate_invalid'),
                          (ssl.SSLError('PRIVATE'), 'tls_error'),
                          (TimeoutError('PRIVATE'), 'tls_timeout')]:
            with self.subTest(code=code):
                sock = MagicMock(); context = MagicMock()
                context.wrap_socket.side_effect = exc
                with patch.object(fetch.ssl, 'create_default_context', return_value=context), patch.object(fetch.socket, 'create_connection', return_value=sock) as connect:
                    with self.assertRaisesRegex(fetch.PageError, '^'+code+'$'):
                        fetch.PinnedHTTPS('example.com', '8.8.8.8').connect()
                sock.close.assert_called_once()
                context.wrap_socket.assert_called_once_with(sock, server_hostname='example.com')
                connect.assert_called_once_with(('8.8.8.8', 443), 8)

    def test_response_and_body_failures_are_distinct_and_close_connection(self):
        cases = [('request', TimeoutError('PRIVATE'), 'request_timeout'),
                 ('response', TimeoutError('PRIVATE'), 'response_timeout'),
                 ('response', http.client.RemoteDisconnected('PRIVATE'), 'response_disconnected'),
                 ('response', http.client.BadStatusLine('PRIVATE'), 'response_invalid_http'),
                 ('body', TimeoutError('PRIVATE'), 'body_timeout'),
                 ('body', http.client.IncompleteRead(b'PRIVATE', 100), 'body_incomplete'),
                 ('body', ConnectionResetError('PRIVATE'), 'body_network_error')]
        for phase, exc, code in cases:
            with self.subTest(code=code):
                connection = MagicMock(); response = connection.getresponse.return_value
                response.status = 200
                response.getheader.side_effect = lambda key, default='': 'text/plain' if key == 'Content-Type' else default
                operation = {'request': connection.request, 'response': connection.getresponse, 'body': response.read}[phase]
                operation.side_effect = exc
                with patch.object(fetch, 'target', return_value=('example.com', '8.8.8.8', '/')), patch.object(fetch, 'PinnedHTTPS', return_value=connection) as factory:
                    result = fetch.read_request(b'{"url":"https://example.com"}')
                self.assertEqual(result, {'error': code})
                self.assertNotIn('PRIVATE', json.dumps(result))
                factory.assert_called_once(); connection.close.assert_called_once()

    def test_site_http_503_is_preserved_and_body_is_not_read(self):
        connection = MagicMock(); response = connection.getresponse.return_value
        response.status = 503
        with patch.object(fetch, 'target', return_value=('example.com', '8.8.8.8', '/')), patch.object(fetch, 'PinnedHTTPS', return_value=connection):
            self.assertEqual(fetch.read_request(b'{"url":"https://example.com"}'), {'error':'http_503'})
        response.read.assert_not_called(); connection.close.assert_called_once()

    def test_internal_error_is_not_mislabeled_network_and_invalid_request_never_fetches(self):
        with patch.object(fetch, 'fetch_page', side_effect=NameError('PRIVATE')):
            self.assertEqual(fetch.read_request(b'{"url":"https://example.com"}'), {'error':'unexpected_worker_error'})
        for raw in [b'not json', b'\xff', b'{}', b'[]', b'x'*4097]:
            with patch.object(fetch, 'fetch_page') as request:
                self.assertEqual(fetch.read_request(raw), {'error':'invalid_request'})
                request.assert_not_called()


class ServiceDiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    async def test_error_discards_old_page_blocks_summary_and_reports_safe_detail(self):
        for code in ['http_503', 'dns_unavailable', 'connection_timeout', 'tls_certificate_invalid', 'body_incomplete', 'unexpected_worker_error', 'https://PRIVATE/token', 'private_secret', None, {'secret':True}]:
            with self.subTest(code=code):
                pages = local.LocalWebPages(); pages.page = {**PAGE, 'pageId':'old'}
                pages.expires = local.time.monotonic()+100
                process = Process({'error':code}); process.wait = AsyncMock(return_value=0)
                with patch.object(local.asyncio, 'create_subprocess_exec', AsyncMock(return_value=process)) as spawn:
                    with self.assertRaises(SearchError) as raised:
                        await pages.read({'url':PAGE['url']})
                self.assertIsNone(pages.page); self.assertEqual(spawn.await_count,1)
                process.wait.assert_awaited_once()
                message = str(raised.exception)
                self.assertNotIn('PRIVATE', message); self.assertNotIn('private_secret', message)
                self.assertIn('Nessun tentativo automatico', message)
                if code == 'http_503': self.assertIn('Il sito ha risposto con HTTP 503', message)
                stream = MagicMock()
                with self.assertRaises(SearchError):
                    await pages.summarize({'pageId':'old', 'question':'Riassumi'}, stream)
                stream.assert_not_called()

    async def test_start_failure_is_specific_and_not_retried(self):
        pages = local.LocalWebPages(); pages.page = PAGE
        with patch.object(local.asyncio, 'create_subprocess_exec', AsyncMock(side_effect=OSError('PRIVATE'))) as spawn:
            with self.assertRaisesRegex(SearchError, 'worker_start_failed'):
                await pages.read({'url':PAGE['url']})
        self.assertEqual(spawn.await_count,1); self.assertIsNone(pages.page)

    async def test_deadline_kills_worker_without_guessing_phase(self):
        process = Process(block=True)
        with patch.object(local.asyncio,'create_subprocess_exec',AsyncMock(return_value=process)), patch.object(local,'READ_TIMEOUT',.001):
            with self.assertRaisesRegex(SearchError, 'read_deadline') as raised:
                await local.LocalWebPages().read({'url':PAGE['url']})
        self.assertEqual(raised.exception.status,504); self.assertTrue(process.killed)
        self.assertIn('fase del blocco non è disponibile', str(raised.exception))

    async def test_worker_crash_and_malformed_output_are_specific(self):
        for returncode, output, code in [(1,b'', 'worker_failed'), (0,b'not json','invalid_response'), (0,b'{"error":"http_503","extra":"PRIVATE"}','invalid_response')]:
            process = Process(); process.returncode = returncode
            process.communicate = AsyncMock(return_value=(output,b'')); process.wait = AsyncMock(return_value=returncode)
            with patch.object(local.asyncio,'create_subprocess_exec',AsyncMock(return_value=process)):
                with self.assertRaisesRegex(SearchError, code):
                    await local.LocalWebPages().read({'url':PAGE['url']})
            process.wait.assert_awaited_once()


class RouteDiagnosticsTests(RouteTests):
    async def test_remote_503_detail_reaches_interface_and_busy_is_released(self):
        mode = self.mode(); mode.pages = local.LocalWebPages()
        sent = []; received = False
        async def receive():
            nonlocal received
            if not received:
                received = True
                return {'type':'http.request', 'body':json.dumps({'url':PAGE['url']}).encode()}
            await asyncio.Event().wait()
        async def send(message): sent.append(message)
        scope = {'type':'http','method':'POST','path':'/api/andrea/web/read',
                 'headers':[(b'host',b'127.0.0.1:8008'),(b'origin',b'http://127.0.0.1:8008'),(b'content-type',b'application/json')]}
        with patch.object(local.asyncio,'create_subprocess_exec',AsyncMock(return_value=Process({'error':'http_503'}))) as spawn:
            await mode(scope,receive,send)
        self.assertEqual(sent[0]['status'],503)
        detail = json.loads(b''.join(m.get('body',b'') for m in sent[1:]))['detail']
        self.assertIn('Il sito ha risposto con HTTP 503', detail)
        self.assertIn('http_503', detail)
        self.assertFalse(mode.busy); self.assertIsNone(mode.pages.page)
        self.assertEqual(spawn.await_count,1)
        mode.app.assert_not_called(); mode.memory.messages.assert_not_called()
        mode.notes.grounding.assert_not_called()


if __name__ == '__main__': unittest.main()
