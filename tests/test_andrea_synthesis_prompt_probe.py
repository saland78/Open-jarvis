"""Finite experiment transport tests; no actual model quality asserted."""
import importlib.util
import io
import json
from pathlib import Path
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.request import build_opener, ProxyHandler
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('prompt_probe',ROOT/'scripts/andrea/synthesis_prompt_probe.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
validator=probe.load_validator(ROOT)
make=probe.messages_from_runtime(ROOT)


class PromptProbeTests(unittest.TestCase):
    def test_proposal_preserves_sources_query_and_mandatory_contexts(self):
        for case in probe.CASES:
            before=json.dumps(case,sort_keys=True)
            current=validator.make_coverage_messages(make,case)
            proposed=probe.proposal_messages(make,validator,case)
            self.assertEqual(current[1],proposed[1])
            self.assertEqual(json.dumps(case,sort_keys=True),before)
            self.assertIn('mantieni giorno e mese senza aggiungere',proposed[0]['content'])
            self.assertNotIn('in massimo sei frasi',proposed[0]['content'])
            self.assertNotIn('Per questa prova',proposed[0]['content'])
            if case['id']=='dated_qualifications':
                self.assertIn('mandatory_contexts',proposed[1]['content'])
                self.assertIn('mandatory_contexts sono vincoli',proposed[0]['content'])

    def test_four_http_requests_same_options_and_pending_quality(self):
        calls=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                calls.append(payload)
                data=json.loads(payload['messages'][1]['content'])
                if 'mandatory_contexts' in data:
                    claims=[{'text':f"Al {c['date']}: {c['qualification']} nella nota.", 'sources':['N1']} for c in data['mandatory_contexts']]
                else:
                    claims=[{'text':'Romanzo di avventura in italiano, 11 capitoli e circa 8.500 parole. Cartaceo dal 4 marzo 2027, digitale dal 16 marzo, copertina online dal 21 aprile.','sources':['N1']}]
                self.send_response(200);self.end_headers()
                for event in ({'message':{'content':json.dumps({'scope':'provided_excerpts','claims':claims})}},
                              {'done':True,'done_reason':'stop','eval_count':50,'eval_duration':1000000000}):
                    self.wfile.write(json.dumps(event).encode()+b'\n');self.wfile.flush()
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        previous=probe.BASE
        try:
            probe.BASE=f'http://127.0.0.1:{server.server_port}'
            with redirect_stdout(io.StringIO()):report=probe.collect(build_opener(ProxyHandler({})),make,validator)
            self.assertEqual(len(calls),4)
            self.assertEqual(report['attempted'],4)
            self.assertEqual(report['automaticRetries'],0)
            self.assertFalse(report['vaultRead']);self.assertFalse(report['runtimeChanged'])
            self.assertEqual(report['decision'],'not_adopted')
            for call,row in zip(calls,report['rows']):
                self.assertEqual(call['model'],probe.MODEL)
                self.assertEqual(call['options'],{'temperature':.4,'num_predict':512,'num_ctx':4096})
                self.assertEqual(call['format'],'json');self.assertFalse(call['think'])
                self.assertEqual(call['keep_alive'],'15m')
                self.assertEqual(row['status'],'completed')
                self.assertEqual(row['contract']['status'],'valid_structure_pending_semantic_review')
                self.assertEqual(row['qualityVerdict'],'pending_review')
        finally:
            probe.BASE=previous;server.shutdown();server.server_close();thread.join()

    def test_errors_stop_without_retries_or_automatic_adoption(self):
        from unittest.mock import patch
        with patch.object(probe,'stream_probe',return_value={'status':'error','syntheticAnswer':None}),redirect_stdout(io.StringIO()):
            report=probe.collect(None,make,validator)
        self.assertEqual(report['attempted'],1)
        self.assertEqual(report['decision'],'not_adopted')
        self.assertEqual(report['rows'][0]['contract']['status'],'rejected')

    def test_validator_unchanged_and_bad_hash_refuses(self):
        from unittest.mock import patch
        with patch.object(probe,'EXPECTED_VALIDATOR','0'*64):
            with self.assertRaises(ValueError):probe.load_validator(ROOT)
        with patch.object(probe,'EXPECTED_RUNTIME','0'*64):
            with self.assertRaises(ValueError):probe.messages_from_runtime(ROOT)
        result=validator.validate_contract(json.dumps({'scope':'provided_excerpts','claims':[{'text':'Online dal 21 aprile 2 2027.','sources':['N1']}]}),probe.CASES[0]['sources'],completed=True)
        self.assertEqual(result['status'],'rejected')
        self.assertEqual(result['reason'],'date_check_failed')
