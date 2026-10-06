"""Consolidation parity and honest separation of reference and candidate review."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import unittest

import web_candidate_pipeline as staged
import web_page_context_contract as installed
import web_page_fidelity as installed_fidelity
import web_native_operation_verb_probe as v9
from test_andrea_web_capability_scope import page, CSV_RULE
from test_andrea_web_definition_context import extracted, html_entry

ROOT = Path(__file__).resolve().parents[1]


def report():
    return json.loads((ROOT/'docs/andrea/web-native-operation-verb-v9-mac-2026-10-06.json').read_text())


class CandidateConsolidationTests(unittest.TestCase):
    def test_original_six_row_failure_is_not_relabelled_as_six_meaning_passes(self):
        observed=report()
        self.assertEqual(observed['originalAutomaticReport']['completedTransports'],6)
        self.assertTrue(observed['originalAutomaticReport']['technicalCaseShapesMet'])
        self.assertEqual(observed['manualReviewCounts'],{'favorable':5,'unfavorable':1})
        self.assertEqual(observed['compactManualReviewCounts'],{'favorable':3,'unfavorable':0})
        self.assertEqual(observed['overallReview'],'not_passed_no_adoption')
        self.assertFalse(observed['automaticIntegrationAllowed'])
        self.assertEqual(observed['rows'][0]['checks']['outcome'],'accepted_pending_semantic_review')
        self.assertEqual(observed['rows'][0]['manualReview']['outcome'],'unfavorable')
        self.assertNotIn('/Users/',json.dumps(observed))

    def test_original_performance_gates_recompute_and_retain_manual_review(self):
        observed=report(); recomputed=v9.baseline.comparison(observed['rows'])
        for key in ('pairs','technicalCaseShapesMet','allNativeCacheCountsEligible','performanceOutcome','fixedGates'):
            self.assertEqual(recomputed[key],observed['originalAutomaticReport'][key])
        self.assertEqual(recomputed['qualityVerdict'],'pending_review')

    def test_three_compact_reviews_are_favorable_in_each_of_three_recorded_revisions(self):
        for filename in ('web-question-focus-v7-mac-2026-10-06.json',
                         'web-operation-predicate-v8-mac-2026-10-06.json',
                         'web-native-operation-verb-v9-mac-2026-10-06.json'):
            value=json.loads((ROOT/'docs/andrea'/filename).read_text())
            compact=[r for r in value['rows'] if r['variant']=='compact']
            self.assertEqual(len(compact),3)
            self.assertTrue(all(r['manualReview']['outcome']=='favorable' for r in compact))
            # Different revisions are observations, not nine independent runs
            # of one unchanged production build or a new adoption permission.
            self.assertFalse(value['automaticIntegrationAllowed'])

    def test_all_three_preparations_are_exact_reviewed_compact_v9(self):
        csv=extracted('<h1>csv</h1>'+html_entry('csv.reader','<p>'+CSV_RULE+'</p>'))
        for index,case in enumerate(v9.baseline.CASES):
            source=page() if index==0 else csv
            before=copy.deepcopy(source)
            self.assertEqual(staged.prepare(source,case['question']),v9.prepared(source,case,'compact'))
            self.assertEqual(source,before)

    def test_actual_compact_answers_keep_their_exact_outputs_and_quotes(self):
        for row in report()['rows']:
            if row['variant']!='compact': continue
            bank=['Unrelated context only.\n']*max(row['selection']['selectedRefs'])
            for claim in row['checks']['claims']: bank[claim['passage']-1]=claim['quote']
            # Validate against the original selection, which owns its source
            # refs. No new response or repaired text is manufactured here.
            source={'headingRanges':[]}
            result=staged.validate(row['result']['modelAnswer'],bank,True,source,row['selection'])
            self.assertEqual(result,row['checks'])

    def test_incomplete_transport_and_genuine_abstention_stay_distinct(self):
        source=page(); bank,_,_,selection=staged.prepare(source,v9.baseline.CASES[0]['question'])
        incomplete=staged.validate('{"claims":[]}',bank,False,source,selection)
        self.assertEqual(incomplete['outcome'],'rejected')
        self.assertEqual(staged.validate('{"claims":[]}',bank,True,source,selection)['outcome'],'abstained')

    def test_aliases_are_isolated_and_current_live_contract_is_not_replaced(self):
        self.assertIsNot(staged.contract,installed_fidelity)
        self.assertEqual(staged.contract.source_identifier_aliases('csv file'),{'CSV'})
        self.assertEqual(installed_fidelity.source_identifier_aliases('csv file'),set())
        self.assertEqual(installed.CONTRACT_REVISION,'complete_api_entries_signal_scope_v1')
        self.assertEqual(hashlib.sha256((ROOT/'scripts/andrea/web_page_context_contract.py').read_bytes()).hexdigest(),
                         'a7fa689865126891912e5f9c280ef9afc8b68771770ee5b7902cc46eac7b02e1')

    def test_staged_pipeline_has_no_benchmark_or_generation_transport(self):
        source=(ROOT/'scripts/andrea/web_candidate_pipeline.py').read_text()
        tree=ast.parse(source)
        imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        imports += [alias.name for n in ast.walk(tree) if isinstance(n,ast.Import) for alias in n.names]
        self.assertFalse(any('probe' in name or 'benchmark' in name for name in imports if name))
        self.assertFalse(any(name in imports for name in ('urllib','requests','httpx','socket','subprocess')))
        self.assertEqual({n.name for n in tree.body if isinstance(n,ast.FunctionDef)},{'prepare','validate'})


if __name__=='__main__':
    unittest.main()
