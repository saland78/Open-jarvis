"""Exact observed identifier omissions plus the unchanged finite attribution protocol."""
import ast
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_andrea_web_short_instructions as archived
import web_short_retention_candidate as candidate
import web_short_retention_probe as probe
import web_short_instructions_candidate as previous
import web_short_instructions_probe as previous_probe
import web_sentence_contract as production

OBSERVED_FIRST='asyncio serve per gestire operazioni asincrone di input/output.'
OBSERVED_SECOND='asyncio permette di eseguire operazioni di I/O e comunicazione tra processi.'
OBSERVED_CSV=('csv.reader restituisce ogni riga come lista di stringhe senza conversione automatica dei tipi, '
              'salvo quando è specificato QUOTE_NONNUMERIC, in cui i campi non virgolettati vengono trasformati in float.')


class CandidatePatch:
    def setUp(self):
        super().setUp()
        for name,value in (('candidate',candidate),('probe',probe)):
            patcher=patch.object(archived,name,value)
            patcher.start();self.addCleanup(patcher.stop)


class RetentionContractTests(CandidatePatch,archived.CompactInstructionTests):
    pass


class RetentionAttributionTests(CandidatePatch,archived.CacheAttributionTests):
    pass


class RetentionFiniteProbeTests(CandidatePatch,archived.FiniteProbeTests):
    pass


class ObservedFailureTests(unittest.TestCase):
    def bank(self):
        bank=['Unselected context only.\n']*11
        bank[0]='asyncio — Asynchronous I/O\n'
        bank[9]='perform network IO and IPC;\n'
        bank[10]='control subprocesses;\n'
        return bank

    def test_exact_two_claim_failure_remains_rejected_and_not_repaired(self):
        answer=json.dumps({'claims':[{'passage':1,'text':OBSERVED_FIRST},
                                     {'passage':10,'text':OBSERVED_SECOND}]})
        result=candidate.validate(answer,self.bank(),True)
        self.assertEqual(result,production.validate(answer,self.bank(),True))
        self.assertEqual(result['reason'],'source_identifiers_not_preserved')
        self.assertEqual(result['details']['missingIdentifiers'],['I/O'])
        self.assertEqual(result['details']['text'],OBSERVED_FIRST)
        self.assertEqual(result['claims'],[])

    def test_first_failure_does_not_mask_missing_ipc_in_second_claim(self):
        answer=json.dumps({'claims':[{'passage':10,'text':OBSERVED_SECOND}]})
        result=candidate.validate(answer,self.bank(),True)
        self.assertEqual(result['details']['missingIdentifiers'],['IPC'])
        self.assertEqual(result['details']['text'],OBSERVED_SECOND)
        self.assertEqual(result['claims'],[])
        faithful='asyncio consente I/O di rete e IPC.'
        result=candidate.validate(json.dumps({'claims':[{'passage':10,'text':faithful}]}),self.bank(),True)
        self.assertEqual(result['outcome'],'accepted_pending_semantic_review')
        self.assertEqual(result['claims'][0]['text'],faithful)

    def test_successful_csv_response_preserves_conditions_and_unquoted_scope_unchanged(self):
        result=candidate.validate(archived.raw(OBSERVED_CSV),[archived.CSV],True)
        self.assertEqual(result['outcome'],'accepted_pending_semantic_review')
        self.assertEqual(result['claims'][0]['text'],OBSERVED_CSV)
        self.assertEqual(result,production.validate(archived.raw(OBSERVED_CSV),[archived.CSV],True))

    def test_original_failed_mac_comparison_keeps_all_original_thresholds(self):
        measurements=((1673,0,34712.084),(1465,3,28575.263),(2237,4,44495.310),
                      (2447,3,53422.591),(2442,4,51022.260),(2238,3,46610.606))
        rows=[]
        for index,((i,variant),(full,cached,duration)) in enumerate(zip(probe.ORDER,measurements)):
            native={'prompt_eval_count':full,'prompt_eval_cached_count':cached,'prompt_evalMs':duration}
            rows.append({'case':probe.CASES[i]['id'],'variant':variant,
                         'result':{'status':'completed','native':native},
                         'cacheQualification':probe.cache_qualification(native),'caseShapeMet':index!=1})
        result=probe.comparison(rows)
        self.assertEqual(result['performanceOutcome'],'gates_not_met')
        self.assertFalse(result['technicalCaseShapesMet'])
        self.assertEqual(result['pairs'][0]['uncachedInputReductionPercent'],12.612)
        self.assertEqual(result['pairs'][1]['uncachedInputReductionPercent'],8.633)
        self.assertFalse(result['pairs'][1]['performanceGateMet'])
        self.assertEqual(result['fixedGates'],previous_probe.comparison(rows)['fixedGates'])
        self.assertEqual(result['qualityVerdict'],'pending_review')

    def test_schema_question_full_source_and_guard_asts_remain_same_as_both_variants(self):
        source=archived.ASYNC+archived.CSV
        for case in probe.CASES:
            old=production.prepare(source,case['question'])
            prior=previous.prepare(source,case['question'])
            new=candidate.prepare(source,case['question'])
            self.assertEqual(old[0],new[0]);self.assertEqual(old[2],new[2])
            self.assertEqual(prior[1][1],new[1][1]);self.assertEqual(old[1][1],new[1][1])
            self.assertEqual(new,probe.compact_prepare(source,case['question']))
            self.assertEqual(''.join(new[0]),source)
            self.assertLess(len(new[1][0]['content']),len(prior[1][0]['content']))
        self.assertEqual(probe.CASES,previous_probe.CASES)
        self.assertEqual(probe.ORDER,previous_probe.ORDER)
        self.assertEqual(probe.EXPECTED,previous_probe.EXPECTED)
        old,new=archived.functions(previous_probe),archived.functions(probe)
        for name in ('stream_probe','native_metrics','cache_qualification','isolated_messages','case_shape','validate'):
            self.assertEqual(ast.dump(old[name]),ast.dump(new[name]),name)


if __name__=='__main__':unittest.main()
