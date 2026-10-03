# Compact message, unchanged native schema

Status: diagnostic prepared; not adopted by production. Local model outputs,
semantic quality and latency still require the finite Mac comparison.

## Hypothesis and boundary

The selected-note synthesis sends the full response schema both as part of
the user message and as Ollama's native `format`. This experiment replaces
only the message copy with a short empty-text outline. It may reduce prompt
evaluation work. Whether quality and elapsed time improve is not yet known.
Empty strings are placeholders, not supplied answers.

The system's substantive instructions, exact mandatory source passages,
query, record IDs, qualifications and source context dates are preserved.
The full native JSON Schema is unchanged. The source adapter, validation
and renderer are loaded from the verified installed baseline. Model,
temperature, context, output budget, thinking and keep-alive remain unchanged.
No final prose is supplied to the model. No second generation repairs output.

## Finite read-only collection

`scripts/andrea/compact_note_prompt_probe.py` runs separately from the app:

- One or two explicitly selected active Markdown notes; no search or vault walk.
- Complete selection and public source hashes checked before any inference.
- One original and one compact request per note, in that order; no retries.
- Same local Ollama endpoint and full native schema for both requests.
- Original notes, vault identity and source hashes rechecked around inference.
  Changes or unavailability refuse the result and stop the comparison.
- Read-only API calls and no file or bytecode writes. Production stays unchanged.
- Native prompt, cached-prompt and output counts and durations are recorded.
  Missing metrics remain null. Characters are not called tokens.
- The first received JSON fragment is hidden diagnostic content, not accepted
  text or browser rendering. Validated text readiness has a separate measure.
- Results include bounded original passages and model prose for private review.
  They must not be committed, uploaded or published as repository reports.

The diagnostic imports only hash-verified public Python modules. It uses a
bundled copy of the compact composer, verified against the separate source
module by tests; there is no installation step for the candidate.

## Acceptance before adoption

Review both outputs against the same original passages. Book description,
counts, approximate quantities, edition/cover roles and missing years must
be preserved. Dated qualifications must retain their separate context dates,
labels and scope. Missing or unverified values do not establish zero, absent
external data, downloaded reports or updated financial values.

All outputs retain `qualityVerdict: pending_review` until that semantic review.
Technical validation is not an entailment oracle: a regression deliberately
shows a semantically false negation that passes structural checks. A refused,
incomplete or truncated answer is not a successful synthesis.

Single observations are not a performance benchmark or proof of a causal
improvement. Original-first ordering, cache state, model loading, other work
and output length can affect times. Inspect those native measurements before
deciding whether another controlled comparison is needed. This diagnostic
does not measure the production security wrapper or browser UI latency.

## Development checks and references

Twelve targeted tests cover the actual serialized API payloads, both note
kinds, identical native schemas and options, mandatory information, wrong
dates/counts/qualifications/predicates, changed sources, wrong selection,
baseline changes, bytecode/file preservation, truncated streams, tool calls
and duplicate protocol keys. Simulated local HTTP and synthetic notes only;
no live Ollama or personal vault is used in development.

Consulted upstream
[Ollama tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_ollama.py)
and the already integrated
[Ollama engine](https://github.com/open-jarvis/OpenJarvis/blob/main/src/openjarvis/engine/ollama.py).
The official [chat API](https://docs.ollama.com/api/chat) documents native
schema `format`, terminal durations in nanoseconds and native token counts.
The diagnostic reuses the existing local phases helpers, with duplicate-key
and tool-call refusal. It does not install another engine or enable tools.

PR remains draft. No merge, original Jarvis change, note/configuration/database
modification or automatic performance/semantic pass is part of this task.
