# Compact message, unchanged native schema

Status: first candidate not adopted; revision 2 diagnostic prepared. The
revised book instructions still require the finite Mac semantic comparison.

The first comparison exposed a meaning problem despite technical acceptance:
a specific literary classification could become generic, and an availability
date could become an ambiguous start. Revision 2 adds source-preserving role
guidance only to book messages. KPI messages remain byte-for-byte identical to
revision 1. This does not rewrite or reclassify the first candidate's output.
Its immutable script and source remain available at commit
`c17f1612e235be1c1e92c1f72548ed4301d9e219`.

## Hypothesis and boundary

The selected-note synthesis sends the full response schema both as part of
the user message and as Ollama's native `format`. This experiment replaces
only the message copy with a short empty-text outline. It may reduce prompt
evaluation work. Whether quality and elapsed time improve is not yet known.
Empty strings are placeholders, not supplied answers.

The system's original substantive instructions, exact mandatory source passages,
query, record IDs, qualifications and source context dates are preserved.
The full native JSON Schema is unchanged. The source adapter, validation
and renderer are loaded from the verified installed baseline. Model,
temperature, context, output budget, thinking and keep-alive remain unchanged.
No final prose is supplied to the model. No second generation repairs output.
The only revision 2 addition specifies preserving the source's specific work
classification and describing edition dates as availability. It contains no
specimen answer, title, quantity or publication date.

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

Fourteen targeted tests cover the actual serialized API payloads, both note
kinds, identical native schemas and options, mandatory information, wrong
dates/counts/qualifications/predicates, changed sources, wrong selection,
baseline changes, bytecode/file preservation, truncated streams, tool calls
and duplicate protocol keys. Simulated local HTTP and synthetic notes only;
no live Ollama or personal vault is used in development.
The two additional regressions preserve the KPI wire payload and demonstrate
that generic work classification and an ambiguous start can pass technical
validation. They remain semantic failures; guard acceptance is not relabelled
as a successful synthesis. The next Mac check selects only the book: two
requests (original and revised compact), without retrying the four-case series.

Consulted upstream
[Ollama tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_ollama.py)
and the already integrated
[Ollama engine](https://github.com/open-jarvis/OpenJarvis/blob/main/src/openjarvis/engine/ollama.py).
The official [chat API](https://docs.ollama.com/api/chat) documents native
schema `format`, terminal durations in nanoseconds and native token counts.
The diagnostic reuses the existing local phases helpers, with duplicate-key
and tool-call refusal. It does not install another engine or enable tools.
For revision 2, consulted upstream
[document-QA tests](https://github.com/open-jarvis/OpenJarvis/blob/792131feb3948aca0b54a94e0344f6827ff3129d/tests/evals/scorers/test_doc_qa.py)
and [DocQAScorer](https://github.com/open-jarvis/OpenJarvis/blob/792131feb3948aca0b54a94e0344f6827ff3129d/src/openjarvis/evals/scorers/doc_qa.py).
Their separate coverage and citation checks inform the review. Heuristic
word overlap is not a proof of meaning, so this diagnostic still requires
review of the actual phrases against their original supports.

PR remains draft. No merge, original Jarvis change, note/configuration/database
modification or automatic performance/semantic pass is part of this task.
