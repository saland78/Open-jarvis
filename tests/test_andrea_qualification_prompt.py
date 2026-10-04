"""Reviewed wire equivalence and bounded routing, synthetic Markdown only."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

from test_andrea_real_notes_synthesis import BOOK, QUALIFICATIONS, note

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/andrea'))
import concise_qualification_text_probe as historical_probe
from andrea_qualification_baseline import load_modules as historical_modules
note_facts = historical_modules(historical_probe).bridge
import predicate_context_synthesis as synthesis
import qualification_prompt

spec = importlib.util.spec_from_file_location('reviewed_compact_probe', ROOT/'scripts/andrea/compact_note_prompt_probe.py')
probe = importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)


class QualificationPromptTests(unittest.TestCase):
    def bundle(self, kind):
        return note_facts.prepare(note(BOOK if kind == 'book' else QUALIFICATIONS, 'Synthetic.md'))

    def test_qualification_wire_is_byte_identical_to_reviewed_candidate(self):
        bundle = self.bundle('qualifications')
        before = copy.deepcopy(bundle)
        expected = probe.compact.messages(bundle['case'], bundle['plan'], synthesis)
        actual = qualification_prompt.messages(bundle['case'], bundle['plan'], synthesis)
        self.assertEqual(actual, expected)
        self.assertEqual(bundle['messages'], expected)
        self.assertEqual(bundle, before)
        original = json.loads(synthesis.messages(bundle['case'], bundle['plan'])[1]['content'])
        compact = json.loads(actual[1]['content'])
        for key in ('richiesta', 'informazioni_obbligatorie'):
            self.assertEqual(original[key], compact[key])
        self.assertEqual(original['response_schema'], bundle['plan']['schema'])
        self.assertLess(sum(len(m['content']) for m in actual),
                        sum(len(m['content']) for m in synthesis.messages(bundle['case'], bundle['plan'])))

    def test_book_route_retains_exact_original_messages_and_refuses_compact_composer(self):
        bundle = self.bundle('book')
        self.assertEqual(bundle['messages'], synthesis.messages(bundle['case'], bundle['plan']))
        with self.assertRaisesRegex(ValueError, 'unsupported_qualification_plan'):
            qualification_prompt.messages(bundle['case'], bundle['plan'], synthesis)

    def test_reordered_incomplete_or_unknown_plans_cannot_use_qualification_compaction(self):
        bundle = self.bundle('qualifications')
        for alter in ('reordered', 'missing', 'unknown'):
            plan = copy.deepcopy(bundle['plan'])
            if alter == 'reordered':
                plan['facts'].reverse()
            elif alter == 'missing':
                plan['facts'].pop()
            else:
                plan['facts'][0]['kind'] = 'unreviewed'
            with self.assertRaisesRegex(ValueError, 'unsupported_qualification_plan'):
                qualification_prompt.messages(bundle['case'], plan, synthesis)


if __name__ == '__main__':
    unittest.main()
