"""Prompt guidance for an observed networking-to-I/O scope substitution.

Only selected evidence that literally says networking and does not contain
an I/O identifier receives this inventory item. Headings and other passages
cannot supply evidence. This runs before inference; it never changes a source,
schema, generated claim, validation rule or model option.
"""
from __future__ import annotations

import copy
import json
import re

NETWORKING_SCOPE_INSTRUCTION = (
    ' For sourceTechnicalTerms networking use networking or rete. '
    'Do not replace it with I/O unless I/O occurs in that same passage.')


def apply(bank, messages, schema, selection, *, contract):
    """Add finite terminology guidance to an already prepared source contract."""
    payload = json.loads(messages[1]['content'], object_pairs_hook=contract.unique_pairs)
    refs = selection['selectedRefs']
    if (not isinstance(refs, list) or refs != sorted(set(refs))
            or any(type(ref) is not int or not 1 <= ref <= len(bank) for ref in refs)
            or payload['passages'] != [[ref, bank[ref-1]] for ref in refs]):
        raise ValueError('networking_source_alignment_failed')
    eligible = set(schema['properties']['claims']['items']['properties']['passage']['enum'])
    context_only = set(payload['contextOnly'])
    network_refs = [ref for ref in refs if ref in eligible and ref not in context_only
                    and re.search(r'\bnetworking\b', bank[ref-1], re.I)
                    and 'I/O' not in contract.protected_identifiers(contract.io_identifier_text(bank[ref-1]))]
    selection = {**selection, 'sourceNetworkingScopeRefs': network_refs}
    if not network_refs:
        return bank, messages, schema, selection
    updated = copy.deepcopy(messages)
    for ref in network_refs:
        terms = payload['sourceTechnicalTerms'].setdefault(str(ref), [])
        if not isinstance(terms, list) or any(not isinstance(term, str) for term in terms):
            raise ValueError('networking_inventory_invalid')
        payload['sourceTechnicalTerms'][str(ref)] = sorted(set(terms) | {'networking'})
    updated[0]['content'] += NETWORKING_SCOPE_INSTRUCTION
    updated[1]['content'] = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    return bank, updated, schema, selection
