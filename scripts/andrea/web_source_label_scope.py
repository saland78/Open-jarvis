"""Keep experimental source labels local and admit one literal csv-file alias.

The guard complements a finite set of *leading labels* with a prefix trie.
It uses only anchored alternation and character classes supported by b11232;
no lookahead, output repair, point dropping or semantic certification.
"""
from __future__ import annotations

import copy
import json
import re

MAX_GUARD_PATTERN = 8192
INSTRUCTION = (' Labels belong only to their own passage; do not copy a different passage\u2019s label. '
               'Keep source frequency qualifications; often means spesso, not always. '
               'CSV is licensed by literal csv file or file csv in the same passage.')
_TEXT = r'[^"\\\x00-\x1F\x7F]*'
_EXCLUDED = r'"\\\x00-\x1F\x7F'


def csv_file_aliases(quote):
    # Only the lower-case format noun in its own evidence. A namespace,
    # extension, different acronym or another passage does not license CSV.
    forms = r'(?<![\w./])(?:csv[ \t]+file\b|file[ \t]+csv(?![\w./]))'
    return {'CSV'} if re.search(forms, quote) else set()


def install_csv_file_aliases(isolated_contract):
    """Augment only a separately constructed experimental contract module."""
    original = isolated_contract.source_identifier_aliases
    def aliases(quote):
        return original(quote) | csv_file_aliases(quote)
    isolated_contract.source_identifier_aliases = aliases


def not_label_start_pattern(labels):
    """All complete strings except those starting with an exact forbidden label.

    Every nonterminal trie node permits a mismatch and an immediate final
    period. Once a forbidden label has completed, that branch has no path.
    Partial labels and ordinary prose remain possible; the original length
    and source checks still apply. The trie has no deferred positive duty.
    """
    labels = sorted(set(labels))
    if (not labels or any(not re.fullmatch(r'[A-Z0-9_/ a-z]+:', label) for label in labels)):
        raise ValueError('native_label_guard_inventory_invalid')
    root = {}
    for label in labels:
        node = root
        for char in label:
            node = node.setdefault(char, {})
        node[None] = True
    alternatives = []
    def visit(node, prefix):
        if None in node:
            return
        children = sorted(node)
        # Labels contain no period: ending here with '.' is always a mismatch.
        alternatives.append(prefix+r'[.]')
        # Spaces before the label are consumed only by the outer prefix,
        # rather than escaping the root as ordinary prose.
        different = '[^'+_EXCLUDED+'.'+(' ' if not prefix else '')+''.join(children)+']'
        alternatives.append(prefix+different+_TEXT+r'[.]')
        for char in children:
            visit(node[char], prefix+char)
    visit(root, '')
    expression = '^[ ]*(?:'+'|'.join(alternatives)+')$'
    if len(expression) > MAX_GUARD_PATTERN:
        raise ValueError('native_label_guard_inventory_too_large')
    return expression


def often_perfect_fit(quote):
    return bool(re.search(r'\boften\s+a\s+perfect\s+fit\b', quote, re.I))


def frequency_scope_error(text, quote):
    if not often_perfect_fit(quote):
        return None
    if re.search(r'\b(?:sempre|always)\b', text, re.I):
        return 'source_frequency_strengthened'
    if (re.search(r'\b(?:perfett[oaie]|perfect|ideal[ei]?)\b', text, re.I)
            and not re.search(r'\b(?:spesso|often)\b', text, re.I)):
        return 'source_frequency_not_preserved'
    return None


def apply(bank, messages, schema, selection, *, contract, native_contract):
    payload = json.loads(messages[1]['content'], object_pairs_hook=contract.unique_pairs)
    if payload['passages'] != [[ref, bank[ref-1]] for ref in selection['selectedRefs']]:
        raise ValueError('native_label_guard_source_alignment_failed')
    policy = selection['nativeIdentifierPolicy']
    rules = {rule['passage']: copy.deepcopy(rule) for rule in policy['rules']}
    label_names = {}
    for rule in rules.values():
        label = rule['requiredStart'].rstrip()
        names = frozenset(rule['mandatoryIdentifiers'])
        if label in label_names and label_names[label] != names:
            raise ValueError('native_label_guard_inventory_ambiguous')
        label_names[label] = names
    frequency_refs = []
    for ref, rule in rules.items():
        if often_perfect_fit(bank[ref-1]):
            rule['requiredStart'] += 'spesso '
            rule['pattern'] = '^'+rule['requiredStart']+native_contract.TEXT+r'[.]$'
            rule['sourceFrequencyQualifier'] = 'often'
            rule['renderedFrequencyQualifier'] = 'spesso'
            frequency_refs.append(ref)
    updated_schema = copy.deepcopy(schema)
    items = updated_schema['properties']['claims']['items']
    # Without unconditional names the original schema is an ordinary object.
    old_branches = items.get('oneOf', [items])
    groups, guards = {}, {}
    for branch in old_branches:
        if set(branch['properties']) != {'passage', 'text'}:
            raise ValueError('native_label_guard_schema_not_compatible')
        for ref in branch['properties']['passage']['enum']:
            quote = bank[ref-1]
            allowed = (contract.protected_identifiers(contract.io_identifier_text(quote))
                       | contract.source_identifier_aliases(quote))
            forbidden = tuple(sorted(label for label, names in label_names.items() if not names <= allowed))
            field = copy.deepcopy(branch['properties']['text'])
            if ref in rules:
                field['pattern'] = rules[ref]['pattern']
            elif forbidden:
                expression = not_label_start_pattern(forbidden)
                field['pattern'] = expression
                guard = guards.setdefault(expression, {'passages': [], 'forbiddenLeadingLabels': list(forbidden),
                                                       'pattern': expression})
                guard['passages'].append(ref)
            key = json.dumps(field, sort_keys=True)
            group = groups.setdefault(key, {'field': field, 'passages': []})
            group['passages'].append(ref)
    branches = []
    for group in groups.values():
        branches.append({'type': 'object', 'properties': {
            'passage': {'type': 'integer', 'enum': sorted(group['passages'])}, 'text': group['field']},
            'required': ['passage', 'text'], 'additionalProperties': False})
    updated_schema['properties']['claims']['items'] = {'oneOf': branches}
    aliases = {str(ref): sorted(csv_file_aliases(bank[ref-1])) for ref in selection['selectedRefs']
               if csv_file_aliases(bank[ref-1])}
    payload['sourceCsvFileAliases'] = aliases
    if rules:
        payload['requiredStarts'] = {str(ref): rule['requiredStart'] for ref, rule in rules.items()}
    if frequency_refs:
        payload['sourceFrequencyQualifiers'] = {str(ref): 'often' for ref in frequency_refs}
    updated_messages = copy.deepcopy(messages)
    updated_messages[0]['content'] += INSTRUCTION
    updated_messages[1]['content'] = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    selection = {**selection,
        'nativeIdentifierPolicy': {**policy, 'rules': list(rules.values())},
        'sourceLabelScopePolicy': {'mode': 'leading_labels_licensed_by_own_source',
            'guardBranches': list(guards.values()), 'sourceFrequencyRefs': frequency_refs,
            'sourceCsvFileAliasRefs': [int(ref) for ref in aliases],
            'finiteCsvFileAliasChangedExplicitly': True,
            'nativeForeignLeadingLabelGuardAddedExplicitly': True,
            'nativeFrequencyPrefixAddedExplicitly': True,
            'postGenerationChecksRequired': True, 'noOutputRepair': True}}
    return bank, updated_messages, updated_schema, selection


def validate_generation(result, selection):
    if result['outcome'] != 'accepted_pending_semantic_review':
        return result
    guards = {ref: rule for rule in selection['sourceLabelScopePolicy']['guardBranches'] for ref in rule['passages']}
    for index, claim in enumerate(result['claims'], 1):
        error = frequency_scope_error(claim['text'], claim['quote'])
        if error:
            return {'outcome': 'rejected', 'reason': error, 'claims': [],
                    'details': {'claimIndex': index, **claim, 'diagnosticOnly': True}}
        guard = guards.get(claim['passage'])
        if guard and re.fullmatch(guard['pattern'], claim['text']) is None:
            return {'outcome': 'rejected', 'reason': 'native_source_label_scope_not_observed', 'claims': [],
                    'details': {'claimIndex': index, **claim,
                                'forbiddenLeadingLabels': guard['forbiddenLeadingLabels'], 'diagnosticOnly': True}}
    return result
