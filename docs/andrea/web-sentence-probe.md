# Isolated sentence evidence probe

The installed indexed-evidence generator was exercised on the selected public
DataCamp article. The UI accepted exact recovered passages, but semantic
review did not pass: the second generated point ended mid-word and its
definition of coroutine was absent from the selected supporting passage.
The observed total was 84.762 seconds, with 1,974 context tokens and 194
generated tokens. These measurements do not demonstrate an improvement over
the earlier rejected 71.176-second request (1,886/194 tokens). No successful
end-to-end quality verdict is recorded for that candidate.

`web_sentence_synthesis_probe.py` is a standalone diagnostic, not an installer.
It verifies the currently installed public baseline hashes without importing
or changing project modules. It reads only the explicitly selected DataCamp
URL through the same local page-reading endpoint and makes one direct local
Ollama chat request. No search provider, vault, memory, chat history, automatic
retry, file output or configuration modification is involved. The explicit
page read replaces the normal ephemeral current page in server RAM.

The candidate uses whole lines or sentence boundaries instead of cutting at
300 characters. All text is retained in the prompt. Units longer than 600 or
shorter than 20 characters stay as context but cannot be cited. A generated
claim now has a soft target below 100 characters and a hard safety cap of 200
(the earlier 100-character hard-cap failure is recorded below). It must finish
with punctuation; it must
not be an exact source copy. Exact evidence is recovered by ID. Numeric and
narrow technical-term checks reject unsupported tokens in the selected unit.
These are conservative structural/lexical checks, not a general entailment
checker. Sentence punctuation alone cannot prove a sentence is meaningful or
complete. A false statement without these checked tokens could still pass.

The model, temperature (0.4), context (4096), token budget (512), keep-alive
(15 minutes) and disabled thinking are unchanged. Raw model JSON and resolved
passages are printed for explicit review, even when validation rejects them.
The production UI never shows a rejected answer; diagnostic stdout is not an
accepted answer. Browser rendering and production engine overhead are not
measured by this direct-model candidate.

The probe needs OpenJarvis and Ollama running. Do not submit another model
request while it runs. One invocation performs one page read and one model
request. After its result, review completeness, paraphrase and whether each
quote supports the entire point; do not declare success on a technical status
alone. The installed version remains unchanged pending that review.

For this task, upstream OpenJarvis `tests/tools/test_web_search.py` and Ollama's
official structured-output documentation were consulted. The former covers
search isolation, not this personal synthesis contract; the latter specifies
schema enforcement, not semantic truth.

Local deterministic suite: 53 tests passed across this probe, indexed evidence,
page reading, timing extraction and disconnection handling. Live model quality
and latency for the sentence candidate are pending.

## First Mac probe and revised candidate

The first complete-sentence candidate did not finish within 90 seconds.
First content arrived at 57.142 seconds; the diagnostic returned at 90.011
seconds without a terminal frame or native metrics. Quality was not reviewed
because the response was incomplete. It is not a passed test.

The revised probe retains the full 6,000-character excerpt and the same
complete-unit bank. Only the system instructions are compacted and each
point is capped at 100 rather than 160 characters. No source context is
removed to make the original test easier. The 90-second deadline and 512-token
budget are unchanged. If an error occurs, collected partial JSON is now
printed as diagnostic-only, with an error category; it is always rejected
without a completed terminal frame. The semantic check remains pending.

## Schema correction after the second Mac probe

The second isolated probe completed in 89.262 seconds, but its JSON contained
five claims, including strings above the requested 100-character limit.
It was correctly rejected as invalid_structure; no claims were trimmed to
force acceptance. The output is not a passed quality test.

The candidate previously combined minLength/maxLength with the pattern
`^.+[.!?]$`. The public llama.cpp JSON-schema converter prioritizes pattern
over string length handling. Its documented dot grammar accepts quote
characters as well as ordinary characters, so this unbounded wildcard may
also consume subsequent JSON fields/items. This explains a plausible path
around both constraints; the precise installed Ollama converter has not
been inspected, so causality on the Mac is still a hypothesis.

This revision removes only the native pattern. The schema still caps claims
at two and text at 20–100 characters. The Python punctuation, evidence,
numeric, lexical and verbatim checks are unchanged. No prompt, context,
temperature, model, timeout, source or token budget is changed in this
comparison. An explicit schemaVariant identifies the new diagnostic.

The 55 deterministic tests include rejection of a complete five-point JSON
and a missing final punctuation mark despite removal of the native pattern.
They do not run Ollama or prove its enforcement. The live Mac comparison and
semantic review remain pending; production has not been modified.

Primary references consulted: upstream OpenJarvis tests/tools/test_web_search.py,
Ollama structured-output documentation, and llama.cpp grammars/README.md and
examples/json_schema_to_grammar.py. The upstream search tests do not fix this
personal synthesis contract.

## Mac bounded-string result and completion headroom

The pattern-free Mac request completed with two claims, but both ended at
exactly 100 characters, without final punctuation; one ended mid-word.
The result was correctly rejected as sentence_not_complete. Client total:
31.295 seconds; first content: 18.980 seconds. Native prompt tokens: 2,224,
cached prompt tokens: 1,024; generated tokens: 74. These cached-context
conditions differ from the earlier run, so this is not evidence of a stable
latency improvement. Removing the pattern coincided with compliance with
the two-item/100-character bounds; that observation alone does not inspect
or prove the exact installed converter's behavior.

The arbitrary 100-character hard cap was too close to the requested prose
length. This revision explicitly changes that candidate contract: the
prompt aims for 6–10 words and fewer than 100 characters, while the native
schema and Python validator allow 20–200 characters as safety headroom for
completion. A complete 101–200-character point is now structurally allowed;
this is not a claim that the old <=100-character criterion has passed.
Shortness and semantic fidelity still require review of the actual output.

The prompt encourages one fact and no incidental clauses. It contains no
article-specific expected answer. All 6,000 source characters, two-point
limit, exact evidence IDs, punctuation, verbatim, numerical and lexical
checks, model/options and one-request/no-retry behavior are preserved.
No answer is cut, repaired with a period, or automatically regenerated.
The candidateRevision and claimLengthPolicy are printed for comparison.
The actual previously rejected 100-character strings remain regression
cases and are still rejected. There is no live passed verdict yet.

The selected deterministic suite passes 57 tests. These do not run the
Mac model; the next explicit live result must be reviewed separately.
