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
Mac collection for this role-aware candidate is completed below. This candidate
is not adopted: formal and semantic issues remain despite the speed gates.

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
These checks establish program behavior. The completed Mac collection below
does not close the latency task.

## Mac collection reviewed — heading fixed, term/type fidelity still open

All six calls complete, without retry. The source snapshots are unchanged from
the preceding comparison: asyncio SHA
`db58150c8bd0490e2344cea1c0ad51099dbca7160ea49286f276d20565529c01`,
CSV SHA `f7a791129dc9ce62e6c623a5ba990c009a0e45010981c5effdefe1e49fc3f215`.
The HTML reader marks asyncio range `[0,26]` as context reference 1, and CSV
ranges `[0,34]` and `[1470,1485]` as references 1 and 13. Neither generated
asyncio response selects the heading as evidence; both select network I/O/IPC
and subprocess control from the actual documented items.

| Call in collection order | Uncached input tokens | Native prefill ms | Client total ms | Review |
|---|---:|---:|---:|---|
| asyncio installed | 1670 | 23211.678 | 34904.712 | Two faithful functionalities; favorable |
| asyncio compact | 1328 | 19211.425 | 26604.857 | Faithful input/output expansion; false literal I/O refusal |
| CSV compact | 2104 | 33535.333 | 45475.086 | Formal acceptance; ambiguous result type, not a semantic pass |
| CSV installed | 2440 | 37270.574 | 50087.612 | Default, condition, unquoted fields and float preserved; favorable |
| Missing price installed | 2441 | 36881.563 | 37735.223 | Empty claims; favorable abstention |
| Missing price compact | 2101 | 32525.442 | 33363.063 | Empty claims; favorable abstention |

Native cache counts are 0–4 and all calls meet the original cache eligibility.
The asyncio pair reduces uncached tokens by 20.479% and prefill by 17.234%;
CSV reduces them by 13.770% and 10.022%. Both original speed gates are met.
The first installed asyncio call includes 4066.436 ms model loading versus
2.433 ms in the compact call: its full total difference is not attributed
entirely to the candidate. CSV load durations are 3.601/1.893 ms. First JSON,
generation, read costs and client totals remain distinct; browser drawing was
not measured. These six calls do not establish a statistical speed guarantee.

The compact asyncio response says `input/output` with IPC and points to the
same network IO/IPC item. The existing literal guard still requires `I/O` and
rejects that standard expansion. The CSV compact response preserves the default
rule, QUOTE_NONNUMERIC and unquoted-field scope, but replaces the explicit
Python result type float with “numeri decimali”. Formal identifier/scope
acceptance does not establish that this type is faithfully preserved.

The original automatic report remains `gates_not_met`, with
`technicalCaseShapesMet: false`, `qualityVerdict: pending_review` and no
integration permission. Four outputs have favorable review; the other two
require the distinct [finite term/type correction](web-type-latency-experiment-2026-10-06.md).
Replaying old responses with a corrected program cannot retroactively turn
this collection into an adopted or fully passed variant.
