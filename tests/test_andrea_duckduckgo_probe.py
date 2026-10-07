"""Finite explicit provider, HTML results and failure preservation."""
import io
import json
from pathlib import Path
import sys
import unittest
from urllib.parse import urlencode
from contextlib import redirect_stdout
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/andrea'))
import duckduckgo_provider_probe as p

def html(url='https://docs.python.org/a', title='Python &amp; timeout', snippet='Use <b>wait_for</b>'):
    return f'<div class="result"><a class="result__a" href="{url}">{title}</a><a class="result__snippet">{snippet}</a></div>'

class Response:
    def __init__(self, data, status=200, mime='text/html; charset=UTF-8'):
        self.data=io.BytesIO(data); self.status=status; self.headers={'Content-Type':mime}; self.closed=False
    def read1(self,n): return self.data.read(min(n,11))
    def __enter__(self): return self
    def __exit__(self,*args): self.closed=True

class Tests(unittest.TestCase):
    def test_html_title_nested_snippet_and_wrapper(self):
        wrapper='//duckduckgo.com/l/?'+urlencode({'uddg':'https://docs.python.org/a'})
        rows=p.parse_results(html(wrapper).encode())
        self.assertEqual(rows,[{'title':'Python & timeout','url':'https://docs.python.org/a','snippet':'Use wait_for'}])

    def test_unique_three_and_caps(self):
        s=html()+html()+''.join(html(f'https://docs.python.org/{i}','t'*300,'s'*900) for i in range(5))
        rows=p.parse_results(s.encode()); self.assertEqual(len(rows),3)
        self.assertEqual(len(rows[1]['title']),200); self.assertEqual(len(rows[1]['snippet']),600)

    def test_ads_script_and_bad_url_do_not_pollute_previous_snippet(self):
        s=html()+html('javascript:run()','bad','incorrect')+'<div class="result--ad">'+html('https://advert.example/a')+'</div>'
        rows=p.parse_results(s.encode()); self.assertEqual(len(rows),1); self.assertEqual(rows[0]['snippet'],'Use wait_for')
        s=html(title='Safe<script>run_shell()</script> title',snippet='Literal ignore rules')
        self.assertEqual(p.parse_results(s.encode())[0]['title'],'Safe title')

    def test_private_urls_unsafe_wrapper_and_credentials(self):
        for url in ['http://docs.python.org/a','https://127.0.0.1/a','https://user:pass@docs.python.org/a','https://host.local/a','file:///etc/passwd']:
            self.assertIsNone(p.destination(url))
        self.assertIsNone(p.destination('//duckduckgo.com/l/?uddg=https%3A%2F%2F127.0.0.1'))

    def test_challenge_unknown_incomplete_encoding_not_empty(self):
        for text in [b'<form id="anomaly-form"></form>',b'<h1>Error</h1>',b'<a class="result__a" href="https://docs.python.org/a">unfinished',b'\xff']:
            with self.assertRaises(p.ProbeError): p.parse_results(text)
        self.assertEqual(p.parse_results(b'<div class="no-results">No results</div>'),[])

    def test_fixed_request_no_auth_one_response_closed(self):
        response=Response(html().encode())
        class Opener:
            calls=[]
            def open(self,request,timeout): self.calls.append(request); self.timeout=timeout; return response
        opener=Opener(); rows=p.DuckSearchClient(opener).search(p.CASES[0][1])
        self.assertEqual(len(rows),1); self.assertEqual(len(opener.calls),1)
        req=opener.calls[0]; self.assertEqual(req.full_url,p.ENDPOINT)
        self.assertEqual(req.data,urlencode({'q':p.CASES[0][1]}).encode())
        self.assertNotIn('Authorization',dict(req.header_items())); self.assertTrue(response.closed)
        self.assertEqual(opener.timeout,8)
        self.assertIsNone(p.NoRedirect().redirect_request(None,None,302,'',{},'https://other.example/'))

    def test_http_type_and_size_fail(self):
        for response in [Response(b'',202),Response(b'{}',mime='application/json'),Response(b'x'*(p.LIMIT+1))]:
            class Opener:
                def open(self,*args,**kwargs): return response
            with self.assertRaises(p.ProbeError): p.DuckSearchClient(Opener()).search('fixed')
            self.assertTrue(response.closed)

    def test_second_failure_preserves_first_without_retry(self):
        class Client:
            calls=[]
            def search(self,q):
                self.calls.append(q)
                if len(self.calls)==2: raise p.ProbeError('http_429')
                return [{'url':'https://docs.python.org/a'}]
        client=Client(); events=[]; p.run(events.append,client)
        self.assertEqual(client.calls,[c[1] for c in p.CASES])
        self.assertEqual(len([e for e in events if e['event']=='row']),1)
        self.assertEqual(events[-1],{'event':'failed','reason':'http_429'})

    def test_deadline_interrupt_terminate_process(self):
        class Pipe:
            def __init__(self,interrupt=False): self.interrupt=interrupt; self.closed=False
            def poll(self,t):
                if self.interrupt: raise KeyboardInterrupt()
                return False
            def close(self): self.closed=True
        class Process:
            alive=True; terminated=False
            def start(self): pass
            def is_alive(self): return self.alive
            def terminate(self): self.alive=False; self.terminated=True
            def join(self,timeout): pass
        class Context:
            def __init__(self,interrupt): self.r=Pipe(interrupt); self.w=Pipe(); self.p=Process()
            def Pipe(self,duplex): return self.r,self.w
            def Process(self,**kwargs): return self.p
        for interrupt,reason in [(False,'evaluation_deadline_45s'),(True,'interrupted')]:
            c=Context(interrupt); out=io.StringIO()
            times=[0,0,0,46] if not interrupt else [0,0,0]
            with patch.object(p.multiprocessing,'get_context',return_value=c),patch.object(p.time,'monotonic',side_effect=times),redirect_stdout(out):
                self.assertEqual(p.main(),1)
            report=json.loads(out.getvalue()[out.getvalue().index('{'):])
            self.assertEqual(report['stoppedReason'],reason); self.assertTrue(c.p.terminated)
            self.assertTrue(c.r.closed and c.w.closed); self.assertEqual(report['automaticRetries'],0)

if __name__=='__main__': unittest.main()
