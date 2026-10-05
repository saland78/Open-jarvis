"""Actual unquoted-field mistranslation and condition/scope regressions."""
import ast
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import web_qualified_prefix_contract_candidate as candidate
import web_qualified_prefix_probe as probe
import web_alias_prefix_contract_candidate as previous
from test_andrea_web_alias_prefix import OBSERVED_CUT, OBSERVED_LOOPS, COMPLETE_CSV
from test_andrea_web_literal_prefix import LOOPS, BAD
from test_andrea_web_identifier_probe import Opener, ASYNC, CSV, GOOD, CONCURRENT, CONDITION, raw

ROOT=Path(__file__).resolve().parents[1]
OBSERVED_BAD=('csv.reader restituisce ogni riga come lista di stringhe; la conversione automatica dei tipi '
              'avviene solo se specificato il formato QUOTE_NONNUMERIC, trasformando i campi non incorniciati in float.')
FAITHFUL=('csv.reader non converte automaticamente i tipi; con QUOTE_NONNUMERIC converte in float '
          'i campi non racchiusi tra virgolette.')


class FieldScopeTests(unittest.TestCase):
    def test_observed_semantic_failure_is_now_refused_and_retained_for_diagnosis(self):
        self.assertEqual(previous.validate(raw(OBSERVED_BAD),[CSV],True)['outcome'],'accepted_pending_semantic_review')
        result=candidate.validate(raw(OBSERVED_BAD),[CSV],True)
        self.assertEqual(result['reason'],'unquoted_field_scope_not_preserved')
        self.assertEqual(result['claims'],[])
        self.assertEqual(result['details']['text'],OBSERVED_BAD)
        self.assertEqual(result['details']['quote'],CSV)

    def test_precise_field_qualifier_and_condition_pass_without_rewriting_answer(self):
        for qualifier in ('unquoted','non-quoted','non quoted','non quotati','non virgolettati',
                          'non racchiusi tra virgolette','non racchiusi in virgolette','senza virgolette'):
            text='csv.reader converte in float i campi '+qualifier+' solo con QUOTE_NONNUMERIC.'
            result=candidate.validate(raw(text),[CSV],True)
            self.assertEqual(result['outcome'],'accepted_pending_semantic_review',qualifier)
            self.assertEqual(result['claims'][0]['text'],text)
            self.assertEqual(result['claims'][0]['quote'],CSV)

    def test_unrelated_field_properties_quoted_fields_and_universal_scope_are_refused(self):
        for qualifier in ('non incorniciati','non numerici','quotati','racchiusi tra virgolette',''): 
            text='Con QUOTE_NONNUMERIC csv.reader converte tutti i campi '+qualifier+' in float.'
            result=candidate.validate(raw(text),[CSV],True)
            self.assertEqual(result['reason'],'unquoted_field_scope_not_preserved',qualifier)
            self.assertEqual(result['claims'],[])

    def test_naming_the_correct_fields_does_not_license_removing_the_condition(self):
        result=candidate.validate(raw('csv.reader converte sempre i campi non quotati in float.'),[CSV],True)
        self.assertEqual(result['reason'],'csv_conversion_condition_not_preserved')
        self.assertEqual(result['claims'],[])

    def test_a_qualifier_elsewhere_in_page_is_not_evidence_for_selected_unit(self):
        quote='The reader returns fields as strings without automatic conversion.\n'
        result=candidate.validate(raw('Il lettore restituisce i campi non quotati come stringhe.'),[quote,CSV],True)
        self.assertEqual(result['reason'],'unquoted_field_scope_missing_from_passage')
        self.assertEqual(result['claims'],[])

    def test_default_rule_summary_without_field_conversion_is_not_forced_to_repeat_other_sentence(self):
        result=candidate.validate(raw(CONDITION),[CSV],True)
        self.assertEqual(result['outcome'],'accepted_pending_semantic_review')
        self.assertIsNone(candidate.csv_field_scope_error('csv.reader restituisce i campi come stringhe.',CSV))
        self.assertEqual(candidate.validate('{"claims":[]}',[CSV],True)['outcome'],'abstained')

    def test_previously_fixed_complete_sentence_and_technical_equivalents_remain(self):
        for text,quote in ((COMPLETE_CSV,CSV),(OBSERVED_LOOPS,LOOPS),(FAITHFUL,CSV)):
            self.assertEqual(candidate.validate(raw(text),[quote],True)['outcome'],'accepted_pending_semantic_review')
        self.assertEqual(candidate.validate(raw(BAD),[LOOPS],True)['reason'],'source_technical_terms_not_preserved')
        self.assertEqual(candidate.validate(raw(OBSERVED_CUT),[CSV],True)['reason'],'sentence_not_complete')

    def test_entire_answer_is_refused_when_later_claim_loses_qualifier(self):
        result=candidate.validate(json.dumps({'claims':[{'passage':1,'text':GOOD},{'passage':2,'text':OBSERVED_BAD}]}),
                                  [ASYNC.splitlines(keepends=True)[1],CSV],True)
        self.assertEqual(result['claims'],[])
        self.assertEqual(result['details']['claimIndex'],2)

    def test_full_source_unchanged_schema_and_stable_prefix_for_distinct_questions(self):
        page=ASYNC+LOOPS+CSV
        bank,messages,schema=candidate.prepare(page,'Sintesi')
        old_bank,old_messages,old_schema=previous.prepare(page,'Sintesi')
        self.assertEqual(bank,old_bank);self.assertEqual(''.join(bank),page)
        self.assertEqual(schema,old_schema)
        payload=json.loads(messages[1]['content'])
        self.assertEqual(payload['passages'],json.loads(old_messages[1]['content'])['passages'])
        self.assertEqual(payload['sourceTechnicalTerms'],{'3':['subprocess'],'4':['unquoted']})
        self.assertNotIn('incorniciat',messages[0]['content'])
        a,b=[candidate.prepare(CSV,q) for q in ('Come converte?','Qual è il prezzo?')]
        self.assertEqual(a[1][0],b[1][0]);self.assertEqual(a[2],b[2])
        self.assertGreater(probe.common_prefix_characters(a[1][1]['content'],b[1][1]['content']),len(CSV))

    def test_standalone_and_pure_functions_are_identical(self):
        def functions(module):
            return {n.name:ast.dump(n) for n in ast.parse(Path(module.__file__).read_text()).body if isinstance(n,ast.FunctionDef)}
        pure,standalone=functions(candidate),functions(probe)
        for name,body in pure.items():self.assertEqual(body,standalone[name],name)


class QualifiedProbeTests(unittest.TestCase):
    def project(self,directory):
        root=Path(directory)
        for relative,digest in probe.EXPECTED.items():
            data=(ROOT/relative).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(),digest)
            target=root/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        return root

    def test_two_reads_three_original_cases_no_writes_options_or_retry_changes(self):
        answers=[json.dumps({'claims':[{'passage':1,'text':CONCURRENT},{'passage':2,'text':GOOD}]}),raw(FAITHFUL),'{"claims":[]}']
        with tempfile.TemporaryDirectory() as directory:
            root=self.project(directory);before={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
            opener=Opener(answers);rows=probe.run(root,opener,lambda _:None)
            self.assertEqual(before,{p:p.read_bytes() for p in root.rglob('*') if p.is_file()})
        self.assertEqual((opener.read_count,opener.infer_count),(2,3))
        self.assertEqual([r['case'] for r in rows],[c['id'] for c in probe.CASES])
        self.assertEqual([r['checks']['outcome'] for r in rows],['accepted_pending_semantic_review','accepted_pending_semantic_review','abstained'])
        for row in rows:
            self.assertEqual(row['qualityVerdict'],'pending_review');self.assertEqual(row['automaticRetries'],0)
            self.assertFalse(row['productionModified'])
        for url,request,_ in opener.calls:
            if url.endswith('/api/chat'):
                self.assertEqual(request['options'],{'temperature':.4,'num_predict':512,'num_ctx':4096})
                self.assertEqual(request['keep_alive'],'15m');self.assertFalse(request['think'])

    def test_semantic_guard_refusal_is_exposed_not_retried_or_repaired(self):
        answers=[json.dumps({'claims':[{'passage':1,'text':CONCURRENT},{'passage':2,'text':GOOD}]}),raw(OBSERVED_BAD),'{"claims":[]}']
        with tempfile.TemporaryDirectory() as directory:
            opener=Opener(answers);rows=probe.run(self.project(directory),opener,lambda _:None)
        self.assertEqual(opener.infer_count,3)
        self.assertEqual(rows[1]['checks']['reason'],'unquoted_field_scope_not_preserved')
        self.assertEqual(rows[1]['result']['modelAnswer'],raw(OBSERVED_BAD))
        self.assertEqual(rows[1]['qualityVerdict'],'pending_review')

    def test_missing_input_or_local_edits_stop_before_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.project(directory);opener=Opener(read_fail=True)
            with self.assertRaises(probe.CheckError):probe.run(root,opener,lambda _:None)
            self.assertEqual(opener.infer_count,0)
            cases=tuple({**c,'requiredContext':'ABSENT CONDITION'} if i==1 else c for i,c in enumerate(probe.CASES))
            opener=Opener()
            with patch.object(probe,'CASES',cases):
                with self.assertRaises(probe.CheckError):probe.run(root,opener,lambda _:None)
            self.assertEqual(opener.infer_count,0)
            (root/next(iter(probe.EXPECTED))).write_text('local change');opener=Opener()
            with self.assertRaises(probe.CheckError):probe.run(root,opener,lambda _:None)
            self.assertEqual(opener.calls,[])

    def test_incomplete_transport_stops_after_one_diagnostic_without_retry(self):
        output=[]
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(probe,'stream_probe',return_value={'status':'incomplete','modelAnswer':''}) as call:
                with self.assertRaises(probe.CheckError):probe.run(self.project(directory),Opener(),output.append)
            self.assertEqual(call.call_count,1)
        row=next(json.loads(x) for x in output if x.startswith('{'))
        self.assertEqual(row['checks']['reason'],'stream_incomplete');self.assertEqual(row['qualityVerdict'],'pending_review')


if __name__=='__main__':unittest.main()
