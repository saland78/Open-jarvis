"""Browser abort completes ASGI normally; server shutdown still cancels."""
import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch
import runtime
import web_search_local as web
from test_andrea_web_search_local import Process

class DisconnectTests(unittest.IsolatedAsyncioTestCase):
    async def test_browser_disconnect_stops_worker_and_releases_request(self):
        process=Process(block=True)
        mode=runtime.LocalMode(AsyncMock(),'local',8008,web=web.LocalWebSearch())
        scope={'type':'http','method':'POST','path':'/api/andrea/web/search','headers':[(b'host',b'127.0.0.1:8008'),(b'origin',b'http://127.0.0.1:8008'),(b'content-type',b'application/json')]}
        calls=0; sent=[]
        async def receive():
            nonlocal calls
            calls+=1
            if calls==1:return {'type':'http.request','body':json.dumps({'query':'public','provider':'duckduckgo'}).encode()}
            await asyncio.sleep(.01)
            return {'type':'http.disconnect'}
        async def send(event):sent.append(event)
        with patch.object(web.asyncio,'create_subprocess_exec',AsyncMock(return_value=process)) as spawn:
            await mode(scope,receive,send)
        self.assertTrue(process.killed);self.assertEqual(spawn.await_count,1)
        self.assertFalse(mode.busy);self.assertEqual(sent,[])
        mode.web=AsyncMock();mode.web.search.return_value={'sources':[]}
        from test_andrea_web_search_local import RouteTests
        response=await RouteTests().request(mode)
        self.assertEqual(response[0]['status'],200)

    async def test_server_cancellation_is_not_swallowed(self):
        mode=runtime.LocalMode(AsyncMock(),'local',8008,web=AsyncMock())
        entered=asyncio.Event(); closed=[]
        async def search(payload):
            entered.set()
            try:await asyncio.Event().wait()
            finally:closed.append(True)
        mode.web.search.side_effect=search
        from test_andrea_web_search_local import RouteTests
        task=asyncio.create_task(RouteTests().request(mode))
        await entered.wait();task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertFalse(mode.busy);self.assertEqual(closed,[True])

    async def test_read_and_summary_disconnect_share_cleanup(self):
        for path in ['/api/andrea/web/read','/api/andrea/web/summarize']:
            pages=AsyncMock();mode=runtime.LocalMode(AsyncMock(),'local',8008,pages=pages)
            closed=[]
            async def pending(*args):
                try:await asyncio.Event().wait()
                finally:closed.append(True)
            pages.read.side_effect=pending;pages.summarize.side_effect=pending
            scope={'type':'http','method':'POST','path':path,'headers':[(b'host',b'127.0.0.1:8008'),(b'origin',b'http://127.0.0.1:8008'),(b'content-type',b'application/json')]}
            calls=0;sent=[]
            async def receive():
                nonlocal calls
                calls+=1
                if calls==1:return {'type':'http.request','body':b'{}'}
                await asyncio.sleep(.001);return {'type':'http.disconnect'}
            async def send(event):sent.append(event)
            await mode(scope,receive,send)
            self.assertEqual(closed,[True]);self.assertEqual(sent,[]);self.assertFalse(mode.busy)
