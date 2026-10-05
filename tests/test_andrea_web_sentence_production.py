"""Production/candidate parity and existing async transport safeguards."""
import asyncio
import json
import time
import unittest
from types import SimpleNamespace
import web_page_local as local
import web_sentence_contract as contract
import web_sentence_synthesis_probe as candidate

PAGE=('La programmazione asincrona gestisce più attività durante le attese.\n'
      'Le coroutine possono sospendere e poi riprendere l’esecuzione.\n')
RAW=json.dumps({'claims':[{'passage':1,'text':'Il codice asincrono prosegue altre attività mentre aspetta.'},
                         {'passage':2,'text':'Una coroutine può sospendersi e successivamente riprendere.'}]})

class ContractParityTests(unittest.TestCase):
    def test_reviewed_mac_claims_preserve_exact_support_and_pending_api_verdict(self):
        bank=['Contesto introduttivo della pagina.\n',
              'Con la programmazione asincrona in Python, il tuo codice può gestire più attività contemporaneamente.\n',
              'Altra sezione della pagina.\n','Altra sezione della pagina.\n','Altra sezione della pagina.\n',
              'Nel Python sincrono tradizionale, il codice viene eseguito una riga alla volta. Per esempio, quando chiami un’API, il programma si ferma e aspetta la risposta.\n']
        raw=json.dumps({'claims':[{'passage':2,'text':"L'asincronia permette al codice di gestire più attività contemporaneamente."},
                                 {'passage':6,'text':'Il codice si ferma in attesa di risposte in Python sincrono.'}]})
        verdict=contract.validate(raw,bank,True)
        self.assertEqual(verdict['outcome'],'accepted_pending_semantic_review')
        self.assertEqual([x['quote'] for x in verdict['claims']],[bank[1],bank[5]])

    def test_same_prompt_schema_bank_and_validation_as_reviewed_candidate(self):
        pages=[PAGE,'X'*700+'\n'+PAGE, 'Una frase breve completa.\n'*200]
        raw_cases=[RAW,'{"claims":[]}', 'not JSON',
                   '{"claims":[{"passage":true,"text":"Un testo completo ma non supportato."}]}',
                   '{"claims":[{"passage":1,"text":"L’async gestisce operazioni in parallelo."}]}',
                   '{"claims":[{"passage":1,"text":"Il testo manca di una conclusione"}]}']
        for page in pages:
            expected=candidate.prepare(page,'Sintesi')
            actual=contract.prepare(page,'Sintesi')
            self.assertEqual(actual,expected)
            for raw in raw_cases:
                for completed in (True,False):
                    self.assertEqual(contract.validate(raw,actual[0],completed),
                                     candidate.validate(raw,expected[0],completed))

class ProductionTests(unittest.IsolatedAsyncioTestCase):
    def service(self):
        service=local.LocalWebPages()
        service.page={'pageId':'token','text':PAGE}
        service.expires=time.monotonic()+300
        return service

    async def test_production_uses_candidate_contract_one_call_exact_quotes_and_metrics(self):
        calls=[];closed=[]
        async def stream(messages,schema):
            calls.append((messages,schema))
            try:
                yield SimpleNamespace(content=RAW[:30],finish_reason=None,tool_calls=None)
                yield SimpleNamespace(content=RAW[30:],finish_reason='stop',tool_calls=None)
            finally:closed.append(True)
        result=await self.service().summarize({'pageId':'token','question':'Sintesi'},stream)
        _,messages,schema=candidate.prepare(PAGE,'Sintesi')
        self.assertEqual(calls,[(messages,schema)])
        self.assertEqual(closed,[True])
        self.assertEqual(result['outcome'],'accepted_pending_semantic_review')
        self.assertEqual([x['quote'] for x in result['claims']],PAGE.splitlines(keepends=True))
        self.assertEqual(result['qualityVerdict'],'pending_review')
        self.assertEqual(result['automaticRetries'],0)
        self.assertEqual(result['sourceId'],'W1')
        self.assertEqual(result['timings']['inputCharacters'],len(PAGE))
        self.assertIsNotNone(result['timings']['firstJsonMs'])
        self.assertIsNotNone(result['timings']['generationMs'])
        self.assertIsNotNone(result['timings']['validationMs'])

    async def test_rejection_is_not_repaired_retried_or_displayed_as_claims(self):
        calls=[]
        async def stream(messages,schema):
            calls.append(True)
            yield SimpleNamespace(content='{"claims":[{"passage":1,"text":"Il codice si interrompe nel fratt"}]}',finish_reason='stop',tool_calls=None)
        result=await self.service().summarize({'pageId':'token','question':'Sintesi'},stream)
        self.assertEqual(calls,[True])
        self.assertEqual(result['reason'],'sentence_not_complete')
        self.assertEqual(result['claims'],[])

    async def test_abstention_preserves_empty_result(self):
        async def stream(messages,schema):
            yield SimpleNamespace(content='{"claims":[]}',finish_reason='stop',tool_calls=None)
        result=await self.service().summarize({'pageId':'token','question':'Informazione assente'},stream)
        self.assertEqual(result['outcome'],'abstained')
        self.assertEqual(result['claims'],[])

    async def test_truncated_tools_and_trailing_transport_rejected_and_closed(self):
        cases=[[(RAW,'length',None)],[(RAW,'stop',[{}])],[(RAW,'stop',None),('extra',None,None)]]
        for chunks in cases:
            closed=[]
            async def stream(messages,schema):
                try:
                    for content,reason,tools in chunks:
                        yield SimpleNamespace(content=content,finish_reason=reason,tool_calls=tools)
                finally:closed.append(True)
            result=await local.generate(stream,'Sintesi',PAGE,sentence=True)
            self.assertEqual(result['outcome'],'rejected')
            self.assertEqual(result['claims'],[])
            self.assertEqual(closed,[True])

    async def test_user_cancellation_closes_one_stream_without_retry(self):
        started=asyncio.Event();closed=[];calls=[]
        async def stream(messages,schema):
            calls.append(True)
            try:
                started.set()
                await asyncio.Event().wait()
                yield SimpleNamespace(content='',finish_reason=None)
            finally:closed.append(True)
        task=asyncio.create_task(self.service().summarize({'pageId':'token','question':'Sintesi'},stream))
        await started.wait();task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertEqual(calls,[True]);self.assertEqual(closed,[True])

if __name__=='__main__':unittest.main()
