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


## Production review after prose-context correction: two passes, one failure

The two-file correction was installed, OpenJarvis restarted, and the same
three-case production check completed with its four expected file hashes.

| Case | Semantic review | Observed evidence |
| --- | --- | --- |
| asyncio scope | Failed | The coroutine/control claim is supported. The network/IPC claim still invents "scambio di processi tra processi" instead of retaining IPC. |
| CSV conversion condition | Passed for the stated criteria | The claim now preserves the no-conversion rule with the QUOTE_NONNUMERIC exception; it does not claim that every field converts. Its original quote contains the whole condition and the unquoted-field scope. |
| Unrelated price | Passed within the selected excerpt | Empty claims; no price, zero or external absence assertion. |

Generation plus checks took about 40.0, 42.7 and 35.4 seconds, respectively.
These individual observations are not a controlled performance benchmark.
The previous CSV source-wrap defect is corrected in the observed run. The
overall quality suite is still failed because the IPC paraphrase is inaccurate.

## Isolated literal-identifier candidate

`web_identifier_preservation_probe.py` is a standalone, read-only candidate
requiring the currently installed four backend hashes. It uses the same three
questions, criteria, two explicit public pages and model settings. Page reads
use the production API; each case's inference goes once to local Ollama with
candidate messages/schema/validation. It is not a production integration or
browser test. It changes no project files and imports no personal context.
The candidate contract is also retained as a pure module for reviewed future
integration, but production still uses `web_sentence_contract.py` unchanged.

For each eligible passage, a sparse prompt inventory lists literal uppercase
source tokens. The candidate requires their retention in the generated claim
and rejects tokens introduced without support in that selected passage.
IO/I/O is one finite spelling equivalence; no acronym definition, translation
or external glossary is supplied. It preserves source quotes and generated
text exactly: a rejection yields no accepted claims, no repair and no retry.
Raw model JSON remains marked diagnostic, even when the candidate refuses it.

This is a conservative retention policy, not a semantic classifier. A faithful
partial paraphrase that omits an acronym from the selected unit can be refused;
retaining an acronym does not prove the rest of the sentence is faithful. The
model must choose a faithful supported unit or abstain, and the original
semantic criteria still decide whether a case passes. No failing generated
answer is relabeled as success, and no native regex grammar is introduced.

15 new program tests pass. They reproduce the observed bad IPC answer, verify
its refusal without repair, retain supported IO/I/O + IPC paraphrases, reject
missing/added identifiers and identifiers anchored only in another passage,
preserve the passing CSV condition and abstention, preserve prior completion,
number and parallelism checks, and assert exact standalone/pure-contract
parity. The harness checks two reads/three distinct inferences, unchanged
files/options, no retries, no inference after read failure or local edits,
missing context, proxy isolation and local redirect refusal.

At candidate publication, the three local-model generations and semantic review
were still pending. The installed suite remained failed in its asyncio case.
The following review records the subsequent results without changing that
historical production verdict.

Upstream consulted again: `open-jarvis/OpenJarvis/tests/tools/test_web_search.py`.
Primary sources consulted: official Python asyncio documentation and Ollama's
structured-output documentation. The latter supports schema validation and
prompt/schema grounding; it does not certify semantic fidelity. Model
settings remain unchanged to keep this candidate comparison interpretable.

## Two isolated Mac runs reviewed; production integration prepared

Andrea supplied two manual executions of the same pinned candidate. Both runs
are retained in the review: each satisfies the same three stated criteria.
The evidence hashes agree between runs: asyncio
`db58150c8bd0490e2344cea1c0ad51099dbca7160ea49286f276d20565529c01`
(2551 characters, not partial) and CSV
`f7a791129dc9ce62e6c623a5ba990c009a0e45010981c5effdefe1e49fc3f215`
(6000 characters, partial). No installed file or model option changed.

| Case | Review of both isolated runs |
| --- | --- |
| asyncio scope | Two supported functionalities: I/O with IPC, and event loops for networking, subprocesses and OS signals. IPC is retained and its Italian expansion has the correct ordinary meaning, unlike the failed production paraphrase. |
| CSV conversion | The claim preserves lists of strings, the default absence of automatic type conversion and the QUOTE_NONNUMERIC exception. It does not claim conversion for every field. |
| Unrelated price | Empty claims in both runs; no invented price, zero or assertion about external information. |

The second event-loop claim says "processi" rather than the more precise
"subprocessi". It does not claim control over all processes; the brief contextual
paraphrase meets the stated criteria, with that precision limitation recorded.
The model expanded IPC correctly despite the instruction to avoid expansion.
Literal retention therefore does not prove full prompt compliance or semantic
entailment. These are scoped reviews of six observed results, not certification
of future answers or all websites. API quality verdicts remain `pending_review`.

| Case | First run, client total | Second run, client total |
| --- | --- | --- |
| asyncio | 42.03 s | 10.75 s |
| CSV condition | 45.84 s | 8.36 s |
| Missing price | 38.32 s | 1.10 s |

The second run reused 1460 of 1461 prompt tokens for asyncio and 2238 of 2239
for both CSV questions. These warm-cache observations do not establish stable
latency or a hardware-independent speed improvement.

Production now uses the reviewed candidate's exact source bank, messages and
native schema. The model settings, transport, deadlines, cancellation, page
lifetime and frontend remain unchanged. Identifier checks preserve generated
text and source evidence; rejection cannot repair a claim or retry generation.

Integration testing found a false rejection of previously reviewed DataCamp
summaries: a multi-sentence paragraph mentioning API in one sentence was made
to require API in a faithful summary of another sentence. Mandatory literal
retention is consequently enforced only for a single-statement evidence unit;
introduced identifiers must still be present in the selected unit, including
multi-sentence paragraphs. The IPC clause is a single unit, so its observed bad
paraphrase remains rejected. Generation instructions still guide retention in
all units, but lexical validation alone cannot certify coverage of conditions
or exceptions in a partial paragraph summary. Semantic review remains required.
The strict isolated candidate is retained unchanged as historical evidence.

228 selected program tests passed. Production regressions replay the claims
and abstentions from both reviewed rounds through the actual service, preserve
exact evidence and pending quality verdicts, reject the observed IPC defect
without repair or retry, verify exact candidate generation-input parity, and
preserve prior valid partial summaries while rejecting new unsupported
identifiers. Existing isolation, SSRF, transport, cancellation, read failures,
model metrics and historical installers also pass. Eight installer checks cover
verified source, syntax, backups, repeated installation, refused local edits,
symlinks, occupied port and failed replacement preservation.

The pinned installer replaces only `web_sentence_contract.py`, requiring port
8008 to be stopped and preserving the old file in a private backup. The finite
production check updates only that fingerprint; its three questions and quality
criteria are unchanged. Mac installation and a new production run still need
review before closing this defect. Source comparison remains the next separate
task and has not started.

Upstream consulted for this integration:
`open-jarvis/OpenJarvis/tests/tools/test_web_search.py`, particularly source
preservation and fetch isolation. Those tests do not certify this local model's
semantic answers.
