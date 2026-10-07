"""Constrain a simple source control verb before the model writes its complement.

Only positive action-led ``control ...;`` units get this finite Italian verb
starter. No object, whole sentence, source selection or empty answer is forced.
Other actions keep their previous grammar. All prior application checks still
apply to the unmodified model output; this is not a meaning certificate.
"""
from __future__ import annotations

import copy
import json
import re


CONTROL_STARTS = ('Permette di controllare ', 'Consente di controllare ')
INSTRUCTION = (
    ' For sourceControlVerbStarts, begin text with one listed control-verb start, '
    'then complete one short fact supported by that SAME passage. '
    'The complement is yours to generate; never change control into execution '
    'or invent an object or example. Other passages keep their existing starts.'
)


def simple_control_statement(quote):
    """Narrow positive single-operation fragment, not a general action parser."""
    compact = ' '.join(quote.split())
    match = re.fullmatch(r'control ([A-Za-z][A-Za-z0-9 /_-]{1,180})[.;]', compact)
    return bool(match and not re.search(
        r'\b(?:not|never|no|without|except|unless|if|and|or|to|with|by)\b',
        match.group(1), re.I))


def control_pattern(source_start, *, native_contract):
    if source_start and not re.fullmatch(r'[A-Z0-9_/ a-z]+: ', source_start):
        raise ValueError('native_operation_source_start_not_compatible')
    # No lookahead, backreference, text cap or wildcard precedes the verb.
    # Source labels, when required, remain before that actual verb starter.
    return '^'+source_start+'(?:'+'|'.join(CONTROL_STARTS)+')'+native_contract.TEXT+r'[.]$'


def apply(bank, messages, schema, selection, *, contract, native_contract):
    payload = json.loads(messages[1]['content'], object_pairs_hook=contract.unique_pairs)
    if payload['passages'] != [[ref, bank[ref-1]] for ref in selection['selectedRefs']]:
        raise ValueError('native_operation_source_alignment_failed')
    if 'sourceControlVerbStarts' in payload or 'nativeOperationVerbPolicy' in selection:
        raise ValueError('native_operation_already_applied')
    policy = {'mode': 'simple_positive_source_control_verb_before_free_complement',
              'rules': [], 'nativeSchemaChanged': False,
              'sourceBytesOrNumbersChanged': False, 'sourceEvidenceEligibilityChanged': False,
              'wholeSentenceForced': False, 'sourceObjectForced': False,
              'freeModelComplementPreserved': True, 'nativeArrayMinimumChanged': False,
              'unboundedTextBeforeMandatoryVerb': False,
              'semanticEntailmentCertified': False, 'noOutputRepair': True}
    eligible = selection['sourceCapabilityScopePolicy']['eligibleOperationRefs']
    controlled = [ref for ref in eligible if simple_control_statement(bank[ref-1])]
    if not selection['sourceCapabilityScopePolicy']['active'] or not controlled:
        return bank, copy.deepcopy(messages), copy.deepcopy(schema), {**selection, 'nativeOperationVerbPolicy': policy}
    if (len(messages) != 2 or [message['role'] for message in messages] != ['system', 'user']
            or list(payload)[-1] != 'question'):
        raise ValueError('native_operation_question_focus_not_compatible')
    source_rules = {rule['passage']: rule for rule in selection['nativeIdentifierPolicy']['rules']}
    guards = {ref: guard for guard in selection['sourceLabelScopePolicy']['guardBranches']
              for ref in guard['passages']}
    revised_schema = copy.deepcopy(schema)
    branches = revised_schema['properties']['claims']['items'].get('oneOf')
    if not isinstance(branches, list):
        raise ValueError('native_operation_schema_not_compatible')
    revised_branches, rules, seen = [], [], set()
    for branch in branches:
        refs = branch['properties']['passage']['enum']
        ordinary = [ref for ref in refs if ref not in controlled]
        if ordinary:
            unchanged = copy.deepcopy(branch)
            unchanged['properties']['passage']['enum'] = ordinary
            revised_branches.append(unchanged)
        for ref in refs:
            if ref not in controlled:
                continue
            if ref in seen:
                raise ValueError('native_operation_duplicate_reference')
            seen.add(ref)
            field = branch['properties']['text']
            source_rule = source_rules.get(ref)
            source_start = source_rule['requiredStart'] if source_rule else ''
            prior_pattern = field.get('pattern')
            # A fixed verb starter composes with an existing fixed-name prefix.
            # Without one it refines the existing leading-label complement.
            # Unknown constraints are never silently overwritten.
            if source_rule:
                expected = '^'+source_start+native_contract.TEXT+r'[.]$'
                compatible = prior_pattern == source_rule['pattern'] == expected
            else:
                guard = guards.get(ref)
                compatible = prior_pattern is None or (guard and prior_pattern == guard['pattern'])
            starts = [source_start+start for start in CONTROL_STARTS]
            if not compatible or (prior_pattern and any(
                    re.fullmatch(prior_pattern, start+'oggetti.') is None for start in starts)):
                raise ValueError('native_operation_prior_constraint_not_compatible')
            expression = control_pattern(source_start, native_contract=native_contract)
            revised = copy.deepcopy(branch)
            revised['properties']['passage']['enum'] = [ref]
            revised['properties']['text']['pattern'] = expression
            revised_branches.append(revised)
            rules.append({'passage': ref, 'sourceOperation': 'control',
                          'sourceStart': source_start, 'allowedStarts': starts,
                          'pattern': expression, 'priorPattern': prior_pattern})
    if seen != set(controlled):
        raise ValueError('native_operation_references_not_bound')
    revised_schema['properties']['claims']['items']['oneOf'] = revised_branches
    revised_messages = copy.deepcopy(messages)
    revised_messages[0]['content'] += INSTRUCTION
    question = payload.pop('question')
    payload['sourceControlVerbStarts'] = {str(rule['passage']): rule['allowedStarts'] for rule in rules}
    payload['question'] = question
    revised_messages[1]['content'] = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    return bank, revised_messages, revised_schema, {**selection, 'nativeOperationVerbPolicy': {
        **policy, 'rules': rules, 'nativeSchemaChanged': True}}


def validate_generation(result, selection):
    if result['outcome'] != 'accepted_pending_semantic_review':
        return result
    rules = {rule['passage']: rule for rule in selection['nativeOperationVerbPolicy']['rules']}
    for index, claim in enumerate(result['claims'], 1):
        rule = rules.get(claim['passage'])
        if rule and re.fullmatch(rule['pattern'], claim['text']) is None:
            return {'outcome': 'rejected', 'reason': 'native_operation_verb_not_observed', 'claims': [],
                    'details': {'claimIndex': index, **claim, 'diagnosticOnly': True,
                                'allowedStarts': rule['allowedStarts']}}
    return result
