"""Unchanged fixtures; actual HTTP client with synthetic inference only."""
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
from urllib.request import build_opener,ProxyHandler
from pathlib import Path
import copy
import importlib.util
import io
import json
import unittest
ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts/andrea'/f'{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
probe=load('fact_grounded_synthesis_probe')
v=probe.load_validator(ROOT)

def value(plan):
    # A test engine repeats source spans. This tests the real envelope and
    # transport, never proves paraphrase quality of the real model.
    return {'records':{f['id']:{'text':f['quote']} for f in plan['facts']}}

class FactSynthesisTests(unittest.TestCase):
    def check(self,case,raw,completed=True):
        plan=probe.synthesis.prepare(case,probe.composer)
        return probe.synthesis.validate(json.dumps(raw),case,plan,v,completed=completed)

    def test_four_inputs_criteria_unchanged_and_no_template_prose_in_prompt(self):
        old=load('typed_synthesis_probe')
        self.assertEqual(probe.CASES,old.CASES)
        for case in probe.CASES:
            before=copy.deepcopy(case)
            plan=probe.synthesis.prepare(case,probe.composer)
            self.assertEqual(plan['status'],'ready')
            user=json.loads(probe.synthesis.messages(case,plan)[1]['content'])
            self.assertEqual(user['richiesta'],case['query'])
            self.assertEqual(case,before)
            for fact in user['informazioni_obbligatorie']:
                self.assertEqual(set(fact),{'id','kind','sourceId','quote'})
                self.assertNotIn('sentence',fact)

    def test_source_supported_envelope_still_pending_semantic_review(self):
        case=probe.CASES[0];plan=probe.synthesis.prepare(case,probe.composer)
        result=self.check(case,value(plan))
        self.assertEqual(result['status'],'valid_structure_pending_semantic_review')
        self.assertEqual(result['semanticVerdict'],'pending_review')
        self.assertTrue(result['freeSynthesis'])
        self.assertEqual(result['factsCovered'],4)

    def test_each_edition_date_has_own_support(self):
        case=probe.CASES[0];plan=probe.synthesis.prepare(case,probe.composer)
        raw=value(plan)
        raw['records']['F3']['text']='Edizione digitale dal 4 marzo 2027.'
        self.assertEqual(self.check(case,raw)['reason'],'date_not_supported_by_fact')
        raw=value(plan);raw['records']['F3']['text']='Digitale dal 16 marzo 2027.'
        self.assertEqual(self.check(case,raw)['reason'],'date_not_supported_by_fact')

    def test_resolution_cannot_use_online_date(self):
        case=probe.CASES[2];plan=probe.synthesis.prepare(case,probe.composer)
        raw=value(plan);raw['records']['F2']['text']='Il problema fu risolto il 2027-03-02.'
        self.assertEqual(self.check(case,raw)['reason'],'date_not_supported_by_fact')

    def test_missing_fact_date_qualification_or_number_refuses(self):
        case=probe.CASES[1];plan=probe.synthesis.prepare(case,probe.composer)
        raw=value(plan);del raw['records']['F2']
        self.assertEqual(self.check(case,raw)['reason'],'missing_or_unknown_fact')
        raw=value(plan);raw['records']['F1']['text']='Vendite e royalty DATO NON VERIFICATO nella nota.'
        self.assertEqual(self.check(case,raw)['reason'],'required_date_missing')
        raw=value(plan);raw['records']['F1']['text']='La nota indica vendite e royalty al 2027-04-01.'
        self.assertEqual(self.check(case,raw)['reason'],'qualification_missing_or_changed')
        case=probe.CASES[0];plan=probe.synthesis.prepare(case,probe.composer);raw=value(plan)
        raw['records']['F1']['text']='Romanzo di avventura in italiano.'
        self.assertEqual(self.check(case,raw)['reason'],'required_numeric_token_missing')

    def test_injection_amount_and_implementation_echo_refuse(self):
        case=probe.CASES[3];plan=probe.synthesis.prepare(case,probe.composer)
        raw=value(plan);raw['records']['F1']['text']='Incassi 1000 euro verificati.'
        self.assertEqual(self.check(case,raw)['reason'],'numeric_token_not_in_fact')
        raw=value(plan);raw['records']['F1']['text']='Il programma le mostrerà dai campi verificati.'
        self.assertEqual(self.check(case,raw)['reason'],'metadata_or_citation_in_text')
        user=probe.synthesis.messages(case,plan)[1]['content']
        self.assertNotIn('1000',user)

    def test_incomplete_duplicate_key_extra_field_and_changed_source_refuse(self):
        case=probe.CASES[2];plan=probe.synthesis.prepare(case,probe.composer)
        raw=value(plan)
        self.assertEqual(self.check(case,raw,False)['status'],'rejected')
        raw['records']['F1']['extra']='x'
        self.assertEqual(self.check(case,raw)['reason'],'invalid_record')
        changed=copy.deepcopy(case);changed['sources'][0]['text']='different content'
        result=probe.synthesis.validate(json.dumps(value(plan)),changed,plan,v,completed=True)
        self.assertEqual(result['reason'],'source_span_changed')
        result=probe.synthesis.validate('{"records":{},"records":{}}',case,plan,v,completed=True)
        self.assertEqual(result['status'],'rejected')

    def test_wrong_semantics_can_pass_technical_guards(self):
        case=probe.CASES[2];plan=probe.synthesis.prepare(case,probe.composer)
        raw=value(plan);raw['records']['F2']['text']='Il problema non fu risolto.'
        result=self.check(case,raw)
        self.assertEqual(result['status'],'valid_structure_pending_semantic_review')
        self.assertEqual(result['semanticVerdict'],'pending_review')
        # The four mandatory record IDs are coverage of fields, not proof
        # that the generated text preserves predicates, negations or scope.

    def test_four_real_http_streams_options_schema_and_no_retry(self):
        calls=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                calls.append(payload)
                user=json.loads(payload['messages'][1]['content'])
                case=next(c for c in probe.CASES if c['query']==user['richiesta'])
                plan=probe.synthesis.prepare(case,probe.composer)
                self.send_response(200);self.end_headers()
                for event in ({'message':{'content':json.dumps(value(plan))}},
                              {'done':True,'done_reason':'stop'}):
                    self.wfile.write(json.dumps(event).encode()+b'\n');self.wfile.flush()
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=Thread(target=server.serve_forever,daemon=True);thread.start();before=probe.BASE
        try:
            probe.BASE=f'http://127.0.0.1:{server.server_port}'
            with redirect_stdout(io.StringIO()): result=probe.collect(build_opener(ProxyHandler({})),v)
            self.assertEqual(len(calls),4)
            self.assertEqual(result['automaticRetries'],0)
            self.assertFalse(result['runtimeChanged']);self.assertFalse(result['vaultRead'])
            self.assertTrue(result['modelWritesText'])
            for call,row in zip(calls,result['rows']):
                self.assertEqual(call['options'],{'temperature':.4,'num_predict':512,'num_ctx':4096})
                self.assertEqual(call['format'],json.loads(call['messages'][1]['content'])['response_schema'])
                self.assertNotIn('tools',call)
                self.assertEqual(row['contract']['semanticVerdict'],'pending_review')
        finally:
            probe.BASE=before;server.shutdown();server.server_close();thread.join()

if __name__=='__main__': unittest.main()
