"""Actual false rejection, finite context scope and unchanged performance gates."""
import ast
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_andrea_web_short_instructions as archived
import web_scoped_latency_candidate as candidate
import web_scoped_latency_probe as probe
import web_sentence_contract as installed
import web_short_retention_probe as previous_probe
import test_andrea_web_short_retention as previous_tests

CATALOGUE='create and manage event loops, which provide asynchronous APIs for networking, running subprocesses, handling OS signals, etc;\n'
OBSERVED="asyncio gestisce i sottoprocessi attraverso l'API di gestione degli event loop."
FIRST='asyncio permette di eseguire operazioni di I/O e comunicazione tra processi (IPC).'
CSV_FIRST=('csv.reader restituisce ogni riga come lista di stringhe; non esegue conversione automatica dei tipi salvo '
           'che quando è specificato il formato QUOTE_NONNUMERIC, in cui i campi non racchiusi tra virgolette vengono trasformati in float.')
CSV_SECOND=('Se il parametro QUOTE_NONNUMERIC non è specificato, csv.reader non esegue alcuna conversione automatica '
            'dei tipi, mantenendo i dati come stringhe originali.')


class CandidatePatch:
    def setUp(self):
        super().setUp()
        for name,value in (('candidate',candidate),('probe',probe)):
            patcher=patch.object(archived,name,value)
            patcher.start();self.addCleanup(patcher.stop)


class ScopedAttributionTests(CandidatePatch,archived.CacheAttributionTests):
    pass


class ScopedFiniteProbeTests(CandidatePatch,archived.FiniteProbeTests):
    pass


class FiniteTermAndScopeTests(unittest.TestCase):
    def test_exact_false_rejection_has_two_independent_program_causes(self):
        raw=archived.raw(OBSERVED)
        old=installed.validate(raw,[CATALOGUE],True)
        self.assertEqual(old['reason'],'technical_term_missing_from_passage')
        self.assertEqual(old['details']['missingConcepts'],['event loop'])
        self.assertEqual(probe.installed_validate(raw,[CATALOGUE],True),old)
        # Correcting only word morphology exposes the unrelated-item OS demand.
        result=copy.deepcopy(old)
        with patch.object(installed,'technical_terms',candidate.technical_terms):
            result=installed.validate(raw,[CATALOGUE],True)
        self.assertEqual(result['details']['missingIdentifiers'],['OS'])
        result=candidate.validate(raw,[CATALOGUE],True)
        self.assertEqual(result['outcome'],'accepted_pending_semantic_review')
        self.assertEqual(result['claims'][0]['text'],OBSERVED)
        self.assertEqual(result['claims'][0]['quote'],CATALOGUE)
        self.assertEqual(probe.validate(raw,[CATALOGUE],True),result)

    def test_finite_singular_plural_alias_is_symmetric_and_does_not_license_elsewhere(self):
        for text in ('event loop','event loops','EVENT LOOPS'):
            self.assertEqual(candidate.technical_terms(text),{'event loop'})
        self.assertEqual(candidate.technical_terms('coroutines'),{'coroutine'})
        self.assertEqual(candidate.technical_terms('event loopback'),set())
        text='asyncio gestisce gli event loop.'
        raw=archived.raw(text)
        result=candidate.validate(raw,['The library handles network communication.\n',CATALOGUE],True)
        self.assertEqual(result['reason'],'technical_term_missing_from_passage')
        self.assertEqual(result['details']['missingConcepts'],['event loop'])

    def test_signals_still_require_os_and_other_identifiers_are_not_removed(self):
        for text in ('asyncio gestisce i segnali dei sottoprocessi.',
                     'asyncio gestisce sottoprocessi e segnali.',
                     'asyncio handles subprocesses and signals.'):
            self.assertEqual(candidate.required_identifiers_for_claim(CATALOGUE,text),{'OS'})
            self.assertEqual(candidate.validate(archived.raw(text),[CATALOGUE],True)['details']['missingIdentifiers'],['OS'])
        self.assertEqual(candidate.required_identifiers_for_claim(CATALOGUE,'asyncio controlla i sottoprocessi.'),set())
        quote='perform network IO and IPC;\n'
        for text,missing in ((previous_tests.OBSERVED_SECOND,['IPC']),
                             ('asyncio gestisce comunicazione tra processi IPC.', ['I/O'])):
            result=candidate.validate(archived.raw(text),[quote],True)
            self.assertEqual(result['details']['missingIdentifiers'],missing)
        result=candidate.validate(archived.raw(previous_tests.OBSERVED_FIRST),['asyncio — Asynchronous I/O\n'],True)
        self.assertEqual(result['details']['missingIdentifiers'],['I/O'])

    def test_exception_requires_explicit_source_neighbouring_items_and_known_partial_fact(self):
        for quote in ('Use OS resources for running subprocesses.\n',
                      'create event loops for networking, running subprocesses. Handle OS signals.\n',
                      'Running subprocesses uses OS signals.\n'):
            # The multi-sentence case already had no forced identifiers; no new
            # relaxation may be attributed to this finite exception.
            self.assertEqual(candidate.required_identifiers_for_claim(quote,'asyncio controlla sottoprocessi.'),
                             installed.required_identifiers(quote))
        self.assertEqual(candidate.required_identifiers_for_claim(CATALOGUE,'asyncio gestisce gli event loop.'),{'OS'})
        for quantifier in ('tutte','tutti','tutta','tutto','ogni','qualsiasi','all','every','always','any'):
            self.assertEqual(candidate.required_identifiers_for_claim(CATALOGUE,quantifier+' sottoprocessi.'),{'OS'})

    def test_added_identifiers_and_wrong_subprocess_terms_still_fail(self):
        for text,quote,reason in (('asyncio controlla i sottoprocessi tramite GPU.',CATALOGUE,'source_identifiers_not_preserved'),
                                  ('asyncio gestisce sottoprogetti.','control subprocesses;\n','source_technical_terms_not_preserved')):
            result=candidate.validate(archived.raw(text),[quote],True)
            self.assertEqual(result['reason'],reason)
        result=candidate.validate(archived.raw('asyncio controlla sottoprocessi e OS segnali.'),
                                  ['control subprocesses;\n',CATALOGUE],True)
        self.assertEqual(result['details']['addedIdentifiers'],['OS'])

    def test_csv_qualifiers_conditions_negations_completion_and_numbers_are_unchanged(self):
        for text,quote,reason in ((archived.OBSERVED_BAD,archived.CSV,'unquoted_field_scope_not_preserved'),
                                 (archived.OBSERVED_CUT,archived.CSV,'sentence_not_complete'),
                                 ('csv.reader converte sempre i campi non quotati in float.',archived.CSV,'csv_conversion_condition_not_preserved'),
                                 ('asyncio gestisce 500 sottoprocessi.',CATALOGUE,'unsupported_number')):
            self.assertEqual(candidate.validate(archived.raw(text),[quote],True)['reason'],reason)
        for text in (CSV_FIRST,CSV_SECOND):
            result=candidate.validate(archived.raw(text),[archived.CSV],True)
            self.assertEqual(result['outcome'],'accepted_pending_semantic_review')
            self.assertEqual(result['claims'][0]['text'],text)
        # Repetition is still a model/semantic criterion, not silently repaired.
        raw=json.dumps({'claims':[{'passage':1,'text':CSV_FIRST},{'passage':1,'text':CSV_SECOND}]})
        self.assertEqual(len(candidate.validate(raw,[archived.CSV],True)['claims']),2)
        self.assertEqual(candidate.validate('{"claims":[]}',[archived.CSV],True)['outcome'],'abstained')

    def test_complete_actual_asyncio_json_preserves_original_numbers_text_and_quotes(self):
        bank=['Unselected context only.\n']*18
        bank[9]='perform network IO and IPC;\n';bank[17]=CATALOGUE
        raw=json.dumps({'claims':[{'passage':10,'text':FIRST},{'passage':18,'text':OBSERVED}]})
        result=candidate.validate(raw,bank,True)
        self.assertEqual(result['outcome'],'accepted_pending_semantic_review')
        self.assertEqual([x['text'] for x in result['claims']],[FIRST,OBSERVED])
        self.assertEqual([x['passage'] for x in result['claims']],[10,18])
        self.assertEqual(probe.installed_validate(raw,bank,True)['reason'],'technical_term_missing_from_passage')
        self.assertEqual(candidate.validate(raw,bank,False)['reason'],'stream_incomplete')

    def test_all_other_guard_and_source_helper_asts_are_identical_and_pure_probe_match(self):
        old,new,standalone=map(archived.functions,(installed,candidate,probe))
        for name,node in old.items():
            if name not in ('prepare','validate','technical_terms'):
                self.assertEqual(ast.dump(node),ast.dump(new[name]),name)
            if name!='prepare':self.assertEqual(ast.dump(new[name]),ast.dump(standalone[name]),name)
        self.assertEqual(ast.dump(new['required_identifiers_for_claim']),ast.dump(standalone['required_identifiers_for_claim']))
        for name in ('stream_probe','native_metrics','cache_qualification','isolated_messages','case_shape'):
            self.assertEqual(ast.dump(archived.functions(previous_probe)[name]),ast.dump(standalone[name]),name)

    def test_sources_schema_inventory_question_original_cases_and_limits_remain_identical(self):
        page=archived.ASYNC+CATALOGUE+archived.CSV
        for case in probe.CASES:
            before=installed.prepare(page,case['question']);after=candidate.prepare(page,case['question'])
            self.assertEqual(before[0],after[0]);self.assertEqual(''.join(after[0]),page)
            self.assertEqual(before[2],after[2]);self.assertEqual(before[1][1],after[1][1])
            self.assertEqual(after,probe.compact_prepare(page,case['question']))
        self.assertEqual(probe.CASES,previous_probe.CASES);self.assertEqual(probe.ORDER,previous_probe.ORDER)
        self.assertEqual(probe.EXPECTED,previous_probe.EXPECTED)
        self.assertEqual(candidate.MAX_CLAIM_CHARS,installed.MAX_CLAIM_CHARS)

    def test_latest_failed_mac_gate_cannot_be_relabelled_by_a_term_fix(self):
        measurements=((1670,0,37972.152),(1430,3,32910.583),(2200,4,37463.390),
                      (2445,3,40960.856),(2442,4,41608.835),(2201,3,38388.695))
        rows=[]
        for (i,v),(full,cached,ms) in zip(probe.ORDER,measurements):
            native={'prompt_eval_count':full,'prompt_eval_cached_count':cached,'prompt_evalMs':ms}
            rows.append({'case':probe.CASES[i]['id'],'variant':v,'result':{'status':'completed','native':native},
                         'cacheQualification':probe.cache_qualification(native),'caseShapeMet':True})
        result=probe.comparison(rows)
        self.assertEqual(result['performanceOutcome'],'gates_not_met')
        self.assertEqual(result['pairs'][1]['uncachedInputReductionPercent'],10.074)
        self.assertEqual(result['pairs'][1]['nativePrefillReductionPercent'],8.539)
        self.assertFalse(result['pairs'][1]['performanceGateMet'])
        self.assertEqual(result['fixedGates'],previous_probe.comparison(rows)['fixedGates'])
        self.assertEqual(result['qualityVerdict'],'pending_review')


if __name__=='__main__':unittest.main()
