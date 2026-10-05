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
are preserved. Source/installer pins are recorded below once packaged.

After installation and restart, `check_web_prefix_reuse.py` makes two selected
public reads and three summaries through `/api/andrea/web/summarize`, not direct
Ollama calls. It retains the same questions and criteria, source hashes, exact
claims/quotes, rejections, timings and pending-review flag. It adds total client
request time separately from backend/model phases; those times are not added.
There are no automatic retries or benchmark warm-ups, and the CSV excerpt is
reused only within the existing page lifetime. The installed Mac measurement
and its manual review are pending; the isolated pass does not substitute for
that production check.

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
