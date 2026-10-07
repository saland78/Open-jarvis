from frozen_web_context import contract as frozen_contract
from unittest.mock import patch
"""Reviewed Mac claims through the actual production service and contract."""
import ast
import json
from pathlib import Path
import time
from types import SimpleNamespace
import unittest

import web_page_local as local
import web_sentence_contract as production
import web_qualified_prefix_contract_candidate as candidate
from test_andrea_web_identifier_probe import CSV, ASYNC
from test_andrea_web_qualified_prefix import OBSERVED_BAD
from test_andrea_web_literal_prefix import LOOPS, BAD
from test_andrea_web_alias_prefix import OBSERVED_CUT

IPC=ASYNC.splitlines(keepends=True)[1]
CONTROL='control subprocesses;\n'
MAC_IO='asyncio permette di eseguire operazioni di I/O e comunicazione tra processi (IPC).'
MAC_CONTROL='asyncio consente di gestire sottoprocessi.'
MAC_CSV=('csv.reader restituisce liste di stringhe e non esegue conversione automatica dei tipi, '
         'salvo che quando è specificato QUOTE_NONNUMERIC, in cui i campi non racchiusi tra '
         'virgolette vengono trasformati in float.')


class ContractPinTests(unittest.TestCase):
    def test_production_functions_are_exactly_the_reviewed_mac_candidate(self):
        def functions(module):
            return {n.name:ast.dump(n) for n in ast.parse(Path(module.__file__).read_text()).body if isinstance(n,ast.FunctionDef)}
        self.assertEqual(functions(production),functions(candidate))
        self.assertEqual(production.MAX_CLAIM_CHARS,candidate.MAX_CLAIM_CHARS)
        for page in (IPC+CONTROL,CSV,LOOPS,'A'*700+'\n'+CSV):
            self.assertEqual(production.prepare(page,'Sintesi'),candidate.prepare(page,'Sintesi'))


class PrefixProductionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Replay the exact historical v1 service contract. Live v9 has a
        # separate service suite with the current facade and actual schema.
        guard = patch.object(local, 'page_context', frozen_contract)
        guard.start()
        self.addCleanup(guard.stop)

    def service(self,page):
        service=local.LocalWebPages()
        service.page={'pageId':'token','text':page}
        service.expires=time.monotonic()+300
        return service

    async def replay(self,service,claims,question='Sintesi'):
        calls=[];closed=[]
        async def stream(messages,schema):
            calls.append((messages,schema))
            try:
                answer=json.dumps({'claims':claims})
                yield SimpleNamespace(content=answer[:20],finish_reason=None,tool_calls=None)
                yield SimpleNamespace(content=answer[20:],finish_reason='stop',tool_calls=None)
            finally:closed.append(True)
        result=await service.summarize({'pageId':'token','question':question},stream)
        self.assertEqual(len(calls),1);self.assertEqual(closed,[True])
        self.assertEqual(result['automaticRetries'],0)
        self.assertEqual(result['qualityVerdict'],'pending_review')
        self.assertIsNotNone(result['timings']['generationMs'])
        self.assertIsNotNone(result['timings']['validationMs'])
        return result,calls[0]

    async def test_actual_reviewed_asyncio_and_csv_claims_keep_their_exact_source(self):
        result,_=await self.replay(self.service(IPC+CONTROL),[
            {'passage':1,'text':MAC_IO},{'passage':2,'text':MAC_CONTROL}])
        self.assertEqual(result['outcome'],'accepted_pending_semantic_review')
        self.assertEqual([c['text'] for c in result['claims']],[MAC_IO,MAC_CONTROL])
        self.assertEqual([c['quote'] for c in result['claims']],[IPC,CONTROL])
        self.assertGreater(len(MAC_CSV),200)
        result,_=await self.replay(self.service(CSV),[{'passage':1,'text':MAC_CSV}])
        self.assertEqual(result['claims'],[{'passage':1,'text':MAC_CSV,'quote':CSV}])

    async def test_same_page_second_question_keeps_context_and_returns_empty_claims(self):
        service=self.service(CSV)
        page_before=dict(service.page);expiry=service.expires
        _,first=await self.replay(service,[{'passage':1,'text':MAC_CSV}],'Come converte?')
        result,second=await self.replay(service,[],'Qual è il prezzo?')
        self.assertEqual(result['outcome'],'abstained');self.assertEqual(result['claims'],[])
        self.assertEqual(service.page,page_before);self.assertEqual(service.expires,expiry)
        self.assertEqual(first[0][0],second[0][0]);self.assertEqual(first[1],second[1])
        first_content,second_content=first[0][1]['content'],second[0][1]['content']
        prefix=first_content[:first_content.index(',"question":')]
        self.assertTrue(second_content.startswith(prefix))
        self.assertNotEqual(first_content,second_content)

    async def test_measured_mistranslations_and_word_cut_are_refused_in_production(self):
        for page,text,reason in ((CSV,OBSERVED_BAD,'unquoted_field_scope_not_preserved'),
                                 (LOOPS,BAD,'source_technical_terms_not_preserved'),
                                 (CSV,OBSERVED_CUT,'sentence_not_complete')):
            result,_=await self.replay(self.service(page),[{'passage':1,'text':text}])
            self.assertEqual(result['reason'],reason);self.assertEqual(result['claims'],[])

    async def test_application_bound_refuses_overlong_complete_answer_without_shortening(self):
        text='La libreria '+ 'gestisce '*35+'le operazioni.'
        self.assertGreater(len(text),320)
        result,(_,schema)=await self.replay(self.service(CSV),[{'passage':1,'text':text}])
        self.assertEqual(result['reason'],'invalid_structure');self.assertEqual(result['claims'],[])
        self.assertNotIn('maxLength',schema['properties']['claims']['items']['properties']['text'])


if __name__=='__main__':unittest.main()
