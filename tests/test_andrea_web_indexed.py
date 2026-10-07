"""Exact evidence resolution is distinct from semantic entailment."""
import json
import unittest
from types import SimpleNamespace
import web_page_local as local

class EvidenceTests(unittest.TestCase):
    def test_entire_excerpt_covered_exactly_including_short_tail(self):
        for text in ['a'*6000, 'Una frase intera.\n'*400, 'x'*301, 'é’\n'*80]:
            bank=local.evidence_passages(text)
            self.assertTrue(all(20 <= len(p) <= 300 and p in text for p in bank))
            # All positions covered; repeated content cannot hide a missing tail.
            cursor=0
            for p in bank:
                start=cursor if len(text)-cursor >= 20 else len(text)-20
                self.assertEqual(text[start:start+len(p)],p)
                cursor=max(cursor,start+len(p))
            self.assertEqual(cursor,len(text))

    def validate(self, claims, completed=True):
        page='Vendite nel settembre 2026: 2 copie.\n'+'Royalty: DATO NON VERIFICATO. '*15
        return local.validate_indexed(json.dumps({'claims':claims}),page,local.evidence_passages(page),completed)

    def test_original_recovered_without_model_copy(self):
        result=self.validate([{'text':'Nel settembre 2026: 2 copie.','passage':1}])
        self.assertEqual(result['outcome'],'accepted_pending_semantic_review')
        self.assertIn('Vendite nel settembre 2026: 2 copie.',result['claims'][0]['quote'])

    def test_bad_ids_and_forged_quotes_rejected(self):
        for ref in [0,999,True,'1',1.0,None]:
            self.assertEqual(self.validate([{'text':'Due copie.','passage':ref}])['outcome'],'rejected')
        self.assertEqual(self.validate([{'text':'Due copie.','passage':1,'quote':'inventata'}])['outcome'],'rejected')

    def test_existing_guards_and_abstention_preserved(self):
        for text in ['1000 euro.','https://example.com','Dato [W2]','']:
            self.assertEqual(self.validate([{'text':text,'passage':1}])['outcome'],'rejected')
        self.assertEqual(self.validate([])['outcome'],'abstained')
        self.assertEqual(self.validate([],False)['reason'],'stream_incomplete')

    def test_ids_do_not_allow_borrowing_numbers_from_another_passage(self):
        page='Nessun dato numerico documentato. '*10+'Vendite: 99 copie confermate.'
        bank=local.evidence_passages(page)
        result=local.validate_indexed('{"claims":[{"text":"Vendite: 99 copie.","passage":1}]}',page,bank,True)
        self.assertEqual(result['reason'],'unsupported_number')

class StreamTests(unittest.IsolatedAsyncioTestCase):
    async def test_one_request_compact_wire_same_ui_output(self):
        calls=[]
        page='asyncio is a library to write concurrent code using async/await syntax.'
        async def stream(messages,schema):
            calls.append((messages,schema))
            yield SimpleNamespace(content='{"claims":[{"text":"asyncio permette codice concorrente.","passage":1}]}',finish_reason='stop',tool_calls=None)
        result=await local.generate(stream,'Che cosa è?',page,indexed=True)
        self.assertEqual(len(calls),1)
        self.assertEqual(result['claims'][0]['quote'],page)
        payload=json.loads(calls[0][0][1]['content'])
        self.assertEqual(payload,{'question':'Che cosa è?','passages':[[1,page]]})
        self.assertNotIn('quote',calls[0][1]['properties']['claims']['items']['properties'])

    async def test_malformed_and_trailing_stream_rejected(self):
        for chunks in [[('not json','stop')],[('{"claims":[]}','length')],[('{"claims":[]}','stop'),('extra',None)]]:
            closed=[]
            async def stream(messages,schema):
                try:
                    for content,reason in chunks: yield SimpleNamespace(content=content,finish_reason=reason,tool_calls=None)
                finally:closed.append(True)
            result=await local.generate(stream,'q','Contenuto della pagina originale e verificabile.',indexed=True)
            self.assertEqual(result['outcome'],'rejected');self.assertEqual(closed,[True])
