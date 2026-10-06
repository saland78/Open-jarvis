# Operation evidence and own-source performance vocabulary

Status: **v6 prepared for a new Mac comparison; no installation**.

The submitted v5 series completes all six transports. All six original technical
case shapes pass and both uncached-input/native-prefill pairs meet the original
10% thresholds. These automatic results are preserved, without changing their
`pending_review` meaning verdict, in the
[complete v5 record](web-source-label-scope-v5-mac-2026-10-06.json).

## Two remaining meaning problems

The original question asks for two functionalities of asyncio. Both v5 variants
choose the statement `often a perfect fit` as their first point. The frequency
is now preserved, but suitability is not an additional functionality. Their
second point describes an operation; neither answer supplies two operations.
The reference's claims are individually faithful to their passages, but its
answer is incomplete against the question.

The compact second point adds `gestione efficiente di connessioni` to its own
passage, `perform network IO and IPC;`. That passage does not document efficiency
or connection management. The separate efficient-protocol passage cannot support
this point. Correct literal I/O/IPC labels do not establish the free predicate's
meaning. The original technical acceptance of this raw point is preserved.

Both CSV variants preserve the default no-automatic-conversion rule, the
`QUOTE_NONNUMERIC` exception, unquoted-field qualification and float conversion.
Both absent-price variants return the model's own empty `claims` array. Their
meaning reviews are favorable. Thus v5 has **four favorable and two unfavorable
whole-answer meaning reviews**, separately from six passing technical case
shapes. Its overall result is `not_passed_no_adoption`.

## Separate modular corrections

`web_capability_evidence.py` recognizes a capability question and a finite set
of action-led documentation units. If at least two such statements are present,
only their existing references are eligible in the native `passage` branches.
Suitability, benefits and headings remain context rather than operation evidence.
All source bytes, numbering and selected input units remain unchanged. The
eligibility change is reported explicitly for both comparison variants; it is
not a claim that the archived prompt is unchanged. Existing literal source-label
constraints are retained on eligible operations, with unused metadata removed.

This recognizer covers the observed English documentation action forms, not
every language or arbitrary prose. When insufficient matching action evidence
is present, it does not force an answer. The original empty-array path and native
minimum remain available. A post-generation check refuses an answer that selects
an ineligible suitability point; there is no point dropping or re-anchoring.

`web_source_performance_scope.py` keeps four finite vocabulary families separate:
efficiency, speed, high performance and low latency. Its prompt inventory is
derived from each own source unit. Supporting an operation does not license an
efficiency claim; efficient protocols in another unit do not license efficient
network connections here. An added family absent from the selected own quote
refuses the whole response, retaining the offending raw text for diagnosis.

This is a narrow lexical guard, not general semantic entailment. A source term
and output term can be identical while their negations, conditions, targets or
meaning differ. Such output still requires source review. No new native word-ban
regex, constrained hard string cap, second model call, repair, retry or synthetic
answer replaces the model's generated predicate. `preCapabilityPerformanceChecks`
retains the preceding result separately from the new checks.

## Validation and unchanged experiment bounds

The [local validation record](web-capability-scope-validation-2026-10-06.json)
includes 23 new regressions. They replay the exact v5 efficiency addition and
suitability references, retain both original automatic and meaning outcomes,
test own-source vocabulary ownership, preserve valid efficiency when that own
unit documents it, keep CSV conditions/types and genuine abstention, verify
source-byte preservation and operation-only native eligibility, and exercise
six balanced mocked calls and incomplete-transport shutdown.

The prior native patterns remain unchanged and the pinned b11232 pattern
conversion tests are included in the relevant suite. No full native schema
converter, sampler or new Mac inference has run in the scratch environment.
The first broad scratch run omitted the existing OpenJarvis package from
`PYTHONPATH`; its import error is recorded, and the rerun uses the existing
upstream source path without dependency installation.

Candidate: `capability_evidence_and_performance_scope_v6`. The standalone probe
embeds all eight v5 sources byte-for-byte and adds the two adapters. The original
three questions, six balanced positions, original source reader and workers,
Ollama 0.35.1, model, temperature .4, 4096 context, 512 output-token budget,
90-second native/95-second worker bounds and array maxima `[2,2,1,2,2,2]` remain
unchanged. Source snapshots are recorded again rather than substituted from v5.

Both variants receive the new operation eligibility and own-source vocabulary
instructions. The reference retains the archived full-context base preparation;
it is explicitly **not** the current installed v1 prompt. The compact path retains
the API-context selector and shorter base instructions. New prompt/schema hashes
make the changes attributable. No v5 response or timing is reused as a v6 output.

Cache bounds stay at at most eight cached tokens and at least 98% uncached input.
The supported asyncio/CSV pairs must each reduce uncached input and native
prefill by at least 10%. Thermal observations cannot prove a phase or causality
and do not cause exclusions, cooling waits or option changes. Every actual new
answer must pass its original meaning criteria. Browser rendering, voice
end-to-end latency and a comparison to the currently installed prompt remain
unmeasured. Automatic integration remains disabled.

## Running on the Mac

Run the checksum-verified v6 standalone probe in **Controlli**, with Ollama
running. This probe uses the Ollama API directly and the verified project reader
in an owned worker; it does not need the OpenJarvis server. OpenJarvis may remain
stopped. Avoid other model requests during the six calls. The probe does not
install files or read personal notes. Wait for `Serie conclusa` and the terminal
prompt, then attach the new saved results.

## Primary sources consulted for this task

- [OpenJarvis structured-output tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_structured_output.py): response-format propagation and JSON structure checks do not certify source meaning.
- [Python asyncio documentation](https://docs.python.org/3/library/asyncio.html): suitability, network I/O/IPC operations and efficient-protocol implementation are separate source statements.
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs): schema-constrained generation and prompt grounding; application validation remains explicit.

This defect remains the active task; unrelated roadmap work is paused. The v6
code is a tested candidate awaiting actual outputs, not a declaration that the
installed system or every future synthesis is perfect.
