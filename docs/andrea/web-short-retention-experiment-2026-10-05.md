# First-request refinement: explicit identifier retention

## Cause addressed

The [previous finite comparison](web-short-instructions-experiment-2026-10-05.md#mac-series-completed-original-gates-not-met--2026-10-05)
does not pass: compact asyncio loses literal I/O and IPC, and CSV uncached token
reduction is only 8.633%, below the fixed 10% gate. All six transports completed,
cache counts were eligible, native prefill was lower in both supported-page
pairs, and five answers were reviewed favorably. This is an instruction-following
failure plus an insufficient prompt reduction, not a network or cache failure.
Its output is retained and its thresholds are not changed.

`web_short_retention_candidate.py` is a distinct candidate, not a retry of the
same prompt. It changes only the installed system instruction:

- It says explicitly to copy **all** identifiers associated with the selected
  passage number into `text`, retaining literal spelling even when explaining
  them. It repeats the identifier check before emitting JSON. This clarifies
  the observed ambiguity: an expanded name cannot replace the source acronym.
- It asks for distinct pertinent points supported by descriptive passages,
  rather than the title alone. The full title still remains in context;
  source selection is neither rewritten nor silently filtered.
- It consolidates the rest into 1265 characters, compared with 1430 in the
  failed candidate and 2202 in installed production (−42.552% of instruction
  characters). This is intended to address the token gate on the longer CSV
  excerpt. No token or latency benefit is claimed before model measurement.

The installed production contract remains unchanged. The candidate contains
the exact installed source-bank and validation functions, with identical ASTs.
Complete source bytes, inventories, source-first user serialization, question,
native schema, two-claim/application length limits, concurrency, identifiers,
numeric support, finite subprocess/unquoted aliases, converted-field condition
and scope, and completion controls are preserved. The instruction still requires
conditions, exceptions, negations, scope, dates, uncertainty, attribution and
abstention; missing is not zero and possibility is not a guarantee. Model,
options, keep-alive, server, configuration, UI, private notes and memory are
unchanged. The validators are not relaxed to accept the two failed claims.

This is a proposed instruction correction, **not evidence that the local model
will obey it**. New program tests replay the exact bad JSON and confirm it
remains rejected; actual candidate correctness requires the next finite model
comparison and semantic review.

## Same fixed protocol and original criteria

`web_short_retention_probe.py` uses the same self-contained standalone machinery
as the previous probe. It verifies the same four installed hashes before use,
reads the same two public pages via the running OpenJarvis API, preflights both
sources before any inference, retains identical snapshots for both variants,
and calls the local model exactly once for each of the original six ordered
case/variant slots: asyncio installed/compact, CSV compact/installed, unsupported
price installed/compact. No warm-up, unload, retry, repair, private read or file
modification. An incomplete transport emits diagnostics and stops the series.

Leading synthetic nonce isolation, native count validation, model/options,
stream controls, case shape checks and original semantic criteria are unchanged.
**Cached count ≤8, uncached fraction ≥98%; ≥10% fewer uncached tokens and ≥10%
lower native prefill in each supported-page pair.** Any failed pair stays
failed; no averaging or after-the-fact threshold changes. All six answers must
also complete, meet original structural shapes and pass manual review. First
JSON arrival is not accepted text or browser rendering. Loading, prefill,
generation and client totals remain separate; total latency must be considered
before adoption, and a single finite comparison is not statistical or universal
proof of improvement.

The report identifies this revision as `literal_identifiers_and_descriptive_evidence`,
retains diagnostic raw output and `qualityVerdict: pending_review`, and never
authorizes automatic installation. Collection on the Mac is pending. Further
modules remain deferred until this latency-and-quality task is resolved.

## Program validation

Upstream [OpenJarvis Ollama tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_ollama.py)
were consulted again for async stream, applied timeout, mid-stream disconnect
and schema handling. Runtime is preserved; the synchronous sequential client
is confined to the standalone diagnostic, not added to the production server.

Twenty tests exercise this distinct candidate: the fifteen original source,
schema, identifier/scope, cache, attribution and finite-orchestration regressions
are reused against the new module; five additional tests reproduce both observed
omissions separately, preserve the actual successful CSV phrasing, replay the
failed Mac comparison under the same fixed thresholds, and pin whole-source,
schema, original questions/options and validator/stream function parity. The
second missing IPC is tested independently so the first I/O error cannot mask
it. Historical candidate modules and their outcome are unchanged.

Together with existing related regressions: **333 program checks passed**.
These checks establish program behavior and refusal rules, not a successful
model answer or a measured performance improvement. No installation is prepared
from a failed comparison.

## Mac collection completed: still not an adoption pass — 2026-10-06

The next uploaded log verifies this probe's pinned SHA, contains each of the six
ordered requests exactly once and preserves source hashes/questions. All stop
frames complete; cache coverage qualifies under the unchanged thresholds.

| Case | Variant | Uncached tokens | Native prefill ms | Native generation ms | Generated tokens | Client total ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| asyncio | Installed | 1670 | 37972.152 | 12936.500 | 60 | 56298.137 |
| asyncio | Compact | 1427 | 32910.583 | 9119.198 | 67 | 42337.554 |
| CSV | Compact | 2196 | 37463.390 | 19553.836 | 126 | 57209.940 |
| CSV | Installed | 2442 | 40960.856 | 13697.567 | 84 | 54920.640 |
| Missing price | Installed | 2438 | 41608.835 | 653.259 | 5 | 42541.919 |
| Missing price | Compact | 2198 | 38388.695 | 625.764 | 5 | 39382.178 |

Asyncio token/prefill reductions are 14.551%/13.330%. CSV token reduction is
10.074%, but prefill reduction is **8.539%**, below the original **10%** gate.
The CSV response repeats the default rule in a second point. Both points are
source-backed, but the overlap adds output work: 126 vs 84 generated tokens,
19.554 vs 13.698 seconds of generation and a slower total client response.
Lower prefill alone does not establish a useful end-to-end improvement. The
first installed asyncio call additionally loads the model for 5334.663 ms;
its total difference cannot be wholly attributed to prompt compaction.

The compact asyncio response now preserves **I/O and IPC** and selects two
descriptive source passages. Its second point is rejected for `event loop`
being absent from the selected passage, although the source explicitly says
**event loops**. Local replay proves the finite morphology bug: the installed
regex recognizes singular `event loop` but not plural `event loops`. Correcting
only that check exposes another first-error barrier: the validator also demands
`OS` from `handling OS signals` in the same source catalogue, although the claim
describes its separate `running subprocesses` item, not signals.

The exact source-backed partial claim is retained unchanged: “asyncio gestisce
i sottoprocessi attraverso l'API di gestione degli event loop.” Its reference
contains event loops, APIs and subprocesses. The checker must distinguish a
literal omission in the selected fact (the prior I/O/IPC failure) from an
identifier belonging to another independent catalogue item. The installed
asyncio answer, both CSV formulations and both empty-price answers are reviewed
favorably for source support; the compact CSV remains unnecessarily repetitive.
This assessment does not relabel the original technical report or override its
failed performance gate. The original `gates_not_met` outcome remains.

**No adoption or repeat of the same candidate.** The
[next isolated refinement](web-scoped-latency-experiment-2026-10-06.md) corrects
the demonstrated finite validator bugs and tests concise nonrepetitive output
with unchanged original questions, sources, schema, options and speed gates.
The full Terminal history is not published.
