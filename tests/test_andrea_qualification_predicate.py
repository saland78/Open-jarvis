"""Source-grounded false-positive regression, using synthetic data only."""
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
from urllib.parse import parse_qs,urlsplit
from urllib.request import build_opener,ProxyHandler
import ast
import copy
import hashlib
import io
import json
import unittest

from test_andrea_real_notes_synthesis import ROOT,load,case,answer,QUALIFICATIONS,note

p=load('qualification_predicate_probe')
old=load('real_notes_synthesis_probe')
v=p.load_validator(ROOT.parents[1])

def qualifier_response(plan):
    value=json.loads(answer(plan))
    value['records']['F3']['text']='I valori aggiornati sono DATO NON VERIFICATO: consultare dashboard o report indicando il periodo.'
    return json.dumps(value)

class PredicateTests(unittest.TestCase):
    def test_source_bundle_and_previous_probe_remain_pinned(self):
        self.assertEqual(p.ADAPTER_CODE,(ROOT/'markdown_fact_adapter.py').read_text())
        self.assertEqual(p.SYNTHESIS_CODE,(ROOT/'predicate_context_synthesis.py').read_text())
        self.assertEqual(hashlib.sha256((ROOT/'real_notes_synthesis_probe.py').read_bytes()).hexdigest(),
                         '4a328d4692455add2b521f316bbbc02e7d1b26f885405ecc71324751edef6a7e')

    def test_false_positive_reproduced_then_resolved_without_rewriting_text(self):
        c=case('qualifications');plan=p.adapter.prepare(c,'qualifications');raw=qualifier_response(plan)
        before=p.adapter.validate(raw,c,plan,old.synthesis,v,completed=True)
        after=p.adapter.validate(raw,c,plan,p.synthesis,v,completed=True)
        self.assertEqual(before['reason'],'unsupported_value_update')
        self.assertEqual(after['status'],'valid_structure_pending_semantic_review')
        self.assertEqual(after['claims'][2]['text'],json.loads(raw)['records']['F3']['text'])
        self.assertEqual(after['claims'][2]['supports'],plan['facts'][2]['proofs'])
        rendered=p.synthesis.render(after)
        self.assertIn('Aggiornamento nella nota del 2027-04-01:',rendered)
        self.assertIn('Fotografia storica del 2027-03-01:',rendered)
        self.assertEqual(after['semanticVerdict'],'pending_review')
        self.assertFalse(after['externalTruthVerified'])

    def test_claimed_updates_negations_extra_updates_and_unsourced_predicates_refuse(self):
        c=case('qualifications');plan=p.adapter.prepare(c,'qualifications')
        invalid=[
            'Le vendite e royalty sono state aggiornate: DATO NON VERIFICATO.',
            'Le royalty sono aggiornate e DATO NON VERIFICATO.',
            'I valori aggiornati non sono DATO NON VERIFICATO.',
            'Non e vero che i valori aggiornati sono DATO NON VERIFICATO.',
            'I valori aggiornati sono DATO NON VERIFICATO, ma le royalty sono state aggiornate.',
            'I dati aggiornati sono DATO NON VERIFICATO.',
            'I valori aggiornati restano DATO NON VERIFICATO.',
            'Vendite aggiornate DATO NON VERIFICATO.',
        ]
        for text in invalid:
            with self.subTest(text=text):
                value=json.loads(qualifier_response(plan));value['records']['F3']['text']=text
                result=p.adapter.validate(json.dumps(value),c,plan,p.synthesis,v,completed=True)
                self.assertEqual(result['reason'],'unsupported_value_update')
                self.assertIsNone(p.synthesis.render(result))

    def test_source_phrase_required_and_other_context_does_not_authorize_update(self):
        text='I valori aggiornati sono DATO NON VERIFICATO.'
        self.assertTrue(p.synthesis.unsupported_value_update(text,'Vendite e royalty DATO NON VERIFICATO.','current_qualification'))
        self.assertTrue(p.synthesis.unsupported_value_update(text,'Non e vero che '+text,'current_qualification'))
        self.assertTrue(p.synthesis.unsupported_value_update(text,text,'historical_qualification'))
        self.assertFalse(p.synthesis.unsupported_value_update(text,text,'current_qualification'))

    def test_dates_counts_labels_and_source_checks_still_refuse_bad_records(self):
        c=case('qualifications');plan=p.adapter.prepare(c,'qualifications')
        for change in ('date','count','label','unknown','source'):
            with self.subTest(change=change):
                value=json.loads(qualifier_response(plan));changed=copy.deepcopy(c)
                if change=='date': value['records']['F3']['contextDate']='2027-03-01'
                if change=='count': value['records']['F1']['text']='I libri pubblicati sono 0.'
                if change=='label': value['records']['F3']['text']='I valori aggiornati sono DATO ASSENTE.'
                if change=='unknown': value['records']['F5']={'text':'Dato inventato.'}
                if change=='source': changed['sources'][0]['text']='changed'
                self.assertEqual(p.adapter.validate(json.dumps(value),changed,plan,p.synthesis,v,completed=True)['status'],'rejected')

    def test_messages_schema_and_options_are_unchanged(self):
        c=case('qualifications');plan=p.adapter.prepare(c,'qualifications')
        self.assertEqual(p.synthesis.messages(c,plan),old.synthesis.messages(c,plan))
        for name in ('prepare','messages','render'):
            def function(code):
                return next(n for n in ast.parse(code).body if isinstance(n,ast.FunctionDef) and n.name==name)
            self.assertEqual(ast.dump(function(p.SYNTHESIS_CODE)),ast.dump(function(old.SYNTHESIS_CODE)))

    def test_book_and_other_synthetic_paths_retain_previous_results(self):
        c=case('book');plan=p.adapter.prepare(c,'book');raw=answer(plan)
        self.assertEqual(p.adapter.validate(raw,c,plan,p.synthesis,v,completed=True),
                         p.adapter.validate(raw,c,plan,old.synthesis,v,completed=True))
        fixtures=load('protected_context_probe')
        for c in fixtures.CASES:
            plan=fixtures.synthesis.prepare(c,fixtures.composer)
            if c['id']=='dated_qualifications':
                texts=['Vendite e royalty sono DATO NON VERIFICATO nella nota.',
                       'Copie e royalty sono DATO ASSENTE nella fotografia storica.']
                raw=json.dumps({'records':{f['id']:{'text':text,'contextDate':f['contextDate']} for f,text in zip(plan['facts'],texts)}})
            else:
                raw=json.dumps({'records':{f['id']:{'text':f['quote']} for f in plan['facts']}})
            self.assertEqual(p.synthesis.validate(raw,c,plan,v,completed=True),
                             old.synthesis.validate(raw,c,plan,v,completed=True))

    def test_technical_acceptance_is_not_a_semantic_oracle(self):
        c=case('qualifications');plan=p.adapter.prepare(c,'qualifications')
        value=json.loads(answer(plan));value['records']['F2']['text']='Vendite e royalty non variano per periodo.'
        result=p.adapter.validate(json.dumps(value),c,plan,p.synthesis,v,completed=True)
        self.assertEqual(result['status'],'valid_structure_pending_semantic_review')
        self.assertEqual(result['semanticVerdict'],'pending_review')

class OneNoteHttpTests(unittest.TestCase):
    def run_proof(self,*,changed=False,unsupported=False):
        path='Numbers/metrics.md';vault='/example/vault';reads=0;posts=[];gets=[]
        data=note(QUALIFICATIONS,path)
        if unsupported: data['text']=data['text'].replace('DATO NON VERIFICATO','unavailable')
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                nonlocal reads
                gets.append(self.path);url=urlsplit(self.path)
                if url.path.endswith('/status'):
                    value={'configured':True,'available':True,'mode':'read-only','vault':vault}
                else:
                    assert parse_qs(url.query)['path']==[path]
                    reads+=1;value=copy.deepcopy(data)
                    if changed and reads>1: value['text']+='\nChanged after inference.'
                self.send_response(200);self.end_headers();self.wfile.write(json.dumps(value).encode())
            def do_POST(self):
                value=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                posts.append(value)
                plan=p.adapter.prepare(case('qualifications'),'qualifications')
                self.send_response(200);self.end_headers()
                for event in ({'message':{'content':qualifier_response(plan)}},{'done':True,'done_reason':'stop'}):
                    self.wfile.write(json.dumps(event).encode()+b'\n');self.wfile.flush()
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=Thread(target=server.serve_forever,daemon=True);thread.start();before=(p.BASE,p.NOTES_BASE)
        try:
            p.BASE=p.NOTES_BASE=f'http://127.0.0.1:{server.server_port}'
            with redirect_stdout(io.StringIO()):
                result=p.collect(build_opener(ProxyHandler({}),p.NoRedirect()),v,vault,path)
            return result,reads,posts,gets
        finally:
            p.BASE,p.NOTES_BASE=before;server.shutdown();server.server_close();thread.join()

    def test_one_inference_same_payload_only_selected_note_read_twice(self):
        result,reads,posts,gets=self.run_proof()
        self.assertEqual(reads,2);self.assertEqual(len(posts),1)
        self.assertEqual(result['requested'],1);self.assertEqual(result['inferenceRequests'],1)
        self.assertEqual(result['automaticRetries'],0);self.assertFalse(result['productionAdoption'])
        self.assertFalse(result['runtimeChanged']);self.assertFalse(result['notesWritten'])
        self.assertEqual(posts[0]['options'],{'temperature':.4,'num_predict':512,'num_ctx':4096})
        c=case('qualifications');plan=p.adapter.prepare(c,'qualifications')
        self.assertEqual(posts[0]['messages'],old.synthesis.messages(c,plan))
        self.assertEqual(posts[0]['format'],plan['schema'])
        self.assertTrue(result['rows'][0]['sourceUnchanged'])
        self.assertEqual(result['rows'][0]['contract']['status'],'valid_structure_pending_semantic_review')
        self.assertEqual(result['rows'][0]['contract']['semanticVerdict'],'pending_review')
        self.assertNotIn('[E',result['rows'][0]['renderedAnswer'])

    def test_changed_note_refuses_without_retry(self):
        result,reads,posts,gets=self.run_proof(changed=True)
        self.assertEqual(len(posts),1)
        self.assertEqual(result['rows'][0]['contract']['reason'],'note_changed_or_unavailable')
        self.assertIsNone(result['rows'][0]['renderedAnswer'])

    def test_unsupported_source_never_calls_model(self):
        result,reads,posts,gets=self.run_proof(unsupported=True)
        self.assertEqual(reads,1);self.assertEqual(posts,[])
        self.assertEqual(result['inferenceRequests'],0)
        self.assertEqual(result['qualityVerdict'],'not_assessed')

if __name__=='__main__': unittest.main()
