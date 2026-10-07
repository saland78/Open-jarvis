"""First-request attribution, unchanged evidence and observed-failure regressions."""
import ast
import copy
import hashlib
import json
from pathlib import Path
from web_prefix_baseline import before_api_context_source
import tempfile
import unittest
from unittest.mock import patch

import web_sentence_contract as production
import web_short_instructions_candidate as candidate
import web_short_instructions_probe as probe
from test_andrea_web_identifier_probe import Opener, Response, ASYNC, CSV, GOOD, CONCURRENT, raw
from test_andrea_web_qualified_prefix import FAITHFUL, OBSERVED_BAD
from test_andrea_web_alias_prefix import OBSERVED_CUT
from test_andrea_web_literal_prefix import LOOPS, BAD
from check_web_prefix_reuse import CASES as ORIGINAL_CASES

ROOT=Path(__file__).resolve().parents[1]


def functions(module):
    return {n.name:n for n in ast.parse(Path(module.__file__).read_text()).body
            if isinstance(n,ast.FunctionDef)}


class CompactInstructionTests(unittest.TestCase):
    def test_every_guard_and_source_helper_is_exactly_the_installed_one(self):
        old, new, standalone = map(functions,(production,candidate,probe))
        for name,node in old.items():
            if name=='prepare':continue
            self.assertEqual(ast.dump(node),ast.dump(new[name]),name)
            self.assertEqual(ast.dump(node),ast.dump(standalone[name]),name)
        baseline=copy.deepcopy(standalone['baseline_prepare']);baseline.name='prepare'
        self.assertEqual(ast.dump(old['prepare']),ast.dump(baseline))

    def test_all_source_units_question_inventory_schema_and_prefix_are_preserved(self):
        page=ASYNC+LOOPS+CSV+'x'*650+'\n'+('An example. '*100)+'\n'
        for question in ('Due funzionalità.','Condizioni di conversione?','Prezzo sconosciuto?'):
            before=production.prepare(page,question)
            after=candidate.prepare(page,question)
            isolated=probe.compact_prepare(page,question)
            self.assertEqual(after,isolated)
            self.assertEqual(before[0],after[0]);self.assertEqual(''.join(after[0]),page)
            self.assertEqual(before[2],after[2]);self.assertEqual(before[1][1],after[1][1])
            self.assertEqual(list(json.loads(after[1][1]['content'])),
                             ['protectedIdentifiers','sourceTechnicalTerms','passages','question'])
            self.assertLess(len(after[1][0]['content']),len(before[1][0]['content']))
            self.assertEqual(candidate.MAX_CLAIM_CHARS,production.MAX_CLAIM_CHARS)

    def test_observed_wrong_qualifier_truncated_sentence_and_wrong_subprocess_still_fail(self):
        for text,quote,reason in ((OBSERVED_BAD,CSV,'unquoted_field_scope_not_preserved'),
                                 (OBSERVED_CUT,CSV,'sentence_not_complete'),
                                 (BAD,LOOPS,'source_technical_terms_not_preserved')):
            result=candidate.validate(raw(text),[quote],True)
            self.assertEqual(result['reason'],reason)
            self.assertEqual(result,production.validate(raw(text),[quote],True))
            self.assertEqual(result['claims'],[])

    def test_retains_original_scope_and_identifiers_even_when_term_is_elsewhere(self):
        for text,bank,reason in (
            ('csv.reader converte tutti i campi in float con QUOTE_NONNUMERIC.',[CSV],'unquoted_field_scope_not_preserved'),
            ('csv.reader converte sempre i campi non quotati in float.',[CSV],'csv_conversion_condition_not_preserved'),
            ('asyncio esegue coroutine in parallelo.',ASYNC.splitlines(keepends=True),'technical_term_missing_from_passage'),
            ('asyncio gestisce I/O di rete con IPC.',[LOOPS,ASYNC],'source_identifiers_not_preserved')):
            result=candidate.validate(raw(text),bank,True)
            self.assertEqual(result['reason'],reason)
        for text,quote in ((FAITHFUL,CSV),(GOOD,ASYNC.splitlines(keepends=True)[1])):
            result=candidate.validate(raw(text),[quote],True)
            self.assertEqual(result['outcome'],'accepted_pending_semantic_review')
            self.assertEqual(result['claims'][0]['text'],text)

    def test_completion_abstention_bounds_and_duplicate_keys_remain(self):
        self.assertEqual(candidate.validate('{"claims":[]}',[CSV],True)['outcome'],'abstained')
        self.assertEqual(candidate.validate(raw(FAITHFUL),[CSV],False)['reason'],'stream_incomplete')
        for answer in ('{"claims":[],"claims":[]}',raw('x'*321+'.'),'{"claims":"empty"}'):
            self.assertEqual(candidate.validate(answer,[CSV],True)['outcome'],'rejected')


class CacheAttributionTests(unittest.TestCase):
    def native(self,full=2000,cached=4,duration=40000):
        return {'prompt_eval_count':full,'prompt_eval_cached_count':cached,'prompt_evalMs':duration}

    def row(self,index,variant,full=2000,cached=4,duration=40000):
        case=probe.CASES[index]['id'];native=self.native(full,cached,duration)
        return {'case':case,'variant':variant,'result':{'status':'completed','native':native},
                'cacheQualification':probe.cache_qualification(native),'caseShapeMet':True}

    def rows(self):
        return [self.row(i,v,1750 if v=='compact' else 2000,
                         duration=33000 if v=='compact' else 40000) for i,v in probe.ORDER]

    def test_missing_fractional_boolean_negative_or_excessive_cache_counts_are_ineligible(self):
        for full,cached in ((2000,None),(2000,4.0),(True,0),(2000,True),(0,0),(-1,0),(2000,-1),(2000,2001),(2**53,0)):
            self.assertFalse(probe.cache_qualification(self.native(full,cached))['eligible'])
        self.assertTrue(probe.cache_qualification(self.native(2000,8))['eligible'])
        self.assertFalse(probe.cache_qualification(self.native(2000,9))['eligible'])
        self.assertFalse(probe.cache_qualification(self.native(100,8))['eligible'])

    def test_perf_gates_do_not_confer_semantic_pass_or_automatic_installation(self):
        result=probe.comparison(self.rows())
        self.assertEqual(result['performanceOutcome'],'measured_gates_met_pending_semantic_review')
        self.assertEqual(result['qualityVerdict'],'pending_review')
        self.assertFalse(result['integrationAllowedByThisAutomaticReport'])
        self.assertTrue(all(p['uncachedInputReductionPercent']>=10 for p in result['pairs']))

    def test_fast_result_with_cache_or_missing_prefill_is_inconclusive(self):
        rows=self.rows();rows[1]=self.row(0,'compact',1750,1700,1)
        self.assertEqual(probe.comparison(rows)['performanceOutcome'],'inconclusive_cache_or_metrics')
        rows=self.rows();rows[1]['result']['native']['prompt_evalMs']=None
        self.assertEqual(probe.comparison(rows)['performanceOutcome'],'inconclusive_cache_or_metrics')
        for ms in (0,True,-1,float('nan'),float('inf')):
            rows=self.rows();rows[1]['result']['native']['prompt_evalMs']=ms
            self.assertEqual(probe.comparison(rows)['performanceOutcome'],'inconclusive_cache_or_metrics')

    def test_one_failed_pair_or_bad_case_shape_cannot_be_averaged_away(self):
        rows=self.rows();rows[2]['result']['native']['prompt_evalMs']=39999
        self.assertEqual(probe.comparison(rows)['performanceOutcome'],'gates_not_met')
        rows=self.rows();rows[2]['caseShapeMet']=False
        self.assertEqual(probe.comparison(rows)['performanceOutcome'],'gates_not_met')
        self.assertFalse(probe.comparison(rows[:2])['allNativeCacheCountsEligible'])

    def test_isolation_copies_only_system_and_rejects_invalid_marker(self):
        _,messages,_=production.prepare(CSV,'Domanda')
        before=copy.deepcopy(messages)
        result=probe.isolated_messages(messages,'A'+'1'*32)
        self.assertEqual(messages,before);self.assertEqual(result[1],messages[1])
        self.assertTrue(result[0]['content'].endswith(messages[0]['content']))
        for marker in ('','A'+'a'*33,'quote:\n','Z'+'g'*32):
            with self.assertRaises(ValueError):probe.isolated_messages(messages,marker)


class NativeOpener(Opener):
    def open(self,request,timeout):
        if request.full_url.endswith('/api/andrea/web/read'):
            return super().open(request,timeout)
        data=json.loads(request.data);self.calls.append((request.full_url,data,timeout))
        index=self.infer_count
        answer=self.answers[index];self.infer_count+=1
        compact=probe.SHORT_SYSTEM in data['messages'][0]['content']
        return Response((json.dumps({'message':{'content':answer},'done':True,'done_reason':'stop',
            'prompt_eval_count':1750 if compact else 2000,'prompt_eval_cached_count':4,
            'prompt_eval_duration':33000000000 if compact else 40000000000,
            'load_duration':1000,'eval_count':25,'eval_duration':1000000})+'\n').encode())


class FiniteProbeTests(unittest.TestCase):
    def project(self,directory):
        root=Path(directory)
        for relative,digest in probe.EXPECTED.items():
            data=before_api_context_source(relative)
            self.assertEqual(hashlib.sha256(data).hexdigest(),digest)
            dest=root/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        (root/'private-note.md').write_text('must not be read')
        return root

    def answers(self):
        async_raw=json.dumps({'claims':[{'passage':1,'text':CONCURRENT},{'passage':2,'text':GOOD}]})
        return [async_raw,async_raw,raw(FAITHFUL),raw(FAITHFUL),'{"claims":[]}','{"claims":[]}']

    def test_six_calls_same_original_cases_two_source_snapshots_no_settings_or_files_changed(self):
        self.assertEqual(probe.CASES,ORIGINAL_CASES)
        with tempfile.TemporaryDirectory() as directory:
            root=self.project(directory);before={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
            opener=NativeOpener(self.answers());rows=probe.run(root,opener,lambda _:None)
            self.assertEqual(before,{p:p.read_bytes() for p in root.rglob('*') if p.is_file()})
        self.assertEqual((opener.read_count,opener.infer_count),(2,6))
        self.assertEqual([(r['case'],r['variant']) for r in rows],[(probe.CASES[i]['id'],v) for i,v in probe.ORDER])
        calls=[(data,timeout) for url,data,timeout in opener.calls if url.endswith('/api/chat')]
        self.assertEqual(len({data['messages'][0]['content'].splitlines()[0] for data,_ in calls}),6)
        for data,timeout in calls:
            self.assertEqual(data['options'],{'temperature':.4,'num_predict':512,'num_ctx':4096})
            self.assertEqual(data['keep_alive'],'15m');self.assertFalse(data['think'])
            self.assertEqual(data['model'],probe.MODEL);self.assertTrue(data['stream'])
            self.assertEqual(timeout,90);self.assertNotIn('tools',data)
        for a,b in ((0,1),(2,3),(4,5)):
            self.assertEqual(calls[a][0]['messages'][1],calls[b][0]['messages'][1])
            self.assertEqual(calls[a][0]['format'],calls[b][0]['format'])
            self.assertEqual(rows[a]['sourceTextSha256'],rows[b]['sourceTextSha256'])
        for row in rows:
            self.assertEqual(row['qualityVerdict'],'pending_review');self.assertFalse(row['vaultRead'])
            self.assertFalse(row['productionModified']);self.assertEqual(row['automaticRetries'],0)
        self.assertEqual(probe.comparison(rows)['performanceOutcome'],'measured_gates_met_pending_semantic_review')

    def test_rejected_raw_output_preserved_without_repair_or_retry(self):
        answers=self.answers();answers[2]=raw(OBSERVED_BAD)
        with tempfile.TemporaryDirectory() as directory:
            opener=NativeOpener(answers);rows=probe.run(self.project(directory),opener,lambda _:None)
        self.assertEqual(opener.infer_count,6)
        self.assertEqual(rows[2]['result']['modelAnswer'],raw(OBSERVED_BAD))
        self.assertEqual(rows[2]['checks']['reason'],'unquoted_field_scope_not_preserved')
        self.assertEqual(probe.comparison(rows)['performanceOutcome'],'gates_not_met')

    def test_read_error_missing_condition_local_edits_and_symlink_stop_before_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.project(directory);opener=NativeOpener(read_fail=True)
            with self.assertRaises(probe.CheckError):probe.run(root,opener,lambda _:None)
            self.assertEqual(opener.infer_count,0)
            cases=tuple({**c,'requiredContext':'absent predicate'} if i==1 else c for i,c in enumerate(probe.CASES))
            opener=NativeOpener()
            with patch.object(probe,'CASES',cases):
                with self.assertRaises(probe.CheckError):probe.run(root,opener,lambda _:None)
            self.assertEqual(opener.infer_count,0)
            target=root/'scripts/andrea/web_sentence_contract.py';data=target.read_bytes();target.write_text('local edit')
            opener=NativeOpener()
            with self.assertRaises(probe.CheckError):probe.run(root,opener,lambda _:None)
            self.assertEqual(opener.calls,[])
            target.unlink();(root/'elsewhere.py').write_bytes(data);target.symlink_to(root/'elsewhere.py')
            with self.assertRaises(probe.CheckError):probe.run(root,opener,lambda _:None)
            self.assertEqual(opener.calls,[])

    def test_preflight_payload_difference_stops_before_model(self):
        original=probe.compact_prepare
        def altered(text,question):
            bank,messages,schema=original(text,question)
            messages[1]['content']+=' altered'
            return bank,messages,schema
        with tempfile.TemporaryDirectory() as directory:
            opener=NativeOpener()
            with patch.object(probe,'compact_prepare',side_effect=altered):
                with self.assertRaises(probe.CheckError):probe.run(self.project(directory),opener,lambda _:None)
            self.assertEqual(opener.infer_count,0)

    def test_incomplete_transport_emits_diagnostic_and_stops_after_one(self):
        output=[]
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(probe,'stream_probe',return_value={'status':'incomplete','modelAnswer':'{','native':{}}) as call:
                with self.assertRaises(probe.CheckError):probe.run(self.project(directory),NativeOpener(),output.append)
            self.assertEqual(call.call_count,1)
        row=next(json.loads(line) for line in output if line.startswith('{'))
        self.assertEqual(row['checks']['reason'],'stream_incomplete')
        self.assertEqual(row['result']['modelAnswer'],'{')
        self.assertEqual(row['qualityVerdict'],'pending_review')


if __name__=='__main__':unittest.main()
