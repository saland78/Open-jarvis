"""Apply the reviewed compact context and rule budget to live page requests."""
from __future__ import annotations
import web_definition_context as context
import web_page_fidelity as fidelity
import web_single_rule_budget as rule_budget

CONTRACT_REVISION = 'complete_api_entries_signal_scope_v1'


def prepare(page, question):
    bank, messages, schema, selection = context.prepare(
        page['text'], question, heading_ranges=page.get('headingRanges', []),
        definition_ranges=page.get('definitionRanges', []), contract=fidelity)
    policy = rule_budget.plan(question, bank, selection, contract=fidelity)
    messages, schema = rule_budget.apply(messages, schema, policy)
    return bank, messages, schema, {**selection, 'outputPolicy': policy}


def validate(raw, bank, complete, page, selection):
    checked = context.validate(raw, bank, complete, heading_ranges=page.get('headingRanges', []),
                               contract=fidelity, selection=selection)
    return rule_budget.validate_cardinality(checked, selection['outputPolicy'])
