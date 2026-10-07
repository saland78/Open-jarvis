"""Schema binding and real HTTP transport; synthetic engine, not model quality."""
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.request import build_opener, ProxyHandler
from pathlib import Path
import copy
import importlib.util
import io
import json
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('typed_probe',ROOT/'scripts/andrea/typed_synthesis_probe.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
validator=probe.load_validator(ROOT)
base=probe.messages_from_runtime(ROOT)


def typed_value(case,plan):
    return {'scope':'provided_excerpts','contexts':{
        c['kind']:{key:c[key] for key in ('date','qualification','sourceId')}|{'text':
            'Vendite e royalty aggiornate nella nota.' if c['kind']=='update' else 'Copie e royalty nella fotografia storica.'}
        for c in plan['contexts']['contexts']}}


class TypedSynthesisTests(unittest.TestCase):
    def test_schema_fixes_each_context_field_and_keeps_sources(self):
        case=probe.CASES[1];before=copy.deepcopy(case);p=probe.plan(case,validator)
        fields=p['schema']['properties']['contexts']['properties']
        for c in p['contexts']['contexts']:
            record=fields[c['kind']]
            self.assertEqual(set(record['required']),{'date','qualification','sourceId','text'})
            self.assertFalse(record['additionalProperties'])
            for key in ('date','qualification','sourceId'):
                self.assertEqual(record['properties'][key]['enum'],[c[key]])
        messages=probe.make_messages(base,validator,case,p)
        self.assertEqual(json.loads(messages[1]['content'])['estratti'],case['sources'])
        self.assertEqual(case,before)
        self.assertIn('response_schema',messages[1]['content'])

    def test_valid_fields_composed_with_model_text_and_existing_checks(self):
        case=probe.CASES[1];p=probe.plan(case,validator)
        value=typed_value(case,p)
        r=probe.validate_typed(json.dumps(value),case,p,validator,completed=True)
        self.assertEqual(r['status'],'valid_structure_pending_semantic_review')
        self.assertEqual(r['contextCoverage'],'complete_for_recognized_conventions')
        self.assertEqual(r['semanticVerdict'],'pending_review')
        self.assertEqual(r['composition'],'source_bound_metadata_with_model_text')
        text=validator.render_contract(r)
        for c in p['contexts']['contexts']:
            self.assertIn(c['date'],text);self.assertIn(c['qualification'],text)
        self.assertIn('[N1]',text)

    def test_missing_swapped_or_extra_fields_rejected_not_completed_by_renderer(self):
        case=probe.CASES[1];p=probe.plan(case,validator);good=typed_value(case,p)
        bad=[]
        x=copy.deepcopy(good);del x['contexts']['update']['date'];bad.append(x)
        x=copy.deepcopy(good);x['contexts']['update']['date']='2027-03-01';bad.append(x)
        x=copy.deepcopy(good);x['contexts']['snapshot']['qualification']='DATO NON VERIFICATO';bad.append(x)
        x=copy.deepcopy(good);x['contexts']['update']['sourceId']='N9';bad.append(x)
        x=copy.deepcopy(good);x['contexts']['update']['other']='x';bad.append(x)
        x=copy.deepcopy(good);x['contexts']['update']['text']='';bad.append(x)
        for x in bad:
            self.assertEqual(probe.validate_typed(json.dumps(x),case,p,validator,completed=True)['status'],'rejected')
        self.assertEqual(probe.validate_typed(json.dumps(good),case,p,validator,completed=False)['status'],'rejected')

    def test_prose_cannot_override_date_or_qualification_fields(self):
        case=probe.CASES[1];p=probe.plan(case,validator)
        for prose in ('Il dato risulta DATO ASSENTE.', 'Situazione verificata il 2030-01-01.', 'Fonte [N9].'):
            x=typed_value(case,p);x['contexts']['update']['text']=prose
            self.assertEqual(probe.validate_typed(json.dumps(x),case,p,validator,completed=True)['status'],'rejected')

    def test_generic_bad_dates_still_refused_and_semantics_not_certified(self):
        case=probe.CASES[0];p=probe.plan(case,validator)
        raw=json.dumps({'scope':'provided_excerpts','claims':[{'text':'Online dal 21 aprile 2 2027.','sources':['N1']}]})
        self.assertEqual(probe.validate_typed(raw,case,p,validator,completed=True)['status'],'rejected')
        # Technical fields cannot certify financial assertions: review is mandatory.
        case=probe.CASES[1];p=probe.plan(case,validator);x=typed_value(case,p)
        x['contexts']['update']['text']='La dashboard conferma 1000 euro.'
        self.assertEqual(probe.validate_typed(json.dumps(x),case,p,validator,completed=True)['semanticVerdict'],'pending_review')

    def test_four_http_requests_send_schema_without_tools_or_option_changes(self):
        calls=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                calls.append(payload)
                user=json.loads(payload['messages'][1]['content'])
                case=next(c for c in probe.CASES if c['query']==user['richiesta'])
                p=probe.plan(case,validator)
                if p['contexts']['status']=='required':value=typed_value(case,p)
                else:value={'scope':'provided_excerpts','claims':[{'text':'Gli estratti contengono informazioni nella nota.','sources':['N1']}]}
                self.send_response(200);self.end_headers()
                for event in ({'message':{'content':json.dumps(value)}},{'done':True,'done_reason':'stop'}):
                    self.wfile.write(json.dumps(event).encode()+b'\n');self.wfile.flush()
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=Thread(target=server.serve_forever,daemon=True);thread.start();before=probe.BASE
        try:
            probe.BASE=f'http://127.0.0.1:{server.server_port}'
            with redirect_stdout(io.StringIO()):r=probe.collect(build_opener(ProxyHandler({})),base,validator)
            self.assertEqual(len(calls),4);self.assertEqual(r['automaticRetries'],0)
            self.assertFalse(r['runtimeChanged']);self.assertFalse(r['vaultRead'])
            self.assertEqual(r['decision'],'not_adopted')
            for call,row in zip(calls,r['rows']):
                self.assertIsInstance(call['format'],dict)
                self.assertEqual(call['format'],json.loads(call['messages'][1]['content'])['response_schema'])
                self.assertEqual(call['options'],{'temperature':.4,'num_predict':512,'num_ctx':4096})
                self.assertEqual(call['model'],probe.MODEL);self.assertFalse(call['think'])
                self.assertNotIn('tools',call);self.assertEqual(call['keep_alive'],'15m')
                self.assertEqual(row['qualityVerdict'],'pending_review')
        finally:probe.BASE=before;server.shutdown();server.server_close();thread.join()

    def test_two_previous_case_inputs_and_criteria_unchanged(self):
        spec=importlib.util.spec_from_file_location('previous_probe',ROOT/'scripts/andrea/synthesis_prompt_probe.py')
        previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
        self.assertEqual(probe.CASES[:2],previous.CASES)
