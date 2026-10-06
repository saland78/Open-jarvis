"""Bind unconditional source identifiers to their own native claim branch.

This is a generation constraint, not an output repair or semantic classifier.
Conditional/multi-sentence identifiers retain their existing application
checks. A source network-I/O item keeps its finite network qualifier.
"""
from __future__ import annotations

import copy
import itertools
import json
import re

MAX_NATIVE_IDENTIFIERS = 3
TEXT = r'[^"\\\x00-\x1F\x7F]*'
IO = r'(?:I/O|IO|input/output)'
NETWORK_IO = r'(?:(?:I/O|IO|input/output)[ ]+(?:di|in)[ ]+rete|network[ ]+(?:I/O|IO|input/output))'
INSTRUCTION = (' Keep your passage\u2019s protectedIdentifiers as names. Source network IO = I/O di rete.')


def unconditional_identifiers(quote, *, contract):
    required = contract.required_identifiers(contract.io_identifier_text(quote))
    # The existing validator permits a subprocess-only partial fact from this
    # catalogue to omit the neighboring OS-signals item. Do not close that
    # valid branch by making its conditional OS token globally mandatory.
    if (contract.subprocess_terms(quote)
            and re.search(r'\brunning\s+subprocesses\s*,\s*handling\s+OS\s+signals\b', quote, re.I)):
        required -= {'OS'}
    return sorted(required)


def pattern(identifiers, *, network_io=False):
    if (not identifiers or identifiers != sorted(set(identifiers))
            or len(identifiers) > MAX_NATIVE_IDENTIFIERS
            or any(not re.fullmatch(r'I/O|[A-Z][A-Z0-9_]{1,31}', token) for token in identifiers)):
        raise ValueError('native_identifier_pattern_not_bounded')
    atoms = [NETWORK_IO if token == 'I/O' and network_io else IO if token == 'I/O' else re.escape(token)
             for token in identifiers]
    # Supported anchored alternation, classes and repetition only. There is
    # no lookaround/backreference, string cap or identifier-order assumption.
    alternatives = [TEXT + TEXT.join(order) + TEXT for order in itertools.permutations(atoms)]
    return '^(?:' + '|'.join(alternatives) + ')$'


def apply(bank, messages, schema, selection, *, contract):
    items = schema['properties']['claims']['items']
    if (items.get('type') != 'object' or items.get('additionalProperties') is not False
            or set(items.get('required', [])) != {'passage', 'text'}
            or set(items.get('properties', {})) != {'passage', 'text'}
            or items['properties']['text'] != {'type': 'string', 'minLength': 20}
            or items['properties']['passage'].get('type') != 'integer'):
        raise ValueError('native_identifier_schema_not_compatible')
    payload = json.loads(messages[1]['content'], object_pairs_hook=contract.unique_pairs)
    refs = selection['selectedRefs']
    if payload['passages'] != [[ref, bank[ref-1]] for ref in refs]:
        raise ValueError('native_identifier_source_alignment_failed')
    eligible = items['properties']['passage']['enum']
    if (not isinstance(eligible, list) or eligible != sorted(set(eligible))
            or any(type(ref) is not int or ref not in refs for ref in eligible)):
        raise ValueError('native_identifier_references_invalid')
    rules, not_encoded, groups = [], [], {}
    for ref in eligible:
        quote = bank[ref-1]
        identifiers = unconditional_identifiers(quote, contract=contract)
        if not identifiers:
            continue
        if len(identifiers) > MAX_NATIVE_IDENTIFIERS:
            not_encoded.append(ref)
            continue
        network_io = bool('I/O' in identifiers and re.search(r'\bnetwork\s+(?:I/O|IO|input/output)\b', quote, re.I))
        expression = pattern(identifiers, network_io=network_io)
        rules.append({'passage': ref, 'mandatoryIdentifiers': identifiers,
                      'networkIOQualifierRequired': network_io, 'pattern': expression})
        groups.setdefault(expression, []).append(ref)
    policy = {'mode': 'own_passage_native_identifiers' if rules else 'no_unconditional_identifiers',
              'rules': rules, 'notEncodedNativeRefs': not_encoded, 'maxIdentifiersPerBranch': MAX_NATIVE_IDENTIFIERS,
              'unmodifiedApplicationValidationRequired': True}
    selection = {**selection, 'nativeIdentifierPolicy': policy}
    if not rules:
        return bank, messages, schema, selection
    branches = []
    for expression, own_refs in groups.items():
        branch = copy.deepcopy(items)
        # Put the passage first for converters that preserve object order.
        # Each disjoint enum binds this text pattern to only its own sources.
        branch['properties'] = {'passage': {'type': 'integer', 'enum': own_refs},
                                'text': {**items['properties']['text'], 'pattern': expression}}
        branches.append(branch)
    constrained = {rule['passage'] for rule in rules}
    ordinary = [ref for ref in eligible if ref not in constrained]
    if ordinary:
        branch = copy.deepcopy(items)
        branch['properties'] = {'passage': {'type': 'integer', 'enum': ordinary},
                                'text': copy.deepcopy(items['properties']['text'])}
        branches.append(branch)
    updated_schema = copy.deepcopy(schema)
    # oneOf has no sibling properties: that unsupported mixed form is avoided.
    updated_schema['properties']['claims']['items'] = {'oneOf': branches}
    updated_messages = copy.deepcopy(messages)
    for rule in rules:
        if rule['networkIOQualifierRequired']:
            ref = str(rule['passage'])
            terms = payload['sourceTechnicalTerms'].setdefault(ref, [])
            payload['sourceTechnicalTerms'][ref] = sorted(set(terms) | {'network IO'})
    updated_messages[0]['content'] += INSTRUCTION
    updated_messages[1]['content'] = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    return bank, updated_messages, updated_schema, selection


def validate_generation(result, selection):
    """Also check the native promise, after all unchanged application checks.

    A decoder that ignores a schema branch must not count as an effective
    constraint. Preserve refusals and raw points; never return a repaired or
    reduced answer. This finite lexical check still needs semantic review.
    """
    if result['outcome'] != 'accepted_pending_semantic_review':
        return result
    rules = {rule['passage']: rule for rule in selection['nativeIdentifierPolicy']['rules']}
    for index, claim in enumerate(result['claims'], 1):
        rule = rules.get(claim['passage'])
        if rule and re.fullmatch(rule['pattern'], claim['text']) is None:
            return {'outcome': 'rejected', 'reason': 'native_identifier_constraint_not_observed', 'claims': [],
                    'details': {'claimIndex': index, **claim,
                                'mandatoryIdentifiers': rule['mandatoryIdentifiers'],
                                'networkIOQualifierRequired': rule['networkIOQualifierRequired'],
                                'diagnosticOnly': True}}
    return result
