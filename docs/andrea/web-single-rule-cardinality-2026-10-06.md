# Single-rule cardinality before generation

Status: the six-request Mac comparison is complete. The native one-item
CSV budget is honored, its full rule has favorable semantic review, and both
original performance pairs pass. A different asyncio qualifier error prevents
adoption: five responses have favorable review and one does not. Original
automatic acceptance remains separate from semantic review. No production
installation is claimed.

## Problem and resulting behavior

The [canonical-term Mac comparison](web-canonical-term-mac-2026-10-06.json)
fixes the observed bad term translations and passes both original performance
pairs. The compact CSV response nevertheless states the same conditional
conversion twice. Asking for up to two distinct points and telling the model
not to repeat a rule was insufficient. The validator correctly refuses the
response; the report remains failed.

The new candidate represents a recognized question about one conditional rule
with an array budget of at most one complete claim, including its default,
exception and field scope. It sends `maxItems: 1` through Ollama's native
`format` schema. It also changes the matching count instruction before
generation. It does not choose, shorten, merge or remove a generated claim.

The original asyncio question still permits two distinct functions. The missing
price question still uses the full context, the ordinary two-claim schema and
genuine model inference; empty claims must be generated and reviewed rather
than returned by an intent shortcut. The production baseline prompt and schema
are unchanged.

## Small independent intent/budget module

`web_single_rule_budget.py` applies the one-rule budget only when all of these
are proven before inference:

- Complete selected HTML definitions match exactly the one named `csv.reader`
  API. Qualified source identifiers remain case-sensitive.
- The original user question matches a supported, closed-domain Italian form
  asking about automatic type/field conversion or its conditions. Generic,
  multi-topic, multi-API, explicit multi-point and unknown phrasings retain the
  ordinary contract. This is a narrow domain route, not general language
  understanding.
- Exactly one selected original source passage contains the complete default
  no-automatic-conversion rule and its QUOTE_NONNUMERIC/unquoted-to-float
  condition. Multiple rule-bearing passages, unsupported result types or
  incomplete context cannot justify one slot.

The module never inspects the expected answer or a benchmark case ID to decide
its budget. It derives the policy from the unchanged question, proven source
selection and source predicate. All original passages, numbers, inventories,
schema item types and allowed evidence references remain unchanged. Only the
native array cardinality and its count instruction change for this route.
No string `maxLength` or lower output-token limit is introduced: a complete
conditional sentence retains the existing 320-character application budget
and the 512-token transport budget. Empty claims remain legal, but do not pass
the answerable case's existing quality criteria.

A separate post-validation count check refuses an engine response violating
the native budget. It retains all original claims diagnostically and returns
no accepted answer. Existing duplicate, identifier, qualifier, type, condition,
own-source, heading and complete-sentence checks still run. There is no repair
or second generation. Native schema delivery is tested at the request boundary;
actual honoring of this array constraint by the Mac's engine remains part of
the real comparison, not a program-test assumption; the collected run below
demonstrates it for this request and engine version.

## Same finite comparison, stronger generation contract

Candidate revision: `native_single_rule_budget_with_canonical_terms`.
The standalone runner embeds the exact baseline, resource observer, selector
and new budget module. It reports each native array limit, native-schema hash
and the output policy's source references and reason.

Native claim limits in the balanced original order are `[2, 2, 1, 2, 2, 2]`:
asyncio production/compact, CSV compact/production, missing price
production/compact. All six original questions, snapshots, source-selection
rules, model/options, version check, cache qualification, 90-second stream
deadline and 95-second owned-worker bound are retained. The compact CSV
preflight refuses to run a comparison unless the one-rule policy is proven.

Original gates: at most 8 cached input tokens, at least 98% uncached input,
at least 10% fewer new tokens and 10% less native prefill in each supported
pair, all six requests complete, original case shapes, and semantic review
of every answer. The cardinality change strengthens distinctness rather than
reducing any requested fact or success threshold. Default no conversion,
QUOTE_NONNUMERIC exception, unquoted field scope and float target must all
remain faithful. There is no claim that a short or single-point answer is
automatically correct.

No warm-up, unload, retry, changed thermal settings, cooling delay,
thermal-based exclusion, private note read or automatic installation.
Lightweight CPU-limit samples do not establish a temperature, native-prefill
phase or causal effect. First JSON is not accepted/painted browser text.

507 program regressions pass, including recognized versus unknown/multi-fact
intents, exact complete-rule proof, immutable source/question, native schema
delivery and unchanged options, over-budget refusal without output repair,
current duplicate replay, correct single-rule qualifications, unsupported type
and field rejection, two-function retention, full-context missing-price
inference, exact embedded-source parity and the original balanced six-case
protocol. Program fixtures and mocked transport do not measure Mac inference.

## Collected result and separate semantic review

The [six raw responses and unmodified automatic report](web-single-rule-cardinality-mac-2026-10-06.json)
come from probe commit `81513b44a740ef8ebf6889c1fe36316a9ffae0f4`.
No earlier private Terminal history is included. All six streams complete,
all native cache counts qualify, and Ollama stays at 0.35.1. The native array
limits remain `[2, 2, 1, 2, 2, 2]`. CSV compact generates one complete rule,
preserving string rows, no automatic conversion, the QUOTE_NONNUMERIC
condition, unquoted fields and float target. Its duplicate problem is resolved
in this run.

| Supported pair | New tokens, baseline → compact | Native prefill, baseline → compact | Client total, baseline → compact |
|---|---:|---:|---:|
| asyncio | 1673 → 1278 (−23.610%) | 31.592 → 24.948 s (−21.032%) | 47.453 → 37.000 s |
| CSV reader rule | 2439 → 831 (−65.929%) | 54.164 → 14.722 s (−72.821%) | 73.447 → 25.149 s |

These are individual observations, not distributions or universal speed
claims. The first production call includes a 7.347-second model load; its
client-total difference is therefore not an isolated measure of prompt work.
The fixed gates use new input tokens and native prefill separately.
CPU-limit samples vary and do not establish temperature, native-prefill phase
or causality. No cooling delay or thermal-based exclusion was used.

The automatic report correctly says
`measured_gates_met_pending_semantic_review`; its checks are retained exactly.
Manual review finds the compact asyncio second point replaces the source's
OS-signal handling with broad communication with the OS. Keeping the acronym
alone does not preserve that qualifier. Both old validators miss the change.
The other five responses have favorable review, including both genuine
missing-price abstentions. This run's overall review is
`not_passed_no_adoption`, separately recorded rather than retroactively
changing the original automatic report.

The [signal-scope correction](web-signal-scope-latency-fix-2026-10-06.md)
retains the successful one-rule budget and context selection. Its new Mac
comparison is pending; no repaired or regenerated answer is substituted into
this collected run.

## Primary sources consulted for this task

- [OpenJarvis structured-output tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_structured_output.py):
  distinguish JSON output from schemas and check propagation at the engine
  boundary. Schema transmission tests do not establish semantic quality.
- [OpenJarvis Ollama engine](https://github.com/open-jarvis/OpenJarvis/blob/main/src/openjarvis/engine/ollama.py)
  and [Ollama tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_ollama.py):
  native payloads, bounded streaming and independent response/usage handling.
  The fetched engine's generic structured-output route sends JSON mode; this
  candidate uses the already existing local direct `format` schema route.
- [OpenJarvis intent-routing tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/core/test_intent_routing.py):
  supported patterns and ordinary routing fallback. The local rule route is
  similarly explicit about its narrow scope and does not substitute a fact
  answer for inference.
- [Ollama structured-output documentation](https://docs.ollama.com/capabilities/structured-outputs):
  native `format` schemas with separate validation. Suggested temperature
  changes are not adopted; the original temperature remains 0.4.
- [llama.cpp schema grammar implementation](https://github.com/ggml-org/llama.cpp/blob/master/common/json-schema-to-grammar.cpp):
  optional single-item repetition in schema grammar. This upstream source does
  not certify which exact grammar implementation the Mac's Ollama build embeds;
  the new generated responses must demonstrate the effective constraint.
- [CPython CSV source](https://github.com/python/cpython/blob/3.14/Doc/library/csv.rst):
  the complete reader rule has one default/exception relation, with unquoted
  fields transformed into float under the stated option.
