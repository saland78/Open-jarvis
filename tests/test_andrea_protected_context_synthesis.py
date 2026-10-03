"""Protected context metadata is program-rendered, not a model ability claim."""
from pathlib import Path
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
from urllib.request import build_opener,ProxyHandler
import hashlib
import importlib.util
import json
import io
import unittest
ROOT=Path(__file__).resolve().parents[1]/'scripts/andrea'
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
p=load('protected_context_probe')
v=p.load_validator(ROOT.parents[1])

def value(plan):
    return {'records':{f['id']:{'text':f['quote']} |
        ({'contextDate':f['contextDate']} if 'contextDate' in f else {}) for f in plan['facts']}}

class ProtectedContextTests(unittest.TestCase):
    def test_two_case_inputs_and_criteria_unchanged(self):
        old=load('fact_grounded_synthesis_probe')
        self.assertEqual(p.CASES,old.CASES)

    def test_distinct_book_date_roles_and_spans(self):
        plan=p.synthesis.prepare(p.CASES[0],p.composer)
        self.assertEqual([f['kind'] for f in plan['facts'][1:]],
            ['paper_edition_start','digital_edition_start','cover_online_date'])
        for fact in plan['facts']:
            source=p.CASES[0]['sources'][0]['text']
            self.assertEqual(source[fact['start']:fact['end']],fact['quote'])

    def test_dates_required_fixed_in_schema(self):
        plan=p.synthesis.prepare(p.CASES[1],p.composer)
        for fact in plan['facts']:
            field=plan['schema']['properties']['records']['properties'][fact['id']]
            self.assertEqual(field['properties']['contextDate']['enum'],[fact['contextDate']])
            self.assertIn('contextDate',field['required'])
            self.assertIn(fact['contextDate'],fact['quote'])

    def test_model_body_retained_and_dates_rendered_from_bound_fields(self):
        case=p.CASES[1];plan=p.synthesis.prepare(case,p.composer);raw=value(plan)
        raw['records']['F1']['text']='Vendite e royalty sono DATO NON VERIFICATO nella nota.'
        raw['records']['F2']['text']='Copie e royalty sono DATO ASSENTE nella fotografia storica.'
        result=p.synthesis.validate(json.dumps(raw),case,plan,v,completed=True)
        self.assertEqual(result['status'],'valid_structure_pending_semantic_review')
        self.assertEqual(result['composition'],'model_text_with_source_bound_context_dates')
        answer=p.synthesis.render(result)
        for fact in plan['facts']: self.assertIn(fact['contextDate'],answer)
        for record in raw['records'].values(): self.assertIn(record['text'],answer)
        self.assertEqual(result['semanticVerdict'],'pending_review')

    def test_missing_or_changed_date_refuses_not_filled(self):
        case=p.CASES[1];plan=p.synthesis.prepare(case,p.composer)
        for date in (None,'2027-03-01'):
            raw=value(plan)
            if date is None: del raw['records']['F1']['contextDate']
            else: raw['records']['F1']['contextDate']=date
            self.assertEqual(p.synthesis.validate(json.dumps(raw),case,plan,v,completed=True)['status'],'rejected')

    def test_value_updates_and_cover_edition_refuse(self):
        case=p.CASES[1];plan=p.synthesis.prepare(case,p.composer);raw=value(plan)
        raw['records']['F1']['text']='Vendite e royalty aggiornate DATO NON VERIFICATO.'
        self.assertEqual(p.synthesis.validate(json.dumps(raw),case,plan,v,completed=True)['reason'],'unsupported_value_update')
        case=p.CASES[0];plan=p.synthesis.prepare(case,p.composer);raw=value(plan)
        raw['records']['F4']['text']='Copertina rifatta e versione online dal 21 aprile.'
        self.assertEqual(p.synthesis.validate(json.dumps(raw),case,plan,v,completed=True)['reason'],'edition_in_cover_fact')

    def test_other_two_paths_identical_to_previous_probe(self):
        expected={'historical':'c56d921f9a0e3b1518541d2ab8790d32a174ec082734601df6d45c6195495388',
                  'missing_with_instruction':'bf0720a4f52e5f68e8cb45772cb1ea8940e67e163137201f8fa8b455a828b53d'}
        old=load('fact_grounded_synthesis_probe')
        for case in p.CASES[2:]:
            plan=p.synthesis.prepare(case,p.composer)
            data=json.dumps({'plan':plan,'messages':p.synthesis.messages(case,plan)},sort_keys=True,ensure_ascii=False).encode()
            self.assertEqual(hashlib.sha256(data).hexdigest(),expected[case['id']])
            raw=json.dumps(value(plan))
            previous=old.synthesis.validate(raw,case,plan,v,completed=True)
            current=p.synthesis.validate(raw,case,plan,v,completed=True)
            self.assertEqual(previous['claims'],current['claims'])
            self.assertEqual(old.synthesis.render(previous),p.synthesis.render(current))

    def test_two_http_requests_with_bound_dates_no_retries_or_option_changes(self):
        calls=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                calls.append(payload)
                user=json.loads(payload['messages'][1]['content'])
                case=next(c for c in p.CASES if c['query']==user['richiesta'])
                plan=p.synthesis.prepare(case,p.composer)
                self.send_response(200);self.end_headers()
                for event in ({'message':{'content':json.dumps(value(plan))}},
                              {'done':True,'done_reason':'stop'}):
                    self.wfile.write(json.dumps(event).encode()+b'\n');self.wfile.flush()
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=Thread(target=server.serve_forever,daemon=True);thread.start();before=p.BASE
        try:
            p.BASE=f'http://127.0.0.1:{server.server_port}'
            with redirect_stdout(io.StringIO()): result=p.collect(build_opener(ProxyHandler({})),v)
            self.assertEqual(len(calls),2);self.assertEqual(result['requested'],2)
            self.assertEqual(result['automaticRetries'],0)
            self.assertFalse(result['runtimeChanged']);self.assertFalse(result['vaultRead'])
            for call,row in zip(calls,result['rows']):
                self.assertEqual(call['options'],{'temperature':.4,'num_predict':512,'num_ctx':4096})
                self.assertEqual(call['format'],json.loads(call['messages'][1]['content'])['response_schema'])
                self.assertNotIn('tools',call)
                self.assertEqual(row['contract']['semanticVerdict'],'pending_review')
        finally:
            p.BASE=before;server.shutdown();server.server_close();thread.join()

if __name__=='__main__': unittest.main()
