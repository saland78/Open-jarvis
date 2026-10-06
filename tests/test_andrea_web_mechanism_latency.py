"""The actual unsupported interface addition is not silently accepted or fixed."""
import json
import unittest

import web_mechanism_latency_candidate as candidate
import web_type_latency_candidate as preceding
from test_andrea_web_type_latency import CSV, OBSERVED_DECIMAL, OBSERVED_IO

QUOTE = 'control subprocesses;\n'
OBSERVED = "asyncio consente di gestire sottoprocessi attraverso un'interfaccia specifica."


def raw(text, ref=1):
    return json.dumps({'claims': [{'text': text, 'passage': ref}]})


class MechanismScopeTests(unittest.TestCase):
    def test_exact_observed_addition_is_rejected_with_raw_diagnostic_text(self):
        answer = raw(OBSERVED)
        self.assertEqual(preceding.validate(answer, [QUOTE], True, heading_ranges=[])['outcome'],
                         'accepted_pending_semantic_review')
        result = candidate.validate(answer, [QUOTE], True, heading_ranges=[])
        self.assertEqual(result['reason'], 'subprocess_mechanism_not_in_passage')
        self.assertEqual(result['claims'], [])
        self.assertEqual(result['details']['text'], OBSERVED)
        self.assertEqual(result['details']['quote'], QUOTE)
        self.assertTrue(result['details']['diagnosticOnly'])

    def test_two_point_answer_is_rejected_entirely_without_removing_its_bad_suffix(self):
        bank = ['perform network IO and IPC;\n', QUOTE]
        answer = json.dumps({'claims': [{'text': OBSERVED_IO, 'passage': 1}, {'text': OBSERVED, 'passage': 2}]})
        result = candidate.validate(answer, bank, True, heading_ranges=[])
        self.assertEqual(result['claims'], [])
        self.assertEqual(result['details']['claimIndex'], 2)
        self.assertEqual(result['details']['text'], OBSERVED)

    def test_correct_capability_and_other_guard_results_remain_unchanged(self):
        for text, quote in (('asyncio consente di gestire sottoprocessi.', QUOTE),
                            (OBSERVED_IO, 'perform network IO and IPC;\n'),
                            (OBSERVED_DECIMAL, CSV)):
            answer = raw(text)
            self.assertEqual(candidate.validate(answer, [quote], True, heading_ranges=[]),
                             preceding.validate(answer, [quote], True, heading_ranges=[]))
        for complete in (False, True):
            self.assertEqual(candidate.validate('{"claims":[]}', [QUOTE], complete, heading_ranges=[]),
                             preceding.validate('{"claims":[]}', [QUOTE], complete, heading_ranges=[]))

    def test_only_the_known_bare_source_capability_gets_the_extra_scope_guard(self):
        for quote in ('control subprocesses using an explicit interface;\n',
                      'A separate interface implements this capability.\n', CSV):
            self.assertIsNone(candidate.bare_subprocess_scope_error(OBSERVED, quote))
        for means in ('tramite', 'mediante', 'usando', 'utilizzando', 'through', 'via', 'using', 'per mezzo di'):
            self.assertEqual(candidate.bare_subprocess_scope_error(
                OBSERVED.replace('attraverso', means), QUOTE), 'subprocess_mechanism_not_in_passage')

    def test_another_unit_with_an_interface_does_not_license_this_claim(self):
        bank = [QUOTE, 'The documented interface performs another operation.\n']
        self.assertEqual(candidate.validate(raw(OBSERVED), bank, True, heading_ranges=[])['reason'],
                         'subprocess_mechanism_not_in_passage')

    def test_preparation_preserves_full_source_user_message_and_native_schema(self):
        page = 'perform network IO and IPC;\n' + QUOTE
        before = preceding.prepare(page, 'Due funzionalità?', heading_ranges=[])
        after = candidate.prepare(page, 'Due funzionalità?', heading_ranges=[])
        self.assertEqual(before[0], after[0]); self.assertEqual(''.join(after[0]), page)
        self.assertEqual(before[2], after[2]); self.assertEqual(before[1][1], after[1][1])
        self.assertEqual(after[1][0]['content'], before[1][0]['content'] + candidate.MECHANISM_INSTRUCTION)


if __name__ == '__main__': unittest.main()
