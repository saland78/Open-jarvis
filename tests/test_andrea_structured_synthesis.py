"""Contract checks exercise rejection, not a semantic accuracy oracle."""
import importlib.util
import io
import json
from pathlib import Path
import unittest
from contextlib import redirect_stdout

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('structured_probe', ROOT / 'scripts/andrea/structured_synthesis_probe.py')
probe = importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)
SOURCE = [{'id':'N1','text':'Al 2026-10-01 le royalty sono DATO NON VERIFICATO in questa nota.'}]


def answer(text, refs=None):
    return json.dumps({'scope':'provided_excerpts','claims':[{'text':text,'sources':['N1'] if refs is None else refs}]})


class ContractTests(unittest.TestCase):
    def test_original_quote_attached_locally_without_model_rewriting(self):
        r = probe.validate_contract(answer('Al 2026-10-01 la nota non verifica le royalty.'), SOURCE, completed=True)
        self.assertEqual(r['status'], 'valid_structure_pending_semantic_review')
        self.assertEqual(r['claims'][0]['supports'][0]['quote'], SOURCE[0]['text'])
        self.assertIs(r['externalTruthVerified'], False)

    def test_unknown_duplicate_and_unlinked_embedded_sources_rejected(self):
        for refs in (['N9'], ['N1','N1'], [], [True]):
            r=probe.validate_contract(answer('dato',refs), SOURCE, completed=True)
            self.assertEqual(r['status'],'rejected'); self.assertEqual(r['claims'],[])
        self.assertEqual(probe.validate_contract(answer('dato [N2]'),SOURCE,completed=True)['status'],'rejected')

    def test_invented_date_rejected_but_date_association_not_certified(self):
        self.assertEqual(probe.validate_contract(answer('Nel 2027-10-01'),SOURCE,completed=True)['status'],'rejected')
        wrong=probe.validate_contract(answer('Il 2026-10-01 furono incassati 1000 euro verificati.'),SOURCE,completed=True)
        self.assertEqual(wrong['status'],'valid_structure_pending_semantic_review')
        self.assertEqual(wrong['semanticVerdict'],'pending_review')

    def test_duplicate_keys_extra_fields_markdown_non_objects_and_oversize_rejected(self):
        bad=['{"scope":"provided_excerpts","scope":"external","claims":[]}',
             '{"scope":"provided_excerpts","claims":[],"verified":true}',
             '```json\n{"scope":"provided_excerpts","claims":[]}\n```',
             '[]', '{"scope":"provided_excerpts","claims":false}', 'x'*32001,
             json.dumps({'scope':'provided_excerpts','claims':[{'text':'dato','sources':['N1'],'quote':'inventata'}]})]
        for raw in bad:
            self.assertEqual(probe.validate_contract(raw,SOURCE,completed=True)['status'],'rejected')

    def test_empty_abstention_not_success_and_partial_valid_json_rejected(self):
        raw=json.dumps({'scope':'provided_excerpts','claims':[]})
        self.assertEqual(probe.validate_contract(raw,SOURCE,completed=True)['status'],'abstained')
        self.assertEqual(probe.validate_contract(answer('dato'),SOURCE,completed=False)['status'],'rejected')
        many=json.dumps({'scope':'provided_excerpts','claims':[{'text':'dato','sources':['N1']}]*3})
        self.assertEqual(probe.validate_contract(many,SOURCE,completed=True)['status'],'rejected')

    def test_four_actual_http_calls_json_mode_same_limits_runtime_unchanged(self):
        from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
        from threading import Thread
        from urllib.request import build_opener,ProxyHandler
        calls=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));calls.append(body)
                self.send_response(200);self.end_headers()
                for event in ({'message':{'content':answer('Negli estratti il dato non è verificato.')}},
                              {'done':True,'done_reason':'stop','private_id':'PRIVATE'}):
                    self.wfile.write(json.dumps(event).encode()+b'\n');self.wfile.flush()
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        previous=probe.BASE;before=(ROOT/'scripts/andrea/runtime.py').read_bytes()
        try:
            probe.BASE=f'http://127.0.0.1:{server.server_port}'
            with redirect_stdout(io.StringIO()): report=probe.collect(build_opener(ProxyHandler({})),probe.messages_from_runtime(ROOT))
            self.assertEqual(len(calls),4)
            self.assertEqual((ROOT/'scripts/andrea/runtime.py').read_bytes(),before)
            for call in calls:
                self.assertEqual(call['format'],'json')
                self.assertEqual(call['options'],{'temperature':.4,'num_predict':512,'num_ctx':4096})
                self.assertEqual(call['keep_alive'],'15m');self.assertIs(call['think'],False)
                self.assertEqual(call['model'],probe.MODEL)
            self.assertTrue(all(r['status']=='completed' for r in report['rows']))
            self.assertTrue(all(r['contract']['semanticVerdict']=='pending_review' for r in report['rows']))
            self.assertNotIn('PRIVATE',json.dumps(report))
            self.assertFalse(report['runtimeChanged']);self.assertFalse(report['vaultRead'])
            self.assertIn('not_adopted',report['decision'])
        finally:
            probe.BASE=previous;server.shutdown();server.server_close();thread.join()

    def test_error_stops_without_retry_and_hides_server_error(self):
        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self,*args): self.close()
        class Opener:
            calls=0
            def open(self,*args,**kwargs):
                self.calls+=1;return Response(b'{"error":"PRIVATE ERROR"}\n')
        opener=Opener()
        with redirect_stdout(io.StringIO()): r=probe.collect(opener,probe.messages_from_runtime(ROOT))
        self.assertEqual(opener.calls,1);self.assertEqual(r['automaticRetries'],0)
        self.assertEqual(r['rows'][0]['contract']['status'],'rejected')
        self.assertNotIn('PRIVATE',json.dumps(r))

    def test_reopening_fixture_explicitly_names_cover_in_both_sources(self):
        case=next(c for c in probe.CASES if c['id']=='reopened')
        self.assertTrue(all('copertina' in s['text'] for s in case['sources']))
        self.assertIn('2026-08-20',case['sources'][0]['text'])
        self.assertIn('2026-10-01',case['sources'][1]['text'])


if __name__=='__main__': unittest.main()
