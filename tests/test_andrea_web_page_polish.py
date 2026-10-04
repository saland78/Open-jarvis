"""Extraction regressions from semantic and Sphinx-like page structures."""
import asyncio
import json
from types import SimpleNamespace as Chunk
import unittest
import web_page_fetch as fetch
import web_page_local as pages
from native_metrics import capture

BODY = 'Il documento descrive due titoli pubblicati nel 2026. Vendite e royalty non verificate. Il valore assente non significa zero.'

class ExtractionTests(unittest.TestCase):
    def extract(self, html): return fetch.extract(html.encode(), 'text/html')[1]

    def test_sphinx_role_main_preserves_meaning_and_removes_chrome(self):
        html = '<title>Documento</title><div class="related" role="navigation">Navigation index modules next Theme</div><div class="sphinxsidebar">Menus</div><div class="body" role="main"><h1>Titolo<a class="headerlink">¶</a></h1><p>'+BODY+'</p></div><div class="footer">Copyright navigation</div>'
        result = self.extract(html)
        self.assertEqual(result, 'Titolo\n'+BODY)
        self.assertNotIn('Navigation',result); self.assertNotIn('Menus',result); self.assertNotIn('¶',result)

    def test_semantic_main_excludes_outside_text_without_truncating_first(self):
        html='<div>'+('menu '*2000)+'</div><main><p>'+BODY+'</p></main><p>Related topic</p>'
        title,text,partial=fetch.extract(html.encode(),'text/html')
        self.assertEqual(text,BODY);self.assertFalse(partial)

    def test_article_header_in_main_kept_but_nested_navigation_removed(self):
        html='<main><article><header><h1>Informazioni datate</h1></header><p>'+BODY+'</p><div role="navigation"><span>Menu</span></div></article></main>'
        text=self.extract(html)
        self.assertIn('Informazioni datate',text);self.assertIn(BODY,text);self.assertNotIn('Menu',text)

    def test_fallback_page_without_main_keeps_article_content(self):
        html='<div role="banner">Top</div><div class="breadcrumbs">Links</div><article><h1>Nota</h1><p>'+BODY+'</p></article><div role="contentinfo">Footer</div>'
        self.assertEqual(self.extract(html),'Nota\n'+BODY)

    def test_hidden_void_selfclosing_and_nested_blocks_do_not_hide_next_content(self):
        html='<main><img hidden><div hidden><br><div>SECRET</div></div><script>BAD</script><div style="display: none">HIDDEN</div><div hidden/><p>'+BODY+'</p></main>'
        self.assertEqual(self.extract(html),BODY)

    def test_empty_main_does_not_invent_content_from_outside(self):
        with self.assertRaisesRegex(fetch.PageError,'no_readable_text'):
            self.extract('<main></main><p>'+BODY+'</p>')

    def test_plain_text_and_quotes_remain_unchanged(self):
        _,text,partial=fetch.extract(BODY.encode(),'text/plain')
        self.assertEqual(text,BODY);self.assertFalse(partial)
        result=pages.validate_answer(json.dumps({'claims':[{'text':'Due titoli pubblicati nel 2026.', 'quote':BODY.split(' Vendite')[0]}]}),self.extract('<main><p>'+BODY+'</p></main>'),True)
        self.assertEqual(result['outcome'],'accepted_pending_semantic_review')

class TimingTests(unittest.IsolatedAsyncioTestCase):
    def service(self):
        p=pages.LocalWebPages();p.page={'pageId':'token','text':BODY};p.expires=pages.time.monotonic()+100
        return p

    async def test_native_context_load_generation_observed_without_extra_request(self):
        calls=[]
        async def stream(messages,schema):
            calls.append(True)
            await asyncio.sleep(.001)
            yield Chunk(content='{"claims":',finish_reason=None)
            capture({'done':True,'load_duration':1000000,'prompt_eval_duration':2000000,'eval_duration':3000000,'prompt_eval_count':40,'eval_count':10,'content':'SECRET'})
            yield Chunk(content='[]}',finish_reason='stop')
        result=await self.service().summarize({'pageId':'token','question':'q'},stream)
        self.assertEqual(calls,[True]);self.assertEqual(result['outcome'],'abstained')
        timings=result['timings'];self.assertEqual(timings['inputCharacters'],len(BODY))
        self.assertGreaterEqual(timings['generationMs'],timings['firstJsonMs'])
        self.assertGreaterEqual(timings['validationMs'],0)
        self.assertEqual(timings['ollamaNative']['promptEvalMs'],2)
        self.assertEqual(timings['ollamaNative']['loadMs'],1)
        self.assertEqual(timings['ollamaNative']['evalMs'],3)
        self.assertNotIn('SECRET',json.dumps(timings));self.assertNotIn(BODY,json.dumps(timings))

    async def test_missing_native_frame_is_explicit_not_reused(self):
        async def stream(messages,schema):yield Chunk(content='{"claims":[]}',finish_reason='stop')
        first=await self.service().summarize({'pageId':'token','question':'q'},stream)
        self.assertFalse(first['timings']['ollamaNative']['terminalFrameReceived'])
        self.assertIsNone(first['timings']['ollamaNative']['loadMs'])

    async def test_failure_metrics_do_not_claim_accepted_text(self):
        async def stream(messages,schema):
            yield Chunk(content='not json',finish_reason='stop')
        result=await self.service().summarize({'pageId':'token','question':'q'},stream)
        self.assertEqual(result['outcome'],'rejected');self.assertEqual(result['claims'],[])
        self.assertIn('firstJsonMs',result['timings']);self.assertNotIn('acceptedTextMs',result['timings'])
