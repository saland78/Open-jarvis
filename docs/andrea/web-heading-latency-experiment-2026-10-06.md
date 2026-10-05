# Reader-produced heading roles for compact web synthesis

## Observed failure and mechanism

The [preceding Mac collection](web-scoped-latency-experiment-2026-10-06.md#mac-collection-reviewed--speed-gates-met-semantic-adoption-failed)
meets both original speed gates but fails semantic adoption. The compact
asyncio answer claims nonblocking execution using only the document heading.
The installed HTML extractor flattens heading and prose into identical strings;
the evidence schema allows every 20–600 character unit, including that heading.
Preferring descriptions in the prompt does not enforce evidence eligibility.

`web_heading_evidence.py` retains structural provenance from HTML h1–h6 tags.
It decorates the verified installed TextParser without changing its filtering,
main-content selection, inline whitespace, paragraph boundaries or 6000-character
cap. Each normalized line entirely from heading elements gets a character range.
The normalized text is checked for exact equality with the installed extractor's
output. A mixed heading/prose line remains selectable, with all its text intact.
No topic-specific title string, punctuation heuristic or model-generated
classification is used. Plain text and HTML without headings have an explicit
empty role list. Only those HTML tags are classified; this is not a complete
classifier for arbitrary visual/ARIA headings, nor semantic entailment checking.

The isolated candidate retains every source unit, byte, number and original
protected/technical inventory. It adds `contextOnly` reference numbers to the
source-first payload and excludes their references from the native evidence
enum. The application validator independently rejects heading-only evidence;
ignoring the grammar cannot make the observed expansion accepted. Missing,
malformed, overlapping or misaligned reader metadata fails closed. Source
headings remain context; no claim, quote or citation is repaired or reassigned
after generation. All other scope, identifier, condition, qualifier, number,
completion and stream guards are retained, including the preceding finite
event-loop plural and neighboring OS-signals scope fixes.

## Finite comparison, original gates

`web_heading_latency_probe.py` is self-contained and installs nothing. It pins
the same four installed file hashes before collection and around each model
call. Its two owned reader subprocesses import only the verified installed
`web_page_fetch.py` and decorate parsing inside those child processes. Network
selection, public-address checks, DNS-pinned TLS, content limits, redirects and
error handling remain the installed reader's. Each child is bounded by 25 seconds;
timeout closes that owned process without retry. Only the same two public Python
documentation pages are requested once each. No personal note, memory, credential,
configuration or conversation is read. This is an isolated diagnostic reader,
not an installed OpenJarvis endpoint or UI change.

Both sources and the CSV predicate are preflighted before inference. The observed
first asyncio heading must actually be recognized from its HTML. The script
performs the same six original ordered model calls, each once:
asyncio installed/compact; CSV compact/installed; missing price installed/compact.
Questions and semantic criteria are unchanged. The installed baseline's system,
user message and schema are exactly unchanged. The compact variant additionally
changes heading eligibility and carries reader roles; this comparison measures
that combined candidate, not solely instruction shortening. Its system is
1239 characters, requesting Italian output; the baseline is 2202 characters.

Both variants use the same stricter role-aware application validator. Original
installed-policy results are separately reported for diagnosis. Complete rejected
outputs are retained; an incomplete stream stops the series. No second generation,
automatic retry, warm-up, unload, global Ollama change or post-hoc deduplication.
Model, temperature, 4096 context, 512 output tokens, think false, 15m keep-alive,
90-second stream bound and source cap remain unchanged.

The original gates remain native cached tokens ≤8 and uncached fraction ≥98%;
each of the two supported-page pairs needs ≥10% fewer uncached input tokens and
≥10% less native prefill. The abstention pair is diagnostic, not used to rescue
a failed supported-page pair. All six outputs require source-based review,
including two distinct documented asyncio functionalities, CSV condition and
unquoted-field scope, and no invented missing price. Model loading, generation,
reader and client total costs remain visible; no times from separate clocks
are added, and first JSON is not accepted text or browser rendering. One small
finite comparison does not establish a statistical or universal speed claim.

The report always retains `qualityVerdict: pending_review` and refuses automatic
integration. The preceding measured speed pass and semantic failure stay recorded.
The installed production contract is unchanged with SHA
`5b8a73b2a9d534074ec61eb67b9abd0eb6c73d3abb2783e76149ad6b3b7b2285`.
Mac collection for this role-aware candidate is pending.

## Validation

Upstream [OpenJarvis Ollama tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_ollama.py)
were consulted again for nonblocking stream paths, applied timeouts and clean
disconnect handling. Streaming runtime is unchanged. Tests use the upstream
principle of replaying concrete regressions with bounded fake transports.

Thirty new checks cover exact observed heading expansion, h1–h6 provenance,
main/hidden/chrome filtering, inline code, Unicode/whitespace and source wrapping,
identical heading/prose text at different offsets, mixed lines, source truncation,
long headings and all-heading documents, missing/malformed role metadata,
native and application exclusion, unchanged inventories and installed baseline,
helper/standalone AST parity, retained guard failures, cache eligibility and
unaltered performance gates, exactly two reads/six calls, preserved rejected
diagnostics, early preflight refusal, incomplete-stream stop, and the owned
reader hook/deadline. With the previous related checks: **383 program tests pass**.
These checks establish program behavior; local model answer quality and timings
still require the pending Mac collection. The latency task remains open.
