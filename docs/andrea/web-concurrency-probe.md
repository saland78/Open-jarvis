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
These tests do not establish model quality: local model and browser review are
still pending. A previous successful generation does not certify subsequent
generations at temperature 0.4.

Upstream consulted for this task:
`open-jarvis/OpenJarvis/tests/tools/test_web_search.py`, plus the official Python
coroutines and tasks documentation. Upstream provider tests do not implement
this custom evidence-linked synthesis contract.
