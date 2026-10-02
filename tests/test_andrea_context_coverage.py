"""Bounded coverage checks, not semantic entailment checks."""
import importlib.util
import io
import json
from pathlib import Path
import unittest
from andrea_historical_runtime import historical_messages
from contextlib import redirect_stdout

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('coverage',ROOT/'scripts/andrea/context_coverage_probe.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
SOURCES=probe.CASES[0]['sources']


def output(first='Al 2026-10-01 il dato in questa nota è DATO NON VERIFICATO.',
           second='Nella fotografia al 2026-08-20 il dato è DATO ASSENTE.'):
    return json.dumps({'scope':'provided_excerpts','claims':[
        {'text':first,'sources':['N1']}, {'text':second,'sources':['N1']}]})


class CoverageTests(unittest.TestCase):
    def test_explicit_two_contexts_extracted_without_quantity_association(self):
        r=probe.required_contexts(SOURCES)
        self.assertEqual(r['status'],'required')
        self.assertEqual([(c['date'],c['qualification']) for c in r['contexts']],
                         [('2026-10-01','DATO NON VERIFICATO'),('2026-08-20','DATO ASSENTE')])
        self.assertTrue(all(set(c)=={'sourceId','kind','date','qualification'} for c in r['contexts']))

    def test_recorded_failure_missing_dates_and_historical_label_rejected(self):
        raw=json.dumps({'scope':'provided_excerpts','claims':[{'text':'Le vendite e le royalty sono state indicate come DATO NON VERIFICATO in questa nota e non sono documentate con precisione; si consiglia di consultare la dashboard o i report KDP indicando il periodo di riferimento.','sources':['N1']}]})
        self.assertEqual(probe.validate_base_contract(raw,SOURCES,completed=True)['status'],'valid_structure_pending_semantic_review')
        r=probe.validate_contract(raw,SOURCES,completed=True)
        self.assertEqual(r['reason'],'missing_or_merged_dated_context');self.assertEqual(r['claims'],[])

    def test_complete_pairs_allowed_but_semantics_remain_pending(self):
        r=probe.validate_contract(output(),SOURCES,completed=True)
        self.assertEqual(r['contextCoverage'],'complete_for_recognized_conventions')
        self.assertEqual(r['semanticVerdict'],'pending_review')
        wrong=output('Al 2026-10-01 la dashboard ha DATO NON VERIFICATO e nessun ricavo.')
        self.assertEqual(probe.validate_contract(wrong,SOURCES,completed=True)['semanticVerdict'],'pending_review')

    def test_swapped_dates_merged_contexts_missing_label_and_wrong_source_rejected(self):
        cases=[output('Al 2026-08-20 il dato è DATO NON VERIFICATO.','Al 2026-10-01 il dato è DATO ASSENTE.'),
               output('Al 2026-10-01 e al 2026-08-20: DATO NON VERIFICATO e DATO ASSENTE.'),
               output('Al 2026-10-01 il dato non risulta verificato.'),
               output().replace('"N1"','"N2"')]
        for raw in cases:self.assertEqual(probe.validate_contract(raw,SOURCES,completed=True)['status'],'rejected')

    def test_ambiguous_contexts_refused_before_inference_and_natural_date_not_guessed(self):
        bad=[dict(SOURCES[0],text=SOURCES[0]['text']+' Evento il 2026-09-01.')]
        self.assertEqual(probe.required_contexts(bad)['status'],'ambiguous')
        with self.assertRaises(ValueError):probe.make_coverage_messages(historical_messages(probe, ROOT),dict(probe.CASES[0],sources=bad))
        natural=[dict(SOURCES[0],text=SOURCES[0]['text'].replace('2026-10-01','1 ottobre 2026'))]
        self.assertEqual(probe.required_contexts(natural)['status'],'ambiguous')

    def test_previous_three_inputs_prompt_and_validator_unchanged(self):
        make=historical_messages(probe, ROOT)
        for case in probe.CASES[1:]:
            expected=make(case['query'],case['sources']);expected[0]['content']+=probe.CONTRACT_PROMPT
            self.assertEqual(probe.make_coverage_messages(make,case),expected)
            raw=json.dumps({'scope':'provided_excerpts','claims':[{'text':'Negli estratti il dato è documentato.','sources':['N1']}]})
            self.assertEqual(probe.validate_contract(raw,case['sources'],completed=True),probe.validate_base_contract(raw,case['sources'],completed=True))

    def test_one_actual_http_stream_with_mandatory_contexts_and_no_runtime_write(self):
        from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
        from threading import Thread
        from urllib.request import build_opener,ProxyHandler
        calls=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                calls.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(200);self.end_headers()
                for event in ({'message':{'content':output()}},{'done':True,'done_reason':'stop'}):
                    self.wfile.write(json.dumps(event).encode()+b'\n');self.wfile.flush()
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        previous=probe.BASE;before=(ROOT/'scripts/andrea/runtime.py').read_bytes()
        try:
            probe.BASE=f'http://127.0.0.1:{server.server_port}'
            with redirect_stdout(io.StringIO()):r=probe.collect(build_opener(ProxyHandler({})),historical_messages(probe, ROOT))
            self.assertEqual(len(calls),1);self.assertEqual(r['requested'],1);self.assertEqual(r['automaticRetries'],0)
            self.assertEqual(r['rows'][0]['contract']['semanticVerdict'],'pending_review')
            self.assertEqual(len(json.loads(calls[0]['messages'][1]['content'])['mandatory_contexts']),2)
            self.assertEqual(calls[0]['options'],{'temperature':.4,'num_predict':512,'num_ctx':4096})
            self.assertEqual(calls[0]['keep_alive'],'15m');self.assertEqual(calls[0]['format'],'json')
            self.assertEqual((ROOT/'scripts/andrea/runtime.py').read_bytes(),before)
        finally:probe.BASE=previous;server.shutdown();server.server_close();thread.join()

    def test_partial_and_abstention_never_promoted_to_complete_coverage(self):
        self.assertEqual(probe.validate_contract(output(),SOURCES,completed=False)['status'],'rejected')
        empty='{"scope":"provided_excerpts","claims":[]}'
        self.assertEqual(probe.validate_contract(empty,SOURCES,completed=True)['status'],'abstained')


if __name__=='__main__':unittest.main()
