import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
import web_sentence_synthesis_probe as p

PAGE='Coroutine: funzioni definite con async def invece di def. Possono sospendere e riprendere l’esecuzione.\nawait sospende una coroutine durante un’attesa, lasciando procedere altro codice.\n'

class SentenceTests(unittest.TestCase):
    def test_all_context_preserved_no_character_cut(self):
        for text in [PAGE,'a'*700+' Fine.\nBreve.\n',('È una frase intera. '*60)+'R']:
            bank=p.sentence_bank(text)
            self.assertEqual(''.join(bank),text)
        bank,_,schema=p.prepare('a'*700+'\n'+PAGE,'q')
        self.assertNotIn(1,schema['properties']['claims']['items']['properties']['passage']['enum'])
        self.assertEqual(bank[0],'a'*700+'\n')

    def verdict(self,text,ref=1):
        return p.validate(json.dumps({'claims':[{'text':text,'passage':ref}]}),p.sentence_bank(PAGE),True)

    def test_full_sentence_with_original_definition(self):
        result=self.verdict('Le coroutine sono funzioni async def che possono sospendersi e riprendere.')
        self.assertEqual(result['outcome'],'accepted_pending_semantic_review')
        self.assertEqual(result['claims'][0]['quote'],PAGE.splitlines(keepends=True)[0])

    def test_missing_definition_anchor_rejected(self):
        self.assertEqual(self.verdict('Le coroutine sono funzioni async def che possono sospendersi e riprendere.',2)['reason'],'technical_term_missing_from_passage')

    def test_truncated_sentence_and_ellipsis_rejected(self):
        for text in ['Le coroutine possono interrompersi nel fratt','Le coroutine possono…','Le coroutine possono...']:
            self.assertEqual(self.verdict(text)['reason'],'sentence_not_complete')

    def test_copied_sentence_is_not_declared_synthesis(self):
        self.assertEqual(self.verdict('Coroutine: funzioni definite con async def invece di def.')['reason'],'verbatim_instead_of_synthesis')

    def test_numbers_limits_fields_and_stream(self):
        for raw in ['{"claims":[{"text":"Le coroutine generano 1000 euro.","passage":1}]}',
                    '{"claims":[{"text":"Una frase completa ma senza supporto.","passage":true}]}',
                    '{"claims":[{"text":"Una frase completa ma senza supporto.","passage":99}]}',
                    '{"claims":[],"claims":[]}',
                    '{"claims":[{"text":"'+('x'*170)+'.","passage":1}]}',
                    '{"claims":[{"text":"Una frase completa ma senza supporto.","passage":1,"quote":"inventata"}]}']:
            self.assertEqual(p.validate(raw,p.sentence_bank(PAGE),True)['outcome'],'rejected')
        self.assertEqual(p.validate('{"claims":[]}',[],True)['outcome'],'abstained')
        self.assertEqual(p.validate('{"claims":[]}',[],False)['reason'],'stream_incomplete')

    def test_schema_shape_and_isolation(self):
        bank,messages,schema=p.prepare(PAGE,'Domanda')
        data=json.loads(messages[1]['content'])
        self.assertEqual(data,{'question':'Domanda','passages':[[i+1,v] for i,v in enumerate(bank)]})
        item=schema['properties']['claims']['items']['properties']
        self.assertEqual(set(item),{'text','passage'});self.assertEqual(item['text']['maxLength'],160)

class HTTPTests(unittest.TestCase):
    def test_one_read_one_inference_no_writes_and_raw_diagnostic(self):
        requests=[]
        class Response(io.BytesIO):status=200
        class Opener:
            def open(self,request,timeout):
                requests.append(request)
                if request.full_url.endswith('/api/andrea/web/read'):
                    self_outer.assertEqual(json.loads(request.data),{'url':p.URL})
                    return Response(json.dumps({'url':p.URL,'sourceId':'W1','text':PAGE,'readMs':10}).encode())
                self_outer.assertEqual(request.full_url,p.BASE+'/api/chat')
                body=json.loads(request.data)
                self_outer.assertEqual(body['options'],{'temperature':.4,'num_predict':512,'num_ctx':4096})
                self_outer.assertFalse(body['think']);self_outer.assertNotIn('tools',body)
                events=[{'message':{'content':'{"claims":[{"text":"Le coroutine possono sospendersi e poi riprendere.","passage":1}]}'},'done':False},
                        {'message':{'content':''},'done':True,'done_reason':'stop','eval_count':20,'eval_duration':10000000}]
                return Response(b''.join(json.dumps(e).encode()+b'\n' for e in events))
        self_outer=self
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for relative in p.EXPECTED:
                path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes((Path(__file__).resolve().parents[1]/relative).read_bytes())
            before={str(v.relative_to(root)):v.read_bytes() for v in root.rglob('*') if v.is_file()}
            with redirect_stdout(io.StringIO()):result=p.run(root,Opener())
            after={str(v.relative_to(root)):v.read_bytes() for v in root.rglob('*') if v.is_file()}
            self.assertEqual(before,after)
        self.assertEqual(len(requests),2)
        self.assertEqual(result['checks']['outcome'],'accepted_pending_semantic_review')
        self.assertIn('modelAnswer',result['result'])
        self.assertEqual(result['qualityVerdict'],'pending_review')

    def test_duplicate_protocol_key_and_tool_call_not_accepted(self):
        for event in [b'{"done":false,"done":true}\n',json.dumps({'message':{'tool_calls':[{}]},'done':False}).encode()+b'\n']:
            class Response(io.BytesIO):pass
            class Opener:
                def open(self,*a,**k):return Response(event)
            _,messages,schema=p.prepare(PAGE,'q')
            self.assertEqual(p.stream_probe(Opener(),messages,schema)['status'],'error')
