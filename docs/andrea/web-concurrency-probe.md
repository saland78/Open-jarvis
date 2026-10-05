# Preserve concurrency claims without introducing parallel execution

The installed sentence contract correctly rejected a model paraphrase that
changed a source description of concurrent activities during waits into
parallel execution. The source passage did not contain that concept; another
passage discussing it cannot support a claim linked to the first passage.

`web_concurrency_synthesis_probe.py` is an isolated candidate. It adds focused
instructions about preserving the meaning of concurrency terms and grounding
each claim only in its selected passage. Sentence banks, schema, validators,
model options and evidence resolution are unchanged. It neither repairs a
rejected answer nor accepts it by weakening checks.

The probe verifies the four installed backend hashes before reading the explicit
Italian DataCamp URL through port 8008. It makes one local Ollama request using
the installed model settings and prints raw output and validation diagnostics.
No project file, private note, memory, configuration or dependency is changed.
HTTP page-read errors print the bounded local API detail and stop before any
inference. There are no automatic retries.

Seven targeted tests cover the observed false parallel claim, a supported
concurrent paraphrase, passage-local evidence, unchanged acceptance functions,
refusal of local edits, one-read/one-inference isolation and page-read failure.
These tests do not establish model quality; local generations and browser
results require separate review. A previous successful generation does not certify subsequent
generations at temperature 0.4.

## Reviewed local generation

The Italian 6000-character excerpt with SHA-256
`f37f6cd91b45dc773450f2d1b437ad62008183c8a2a9998af2d19d8694ffe73a`
produced two complete paraphrases: concurrent activity management, and the
source's description of sequential synchronous Python waiting for a response.
Both were supported by their exact selected passages and passed manual review
for this brief excerpt summary. No parallel execution was inferred. One request
took 52.492 seconds (context 37.473 s, token generation 10.663 s, load 4.318 s).
This is not evidence of a latency improvement or universal reliability.

Production now uses exactly the candidate's `prepare` function. All validators,
schema bounds, source preservation, model options and transport safeguards
remain unchanged. The installed browser confirmation remains pending until
the one-file prompt update is installed and exercised. Historical installer
and isolated-probe baselines remain as fixtures, rather than rewriting the
expected hashes to accept a different historical implementation.

The integration and installer passed 146 selected Python tests, including
transport cancellation, source verification, historical installer regression
and eight tests for the one-file updater. The updater holds port 8008 while
checking the baseline, download hash and Python syntax, preserves the old
module in a private backup, refuses local edits and atomically replaces only
`scripts/andrea/web_sentence_contract.py`. No frontend rebuild is needed.

Upstream consulted for this task:
`open-jarvis/OpenJarvis/tests/tools/test_web_search.py`, plus the official Python
coroutines and tasks documentation. Upstream provider tests do not implement
this custom evidence-linked synthesis contract.
