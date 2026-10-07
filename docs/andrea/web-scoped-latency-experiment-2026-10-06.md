# Finite term/scope corrections and nonrepetitive first-request synthesis

## Diagnosis and exact guard changes

The [retention refinement's finite Mac series](web-short-retention-experiment-2026-10-05.md#mac-collection-completed-still-not-an-adoption-pass--2026-10-06)
still fails adoption: CSV prefill reduction is 8.539% under the original 10%
gate, its duplicated point increases generation and total latency, and asyncio
hits two program-level false rejection barriers. Neither threshold nor historical
outcome is changed. Original I/O and IPC omissions are corrected in that model
output; they are not accepted when replayed without the identifiers.

`web_scoped_latency_candidate.py` makes two finite, source-anchored guard changes:

1. `event loop` and `event loops` canonicalize to the same lexical concept, just
   as `coroutine`/`coroutines` already do. A term still needs support in its own
   selected passage. No general synonym expansion or missing-term bypass.
2. `required_identifiers_for_claim` recognizes the explicit source relation
   `running subprocesses, handling OS signals`. In a subprocess-only partial
   claim, `OS` qualifies the separate signals item, not subprocesses. The OS
   requirement is excluded only with that exact neighbouring-item pattern,
   a recognized subprocess equivalent in the claim, no signal claim and no
   broad quantifier. Signal claims still require OS; other source patterns,
   identifiers, added acronyms and unknown/broad claims retain the old policy.

The observed claim is replayed without adding an irrelevant OS statement,
rewriting its text/quote, retrying generation or choosing a different reference.
It becomes structurally accepted pending semantic review. The original checker
continues to reject it and that legacy diagnostic remains available. Missing
I/O/IPC, unsupported parallelism/numbers, wrong subprocess translations,
unquoted-field qualification and CSV condition failures remain rejected.
These lexical/source-pattern guards do not prove general semantic entailment
or solve all partial-summary ambiguities.

## Model input and end-to-end aim

The candidate changes the system instruction to 1229 characters, explicitly
requesting Italian output, distinct useful points and only the number of points
needed to answer. It forbids restating a rule as another point. Instructions
are in English with an Italian output requirement, preserving the source-support,
literal-identifier, finite equivalent, condition/exception/negation/scope,
date/uncertainty/attribution, missing-not-zero, possibility-not-certainty,
parallelism, completion, nonverbatim and abstention requirements. Actual native
token savings and model obedience must be measured; character count/language
alone is not a speed claim.

Full source bytes, bank numbering, protected/source inventories, source-first
user serialization, question and native schema are unchanged. The native string
has no character cap that can force a word cut; the application still enforces
320 characters and complete punctuation. At most two claims, model
`qwen3:4b-instruct-2507-q4_K_M`, temperature 0.4, context 4096, output 512, think
false, keep-alive 15m and existing stream limits are preserved. No source is
dropped or shortened, response repaired/deduplicated after generation, global
Ollama option changed, model unloaded/warmed, private note read or retry added.
Production remains unchanged with contract SHA
`5b8a73b2a9d534074ec61eb67b9abd0eb6c73d3abb2783e76149ad6b3b7b2285`.

## Same comparison gates, explicit dual diagnostics

`web_scoped_latency_probe.py` verifies the same installed fingerprints, reads
only the same two public pages through OpenJarvis, preflights both complete
snapshots and the CSV predicate, then performs the same six original ordered
requests: asyncio installed/compact; CSV compact/installed; missing price
installed/compact. A completed rejection stays diagnostic; incomplete transport
stops the series. No retries or file modifications. Leading nonce isolation is
diagnostic only, not part of a production prompt.

Only the system message differs in inputs to the model. **Both variants are
evaluated by the same candidate validator**, avoiding a different admission
policy in the performance comparison. Every raw answer is additionally checked
against the embedded original installed policy and reported as
`installedPolicyChecks`. Its original false refusal is not hidden, overwritten
or silently relabeled as a production pass. The finite word/scope fixes do not
affect source payload, grammar or generation counts.

Unchanged gates: integer native counts, cached tokens ≤8, uncached fraction ≥98%;
in each supported-page pair ≥10% fewer uncached tokens and ≥10% less native
prefill. Same original questions, structural case shapes and semantic criteria.
All six answers must complete and receive source-based review; CSV conditions
and field qualifier remain essential, missing price must abstain. Repetition and
total generation/client costs must also be considered before adoption, even if
prefill gates pass. The probe always retains `qualityVerdict: pending_review`
and never authorizes automatic installation.

Native loading/prefill/generation and client totals stay separate. First JSON is
not accepted text or UI rendering. Opposite order across pages and nonce cache
qualification do not remove thermal/background variation or constitute statistical
proof. No browser/voice latency or universal improvement is measured. The previous
failed comparison stays failed even if its raw answers pass a corrected lexical
check. No further module begins before this latency-and-quality task is resolved.

## Validation and status

Upstream [OpenJarvis Ollama tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_ollama.py)
were consulted again for asynchronous streams, applied timeouts, disconnections
and structured responses. Runtime is unchanged; the sequential synchronous
diagnostic is confined to the standalone script, not added to uvicorn.

Twenty candidate tests exercise actual full-output replay, symmetric finite
plural recognition, unsupported references, the two staged false-refusal
barriers, source catalogue boundaries, retained OS for signals/broad claims,
retained missing I/O/IPC and unsupported acronyms, prior qualifier/condition/
completion/number failures, unchanged source/schema/options, standalone/pure
function parity, original gates replay, plus the ten cache/finite-request
orchestration regressions reused against this candidate. The duplicated CSV
output is retained as two diagnostic claims, not silently repaired. All other
source helpers and guards have identical ASTs to the installed contract.

Together with previous related checks: **353 program tests passed**. The Mac
collection is reviewed below. No production adoption is prepared from a failed
quality or latency comparison.

## Mac collection reviewed — speed gates met, semantic adoption failed

The six-request run of script commit
`699dde4fd9536eeb7a26c86473cd8f5dce8504be` completed without retry. Both public
source hashes match the preceding experiment. All native cache counts are
eligible: 0–4 cached tokens and at least 99.77% uncached input. Both original
performance gates now pass independently; these are measured observations,
not a statistical or universal speed guarantee.

| Case | Installed/compact uncached tokens | Installed/compact native prefill ms | Token reduction | Prefill reduction | Client total ms, installed/compact |
|---|---:|---:|---:|---:|---:|
| asyncio | 1667 / 1326 | 24099.595 / 21467.471 | 20.456% | 10.922% | 38052.864 / 31431.191 |
| CSV | 2438 / 2095 | 38091.108 / 34244.080 | 14.069% | 10.100% | 50910.277 / 46815.908 |
| Missing price | 2441 / 2090 | 37834.210 / 35379.613 | Diagnostic only | Diagnostic only | 38767.060 / 36246.122 |

First asyncio loading is 4823.832 ms in the installed-prompt call versus
2.891 ms in the compact call. The entire 6621.673 ms client-total difference
must not be attributed to instruction compaction. CSV has small loading times
on both sides and 4094.369 ms lower client total. Native and client times have
different clocks; no UI rendering or accepted production response is measured.

Manual source-based review finds five responses favorable: two explicit asyncio
functionalities in the installed-prompt answer; both CSV answers retain the
default rule, QUOTE_NONNUMERIC condition and unquoted-field qualification;
both missing-price answers abstain. The compact asyncio answer fails review:
its first point claims nonblocking execution while selecting only passage 1,
the heading `asyncio — Asynchronous I/O`. That heading alone does not document
the added behavior; together with its second I/O point this also fails the
request for two source-supported functionalities. The raw output and its
original structural acceptance are not repaired, re-anchored or relabeled.

Both old and candidate lexical validators accept this heading expansion,
demonstrating why `accepted_pending_semantic_review` is not a quality pass.
The overall variant is **not adopted**. The next
[distinct heading-role refinement](web-heading-latency-experiment-2026-10-06.md)
addresses the observed selection mechanism while retaining the original
questions, source bytes, speed gates and quality review. No unrelated module
starts before this task is resolved.
