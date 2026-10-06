"""Consolidated v9 compact preparation and validation for the web service.

This adapter preserves the reviewed preparation and validation byte for byte at
the interface. It imports no benchmark, creates no model requests, and makes no
adoption decision. General source entailment still requires meaning review.
"""
from __future__ import annotations

import importlib.util

import web_definition_context as context
import web_single_rule_budget as rule_budget
import web_networking_scope as networking
import web_native_identifier_schema as identifiers
import web_native_identifier_prefix as prefix
import web_source_label_scope as labels
import web_capability_evidence as capabilities
import web_source_performance_scope as performance
import web_question_focus as question_focus
import web_operation_predicate_scope as operations
import web_native_operation_verb as verbs

CONTRACT_REVISION = 'compact_web_evidence_v9'

# Isolate the exact reviewed finite CSV alias without changing the contract
# currently used by the installed server or another request path.
_spec = importlib.util.spec_from_file_location(
    '_staged_web_candidate_fidelity', importlib.util.find_spec('web_page_fidelity').origin)
contract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(contract)
labels.install_csv_file_aliases(contract)


def prepare(page, question):
    bank, messages, schema, selection = context.prepare(
        page['text'], question, heading_ranges=page.get('headingRanges', []),
        definition_ranges=page.get('definitionRanges', []), contract=contract)
    policy = rule_budget.plan(question, bank, selection, contract=contract)
    messages, schema = rule_budget.apply(messages, schema, policy)
    selection = {**selection, 'outputPolicy': policy}
    bank, messages, schema, selection = networking.apply(
        bank, messages, schema, selection, contract=contract)
    bank, messages, schema, selection = identifiers.apply(
        bank, messages, schema, selection, contract=contract)
    bank, messages, schema, selection = prefix.apply(
        bank, messages, schema, selection, native_contract=identifiers)
    bank, messages, schema, selection = labels.apply(
        bank, messages, schema, selection, contract=contract, native_contract=identifiers)
    for adapter in (capabilities, performance, question_focus, operations):
        bank, messages, schema, selection = adapter.apply(
            bank, messages, schema, selection, contract=contract)
    return verbs.apply(bank, messages, schema, selection,
                       contract=contract, native_contract=identifiers)


def validate(raw, bank, completed, page, selection):
    checked = context.validate(raw, bank, completed,
        heading_ranges=page.get('headingRanges', []), contract=contract, selection=selection)
    checked = rule_budget.validate_cardinality(checked, selection['outputPolicy'])
    for adapter in (labels, identifiers, capabilities, performance, question_focus, operations, verbs):
        checked = adapter.validate_generation(checked, selection)
    return checked
