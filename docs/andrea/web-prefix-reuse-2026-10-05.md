# Source-first context reuse for web synthesis

The isolated qualified-field candidate at
`1e7315be28de6fdcf24680db5aa63145846e90c0` passed manual review of the original
three finite criteria. Details, exact failures of earlier versions and measured
phase costs remain in `web-prompt-prefix-latency-2026-10-05.md`.

## Behavior and scope

The production change is only `scripts/andrea/web_sentence_contract.py`:

- Stable source passages and source-anchored term inventories precede the
  variable question in the user message, allowing reuse of their shared prefix.
- Precise finite subprocess equivalents and the source `APIs`/`API` spelling
  equivalence prevent measured translation and spelling failures without
  licensing a term from a different passage.
- A source-qualified CSV conversion claim must retain QUOTE_NONNUMERIC and the
  unquoted-field qualifier when it describes those converted fields.
- Native strings no longer have a maximum that can force a mid-word closure.
  The application still refuses complete claims longer than 320 characters;
  it never truncates, repairs, retries or silently accepts incomplete output.

The model, temperature, context/output budgets, keep-alive, runtime, page
extraction, frontend, read-only vault, memory and configuration are unchanged.
The source excerpt remains intact. Two-claim, passage-selection, identifier,
number, concurrency, completion, deadline and cancellation controls remain.
These finite lexical guards are not general semantic entailment; API responses
keep `qualityVerdict: pending_review` and require review against the originals.

The reviewed repeated-page question took 2.526 seconds with 2364/2395 cached
tokens. First-page requests took 47.448 and 53.750 seconds. This integration
targets repeated-page context cost, not universal low latency. It does not
measure browser rendering, voice stages or changes of hardware.

## Validation and installation

298 related program tests passed. New production service regressions replay the
actual reviewed claims without modifying them, refuse the previously measured
wrong terms and unfinished string, exercise application bounds and preserve the
page/schema prefix across different questions. Existing transport interruption,
timeout, source isolation and private-data checks remain. Original pinned
candidate tests use an explicit frozen pre-integration baseline so their
historical conditions and failed outcomes are not rewritten as current passes.
Current production/service behavior is tested separately, with exact function
and prompt/schema parity to the candidate reviewed on the Mac.

`update_web_prefix_reuse.py` is a pinned one-file updater using existing hash
checks, port ownership protection, syntax validation, backup and atomic
replacement. It refuses local edits or a running listener before applying
anything, never terminates a process, and verifies the baseline again after
download. Wrong content, invalid Python, symlinks, occupied ports and replacement
failures are covered by its tests. Existing notes, databases, memory and settings
are preserved. Source/installer pins are recorded below.

After installation and restart, `check_web_prefix_reuse.py` makes two selected
public reads and three summaries through `/api/andrea/web/summarize`, not direct
Ollama calls. It retains the same questions and criteria, source hashes, exact
claims/quotes, rejections, timings and pending-review flag. It adds total client
request time separately from backend/model phases; those times are not added.
There are no automatic retries or benchmark warm-ups, and the CSV excerpt is
reused only within the existing page lifetime. The installed Mac check and
manual review below complete this finite adoption; the isolated pass was not
used as a substitute for the production check.

Upstream `open-jarvis/OpenJarvis/tests/engine/test_ollama.py` was consulted again
for asynchronous stream, timeout/disconnect behavior and schema propagation.

## Package pins

- Source commit: `94504dd9e8bec8349f628e3041808dc4ad7c2e1e`.
- Previous contract SHA-256: `21ce7da49c28097784c2defd0518503f7abf31fc00842d9e87c659eb1cf8b185`.
- Installed contract SHA-256: `5b8a73b2a9d534074ec61eb67b9abd0eb6c73d3abb2783e76149ad6b3b7b2285`.
- Installed-check SHA-256: `1ca35797a9750dcb188454c2f1b89edddca43409b4c3b32ec2c25e4a3001c324`.

The updater downloads only the source contract from that immutable source commit.
Run the updater with OpenJarvis stopped; restart it for the production check.
No installed success or final performance claim is assigned before that check.

## Installed Mac check completed — 2026-10-05

Installer commit `579869ec2a62b0842dbf8125de2fe32c692a7e77` applied the single
contract file and reported backup `20261005-222132-em2eugix`. The installed
checker verified its own published checksum and project fingerprints before
requesting three summaries via the OpenJarvis API. All three original cases
completed without retry; source hashes match the isolated series.

Manual semantic review passes all three stated criteria:

- asyncio reports I/O/IPC and subprocess control, each supported by its own
  original selected passage; it makes no acceleration or parallelism promise.
- CSV preserves the absence of default type conversion, the QUOTE_NONNUMERIC
  exception, and conversion of fields not enclosed in quotation marks to float.
- The undocumented price yields no claims, without inventing a price, zero,
  or absence of information outside the provided excerpt.

The automated API still says `accepted_pending_semantic_review` or `abstained`
and keeps `qualityVerdict: pending_review`. The favorable manual review is this
explicit record; program acceptance was not relabeled as semantic certification.
Earlier failed experiments retain their failed verdicts.

| Case | Client summary total | Native model load | Native context evaluation | Native output evaluation | Cached / context tokens | Output tokens |
| --- | --- | --- | --- | --- | --- | --- |
| asyncio | 46.691 s | 7.356 s | 29.917 s | 9.308 s | 0 / 1624 | 60 |
| CSV conversion | 50.260 s | 0.002 s | 36.879 s | 13.129 s | 616 / 2396 | 71 |
| Missing price, same CSV excerpt | 3.592 s | 0.003 s | 2.463 s | 1.073 s | 2364 / 2395 | 5 |

Page reads took 364 and 652 ms. Native terminal frames were received in all
three cases. The repeated-page request used only 31 uncached context tokens,
corroborating the intended context reuse in the installed path. These client,
backend and native phase clocks describe the same request and are not summed.
Browser drawing was not measured. The original first-page responses remain
slow: context evaluation is the largest measured phase (about 30–37 seconds),
followed by output generation, with initial model loading also contributing.

This one-file context-reuse adoption is closed for its finite quality and
production criteria, supported by 298 program regressions and both isolated and
installed manual review. It establishes the observed repeated-page improvement;
it does not establish universal response speed or reliability of all future
summaries. No additional benchmark or retry is required to close this change.
Reducing the first-request context cost is a separate remaining latency task.
