# Keep operation predicates within their own evidence

Status: **v8 measured on the Mac: five favorable answers and one unfavorable; no adoption**.

The [v8 record](web-operation-predicate-v8-mac-2026-10-06.json) preserves all six
raw answers and the unchanged automatic report. The reference asyncio claim
changes `control subprocesses;` into subprocess execution. The new v8 operation
guard correctly rejects it, but refusal is still a failed model answer. Both
original performance pairs pass; the complete series does not pass.

The active correction is now the [native source-verb experiment](web-native-operation-verb-fix-2026-10-06.md).
It constrains the main control verb during generation and still requires new
Mac outputs and meaning review. The preparation and local tests below document
the original v8 attempt; they are not a successful real-model result.

The [complete v7 Mac record](web-question-focus-v7-mac-2026-10-06.json) preserves
all six raw model outputs, the original automatic report and separate meaning
reviews. All six transports and technical case shapes pass. Both supported
performance pairs meet the original uncached-input/native-prefill thresholds.
Five whole-answer meaning reviews are favorable and one is unfavorable; the
overall meaning result remains `not_passed_no_adoption`.

## What is resolved and what remains

Both v7 missing-price answers are the model's own `{"claims":[]}`. The question
presentation change is consistent with the corrected behavior in this observed
run. It does not prove a sole cause or correctness for every future question.
Both CSV answers preserve the default conversion rule, the QUOTE_NONNUMERIC
exception, unquoted-field qualification and float conversion. The compact
asyncio answer describes two operations supported by its respective own units.
Thus all three compact answers have favorable meaning reviews.

The reference asyncio answer describes network I/O/IPC faithfully. Its second
point correctly mentions subprocess control, but adds an example of executing
external commands to its own quote, `control subprocesses;`. That quote does
not document the added execution example. The original instruction requires
one fact entirely supported by the selected passage, without outside knowledge
or borrowing another passage. Whether such behavior exists elsewhere in Python
is not this claim's evidence. The original technical acceptance is retained;
it is not changed into a retrospective automatic rejection or a meaning pass.

Measured totals are approximately 54.7 to 42.0 seconds for asyncio and 63.9 to
28.2 seconds for CSV. The original paired uncached-input reductions are 15.927%
and 60.914%; native prefill reductions are 11.707% and 62.613%. These values were
recomputed from the submitted native counts and times. They pass the unchanged
10% pair thresholds, without certifying repeatability, browser drawing, voice
latency or a speedup against the currently installed v1 prompt.

## Modular correction

`web_operation_predicate_scope.py` applies only when the existing capability
question policy is active. It asks the model to paraphrase the stated operation
without adding examples or converting control into execution. A finite source
inventory distinguishes execution, commands, external-command qualification and
shell vocabulary. English and Italian execution forms include `run`, `perform`
and `eseguire`, so an own source unit saying `perform network IO` still licenses
the existing Italian I/O paraphrase. A unit saying only `control subprocesses`
does not license an added execution, command or shell example.

The inventory belongs to the selected operation's own source unit. A command
documented in another unit cannot support a control-only unit. A command alone
does not establish external-command qualification or use of a shell. This is a
finite lexical guard, not complete predicate entailment or a negation verifier.
Vocabulary presence can occur in a negated or differently scoped statement; such
an answer still requires meaning review. Unrecognized synonyms and arbitrary
extra facts remain outside the guard's coverage.

The adapter leaves the native schema, evidence eligibility, source bytes,
numbering, original question and array bounds exactly unchanged from v7. It
keeps the original question last after metadata. CSV and missing-price questions
receive exactly the v7 messages and schema; the new capability instruction is
not applied to them. No answer is injected, repaired, shortened after generation,
dropped or re-anchored. A detected addition refuses the entire answer, preserves
raw model text and records `preOperationPredicateChecks` separately. That program
refusal is still a failed model test, not successful abstention.

## Validation and next evidence

The [local validation record](web-operation-predicate-validation-2026-10-06.json)
records 705 passing relevant tests, including 18 new regressions. They replay the
actual v7 expansion and preserve its original automatic acceptance; keep the
other five actual outcomes; distinguish control, execution, command qualification
and shell vocabulary; permit examples only when their vocabulary is in the own
source unit; verify per-unit ownership and the finite negation limitation; and
check all six unchanged schemas and questions. Mocked six-call runs keep an
added example or nonempty missing-answer response failed, without output repair.
An incomplete transport stops the series without further requests or retries.

Candidate: `own_operation_predicate_without_examples_v8`. The standalone probe
embeds all eleven v7 sources byte-for-byte and adds the operation adapter. All
reader/model-worker transport functions remain unchanged. Ollama 0.35.1, model,
temperature .4, 4096 context, 512 output tokens, the six balanced positions and
90-second native/95-second worker bounds remain fixed. Cache gates remain at
eight tokens maximum and 98% uncached input minimum. Both supported pairs still
require at least 10% reductions in uncached input and native prefill. The archived
full-context reference is not the currently installed v1 prompt.

Actual v8 outputs and times have now been measured and are recorded above. The
complete result remains failed; no prior times will be reused for v9. The 705 tests include the
previous pinned b11232 native-pattern conversion fixture, but no new native
pattern or full native schema converter/sampler is introduced or executed here.
Local program tests and mocked series are not a new Mac model run. Thermal
samples do not establish phase or causality and cause no exclusions or cooling
waits. Automatic integration remains disabled until all six actual new answers
have favorable meaning reviews and the original performance gates pass.

## Mac protocol and primary sources

Run the checksum-verified v8 standalone probe in **Controlli** with Ollama running
and no other model requests during the six calls. For read-only probes, leave the OpenJarvis window exactly as it is. Do not press
Command+R or Control+C. The probe uses Ollama directly and the verified reader
in an owned worker; no OpenJarvis server state change is required.
No files are installed and no personal notes are read. Wait for `Serie conclusa`
and the terminal prompt, then attach the new saved results file.

- [OpenJarvis structured-output tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_structured_output.py) were consulted for this task. They test native-format propagation and output structure; they do not establish source meaning.
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs) documents schema-constrained generation, prompt grounding and application validation. Its lower-temperature suggestion is not applied to this experiment; the original .4 setting remains fixed.

This defect remains the active task. No unrelated roadmap task is advanced and
no claim that the installed system or every future synthesis is perfect is made.
