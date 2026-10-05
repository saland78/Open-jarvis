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
