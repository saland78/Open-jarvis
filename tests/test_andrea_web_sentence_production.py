"""Production/candidate parity and existing async transport safeguards."""
import asyncio
import json
import time
import unittest
from types import SimpleNamespace
import web_page_local as local
import web_sentence_contract as contract
import web_concurrency_synthesis_probe as candidate

PAGE=('La programmazione asincrona gestisce più attività durante le attese.\n'
      'Le coroutine possono sospendere e poi riprendere l’esecuzione.\n')
RAW=json.dumps({'claims':[{'passage':1,'text':'Il codice asincrono prosegue altre attività mentre aspetta.'},
                         {'passage':2,'text':'Una coroutine può sospendersi e successivamente riprendere.'}]})

class ContractParityTests(unittest.TestCase):
    def test_observed_english_title_supports_italian_async_translation(self):
        quote='asyncio — Asynchronous I/O\n'
        text='asyncio serve per I/O asincrono.'
        raw=json.dumps({'claims':[{'passage':1,'text':text}]})
        result=contract.validate(raw,[quote],True)
        self.assertEqual(result['outcome'],'accepted_pending_semantic_review')
        self.assertEqual(result['claims'][0],{'text':text,'quote':quote,'passage':1})
        self.assertEqual(contract.technical_terms('asynchronous'),contract.technical_terms('asincrono'))

    def test_english_async_alias_does_not_add_other_technical_concepts(self):
        quote='This library provides asynchronous input and output operations.\n'
        for text,missing in [('Il codice asincrono esegue operazioni in parallelo.','parallel_execution'),
                             ('Await sospende il codice asincrono mentre attende.','await'),
                             ('Il codice async def gestisce le operazioni asincrone.','def')]:
            result=contract.validate(json.dumps({'claims':[{'passage':1,'text':text}]}),[quote],True)
            self.assertEqual(result['outcome'],'rejected')
            self.assertIn(missing,result['details']['missingConcepts'])
        result=contract.validate(json.dumps({'claims':[{'passage':1,'text':'Il codice gestisce operazioni asincrone durante le attese.'}]}),
                                 ['The library manages input and output operations.\n'],True)
        self.assertEqual(result['outcome'],'rejected')
        self.assertEqual(result['details']['missingConcepts'],['async'])

    def test_reviewed_concurrency_generation_and_observed_failure(self):
        bank=['Con la programmazione asincrona in Python, il tuo codice può gestire più attività contemporaneamente.\n',
              'Nel Python sincrono tradizionale, il codice viene eseguito una riga alla volta. Per esempio, quando chiami un’API, il programma si ferma e aspetta la risposta.\n']
        for second in ('In Python sincrono, il codice esegue una riga alla volta e si ferma in attesa.',
                       "Il codice sincrono aspetta operazioni, bloccando l'esecuzione."):
            # Reviewed isolated generation and subsequent installed UI output.
            texts=["L'asincronia permette al codice di gestire più attività contemporaneamente.", second]
            raw=json.dumps({'claims':[{'passage':i+1,'text':text} for i,text in enumerate(texts)]})
            accepted=contract.validate(raw,bank,True)
            self.assertEqual(accepted['outcome'],'accepted_pending_semantic_review')
            self.assertEqual([x['text'] for x in accepted['claims']],texts)
            self.assertEqual([x['quote'] for x in accepted['claims']],bank)
        bad=json.dumps({'claims':[{'passage':1,'text':"L'asincrono permette di eseguire attività in parallelo mentre si aspetta."}]})
        rejected=contract.validate(bad,bank,True)
        self.assertEqual(rejected['outcome'],'rejected')
        self.assertEqual(rejected['claims'],[])
        self.assertEqual(rejected['details']['missingConcepts'],['parallel_execution'])

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

    def test_full_bank_and_old_general_guards_survive_completion_schema_change(self):
        pages=[PAGE,'X'*700+'\n'+PAGE, 'Una frase breve completa.\n'*200]
        raw_cases=[RAW,'{"claims":[]}', 'not JSON',
                   '{"claims":[{"passage":true,"text":"Un testo completo ma non supportato."}]}',
                   '{"claims":[{"passage":1,"text":"L’async gestisce operazioni in parallelo."}]}',
                   '{"claims":[{"passage":1,"text":"Il testo manca di una conclusione"}]}']
        for page in pages:
            expected=candidate.prepare(page,'Sintesi')
            actual=contract.prepare(page,'Sintesi')
            self.assertEqual(actual[0],expected[0])
            actual_payload=json.loads(actual[1][1]['content'])
            expected_payload=json.loads(expected[1][1]['content'])
            self.assertEqual(actual_payload['question'],expected_payload['question'])
            self.assertEqual(actual_payload['passages'],expected_payload['passages'])
            expected_schema=json.loads(json.dumps(expected[2]))
            del expected_schema['properties']['claims']['items']['properties']['text']['maxLength']
            self.assertEqual(actual[2],expected_schema)
            self.assertNotEqual(actual[1][0],expected[1][0])
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

    async def test_production_uses_reviewed_context_contract_one_call_exact_quotes_and_metrics(self):
        calls=[];closed=[]
        async def stream(messages,schema):
            calls.append((messages,schema))
            try:
                yield SimpleNamespace(content=RAW[:30],finish_reason=None,tool_calls=None)
                yield SimpleNamespace(content=RAW[30:],finish_reason='stop',tool_calls=None)
            finally:closed.append(True)
        result=await self.service().summarize({'pageId':'token','question':'Sintesi'},stream)
        _,messages,schema,_=local.page_context.prepare({'text':PAGE},'Sintesi')
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
