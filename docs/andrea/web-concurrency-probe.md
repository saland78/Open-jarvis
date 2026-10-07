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
remain unchanged. The installed browser confirmation passed for the reviewed
brief Italian excerpt summary described below. Historical installer
and isolated-probe baselines remain as fixtures, rather than rewriting the
expected hashes to accept a different historical implementation.

The integration and installer passed 146 selected Python tests, including
transport cancellation, source verification, historical installer regression
and eight tests for the one-file updater. The updater holds port 8008 while
checking the baseline, download hash and Python syntax, preserves the old
module in a private backup, refuses local edits and atomically replaces only
`scripts/andrea/web_sentence_contract.py`. No frontend rebuild is needed.

## Installed interface verification

After installing the pinned one-file updater and restarting port 8008, the
Italian page was read and its default summary generated through the browser.
The visible output contained two complete claims with their original passages:
concurrent activity management and synchronous execution waiting for operations.
The previously introduced parallel-execution claim did not appear. Format and
source checks passed; manual review found both points faithful to their displayed
evidence for this brief summary. This closes the observed defect for this case,
not every possible page or future generation.

Observed backend/model measurements: page reading 667 ms, generation and checks
11.288 s, first partial JSON 237.45 ms, context evaluation 182.808 ms, model load
2.034 ms, token generation 11.049643 s, context/generated tokens 2434/61.
The fast context phase differs substantially from the preceding local probe;
these measurements do not establish why it was faster, a repeatable speedup,
browser paint time or end-to-end voice latency. The partial JSON was not shown
as an accepted response. Model options remain unchanged and no second automatic
generation occurred. The observed interface paraphrases are covered by the
production regression test; its acceptance remains pending human semantic
review in the API, without rewriting that verdict to claim automatic quality.

Upstream consulted for this task:
`open-jarvis/OpenJarvis/tests/tools/test_web_search.py`, plus the official Python
coroutines and tasks documentation. Upstream provider tests do not implement
this custom evidence-linked synthesis contract.
