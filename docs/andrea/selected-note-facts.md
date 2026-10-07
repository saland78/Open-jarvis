# Selected-note synthesis

The read-only notes page offers **Sintesi della nota** on an active search
result. The request sends its relative path, never a cached preview as evidence.
The backend reads that file afresh through the existing bounded, no-follow vault
reader. Selecting one file does not claim complete search or complete note coverage.

The bounded adapter currently recognises two conventions: a book introduction
with independent paper, digital and cover dates, or dated KPI update/snapshot
callouts with count, variability and documentation qualifications. Unsupported,
inactive or ambiguous notes stop before inference. The existing three search
summary modes remain separate.

The model receives only proved original spans and the same prompt and JSON Schema
used by the read-only candidate probes. Ollama's `format` receives the full schema
through the secured engine, rather than a generic JSON-mode flag. The local
model, 512-token budget, 4096-token context, temperature, retention and timeout
remain bounded by the existing profile. No tools or external sources are enabled.

One generation is buffered until the secured stream has fully drained. Original
spans, required records, dates, numbers and dated qualifications are checked.
The source is read again before acceptance; changed or inaccessible notes refuse
the synthesis. There is no automatic second generation. Cancellation releases
the producer and busy guard; partial JSON is never displayed.

The model writes the claim text. Qualification context dates are source-bound
fields rendered by the program. The UI displays original passages separately,
each with its own inclusive line range. File modification time is metadata,
not evidence that a claim is true or current.

Technical acceptance remains `pending_review` for meaning. The regression suite
includes a deliberate semantically wrong negation that passes lexical checks:
passing a schema is not an entailment oracle. Review the actual output against
its passages before declaring a quality case passed. Browser completion is a
transport result and cannot certify quality or external data.

Validation uses synthetic files and simulated secured-engine streams. Real local
model quality, browser behaviour and latency after installation require separate
checks on the target machine. The source-only installer pins downloads, verifies
hashes and previous file versions, backs up replacements and rolls back on failure.
It requires port 8008 to be stopped and does not update notes, databases,
configuration or dependencies.
