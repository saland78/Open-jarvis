# Web reliability: distinguish reading failures

This continues the existing web module. The Italian brief page synthesis case
passed its installed interface review; broader synthesis quality and comparison
of sources are separate, unfinished steps.

The earlier page-read HTTP 503 cannot be diagnosed retrospectively: its response
body was not captured. A later successful read does not prove its cause or fix
every transient network failure.

## Implemented reading diagnostics

The disposable reader emits fixed codes for TCP connection timeout/refusal,
TLS certificate validation and handshake errors, request/response/body failures,
incomplete HTTP transfer, remote HTTP status and unexpected internal errors.
The backend translates these codes to bounded Italian messages. In particular,
`http_503` says that the remote site returned HTTP 503; it is not described as
proof that the local Jarvis server is unavailable. Raw exception messages,
remote error bodies, URLs, IPs and credentials are not included in diagnostics.
Unknown error values are rejected as an invalid worker response.

The 25-second overall deadline cannot identify a blocked phase; the message
explicitly says so. Worker startup failure, process failure and malformed output
are distinct. A failed read invalidates the previous page and cannot call the
model or reuse stale context. Process cleanup, cancellation and the busy guard
are preserved. No automatic network or model retries are added.

HTTPS certificate verification, DNS pinning, validation of every redirect,
private destination blocking, response limits and model settings are unchanged.
Successful page and summary response structures are unchanged; the existing
interface already displays the API's detail message. No frontend build is needed.

## Verification and limits

162 selected Python tests passed before packaging. Failure-injection coverage
includes connection/TLS failures, HTTP 503 without reading its body, response
and body timeout, malformed HTTP, premature disconnection, incomplete transfer,
internal exception redaction, invalid requests, process startup/deadline/crash,
safe error messages, stale page invalidation, no inference, no retry, cleanup and
the API response/busy reset. Existing SSRF, redirect, content, summary, transport,
historical installer and model metric tests passed. Historical pinned programs
use their original fixtures; their expected hashes have not been weakened.

These are program tests with injected failures, not a claim that every real
website will be readable. The update was installed on the Mac with both download
hashes verified and a backup created. The installed API then returned the expected
503 with `private_destination` for the deliberately blocked localhost URL.
An explicit public asyncio documentation read succeeded with HTTP 200 in 565 ms,
2551 extracted characters and `partial: false`. These confirm the blocked and
successful reading paths in this installation, not all failures on real sites
or browser rendering. The old 503 remains unexplained unless its detailed code
is observed again. No repeated live requests are needed merely to make it reappear.

The pinned two-file installer adds eight passing tests for verified downloads,
syntax checks, refusing local edits and symlinks, occupied-port refusal without
killing processes, backup preservation, repeat installation and rollback after
the second replacement fails. The final combined run passed 170 selected tests.
The installer replaces only the worker and page service; it requires port 8008
to be stopped and does not change notes, memory, configuration or dependencies.

Upstream consulted: `open-jarvis/OpenJarvis/tests/security/test_ssrf.py`.
Primary references: Python `ssl` and `http.client` exception documentation.
This custom worker keeps DNS failures closed; upstream's optional fail-open
escape hatch is not used.

## Remaining work in this web reliability task

1. Review a finite set of brief syntheses on different content, preserving
   conditions, dates, attribution and uncertainty, and distinguish automatic
   validation from semantic review.
2. Implement an explicit bounded comparison of sources with separate evidence,
   periods and disagreements. The current latest-page-only API does not compare
   multiple pages.

## Finite production synthesis check

`check_web_reliability.py` verifies the four installed backend hashes and uses
only the production read/summarize API on port 8008. It reads two explicit public
Python documentation pages and makes exactly three distinct summary requests:
asyncio's scope, CSV reader type conversion with its condition, and abstention
when asked for an unrelated synthetic service price. The CSV page is reused for
the latter two requests within the installed page lifetime. If the required CSV
context is absent, the affected summary is not requested. Reading or API failures
stop the check; rejected model answers remain in the report and do not trigger a
retry. Each completed case is emitted immediately with its question, criteria,
original selected evidence, rejection detail and numeric timings.

The check changes no files, options, notes or memory and does not call search
providers or Ollama directly. Program tests passed for the two reads/three
requests, page reuse, endpoint isolation, refusing local edits, unchanged files,
read failure before inference, missing context, quote/page validation, preserving
rejected outcomes without regeneration, refusing local redirects and disabling
environment proxies for local API calls. The 32 selected checks passed; these
test the harness and existing program behavior, not the local model's quality.
Actual production generations and semantic review are pending. Every generated
result remains `qualityVerdict: pending_review`; no automatic overall quality
pass is assigned.

Upstream additionally consulted for this quality check:
`open-jarvis/OpenJarvis/tests/tools/test_web_search.py`. The production reading
and synthesis design remains the custom local adapter; no upstream provider
test is presented as certification of its answers.

## First production run: failed, retained

The first asyncio response was rejected after 37.288 seconds:
`technical_term_missing_from_passage`, missing concept `async`. The diagnostic
claim was `asyncio serve per I/O asincrono.` and its original selected passage
was `asyncio — Asynchronous I/O`. The claim preserves that heading's scope;
the lexical guard recognized Italian `asincrono` but not English `Asynchronous`.
This is a false technical rejection, not evidence that the full two-feature
summary met all criteria. Only the first rejected claim was exposed.

The CSV case stopped before inference because a literal context substring was
not found. No CSV model answer exists from that run; the third case was not run.
The report did not retain the CSV text, so the exact cause is not established.
Official documentation contains the intended conversion condition. HTML text
can preserve line breaks inside that phrase, which the literal precondition
would incorrectly treat as missing. This possibility is addressed explicitly:
the harness now compares only whitespace-normalized strings, retaining the
original excerpt and evidence unmodified. If the phrase is still absent, it
prints the bounded original excerpt and stops before requesting the summary.
No missing context is fabricated or filled from external documentation.

The production lexical guard now maps the finite English word `asynchronous`
to the existing `async` concept alongside the Italian forms. It does not treat
concurrency as parallelism, accept arbitrary identifiers or alter generated
text. The observed false rejection is covered by a regression that preserves
the exact claim and source and accepts it only as pending semantic review.
Additional cases still reject unsupported parallel execution, await, def and
asynchronous claims without any async source anchor. Historical pinned programs
use their original contract fixture; expected historical hashes stay unchanged.

181 selected tests passed after these corrections, including the normalized
context precondition and preservation of its unmodified original quote.
Prompt, model options, schema, timeouts and evidence selection are unchanged.
The initial production run remains failed; new installation and a complete
three-case production run are required before declaring the series passed.

The pinned one-file installer for the English alias requires the installed
reading-diagnostics baseline. Eight installer tests passed for hashes, backup,
occupied-port refusal, rollback, local edits, symlinks and syntax checks. The
combined final program test run passed 189 checks. It updates only
`web_sentence_contract.py`; the revised finite check is run separately from
`/tmp` and is not installed. Installation and model review are still pending.


## Complete production run after the English alias update: semantic failure

The English alias update was installed and the three-case production check
completed. All three requests ended; this does not make the series pass.

| Case | Program outcome | Semantic review |
| --- | --- | --- |
| asyncio scope | accepted pending review | Failed: the network/IPC claim translated IPC as "scambio di processi", which changes its meaning. The concurrent coroutine claim was supported. |
| CSV conversion | accepted pending review | Failed: an unconditional no-conversion claim omitted the QUOTE_NONNUMERIC exception. |
| Unrelated service price | abstained | Passed within this excerpt: no price, zero or external absence claim was invented. |

Measured generation and checking times were approximately 37.5, 50.3 and 39.3
seconds. The model options were unchanged. The original failed results remain
failed; automatic lexical acceptance did not establish semantic correctness.

The CSV evidence exposes a source preparation defect. HTML source wrapping
split one prose paragraph into different evidence units, stranding "No" on a
preceding line and separating the exception from its scope. The asyncio API
list was likewise broken at source line wraps. These are formatting boundaries,
not reliable sentence or paragraph boundaries.

## Prose context correction and qualification instructions

The HTML reader now collapses whitespace inside prose data while preserving
real paragraph/list/block boundaries, explicit br elements and line breaks in
pre elements. Spaces around inline code, emphasis and entities are retained.
It neither supplies missing words nor rewrites the source's assertions. Plain
text, source length limits, private destination blocking, DNS-pinned TLS,
redirect validation, cancellation, deadlines and model settings are unchanged.
Evidence quotes still come from the extracted page, never from generated text.

The system instructions no longer require six-to-ten-word sentences or prohibit
subordinate clauses. The existing 200-character bound remains, with a soft
100-character goal. Negation, conditions, exceptions, scope, uncertainty and
attribution take priority over brevity. Acronyms and technical identifiers must
be retained rather than translated or expanded without a definition in the
selected passage. No semantic acceptance check is removed or relabeled.
The validators remain structural and lexical; the model can still make errors.

Four extraction regressions cover the observed conditional paragraph (including
negation, exception and affected fields), inline whitespace and entities,
separate prose/list/code blocks and explicit line breaks. Production contract
checks keep the previous schema, complete evidence coverage, validators,
transport closure and no-retry behavior, while using the revised prompt.
Historical pinned installers/candidates use frozen payloads at their original
hashes. The finite check keeps the same three questions and criteria and updates
only the two changed installed file fingerprints.

201 selected program tests passed, including eight installer checks for backup,
verified downloads, syntax, local edits, symlinks, occupied-port refusal and
rollback after the second replacement fails. This is program verification,
not a successful local-model review. The two-file correction still needs Mac
installation and the same three-case production check before this defect can
be declared resolved. Source comparison remains pending until then.

Upstream consulted for this correction:
`open-jarvis/OpenJarvis/tests/tools/test_web_search.py`, particularly source
content preservation and fetch isolation tests. The CSV and asyncio official
Python documentation was consulted to review the claims; upstream tests do
not certify the custom local model's answers.
