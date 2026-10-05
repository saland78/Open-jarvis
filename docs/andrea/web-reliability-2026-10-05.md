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
website will be readable. Installation on the Mac and one interface confirmation
are pending. The old 503 remains unexplained unless its detailed code is observed
again. No repeated live requests are needed merely to make it reappear.

Upstream consulted: `open-jarvis/OpenJarvis/tests/security/test_ssrf.py`.
Primary references: Python `ssl` and `http.client` exception documentation.
This custom worker keeps DNS failures closed; upstream's optional fail-open
escape hatch is not used.

## Remaining work in this web reliability task

1. Install and confirm the diagnostic messages on the Mac.
2. Review a finite set of brief syntheses on different content, preserving
   conditions, dates, attribution and uncertainty, and distinguish automatic
   validation from semantic review.
3. Implement an explicit bounded comparison of sources with separate evidence,
   periods and disagreements. The current latest-page-only API does not compare
   multiple pages.
