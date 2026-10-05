"""Finite checks reuse only explicitly read pages through production endpoints."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('web_check',ROOT/'scripts/andrea/check_web_reliability.py')
check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)
TEXT='No automatic data type conversion is performed unless the QUOTE_NONNUMERIC format option is specified.'


class Response:
    status=200
    def __init__(self,data):self.data=json.dumps(data).encode()
    def read(self,size):return self.data[:size]
    def __enter__(self):return self
    def __exit__(self,*args):pass


class Opener:
    def __init__(self,outcomes=None,fail=False):
        self.requests=[];self.reads=0;self.summaries=0
        self.outcomes=outcomes or ['accepted_pending_semantic_review','accepted_pending_semantic_review','abstained']
        self.fail=fail
    def open(self,request,timeout):
        payload=json.loads(request.data)
        self.requests.append((request.full_url,payload,timeout))
        if self.fail:raise urllib.error.HTTPError(request.full_url,503,'unavailable',{},io.BytesIO(b'{"detail":"dns_unavailable"}'))
        if request.full_url.endswith('/read'):
            self.reads+=1
            return Response({'text':TEXT,'url':payload['url'],'pageId':'page'+str(self.reads),
                             'sourceId':'W1','modelUsed':False,'partial':False,'readMs':3})
        outcome=self.outcomes[self.summaries];self.summaries+=1
        claims=[{'text':'Una frase generata completa.','quote':TEXT,'passage':1}] if outcome=='accepted_pending_semantic_review' else []
        return Response({'pageId':payload['pageId'],'sourceId':'W1','modelUsed':True,
                         'automaticRetries':0,'qualityVerdict':'pending_review',
                         'outcome':outcome,'claims':claims,'reason':'synthetic_rejection' if outcome=='rejected' else None,
                         'details':{'diagnosticOnly':True} if outcome=='rejected' else None})


class ReliabilityCheckTests(unittest.TestCase):
    def project(self,directory):
        root=Path(directory)
        for relative,expected in check.EXPECTED.items():
            source=(ROOT/relative).read_bytes()
            self.assertEqual(hashlib.sha256(source).hexdigest(),expected)
            path=root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(source)
        return root

    def test_two_reads_three_distinct_production_summaries_no_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.project(directory)
            before={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
            opener=Opener();output=[]
            rows=check.run(root,opener,output.append)
            self.assertEqual(before,{p:p.read_bytes() for p in root.rglob('*') if p.is_file()})
        self.assertEqual((opener.reads,opener.summaries),(2,3))
        self.assertEqual(len(opener.requests),5)
        self.assertTrue(all(url.startswith(check.API+'/api/andrea/web/') for url,_,_ in opener.requests))
        reads=[payload for url,payload,_ in opener.requests if url.endswith('/read')]
        self.assertEqual(reads,[{'url':case['url']} for case in check.CASES[:2]])
        summaries=[payload for url,payload,_ in opener.requests if url.endswith('/summarize')]
        self.assertEqual([p['pageId'] for p in summaries],['page1','page2','page2'])
        self.assertTrue(all(set(p)=={'pageId','question'} for p in summaries))
        self.assertTrue(all(r['qualityVerdict']=='pending_review' for r in rows))

    def test_failed_read_stops_before_inference_without_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.project(directory);opener=Opener(fail=True)
            with self.assertRaisesRegex(check.CheckError,'dns_unavailable'):
                check.run(root,opener,lambda _:None)
        self.assertEqual(len(opener.requests),1);self.assertEqual(opener.summaries,0)

    def test_local_edit_refused_before_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.project(directory);(root/next(iter(check.EXPECTED))).write_text('changed')
            opener=Opener()
            with self.assertRaisesRegex(check.CheckError,'Versione installata diversa'):
                check.run(root,opener,lambda _:None)
            self.assertEqual(opener.requests,[])

    def test_rejection_diagnostics_preserved_without_regeneration(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.project(directory);opener=Opener(['rejected','accepted_pending_semantic_review','abstained'])
            rows=check.run(root,opener,lambda _:None)
        self.assertEqual(opener.summaries,3)
        self.assertEqual(rows[0]['outcome'],'rejected')
        self.assertEqual(rows[0]['rejectionDetails'],{'diagnosticOnly':True})
        self.assertEqual(rows[0]['qualityVerdict'],'pending_review')

    def test_missing_required_context_stops_before_second_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.project(directory);opener=Opener()
            cases=tuple({**case,'requiredContext':'THIS DOES NOT EXIST'} if i==1 else case for i,case in enumerate(check.CASES))
            with patch.object(check,'CASES',cases):
                with self.assertRaisesRegex(check.CheckError,'passaggio necessario'):
                    check.run(root,opener,lambda _:None)
        self.assertEqual(opener.summaries,1);self.assertEqual(opener.reads,2)

    def test_unknown_page_and_fabricated_quote_are_refused(self):
        page={'pageId':'page1','text':TEXT}
        result={'pageId':'page2','sourceId':'W1','modelUsed':True,'automaticRetries':0,
                'qualityVerdict':'pending_review','outcome':'accepted_pending_semantic_review','claims':[]}
        with self.assertRaises(check.CheckError):check.checked_result(result,page)
        result['pageId']='page1';result['claims']=[{'text':'Frase inventata.','quote':'Not in page'}]
        with self.assertRaisesRegex(check.CheckError,'Passaggio'):check.checked_result(result,page)

    def test_redirect_is_not_followed(self):
        handler=check.NoRedirect()
        with self.assertRaises(check.CheckError):handler.redirect_request(None,None,302,'redirect',{},'https://example.com')

    def test_requests_do_not_use_environment_proxy(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.project(directory);opener=Opener()
            with patch.object(check.urllib.request,'build_opener',return_value=opener) as build:
                check.run(root,emit=lambda _:None)
            handlers=build.call_args.args
            self.assertEqual(handlers[0].proxies,{})
            self.assertIsInstance(handlers[1],check.NoRedirect)


if __name__=='__main__':unittest.main()
