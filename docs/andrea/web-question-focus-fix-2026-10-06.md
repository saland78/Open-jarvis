# Keep the actual question separate from source-format instructions

Status: **v7 prepared for a new Mac comparison; no installation**.

The submitted v6 run completes six transports. Its original input and native
prefill performance thresholds pass for both supported pairs. Five whole-answer
meaning reviews are favorable; the compact absent-price answer is unfavorable.
The [complete v6 record](web-capability-scope-v6-mac-2026-10-06.json) preserves every
raw model answer, the original automatic report, and separate manual reviews.
The result is `not_passed_no_adoption`, not six passing synthesis tests.

## Concrete remaining failure

The last question asks for the monthly subscription price of Zefiro according
to a CSV documentation excerpt. That excerpt supplies no Zefiro price. The
compact model returns two unrelated CSV statements instead of its own empty
`claims` array. Its second statement also changes the documented converted type
from floats to decimal numbers. The original type check correctly refuses the
whole answer. That refusal is not a successful model abstention.

The reference absent-price answer is the model's own `{"claims":[]}`. Both asyncio
answers supply two operations; both CSV answers preserve the default conversion
rule, exception and converted-field qualification. These five favorable reviews
do not make the failed sixth answer favorable. No result is dropped or relabelled.

The supported asyncio totals are approximately 57.7 seconds for the archived
reference and 39.0 seconds for the compact path; CSV totals are 62.2 and 25.2
seconds. Their uncached-input reductions are 16.743% and 62.630%; native prefill
reductions are 26.748% and 67.746%. These observed pairs pass the original 10%
thresholds. They do not measure browser rendering, voice latency, statistical
repeatability or a speedup against the currently installed v1 prompt. The overall
automatic `gates_not_met` result, including the failed case shape, is preserved.

## Observed prompt conflict and modular correction

The v6 system message unconditionally says to describe capabilities. This applies
even when the actual question asks for a price. Its user JSON also places format
metadata after the question. These are observed prompt features and plausible
contributors to the off-topic answer; this experiment has not proven either is
the sole cause.

`web_question_focus.py` replaces only that capability instruction's opening with
a question-neutral instruction, then puts the unchanged original question last
after all source metadata. It adds an explicit requirement to answer that question
and to generate an empty claims array when the requested information is unsupported.
Both roles remain `system` and `user`; no third message, duplicated question or
invented source fact is inserted. Existing source bytes, selected references,
metadata values and native schema remain unchanged.

Names explicitly introduced by contextual nouns such as service, project or
product are copied from the user question into `requestedSubjects`, as names
rather than evidence. They are not taken from a case-specific answer table.
A narrow post-generation guard refuses an otherwise accepted nonempty answer
when such a name is absent from every actually supplied source passage. It never
changes an answer into `abstained`. Raw text and the preceding check remain in the
report; a separate relevance diagnostic can identify this issue even when an
earlier type check already refuses the answer.

This name guard is lexical and finite. It does not resolve aliases or certify
general answerability, relevance, prices or entailment. A name appearing in a
source does not prove that the requested price appears there. The model still
must produce its own abstention and every output still requires meaning review.
No schema branch forces `claims:[]`; nonempty branches remain available for the
absent-price question. No repair, dropped claim, injected empty output, extra
model call, automatic retry or timeout increase is used to obtain a passing test.

## Validation and unchanged experimental bounds

The [local validation record](web-question-focus-validation-2026-10-06.json)
records 687 passing relevant tests, including 18 new regressions. They preserve
the six real v6 outputs and original decisions, reject a true but unrelated answer
without relabelling it as abstention, preserve genuine model abstention, check all
six question positions and unchanged payload values, and verify unchanged native
schema and source alignment. Mocked six-call and timeout paths confirm that a
wrong missing-answer case keeps the whole series failed and that an incomplete
transport stops without a retry. These are program tests, not a new Mac model run.

Candidate: `question_last_and_named_subject_scope_v7`. The standalone probe embeds
all ten v6 sources byte-for-byte and adds only the question-focus adapter. The
original three questions and balanced six positions remain unchanged, as do
source readers and model workers, Ollama 0.35.1, temperature .4, 4096 context,
512 output tokens, the 90-second native/95-second worker bounds and array maxima
`[2,2,1,2,2,2]`. Both variants receive the question-focus change. The reference is
explicitly the archived full-context base, not the currently installed v1 prompt.

The cache bounds remain at most eight cached tokens and at least 98% uncached
input. Both supported pairs must reduce uncached input and native prefill by at
least 10%. The new run must capture new source snapshots, all six actual model
answers and new timings. No v6 answer or timing is reused as a v7 measurement.
Thermal samples do not prove a phase or cause and do not justify exclusions,
cooling waits or model changes. Automatic integration remains disabled.

## Running on the Mac

Run the checksum-verified v7 standalone probe in **Controlli**, with Ollama
running and no other model requests during the six calls. It uses Ollama directly
and the verified project reader in an owned worker. The OpenJarvis server is not
required and may remain stopped. No files are installed and no personal notes
are read. Wait for `Serie conclusa` and the terminal prompt, then attach the new
saved results file.

## Primary sources consulted for this development task

- [OpenJarvis structured-output tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_structured_output.py): response-format propagation and JSON checks are distinct from source meaning.
- [OpenJarvis prompt-builder tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/prompt/test_system_prompt_builder_few_shot.py): prompt construction is tested explicitly; these tests do not establish this candidate's meaning quality.
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs): schema constraints and prompt grounding support explicit application validation, without guaranteeing a correct substantive answer.

The next evidence required is all six new Mac answers satisfying their original
meaning criteria and the unchanged performance thresholds. This defect remains
the active task; unrelated roadmap work is paused.
