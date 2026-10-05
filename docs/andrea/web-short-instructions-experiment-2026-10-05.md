# First-request web context: shorter instructions, isolated comparison

## Trigger and candidate

The installed source-first reuse task is already closed. Its three original
cases were reviewed favorably through the production service. The next request
from Andrea is to reduce latency further. The installed first-page observations
show native prefill costs of 29916.533 ms for asyncio and 36879.466 ms for CSV;
subsequent use of the same CSV context was much faster because of prefix reuse.
This distinct experiment targets the first-request prefill, preserving source
content rather than discarding information to make the model appear faster.

`web_short_instructions_candidate.py` changes only the system instruction in
the installed contract. It consolidates repeated explanations: 2202 → 1430
characters, −35.059% in the instruction itself. **These are character counts,
not token savings or measured latency.** The complete source bank, numbering,
source term inventories, question, user serialization/order and native schema
remain identical. All other function ASTs, including every validator and source
helper, are identical to the installed contract. The native string has no hard
length cap; the application still rejects unfinished or over-320-character
claims without trimming, repairing or retrying them.

The shorter instruction retains: sole selected-passage support, Italian JSON,
at most two pertinent paraphrases, source instruction isolation, no tools or
external knowledge/memory, literal identifiers, finite subprocess and unquoted
aliases, converted-field qualifiers and conditions, exceptions, negations,
scope, dates, uncertainty and attribution, missing-not-zero, possibility-not-
guarantee, explicit support for parallelism, complete punctuation, and
abstention when support or faithful reformulation is unavailable. No new
glossary or information is added to the sources.

No installation, model replacement, global Ollama setting, unload, warm-up,
private note/memory read, additional provider search or automatic retry occurs.
Production remains the installed contract with SHA-256
`5b8a73b2a9d534074ec61eb67b9abd0eb6c73d3abb2783e76149ad6b3b7b2285`.

## Protocol fixed before Mac collection

`web_short_instructions_probe.py` is self-contained. It verifies four installed
file fingerprints, refuses symlinks/local changes, and reads only two explicitly
selected public pages through `/api/andrea/web/read`: Python asyncio and CSV.
Both snapshots and the required CSV conversion context are checked before any
inference. Their exact text is retained in process memory for this finite
comparison; the standalone calls do not depend on expiration of the service's
five-minute page cache. For each case, source bytes, user message and schema
are checked equal between variants before calling the model.

Six direct local model calls, with no retries or warm-ups:

| Order | Original case | Instruction variant |
| --- | --- | --- |
| 1 | Two supported asyncio functionalities | Installed |
| 2 | Same asyncio question and snapshot | Compact |
| 3 | CSV default conversion rule and exception | Compact |
| 4 | Same CSV question and snapshot | Installed |
| 5 | Monthly Zefiro price absent from CSV excerpt | Installed |
| 6 | Same missing-price question and snapshot | Compact |

The model is `qwen3:4b-instruct-2507-q4_K_M`; temperature 0.4, context 4096,
output 512, think false and keep-alive 15m match the installed setup. The existing
90-second stream checks, response limits, complete-stop requirement and closure
behavior are retained. Incomplete transport stops the series after emitting
diagnostics. A completed but rejected answer stays visible as a diagnostic and
does not cause a retry, repair or omission of the remaining independent cases.
Do not issue other model requests during the comparison.

Each request has a unique leading synthetic nonce in its system message, marked
as a diagnostic identifier and not a fact. This discourages previous-prefix
reuse without unloading or warming the model. **This prefix is not part of the
candidate production instruction.** Native counts still determine eligibility;
the nonce alone is never evidence that a request was uncached. Its character
overhead is reported and both variants have the same marker format. Template
prefixes and nonce tokenization can introduce small residual differences.

Fixed attribution and performance gates:

- Every native count must be a valid integer, with cached count no larger than
  eight and at least 98% of prompt tokens newly evaluated. Missing counts or
  excessive reuse mean an inconclusive first-request comparison.
- For **each** of the two supported-page pairs, compact instructions must reduce
  uncached input tokens by at least 10% and native prefill duration by at least
  10%. Improvements are not averaged across a failed pair.
- All six calls must complete and meet original structural case shapes: two
  asyncio points, at least one CSV point, and empty claims for the unsupported
  price. Native latency gates cannot establish correct meaning.
- All six answers require manual review against their exact selected passages
  and the original criteria. CSV must preserve both the default absence of
  conversion and the QUOTE_NONNUMERIC exception applying to unquoted fields;
  asyncio cannot promise universal acceleration or unsupported parallelism.
  Price absence cannot become zero or a claim about external information.

The report always retains `qualityVerdict: pending_review` and explicitly does
not authorize automatic installation. Adoption additionally requires review of
generation/load/total client latency, not just a faster prefill. The data do not
measure browser rendering, first accepted production text, voice stages or
statistical/general speedup. Raw first JSON content is not an accepted answer.
Native phases and client wall-clock durations are reported separately and are
not added across clocks. One finite pair per page cannot eliminate thermal,
background-process or order effects; opposite order across the two pages only
reduces a simple order bias.

## Validation and current status

Upstream [OpenJarvis Ollama tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_ollama.py)
were consulted again for async stream handling, deadlines, disconnections and
structured response propagation. Existing production runtime is preserved; the
standalone sequential diagnostic does not introduce blocking operations in the
server. No universal upstream performance promise is inferred from those tests.

Fifteen new regression tests check exact installed helper/validator AST parity,
whole source and schema preservation, measured bad output replay, completed
faithful paraphrases, cache eligibility, missing/invalid metrics, fixed pair
gates, no automatic semantic pass, precise six-call order/settings, unchanged
files, unchanged original questions/criteria, preflight failure, local edits and
symlinks, and incomplete-transport stopping. Together with the existing related
web/metrics/service/install regressions, 313 program checks pass.

**Mac performance and model quality collection are pending.** No first-request
speedup is claimed and no production update is applied by this experiment. The
prior reuse adoption and the historical failed candidates keep their existing
outcomes; they are not rerun or relabeled to close this distinct task.

## Mac series completed: original gates not met — 2026-10-05

The uploaded Terminal output verifies the pinned standalone script and contains
all six requests exactly once, with complete `stop` frames, unchanged original
questions/criteria and source hashes. All cache counts are eligible under the
predeclared limits: 0–4 cached tokens, at least 99.7952% uncached coverage.
There is no retry, incomplete transport or private read in this series.

| Case | Variant | Uncached prompt tokens | Native prefill ms | Client total ms | Reviewed quality |
| --- | --- | ---: | ---: | ---: | --- |
| asyncio | Installed | 1673 | 34712.084 | 49451.414 | Favorable: I/O and IPC; subprocess control |
| asyncio | Compact | 1462 | 28575.263 | 37067.444 | Failed: missing I/O, then missing IPC |
| CSV | Compact | 2233 | 44495.310 | 56526.163 | Favorable: default, exception and unquoted-field scope |
| CSV | Installed | 2444 | 53422.591 | 68000.628 | Favorable: default, exception and unquoted-field scope |
| Missing price | Installed | 2438 | 51022.260 | 52066.814 | Favorable: empty claims |
| Missing price | Compact | 2235 | 46610.606 | 47680.045 | Favorable: empty claims |

The instruction reduction gives 12.612% fewer uncached tokens and 17.679% lower
prefill cost for asyncio. CSV prefill is 16.711% lower, but token reduction is
only **8.633%**, below the original **10%** gate. This result remains
`gates_not_met`; the threshold is not reduced after collection. The first
installed call additionally has 5337.202 ms of load time, unlike the compact
call's 2.254 ms. Their total difference cannot be assigned wholly to instruction
compaction. Native prefill comparisons and total client time remain separate.

The failed compact asyncio JSON contains these two unchanged generated claims:

- Passage 1, `asyncio — Asynchronous I/O`: “asyncio serve per gestire operazioni
  asincrone di input/output.” The literal `I/O` is replaced by an expansion, so
  the existing identifier check rejects it. It also selects a title rather than
  a descriptive functionality and is not an independent second functionality
  alongside its other I/O claim.
- Passage 10, `perform network IO and IPC;`: “asyncio permette di eseguire
  operazioni di I/O e comunicazione tra processi.” This preserves I/O, but drops
  the literal **IPC**. The first rejection prevented this second omission from
  appearing in the original first-error diagnostic. Independent replay verifies
  that the unchanged validator also rejects this claim for missing IPC.

Manual review is favorable for the other five answers: both CSV formulations
preserve no automatic conversion by default and the QUOTE_NONNUMERIC exception
for unquoted fields; both missing-price answers abstain; the installed asyncio
answer preserves I/O, IPC and subprocess meaning without promising parallelism
or universal speedup. The protocol flags remain `pending_review`; review does
not modify the emitted answers or make the failed candidate acceptable.

**No production adoption.** A different compact instruction revision is prepared
in [the retention refinement](web-short-retention-experiment-2026-10-05.md).
The exact failure and original performance gates are retained in regressions.
The full uploaded Terminal history is not published. No further series is run
merely to obtain a favorable repeat of this same candidate.
