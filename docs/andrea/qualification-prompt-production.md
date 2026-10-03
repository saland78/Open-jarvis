# Compact message for bounded dated qualifications

This change routes only the existing dated-qualification note plan through
the compact message composer. The book plan retains its original messages
byte-for-byte. Search, note selection, Markdown extraction and all other
response modes are unchanged.

The compact qualification message is identical to the candidate exercised
by the read-only comparison. It preserves the exact mandatory source
information, request, IDs and source context dates. Only the redundant
message copy of the JSON Schema becomes an empty-text response outline.
The full native schema passed to Ollama remains unchanged. The outline is
not a supplied answer.

## Boundaries and validation

`qualification_prompt.messages` accepts exactly the existing four-kind
qualification plan. An unknown, reordered or incomplete plan is refused.
The bridge continues to use original source proofs, the same response
contract, rereading of the note and vault identity, transport limits,
citations and rendering. No model options, token budgets, timeouts, tools,
cloud services, dependencies or frontend files are changed.

This is a prompt change, not a new quality oracle. Structural acceptance
still requires semantic comparison with the original passages. Failed book
experiments are not relabelled as passes and are not used in production.
Single diagnostic observations are not a latency benchmark: cache state,
loading, order and output length can affect elapsed time. The updated
production path and browser latency still require the finite Mac check.

## Development checks

The server regression runs both selected-note routes through the actual
ASGI path with synthetic notes and simulated inference. It asserts the
original book wire message, the reviewed compact qualification wire message
and the unchanged full native schema. Existing checks retain source-change,
disconnect, truncation, date, quantity, qualification and predicate refusal.

The historical probe and previous installer stay pinned. Their regression
fixtures use the exact public bridge from before this change rather than
relaxing source hashes. The old read-only probe will refuse a subsequently
updated installation, as expected for a version-pinned diagnostic.

The two-file updater checks the previous bridge and seven unchanged runtime
components, refuses an occupied server port, stages and verifies all
downloads before replacement, and saves previous files locally. Hash,
syntax, collision, concurrent-edit and replacement-failure tests exercise
the actual manifest. It restores applied files if replacement fails. Notes,
configuration, databases and dependencies are outside its write manifest.

The updater downloads both runtime files from source commit
`fa4ed4574218f1fc9dbb3e8428cc7b8f6970c360`, with fixed SHA-256 checks.
Fifty-nine targeted development checks passed, including ten tests of the
actual two-file transaction. This does not include a new Mac production or
browser check. Installation and that final check remain pending.

Consulted upstream [document-QA tests](https://github.com/open-jarvis/OpenJarvis/blob/792131feb3948aca0b54a94e0344f6827ff3129d/tests/evals/scorers/test_doc_qa.py)
and [DocQAScorer](https://github.com/open-jarvis/OpenJarvis/blob/792131feb3948aca0b54a94e0344f6827ff3129d/src/openjarvis/evals/scorers/doc_qa.py).
Separate fact coverage and citation checks inform the review; heuristic word
overlap is not proof of meaning. The official [Ollama chat API](https://docs.ollama.com/api/chat)
supports the unchanged native schema format and phase measurements.

The PR remains draft. No merge, personal report publication or original
Jarvis modification is part of this update.
