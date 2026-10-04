import asyncio
import json
from types import SimpleNamespace as Chunk
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import web_page_fetch as fetch
import web_page_local as local
from web_search_local import SearchError
from test_andrea_web_search_local import Process, RouteTests

TEXT = 'Il manuale dichiara due configurazioni. Nel 2026 il parametro documentato vale 2. Non sono disponibili misure comparative.'
PAGE = {'url': 'https://example.com/page', 'title': 'Manuale', 'text': TEXT, 'partial': False, 'redirects': 0}

def dns(*ips):
    return [(2, 1, 6, '', (ip, 443)) for ip in ips]

class SecurityTests(unittest.TestCase):
    def test_private_mixed_dns_and_transition_addresses(self):
        for ip in ['127.0.0.1', '10.0.0.1', '169.254.169.254', '100.100.100.200', '::1', '::ffff:127.0.0.1', '2002:7f00:1::', '224.0.0.1']:
            with self.subTest(ip=ip):
                self.assertFalse(fetch.address_allowed(ip))
        with patch.object(fetch.socket, 'getaddrinfo', return_value=dns('8.8.8.8', '127.0.0.1')):
            with self.assertRaises(fetch.PageError): fetch.target('https://example.com/')

    def test_url_validation_before_dns(self):
        for url in ['http://example.com', 'file:///etc/passwd', 'https://u:p@example.com', 'https://example.com:8008', 'https://localhost', 'https://metadata.google.internal', 'https://example.com\\@localhost', 'https://example.com/\n']:
            with patch.object(fetch.socket, 'getaddrinfo') as resolve:
                with self.assertRaises(fetch.PageError): fetch.target(url)
                resolve.assert_not_called()

    def test_dns_failure_closed(self):
        with patch.object(fetch.socket, 'getaddrinfo', side_effect=fetch.socket.gaierror()):
            with self.assertRaisesRegex(fetch.PageError, 'dns_unavailable'): fetch.target('https://example.com')

    def test_pin_ip_and_tls_original_hostname(self):
        tls = MagicMock(); sock = MagicMock()
        with patch.object(fetch.ssl, 'create_default_context', return_value=tls), patch.object(fetch.socket, 'create_connection', return_value=sock) as connect:
            connection = fetch.PinnedHTTPS('example.com', '8.8.8.8')
            connection.connect()
            connect.assert_called_once_with(('8.8.8.8', 443), 8)
            tls.wrap_socket.assert_called_once_with(sock, server_hostname='example.com')

    def test_tls_failure_closes_socket(self):
        sock = MagicMock(); tls = MagicMock(); tls.wrap_socket.side_effect = fetch.ssl.SSLError()
        with patch.object(fetch.ssl, 'create_default_context', return_value=tls), patch.object(fetch.socket, 'create_connection', return_value=sock):
            with self.assertRaises(fetch.ssl.SSLError): fetch.PinnedHTTPS('example.com', '8.8.8.8').connect()
        sock.close.assert_called_once()

    def test_redirect_revalidated_before_new_connection(self):
        connection = MagicMock(); response = connection.getresponse.return_value
        response.status = 302; response.getheader.return_value = 'https://127.0.0.1/private'
        with patch.object(fetch.socket, 'getaddrinfo', side_effect=[dns('8.8.8.8'), dns('127.0.0.1')]), patch.object(fetch, 'PinnedHTTPS', return_value=connection) as factory:
            with self.assertRaisesRegex(fetch.PageError, 'private_destination'): fetch.fetch_page('https://example.com')
        self.assertEqual(factory.call_count, 1); connection.close.assert_called_once()

    def test_content_limits_types_and_no_cookies(self):
        for content_type, body, error in [('application/pdf', b'pdf', 'unsupported_content_type'), ('text/html', b'a'*(fetch.MAX_BYTES+1), 'page_too_large')]:
            c = MagicMock(); r = c.getresponse.return_value; r.status = 200
            r.getheader.side_effect = lambda key, default='': content_type if key == 'Content-Type' else default
            r.read.return_value = body
            with patch.object(fetch, 'target', return_value=('example.com', '8.8.8.8', '/')), patch.object(fetch, 'PinnedHTTPS', return_value=c):
                with self.assertRaisesRegex(fetch.PageError, error): fetch.fetch_page('https://example.com')
            self.assertNotIn('Cookie', c.request.call_args.kwargs['headers']); c.close.assert_called_once()

    def test_extract_scripts_navigation_and_size(self):
        title, text, partial = fetch.extract(b'<title>Test</title><nav>Menu</nav><script>BAD</script><div hidden>secret</div><p>'+TEXT.encode()+b'</p>', 'text/html')
        self.assertEqual(title, 'Test'); self.assertEqual(text, TEXT); self.assertFalse(partial)
        _, text, partial = fetch.extract(b'x'*7000, 'text/plain')
        self.assertEqual(len(text), 6000); self.assertTrue(partial)
        with self.assertRaises(fetch.PageError): fetch.extract(b'no', 'text/plain')

class ContractTests(unittest.TestCase):
    def test_good_quote_and_abstention(self):
        answer = {'claims': [{'text': 'Il valore documentato nel 2026 è 2.', 'quote': 'Nel 2026 il parametro documentato vale 2.'}]}
        self.assertEqual(local.validate_answer(json.dumps(answer), TEXT, True)['outcome'], 'accepted_pending_semantic_review')
        self.assertEqual(local.validate_answer('{"claims":[]}', TEXT, True)['outcome'], 'abstained')

    def test_invented_quote_number_incomplete_unknown_fields(self):
        for data, completed, reason in [({'claims':[{'text':'Vale 3.', 'quote':'Nel 2026 il parametro documentato vale 2.'}]},True,'unsupported_number'), ({'claims':[{'text':'Vale 2.', 'quote':'La pagina dichiara qualcosa che non esiste.'}]},True,'quote_not_in_page'), ({'claims':[]},False,'stream_incomplete'), ({'claims':[], 'action':'buy'},True,'invalid_structure')]:
            result = local.validate_answer(json.dumps(data), TEXT, completed)
            self.assertEqual(result['reason'],reason); self.assertEqual(result['claims'],[])

class PageServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_read_only_url_and_ephemeral_page(self):
        process = Process(PAGE)
        pages = local.LocalWebPages()
        with patch.object(local.asyncio,'create_subprocess_exec',AsyncMock(return_value=process)) as spawn:
            result = await pages.read({'url':PAGE['url']})
        self.assertEqual(json.loads(process.input), {'url':PAGE['url']}); self.assertEqual(spawn.await_count,1)
        self.assertEqual(result['text'],TEXT); self.assertFalse(result['modelUsed'])
        self.assertEqual(result['sourceId'],'W1')
        self.assertEqual(pages.page, result)

    async def test_read_cancel_timeout_kill_and_no_retry(self):
        for cancel in [False, True]:
            process = Process(block=True)
            with patch.object(local.asyncio,'create_subprocess_exec',AsyncMock(return_value=process)) as spawn, patch.object(local,'READ_TIMEOUT',.01):
                task = asyncio.create_task(local.LocalWebPages().read({'url':PAGE['url']}))
                if cancel:
                    await asyncio.sleep(.001); task.cancel()
                    with self.assertRaises(asyncio.CancelledError): await task
                else:
                    with self.assertRaises(SearchError): await task
                self.assertEqual(spawn.await_count,1); self.assertTrue(process.killed)

    async def test_summary_requires_live_token_and_no_client_text(self):
        pages = local.LocalWebPages(); pages.page = {**PAGE,'pageId':'token'}; pages.expires = 0
        with self.assertRaises(SearchError): await pages.summarize({'pageId':'token','question':'x'},None)
        self.assertIsNone(pages.page)
        for payload in [{'pageId':'token','question':'x','text':TEXT}, {'pageId':3,'question':'x'}]:
            with self.assertRaises(SearchError): await pages.summarize(payload,None)

    async def test_model_only_gets_current_page_and_question(self):
        pages = local.LocalWebPages(); pages.page = {**PAGE,'pageId':'token'}; pages.expires=local.time.monotonic()+100
        captured=[]
        async def stream(messages,schema):
            captured.append(messages)
            yield Chunk(content='{"claims":[]}',finish_reason='stop')
        result=await pages.summarize({'pageId':'token','question':'Che cosa dice?'},stream)
        self.assertEqual(result['outcome'],'abstained'); self.assertEqual(result['automaticRetries'],0)
        self.assertEqual(json.loads(captured[0][1]['content']),{'question':'Che cosa dice?','pageExcerpt':TEXT})
        self.assertEqual(len(captured),1)

    async def test_stream_closes_on_length_or_timeout(self):
        closed=[]
        async def stream(messages,schema):
            try:
                yield Chunk(content='x'*5001,finish_reason=None)
            finally: closed.append(True)
        result=await local.generate(stream,'q',TEXT)
        self.assertEqual(result['reason'],'stream_incomplete'); self.assertEqual(closed,[True])

class PageRouteTests(RouteTests):
    async def request(self,mode,origin='http://127.0.0.1:8008',payload=None,method='POST'):
        headers=[(b'host',b'127.0.0.1:8008'),(b'content-type',b'application/json')]
        if origin is not None: headers.append((b'origin',origin.encode()))
        scope={'type':'http','method':method,'path':'/api/andrea/web/read','headers':headers}
        sent=[]; read=False
        async def receive():
            nonlocal read
            if not read: read=True; return {'type':'http.request','body':json.dumps(payload or {'url':PAGE['url']}).encode()}
            await asyncio.Event().wait()
        async def send(x): sent.append(x)
        await mode(scope,receive,send)
        return sent
    def mode(self):
        mode=super().mode(); mode.pages=AsyncMock(); mode.pages.read.return_value=PAGE
        # Inherited assertions refer to web.search: alias only in test fixture.
        mode.web.search=mode.pages.read
        return mode
