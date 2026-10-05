"""Identifier failure regressions and finite, read-only candidate orchestration."""
import ast
from hashlib import sha256
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
import web_identifier_preservation_probe as probe
import web_identifier_contract_candidate as candidate
import web_sentence_contract as installed
import check_web_reliability as production_check

ROOT=Path(__file__).resolve().parents[1]
ASYNC=('run Python coroutines concurrently and have full control over their execution;\n'
       'perform network IO and IPC;\n')
CSV=('Each row read from the csv file is returned as a list of strings. No automatic '
     'data type conversion is performed unless the QUOTE_NONNUMERIC format option '
     'is specified (in which case unquoted fields are transformed into floats).\n')
BAD='asyncio permette di eseguire operazioni di rete e scambio di processi tra processi.'
GOOD='asyncio gestisce I/O di rete e IPC.'
CONCURRENT='asyncio esegue coroutine in modo concorrente, controllandone l’esecuzione.'
CONDITION='csv.reader restituisce stringhe senza conversione automatica, salvo che QUOTE_NONNUMERIC sia specificato.'

def raw(text,passage=1):return json.dumps({'claims':[{'passage':passage,'text':text}]})

class ContractTests(unittest.TestCase):
    def test_observed_failed_paraphrase_cannot_be_accepted_as_before(self):
        bank=installed.sentence_bank(ASYNC)
        self.assertEqual(installed.validate(raw(BAD,2),bank,True)['outcome'],'accepted_pending_semantic_review')
        result=candidate.validate(raw(BAD,2),bank,True)
        self.assertEqual(result['outcome'],'rejected')
        self.assertEqual(result['claims'],[])
        self.assertEqual(result['details']['missingIdentifiers'],['I/O','IPC'])
        self.assertEqual(result['details']['text'],BAD)
        self.assertEqual(result['details']['quote'],bank[1])
        self.assertTrue(result['details']['diagnosticOnly'])

    def test_supported_literal_terms_and_finite_io_spelling_alias(self):
        for text in (GOOD,'asyncio gestisce IO di rete e IPC.'):
            result=candidate.validate(raw(text,2),candidate.sentence_bank(ASYNC),True)
            self.assertEqual(result['outcome'],'accepted_pending_semantic_review')
            self.assertEqual(result['claims'][0]['text'],text)
            self.assertEqual(result['claims'][0]['quote'],ASYNC.splitlines(keepends=True)[1])
        self.assertEqual(candidate.protected_identifiers('IO I/O IPC IPCX'),{'I/O','IPC','IPCX'})

    def test_an_identifier_in_a_different_passage_is_not_support(self):
        result=candidate.validate(raw('La libreria gestisce operazioni tramite IPC.'),
            ['The library controls concurrent execution.\n','perform network IO and IPC;\n'],True)
        self.assertEqual(result['outcome'],'rejected')
        self.assertEqual(result['details']['addedIdentifiers'],['IPC'])

    def test_preserving_one_identifier_does_not_allow_removing_another(self):
        result=candidate.validate(raw('asyncio gestisce I/O di rete tra processi.',2),candidate.sentence_bank(ASYNC),True)
        self.assertEqual(result['details']['missingIdentifiers'],['IPC'])
        self.assertEqual(result['claims'],[])

    def test_source_units_without_uppercase_identifiers_keep_existing_acceptance(self):
        for text in (CONCURRENT,'La biblioteca consente l’esecuzione concorrente delle coroutine.'):
            result=candidate.validate(raw(text),candidate.sentence_bank(ASYNC),True)
            self.assertEqual(result['outcome'],'accepted_pending_semantic_review')
        bad=candidate.validate(raw('Le coroutine eseguono operazioni in parallelo.'),candidate.sentence_bank(ASYNC),True)
        self.assertEqual(bad['reason'],'technical_term_missing_from_passage')

    def test_csv_condition_and_abstention_are_retained_as_pending_review(self):
        result=candidate.validate(raw(CONDITION),[CSV],True)
        self.assertEqual(result['outcome'],'accepted_pending_semantic_review')
        self.assertEqual(result['claims'][0]['quote'],CSV)
        self.assertEqual(candidate.validate('{"claims":[]}',[CSV],True)['outcome'],'abstained')
        result=candidate.validate(raw('csv.reader non converte automaticamente i tipi.'),[CSV],True)
        self.assertEqual(result['reason'],'source_identifiers_not_preserved')

    def test_failed_second_claim_does_not_leave_partial_accepted_answer_or_repair(self):
        answer=json.dumps({'claims':[{'passage':1,'text':CONCURRENT},{'passage':2,'text':BAD}]})
        result=candidate.validate(answer,candidate.sentence_bank(ASYNC),True)
        self.assertEqual(result['outcome'],'rejected');self.assertEqual(result['claims'],[])
        self.assertEqual(result['details']['claimIndex'],2)

    def test_bounded_schema_and_full_evidence_remain_without_external_glossary(self):
        bank,messages,schema=candidate.prepare(ASYNC,'Due funzionalità.')
        self.assertEqual(''.join(bank),ASYNC)
        payload=json.loads(messages[1]['content'])
        self.assertEqual(payload['protectedIdentifiers'],{'2':['I/O','IPC']})
        self.assertEqual(payload['passages'],[[1,bank[0]],[2,bank[1]]])
        self.assertNotIn('interprocess',json.dumps(payload).lower())
        self.assertEqual(schema,installed.prepare(ASYNC,'Due funzionalità.')[2])

    def test_complete_stream_and_nonliteral_original_checks_are_preserved(self):
        for answer,completed,reason in [(raw(GOOD,2),False,'stream_incomplete'),
            (raw('asyncio gestisce I/O di rete e IPC',2),True,'sentence_not_complete'),
            (raw('asyncio gestisce 100 operazioni IO e IPC.',2),True,'unsupported_number')]:
            result=candidate.validate(answer,candidate.sentence_bank(ASYNC),completed)
            self.assertEqual(result['reason'],reason);self.assertEqual(result['claims'],[])

    def test_standalone_and_future_candidate_pure_functions_are_identical(self):
        def functions(module):
            return {n.name:ast.dump(n) for n in ast.parse(Path(module.__file__).read_text()).body if isinstance(n,ast.FunctionDef)}
        left,right=functions(candidate),functions(probe)
        for name in left:self.assertEqual(left[name],right[name],name)


class Response(io.BytesIO):status=200

class Opener:
    def __init__(self,answers=None,read_fail=False):
        self.calls=[];self.read_count=0;self.infer_count=0;self.read_fail=read_fail
        self.answers=answers or [json.dumps({'claims':[{'passage':1,'text':CONCURRENT},{'passage':2,'text':GOOD}]}),raw(CONDITION),'{"claims":[]}']
    def open(self,request,timeout):
        data=json.loads(request.data);self.calls.append((request.full_url,data,timeout))
        if request.full_url.endswith('/read'):
            self.read_count+=1
            if self.read_fail:raise HTTPError(request.full_url,503,'error',{},io.BytesIO(b'{"detail":"dns_unavailable"}'))
            page=ASYNC if self.read_count==1 else CSV
            return Response(json.dumps({'text':page,'url':data['url'],'pageId':'page'+str(self.read_count),
                                       'sourceId':'W1','modelUsed':False,'readMs':5,'partial':False}).encode())
        answer=self.answers[self.infer_count];self.infer_count+=1
        return Response((json.dumps({'message':{'content':answer},'done':True,'done_reason':'stop',
                                    'load_duration':1000,'eval_count':25,'eval_duration':1000000})+'\n').encode())


class OrchestrationTests(unittest.TestCase):
    def project(self,directory):
        project=Path(directory)
        for relative,expected in probe.EXPECTED.items():
            data=(ROOT/relative).read_bytes();self.assertEqual(sha256(data).hexdigest(),expected)
            dest=project/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        return project

    def test_same_three_cases_two_reads_three_inferences_no_file_or_option_changes(self):
        self.assertEqual(probe.CASES,production_check.CASES)
        self.assertEqual(probe.EXPECTED,production_check.EXPECTED)
        with tempfile.TemporaryDirectory() as directory:
            project=self.project(directory)
            before={p:p.read_bytes() for p in project.rglob('*') if p.is_file()}
            opener=Opener();rows=probe.run(project,opener,lambda _:None)
            self.assertEqual(before,{p:p.read_bytes() for p in project.rglob('*') if p.is_file()})
        self.assertEqual((opener.read_count,opener.infer_count),(2,3))
        self.assertEqual(len(opener.calls),5)
        inferences=[data for url,data,_ in opener.calls if url.endswith('/api/chat')]
        for call in inferences:
            self.assertEqual(call['model'],probe.MODEL)
            self.assertEqual(call['options'],{'temperature':.4,'num_predict':512,'num_ctx':4096})
            self.assertEqual(call['keep_alive'],'15m');self.assertFalse(call['think'])
            self.assertNotIn('tools',call)
        self.assertTrue(all(row['qualityVerdict']=='pending_review' for row in rows))
        self.assertTrue(all(not row['productionModified'] and row['rawAnswerDiagnosticOnly'] for row in rows))

    def test_observed_rejection_kept_without_repair_retry_or_success_relabel(self):
        answers=[raw(BAD,2),raw(CONDITION),'{"claims":[]}']
        with tempfile.TemporaryDirectory() as directory:
            opener=Opener(answers);rows=probe.run(self.project(directory),opener,lambda _:None)
        self.assertEqual(opener.infer_count,3)
        self.assertEqual(rows[0]['checks']['outcome'],'rejected')
        self.assertEqual(rows[0]['checks']['claims'],[])
        self.assertEqual(json.loads(rows[0]['result']['modelAnswer'])['claims'][0]['text'],BAD)
        self.assertTrue(rows[0]['rawAnswerDiagnosticOnly'])

    def test_failed_read_and_local_modification_stop_before_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            project=self.project(directory);opener=Opener(read_fail=True)
            with self.assertRaisesRegex(probe.CheckError,'dns_unavailable'):probe.run(project,opener,lambda _:None)
            self.assertEqual(len(opener.calls),1);self.assertEqual(opener.infer_count,0)
            (project/next(iter(probe.EXPECTED))).write_text('modified')
            opener=Opener()
            with self.assertRaises(probe.CheckError):probe.run(project,opener,lambda _:None)
            self.assertEqual(opener.calls,[])

    def test_missing_context_stops_before_affected_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            project=self.project(directory);opener=Opener()
            cases=tuple({**case,'requiredContext':'NOT PRESENT'} if i==1 else case for i,case in enumerate(probe.CASES))
            with patch.object(probe,'CASES',cases):
                with self.assertRaises(probe.CheckError):probe.run(project,opener,lambda _:None)
            self.assertEqual((opener.read_count,opener.infer_count),(2,1))

    def test_proxies_and_local_redirects_are_not_used(self):
        with tempfile.TemporaryDirectory() as directory:
            project=self.project(directory);opener=Opener()
            with patch.object(probe.urllib.request,'build_opener',return_value=opener) as build:
                probe.run(project,emit=lambda _:None)
            self.assertEqual(build.call_args.args[0].proxies,{})
            with self.assertRaises(probe.CheckError):
                build.call_args.args[1].redirect_request(None,None,302,'redirect',{},'https://example.com')


if __name__=='__main__':unittest.main()
