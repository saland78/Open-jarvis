"""Put source-required names before the free predicate, without repairing text.

An unbounded wildcard before a required name permits indefinitely postponed
obligations. A finite source-name prefix removes that path. The free predicate
still comes from the model and requires all original source checks and review.
"""
from __future__ import annotations

import copy
import json
import re

INSTRUCTION = (' If a passage has a requiredStart, START its text with that exact source-name label, '
               'then paraphrase one complete fact ending with a period. Otherwise use normal text.')


def source_prefix(rule):
    identifiers = rule['mandatoryIdentifiers']
    if (not identifiers or identifiers != sorted(set(identifiers)) or len(identifiers) > 3
            or any(not re.fullmatch(r'I/O|[A-Z][A-Z0-9_]{1,31}', name) for name in identifiers)):
        raise ValueError('native_prefix_inventory_not_bounded')
    names = ['I/O di rete' if name == 'I/O' and rule['networkIOQualifierRequired'] else name
             for name in identifiers]
    return ' e '.join(names)+': '


def prefix_pattern(prefix, *, native_contract):
    # Prefix characters are checked source names, spaces and ':'; none is a
    # regex operator. Free text comes only AFTER all mandatory names. A final
    # period already belongs to the original complete-sentence requirement.
    if not re.fullmatch(r'[A-Z0-9_/ a-z]+: ', prefix):
        raise ValueError('native_prefix_characters_invalid')
    return '^'+prefix+native_contract.TEXT+r'[.]$'


def apply(bank, messages, schema, selection, *, native_contract):
    policy = selection['nativeIdentifierPolicy']
    if not policy['rules']:
        return bank, messages, schema, selection
    if messages[0]['content'].count(native_contract.INSTRUCTION) != 1:
        raise ValueError('native_prefix_instruction_not_compatible')
    payload = json.loads(messages[1]['content'])
    if payload['passages'] != [[ref, bank[ref-1]] for ref in selection['selectedRefs']]:
        raise ValueError('native_prefix_source_alignment_failed')
    rules, replacements, starts = [], {}, {}
    for rule in policy['rules']:
        prefix = source_prefix(rule)
        expression = prefix_pattern(prefix, native_contract=native_contract)
        previous = replacements.setdefault(rule['pattern'], expression)
        if previous != expression:
            raise ValueError('native_prefix_branch_ambiguous')
        rules.append({**rule, 'pattern': expression, 'requiredStart': prefix})
        starts[str(rule['passage'])] = prefix
    updated_schema = copy.deepcopy(schema)
    branches = updated_schema['properties']['claims']['items'].get('oneOf')
    if not isinstance(branches, list):
        raise ValueError('native_prefix_schema_not_compatible')
    changed = set()
    for branch in branches:
        field = branch['properties']['text']
        if 'pattern' in field:
            old = field['pattern']
            if old not in replacements:
                raise ValueError('native_prefix_unknown_branch_pattern')
            field['pattern'] = replacements[old]
            changed.update(branch['properties']['passage']['enum'])
    if changed != {rule['passage'] for rule in rules}:
        raise ValueError('native_prefix_references_not_bound')
    updated_messages = copy.deepcopy(messages)
    updated_messages[0]['content'] = updated_messages[0]['content'].replace(
        native_contract.INSTRUCTION, INSTRUCTION, 1)
    payload['requiredStarts'] = starts
    updated_messages[1]['content'] = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    selection = {**selection, 'nativeIdentifierPolicy': {
        **policy, 'mode': 'own_passage_names_before_free_predicate', 'rules': rules,
        'unboundedTextBeforeMandatoryNames': False,
        'fixedNameOrderChangedExplicitly': True,
        'sourceNameLabelsAreNotGeneratedPredicates': True}}
    return bank, updated_messages, updated_schema, selection
