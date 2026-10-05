# Finite I/O equivalence and CSV result-type fidelity

## Concrete remaining errors

The [completed heading-role comparison](web-heading-latency-experiment-2026-10-06.md#mac-collection-reviewed--heading-fixed-termtype-fidelity-still-open)
meets the original speed gates and prevents selecting the observed heading as
descriptive evidence. It is not adopted. The compact asyncio response is
faithful but rejected because input/output is not recognized as I/O. The
compact CSV response is formally accepted but calls the documented float
result “numeri decimali”, losing the explicit Python type. Those outcomes remain
recorded, with no retry or post-hoc alteration of their generated text.

Primary sources consulted for this correction:

- [Microsoft I/O documentation in Italian](https://learn.microsoft.com/it-it/windows/win32/fileio/synchronous-and-asynchronous-i-o)
  explicitly pairs input/output and I/O.
- [Python CSV documentation](https://docs.python.org/3/library/csv.html)
  identifies float as the conversion result for unquoted fields under QUOTE_NONNUMERIC.
- [Python floating-point documentation](https://docs.python.org/3/tutorial/floatingpoint.html)
  distinguishes binary floating-point representation from exact decimal arithmetic.
- [OpenJarvis Ollama tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_ollama.py)
  were consulted again for bounded asynchronous streaming and disconnect handling.
  The streaming transport is unchanged.

## Isolated correction

`web_type_fidelity.py` supplies finite lexical checks. The exact whole-word
input/output expansion, including case variants, is scanned as I/O in a
temporary representation of both the claim and its own source passage. Original
strings, evidence numbers, resolved quotes and returned claims remain unchanged.
Input alone, output alone, general paraphrases and unrelated acronyms do not
receive that equivalence. Another passage cannot license an identifier.

For CSV, float is added to the protected source inventory only when the selected
bounded source unit explicitly contains the QUOTE_NONNUMERIC option and the
conversion of unquoted fields into floats. This exposes the literal source type
to the model before generation, using the existing instruction to preserve
protected terms. System instructions, source bank, question, other inventories
and all native bounds stay unchanged from the heading candidate. No replacement
is made in a generated answer, and the source itself is not rewritten.

The additional application guard checks known positive conversion predicates
with a stated target in a field clause. It rejects an absent float equivalent
or an explicit alternative such as Decimal, int or string. A mention of float
elsewhere does not license a different conversion result. Literal float/floats,
floating-point and “a virgola mobile” are finite same-concept forms. A partial
default-only summary is not forced to invent a conversion target. Known explicit
negated conversion forms are not treated as positive target assertions.

This is a bounded lexical detector, not a complete Italian/English parser,
entailment system or guarantee of source correctness. Negation, source scope,
conditions and meaning still require review. Existing QUOTE_NONNUMERIC,
unquoted-field, identifier, heading-role, number, completion and stream guards
remain active. No rejected sentence is repaired, reassigned or deduplicated.

`web_type_latency_candidate.py` is the pure isolated contract;
`web_type_latency_probe.py` embeds the same helpers for a self-contained Mac
diagnostic. The baseline prepare function and original installed validator stay
exactly unchanged. Both prompt variants are checked by the same new validator;
their original installed-policy results are also retained separately. The new
guard does not relabel the historical collection as passed.

## Same finite comparison and original gates

The diagnostic verifies the same four installed file hashes before collection
and around every call. The installed production contract remains SHA
`5b8a73b2a9d534074ec61eb67b9abd0eb6c73d3abb2783e76149ad6b3b7b2285`.
It uses the verified installed network reader in two owned 25-second child
processes, with the previously tested heading provenance. Each of the same two
public Python pages is read once. Full source text, numbering and question are
preflighted before inference; only heading eligibility and the source-anchored
float inventory addition are allowed. No personal note, memory or configuration
is read or changed.

Six original calls, each once: asyncio installed/compact, CSV compact/installed,
missing price installed/compact. Original questions and source-based criteria
are unchanged. Faithful CSV conversion includes preserving the actual result
type when that result is asserted. Source hashes, heading ranges, source types,
raw model answers, both validator results and native metrics are reported.

Model, temperature, context 4096, output budget 512, think false, keep-alive 15m,
90-second transport deadline and 6000-character source cap stay unchanged. No
warm-up, unload, global model change or automatic second generation. A diagnostic
nonce isolates each prefix; the same snapshot is used in both variants.

Original gates: native cached tokens at most 8, uncached fraction at least 98%;
each supported-page pair requires at least 10% fewer uncached input tokens and
10% less native prefill. A failed pair cannot be rescued by an average or by the
abstention case. The generated outputs must also be faithful, pertinent and
complete. Every report remains `qualityVerdict: pending_review` and refuses
automatic integration. Loading, prefill, generation, read and client costs are
separate; first JSON is not accepted text or browser rendering. A small finite
comparison cannot establish a statistical or universal speed guarantee.

## Program validation completed; Mac collection pending

43 checks of this candidate pass: the two exact observed outputs are replayed,
the old false refusal is corrected without changing text/quotes, and the decimal
type imprecision is rejected without hiding its previous formal acceptance.
Negative checks cover finite alias boundaries, own-passage anchoring, missing
IPC, unknown acronyms, target types, float mentioned elsewhere, common positive
and negated predicates, unchanged source/question/schema, exact inventory
addition, unchanged baseline/legacy transport, and standalone helper parity.
The heading, cache and finite six-call protocol regressions are also applied to
this candidate. With the existing suite: **426 program tests pass**.

No new Mac model answer or latency is yet measured for this revision. Program
replay establishes the correction's behavior, not a successful local model run.
Production remains unchanged; installation and unrelated modules remain pending
until the fresh finite comparison passes both quality and the original gates.
