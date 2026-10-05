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
