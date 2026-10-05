# Web prompt prefix latency experiment — 2026-10-05

Andrea requested latency work before the planned source comparison. The installed
finite three-case synthesis suite passed its semantic review. Its observed
generation/check times were 41.810, 46.278 and 36.728 seconds; public reads took
452 and 601 milliseconds. Ollama reported context evaluation of 26.231, 38.076
and 35.713 seconds. Only 467/2239 prompt tokens were cached on both CSV questions,
despite the same excerpt. These measurements identify an expensive context phase,
not a general explanation of latency in every Jarvis module.

## One isolated change

The current user JSON puts the changing question before protected identifiers
and page passages. The candidate changes only JSON field insertion order:
`protectedIdentifiers`, `passages`, then `question`. The system instructions,
roles, full original evidence bank, questions, schema and validator are identical
to the reviewed installed version. No source shortening, external facts,
answer cache, new inference, weaker guard or model-option change is introduced.

Keeping page context at the start of the user content creates a longer identical
prefix across different questions about that page. This is a hypothesis about
KV prefix reuse, not an observed speedup. Ollama v0.34.2's own benchmark varies
the starting prompt to defeat KV prefix matching. Its chat API reports cached
prompt tokens and evaluation duration. A model being loaded does not itself
prove reusable context; other requests, cache slots, model switches and the
runner's behavior can still affect the measured outcome.

## Finite comparison on the Mac

`web_prompt_prefix_probe.py` verifies the four installed backend fingerprints
including the identifier contract. It explicitly reads the asyncio and CSV
public documentation through OpenJarvis. Both variants use those same bounded
excerpts in memory. A missing CSV condition or a read failure prevents all
inference. It then makes exactly six sequential local Ollama calls: the original
three questions with installed message order, followed by the same three with
candidate order. Each completed outcome and rejected diagnostic is retained;
transport failure stops the series without a retry. No warm-up, unload or
model reconfiguration is performed. No project file, vault, memory or provider
search is read or changed apart from the known code fingerprints.

The comparison bypasses production inference and the server's busy guard.
OpenJarvis must be running but idle, with no concurrent Jarvis/Ollama interaction
during the finite series. The standalone probe uses the existing model,
temperature 0.4, context 4096, output cap 512, think false and keep_alive 15m.
The model already in use is not downloaded or replaced. Environment proxies
are disabled and local redirects rejected. Sources remain public bounded text;
no excerpt from the personal vault is included.

Each row reports original question/criteria, source hash, raw diagnostic model
JSON, resolved exact evidence and native load/context/output timings, cached
tokens and total client time. The literal common prefix is measured in user-JSON
characters, explicitly not tokens and not a cache-hit assertion. Source-first
is expected to help the second different question on the same page; first-use
context evaluation and output generation still cost time. Cache state is not
forced, order is fixed and there is one run per variant: this is a diagnostic
comparison, not a controlled cold-start or statistically stable benchmark.
Native and client durations are not added together. Browser rendering is not
measured; partial JSON is not accepted visible text.

## Acceptance and current state

All three original semantic criteria must still pass for the candidate: two
faithful asyncio functionalities, the CSV default/QUOTE_NONNUMERIC condition,
and abstention on the unrelated absent price. Automatic acceptance stays
`pending_review` and does not certify meaning. A fast but incorrect response
fails. Performance assessment will compare the repeated-page case's actual
cached-token count and prompt evaluation duration, recording load and output
differences rather than attributing all total-time changes to this modification.

Ten new program tests and 51 related regressions passed (61 total). They cover
full source and question preservation, unchanged instruction/schema/guards,
literal stable page prefix, exact standalone/baseline/candidate function parity,
two reads/six calls without warm-ups or writes, unchanged options, evidence
hash parity, rejected outcomes without retry, fail-before-inference on missing
context or local edits, stopping on incomplete transport, proxy/redirect isolation
and absent native metrics remaining unknown.

The production contract is unchanged. Local-model measurements and semantic
review are pending. Only a candidate that preserves quality and demonstrates
useful latency behavior should be packaged for production with a backup and
the finite installed check. The larger end-to-end plan, including voice stages,
remains in `end-to-end-latency-plan.md`; this experiment tackles the current
measured text-context cost first.

Upstream consulted for this task:
- `open-jarvis/OpenJarvis/tests/engine/test_ollama.py`: async streaming, bounded
  requests, stream timeout/disconnect behavior and option propagation.
- `ollama/ollama` v0.34.2 `cmd/bench/bench.go`: varying prompt starts to defeat
  KV prefix matching and reporting uncached context evaluation.
- https://docs.ollama.com/api/chat: native duration/count fields and model lifetime.

These references inform the experiment; they do not certify its performance
or semantic quality on Andrea's Mac.

## First Mac comparison: cache gain, candidate quality failed

The pinned six-call probe at `805117cbbe627ae1d053c2172db97e4b3809c764`
completed without retry or production changes. Its two source hashes match the
previous production review. All three baseline cases pass their stated semantic
criteria. The candidate CSV condition and missing-price abstention pass, but
asyncio fails: the model translated `subprocesses` as "sottoprogetti". The
validator rejected its second claim for `API`, because the source said `APIs`.
That plural spelling is a false lexical rejection, but fixing it alone would
not fix the actual subprocess mistranslation. The candidate remains failed;
it has not been integrated into production.

| Case | Baseline client total | Candidate client total | Baseline / candidate cached tokens | Candidate quality |
| --- | --- | --- | --- | --- |
| asyncio | 39.666 s | 33.725 s | 0/1461 / 465/1462 | Failed: subprocesses became sottoprogetti |
| CSV condition | 44.470 s | 48.340 s | 467/2239 / 471/2240 | Passed for the stated criteria |
| Missing price, different question on the same CSV excerpt | 40.184 s | 2.399 s | 467/2239 / 2208/2239 | Passed: empty claims |

For the repeated-page question, prompt evaluation fell from 39.218 seconds to
1.682 seconds; output evaluation remained 0.668 versus 0.666 seconds with five
output tokens in both variants. The total decreased by about 94% in this one
comparison. The serialized user-content prefix shared across the CSV questions
increased from 13 to 6861 characters. Native cached-token counts, rather than
those characters alone, corroborate context reuse in the observed run.

This does not speed up every request. The candidate's first CSV response was
slower, with 59 instead of 45 output tokens and context evaluation 38.337 versus
36.043 seconds. The first asyncio comparison also differs in model load cost
and generated length. Fixed order, unforced cache state and one sample per case
still limit causal and statistical conclusions. The narrow performance
hypothesis is supported, but the overall candidate fails its quality gate.

## Literal-term refinement prepared, still isolated

`web_literal_prefix_contract_candidate.py` retains source-first layout and adds
a sparse inventory of literal `subprocess` / `subprocesses` tokens actually
present in each eligible passage. The model is instructed to keep those tokens
instead of translating or expanding them. The validator requires retention for
single-statement selected units and refuses introducing them without support
in that same selected unit. This is a narrow conservative literal policy; it
can refuse a valid partial summary and does not establish general entailment.
Multi-sentence paragraphs are not forced to retain a term from another sentence.
No definition, external glossary or suggested replacement fact is supplied.

An explicit finite `APIs` → `API` source spelling equivalence applies only to
the added-identifier check for the selected passage. It does not add a mandatory
API retention rule, license other acronyms or use another passage as support.
Generated text and original evidence remain unmodified. The original bad
subprocess claim is still refused even after resolving its API false rejection;
a precise claim retaining `subprocesses` is accepted only pending semantic review.

The standalone `web_literal_prefix_probe.py` makes two public reads and exactly
three candidate inferences using the original questions/criteria. It does not
repeat the baseline or retry until a favorable answer appears. The failed first
candidate remains failed. This is a materially different prompt/validation
candidate, with model, schema, full source coverage, settings and transport
unchanged. Its page prefix remains stable across the two CSV questions. It
reports literal-term inventories, exact evidence, diagnostics, cached tokens
and timings; acceptance still requires semantic review of actual Mac outputs.

Ten new tests plus 61 related regressions passed (71 total). They reproduce the
observed bad term after the API alias correction, accept the exact retained
technical term without repair, keep aliases and terms anchored to their own
unit, discard all accepted claims when a later claim fails, preserve source,
schema, the CSV condition and abstention, assert standalone/pure-function parity,
and verify two reads/three calls without file or option changes. Missing context,
failed reads or modified installed code stop before inference; incomplete model
transport remains diagnostic and stops without retry.

Production is unchanged. New local-model measurements and review are pending;
the latency task remains open. Upstream `open-jarvis/OpenJarvis/tests/tools/test_web_search.py`
was consulted again for evidence-content preservation and explicit fetch paths.

## Literal refinement Mac result: two refusals, not a production pass

The three-call run pinned at `e875987dda1132fd2fb6e8d829b598256a602ee4`
completed without retries or production changes. The same two public excerpts
were used. asyncio took 49.641 seconds and CSV 48.385 seconds; the repeated CSV
question abstained in 2.397 seconds, with 2283/2314 cached context tokens and
1.621 seconds of context evaluation. That preserves the narrow repeated-page
cache observation; the first requests are still slow.

The asyncio answer correctly used the Italian word "subprocessi" in place of
`subprocesses`. The literal English-only guard rejected it. This is a false
lexical refusal introduced by the refinement, unlike the preceding genuinely
wrong "sottoprogetti" translation. The next candidate must permit the precise
finite technical equivalent while continuing to refuse the observed wrong word.

CSV was refused for `sentence_not_complete`: its generated string was exactly
200 characters and ended with "vengono trasformi". The JSON transport ended with
`stop` after only 67 generated tokens; it did not exhaust the 512-token budget.
The string ends exactly at the native schema's `maxLength:200`, strong evidence
that this character bound prevents sentence completion. Adding a period or
accepting the unfinished word would not repair the meaning. The entire literal
refinement remains failed and isolated, regardless of the successful abstention.

## Anchored equivalents and completion space: new isolated candidate

`web_alias_prefix_contract_candidate.py` maps only these finite lexical forms
to the same subprocess concept: `subprocess`, `subprocesses`, `subprocesso`,
`subprocessi`, `sottoprocesso`, `sottoprocessi`. A generated equivalent requires
that concept in the selected evidence unit. Single-statement evidence retaining
the term is still required to retain its concept. "Sottoprogetti" is not an
equivalent and the actual wrong answer remains rejected. This is a lexical
check, not general semantic entailment or permission to import other facts.
The existing source-anchored `APIs` to `API` spelling rule is unchanged.

The native JSON string schema no longer has a character maximum that can force
closure mid-word. The prompt still targets 100 characters and allows 320 when
needed to finish a thought and its qualifications. The application refuses a
complete claim longer than 320 characters; it never trims or repairs it. Two
claims maximum, source passage selection, original full excerpt, 512 output
tokens, model settings, 90-second deadline, transport completion, punctuation,
number/identifier/concurrency guards, no retry, and semantic review all remain.
The larger completion space may increase generation time for a longer answer;
this needs measurement instead of an assumption of speed improvement.

`web_alias_prefix_probe.py` repeats the same three questions and semantic
criteria once, with two selected public reads and no baseline rerun, warm-up,
option change or installation. The source-first user payload, system prompt and
schema are identical between the two questions about the CSV excerpt except
for the final question. Cached token counts and phase timings remain reported;
character prefix length alone is not a cache metric. Earlier failures remain
in this record and are not reclassified as passing tests.

Fourteen new regressions and the 71 preceding related checks passed (85 total).
They reproduce the actual false Italian rejection and exact 200-character
unfinished CSV output, accept the complete 212-character CSV statement without
alteration, reject wrong or unanchored terms, excessive or incomplete output,
unsupported numbers and concurrency, and discard all claims after a later
failure. They also pin standalone/pure function parity, full evidence, identical
question-independent prefix/schema, unchanged settings, exactly two reads/three
calls, no writes, no retry and failure before inference on missing input or local
changes. These are program regressions; the new Mac generation and its semantic
review are still pending.

Upstream `open-jarvis/OpenJarvis/tests/engine/test_ollama.py` was consulted again
for asynchronous stream handling, timeout/disconnect/error behavior and schema
propagation. Production is unchanged and the latency task remains open.

## Anchored-alias Mac result: cache confirmed, CSV meaning failed review

The three requests at `11c6721260a3df29e3cbc72c1711744b08a54c0c` completed
without retries, option changes or installation. The source hashes match the
previous runs. Structural results were two `accepted_pending_semantic_review`
and one abstention. Manual review passes asyncio's two features and the
missing-price abstention. CSV fails its field-scope criterion: the output
translated `unquoted fields` as "campi non incorniciati". The source qualifies
fields by quoting, not by framing. A valid complete JSON and the correct option
name do not resolve that semantic error. The candidate is not a 3/3 pass and
has not been integrated.

| Case | Client total | Native context evaluation | Cached / context tokens | Manual semantic review |
| --- | --- | --- | --- | --- |
| asyncio | 38.948 s | 28.428 s | 158 / 1558 | Passed: I/O, IPC and subprocess control |
| CSV conversion | 55.281 s | 40.692 s | 550 / 2325 | Failed: unquoted became non incorniciati |
| Missing price, same CSV excerpt | 2.798 s | 1.946 s | 2293 / 2324 | Passed: empty claims |

The repeated-page prefix was 6887 characters; actual cached-token counts again
corroborate context reuse. First-page responses remain slow and this run does
not establish their improvement. CSV decoding took 14.346 seconds for 74 output
tokens. The task remains both quality and latency; first-request cost must not
be hidden by the fast repeated-page abstention.

## Source-qualified conversion candidate, still isolated

`web_qualified_prefix_contract_candidate.py` keeps the previous source-first
layout, completion space and precise subprocess equivalents. It adds finite
equivalents for `unquoted`: `non-quoted`, `non quoted`, `non quotato/quotati`,
`non virgolettato/virgolettati`, `non racchiuso/racchiusi tra/in virgolette`,
and `senza virgolette`. These words license only the same qualifier present in
the selected evidence unit, not an arbitrary negation or another field property.
The sparse source-term inventory now includes that qualifier when it occurs.

A narrow guard checks the source predicate: QUOTE_NONNUMERIC with unquoted
fields converted to float. If a generated claim describes those converted
fields, it must preserve both the option name and the unquoted qualifier. It
refuses the observed "non incorniciati", wrong or universal field scopes and
removal of the condition, without editing the answer. A partial default-rule
summary that does not describe converted fields is not forced to restate a
different sentence. Added qualifiers still require their own selected passage.
This guard detects the measured failure class; it is not a general semantic
entailment check. All outputs still require semantic review against their quotes.

`web_qualified_prefix_probe.py` uses the original two public pages and the same
three questions/criteria once. It keeps the model, temperature, context/output
budgets, full excerpt, schema, request order, deadlines and no-retry behavior.
No baseline rerun, forced cache state, settings or installed files are changed.

Fourteen new regressions and the preceding 85 related checks passed (99 total).
They reproduce the actual prior structural acceptance of the incorrect CSV
answer and require its new refusal; accept the precise source qualifier without
rewriting; reject unsupported properties, removal of the condition and use of
a qualifier from another passage; preserve abstention, valid partial summaries,
previous technical aliases and complete statements; discard all claims after
a later failure; preserve standalone parity, full evidence, stable prefix and
schema; verify the same two reads/three calls, no writes/options/retries and
bounded diagnostic-only failure. The candidate's actual Mac quality/latency
result is pending. Production is unchanged.

Consulted again: `open-jarvis/OpenJarvis/tests/tools/test_web_search.py` for fetch,
content preservation and bounded extraction. Python's primary CSV documentation
at https://docs.python.org/3/library/csv.html explicitly ties QUOTE_NONNUMERIC
reader conversion to non-quoted fields; that source informs review and this
finite lexical equivalence, not additional factual context given to the model.

## Qualified-field Mac run: three-case semantic gate passed

The run at `1e7315be28de6fdcf24680db5aa63145846e90c0` completed all three
original cases once with unchanged model settings and source hashes. Manual
review now passes each stated criterion: asyncio reports I/O/IPC and subprocess
control supported by their selected passages; CSV retains the default lack of
conversion, QUOTE_NONNUMERIC exception and non-quoted-field scope; the unsupported
price returns empty claims without inventing a number or asserting external
absence. The API's `pending_review` flag remains a program flag, distinct from
this explicit manual review. Previous failed runs remain failed in this record.

| Case | Client total | Native context evaluation | Cached / context tokens |
| --- | --- | --- | --- |
| asyncio | 47.448 s | 31.641 s | 0 / 1624 |
| CSV conversion | 53.750 s | 40.352 s | 616 / 2396 |
| Missing price, same CSV excerpt | 2.526 s | 1.741 s | 2364 / 2395 |

The first call also loaded the model for 5.595 seconds. Output generation took
10.169, 13.164 and 0.738 seconds respectively, for 58, 73 and 5 tokens. Native
cached-token counts support the narrow repeated-page improvement; they do not
show an improvement to all first-page requests or to voice latency. The fixed
order and unforced cache state still limit benchmarking claims.

The one-file production integration, installed check and backup installer are
described in `web-prefix-reuse-2026-10-05.md`. Its installed Mac result is pending.
