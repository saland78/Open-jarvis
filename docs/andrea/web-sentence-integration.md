# Complete-sentence web synthesis integration

The isolated candidate at 29f0e0758c75e7a36fd12c947e99b10589f3d4b0
completed the selected DataCamp request with two complete, paraphrased
claims supported by their exact cited passages. Manual review of that
specific output passed. This is not a guarantee for every page or question.
Source excerpt: 6,000 characters; SHA-256:
f37f6cd91b45dc773450f2d1b437ad62008183c8a2a9998af2d19d8694ffe73a.
Total client time was 55.723 seconds (first JSON: 40.800 seconds).
Native load was 4.574 seconds, context evaluation 36.190 seconds and token
generation 14.922 seconds; prompt tokens 2,300, cached tokens zero, generated
tokens 60. These measurements do not certify latency improvement or browser
rendering. The performance task remains separate and pending.

Production now uses web_sentence_contract.py, copied from the reviewed
candidate's pure preparation/validation functions. A parity test compares
the exact prompt, schema, source bank and acceptance/rejection behavior.
The LocalWebPages.summarize path selects this contract; the existing legacy
quote/indexed helpers remain for compatibility. The rich async production
transport, metrics, source expiry and interruption behavior are preserved.

All excerpt characters remain in the input. The source is divided only at
line/sentence boundaries; units over 600 or below 20 characters remain as
context but cannot serve as evidence. At most two generated claims are
allowed. The soft target is fewer than 100 characters, the hard cap 200;
claims must end with punctuation and cannot be verbatim source copies.
The program resolves exact source units rather than asking the model to
reproduce quotes. Numeric and finite technical-concept checks reject some
unsupported substitutions. They cannot prove general entailment, detect
every negation, or establish truth on outside systems. The API and UI retain
accepted_pending_semantic_review/pending_review; rejected claims stay hidden.

There is one model request, with no automatic retries, text clipping, period
insertion, external fallback, memory/vault access or model-setting changes.
The frontend is unchanged and accepts the existing text/quote result shape.
Production rendering and the actual rich transport on the Mac still require
an explicit UI check after installation; the isolated request did not test
them. Do not describe the whole application as tested or perfect from this
single candidate result.

update_web_sentence_evidence.py installs exactly two backend files. It
requires the known baseline or already-installed target hashes, holds port
8008, checks all downloads and Python syntax before modifying the project,
backs up existing files, and rolls back a failed replacement including a
new module that had already been written. Private configuration, notes,
database and dependencies are unchanged. It refuses an unknown preexisting
module or local edits. Run only after stopping OpenJarvis; the separate
original Jarvis installation/port is not touched.

Validation includes candidate/production parity, exact evidence recovery,
abstention, rejection without repairs, malformed/truncated/tool/trailing
streams, cancellation and stream closure, request-bound metrics, and pinned
installer backups, repeated installation, bad downloads, changed files,
occupied ports, symlinks and rollback after the first replacement.
The source and installer are published as pinned commits on the draft
feature branch. The next Mac step is installation followed by reading the
same explicit URL and reviewing the UI summary and supporting passages.

Selected local verification: 130 Python tests passed, plus 11 existing
frontend page tests on the unchanged frontend source. Frontend tests use
mocked responses/rendering and do not establish live browser timing or
Mac UI success. The updater's two-file rollback is exercised after the
first new module has been replaced, not only before any write.
