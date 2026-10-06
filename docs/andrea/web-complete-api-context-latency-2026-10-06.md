# First-request latency: complete API entries and shorter instructions

Status: isolated implementation tested; Mac A/B results pending. No installation
or successful latency claim. The installed contract and original failed
performance reports retain their original verdicts.

## Evidence motivating the change

The single unchanged CSV request collected on the Mac completed in 57695.697 ms
client time. Ollama 0.35.1 reported 4821.433 ms loading, 39744.500 ms context
evaluation, and 13090.141 ms generation. All 2440 input tokens were uncached;
uncached input throughput was 61.392 tokens/s. Reading the source cost 796.830 ms.
These durations use different scopes and clocks; they are not added together.

The reported CPU speed limit was 100 before the request and in the approximately
6-second sample, 64 in the 18-second sample, and 62 in the 36-second sample. Those
windows were inside the request and before the first JSON arrival. They are not
proven native-prefill-only intervals. The expected model was loaded during the
samples with size_vram=0 and context_length=4096. Swap usage and the measured swap
counter deltas were zero. This supports reducing inference work; it does not
prove the temperature, actual CPU frequency, exact performance impact, or the
cause of earlier A/B variation. A reported limit of 62 is not an established
38% reduction in actual clock speed.

The CPU interval query timed out during all three observations. The legacy
runner process query did not find the current runner. The observed near-zero
CPU percentages belong to the detected server process, not proof of idle
inference or the effective thread/batch settings. Those missing measurements
remain unknown. The next comparison does not repeat the expensive top scan;
it collects only small, bounded `pmset -g therm` observations.

The CSV answer preserves the default string result, absent automatic conversion,
the QUOTE_NONNUMERIC exception, unquoted field scope, and float result type.
Manual source comparison is favorable for this single response. This does not
close the six-case quality/performance gate or test browser rendering.

## Concrete optimization

The candidate changes two model-input components explicitly:

1. It reduces the general instruction text to 772 characters, including the
   mechanism instruction, versus 1239 in the preceding English candidate.
   This is a character measurement, not a measured model-token reduction.
2. For a question naming a qualified API such as `csv.reader`, it sends complete
   matching HTML definition entries instead of the entire 6000-character page
   extract. General or unmatched questions keep the full extracted context.

The reader captures `dl` entry ownership and `dt` API identifiers alongside the
unchanged installed HTML extraction. Main-content choice, hidden/navigation
exclusions, Unicode, whitespace normalization, code lines, source cap, and
heading provenance retain their existing behavior. Entry ranges must align
exactly with the original extracted text. Only explicitly closed entries whose
whole content fits inside the extracted source can narrow the prompt.

All entries matching every named API are retained, including repeated entries
that could carry a later qualification or conflict. Nested entry text remains
in its parent. Relevant preceding headings stay as context; headings cannot
be chosen as independent evidence. Original passage numbers and source bytes
do not change. No condition is clipped to fit the 3500-character entry budget:
oversized, mixed, incomplete, unmatched or unaligned entries use full context
or fail preflight. There is no top-k paraphrase selection or additional model
call. A broad page summary always keeps the whole bounded extract.

This is a scope change, not lossless compression of the model input. The entire
original snapshot stays in the audit bank, while the report explicitly records
`fullSourceSuppliedToModel`, selected original references, matched identifiers,
source/model character counts, omitted characters, and the reason for fallback.
The model is instructed that selected API entries are not the whole page.
Module-wide context or external linked documentation is not automatically
included in a narrowed entry. Quality review must assess whether the selected
scope is sufficient for the original question; missing support never becomes
proof of absence from the whole page or an external system.

## Checks and unchanged comparison protocol

`web_definition_context.py` is independently testable. The one-file Mac runner
embeds its exact source plus the already reviewed baseline and resource reader.
Each payload is preflighted before inference. The installed baseline bank,
question, prompt and schema are unchanged except for the existing diagnostic
nonce used to prevent prefix-cache reuse.

Both variants keep the existing source-anchored heading, identifier, condition,
unquoted-field, float-type, number and complete-sentence checks. Both also reject
the observed added interface in the bare `control subprocesses;` source unit.
The candidate additionally refuses a reference to a passage not actually
supplied to the model. Raw rejected answers are retained diagnostically and
are never shortened, repaired or re-anchored. These finite checks are not a
general entailment classifier; all six answers require semantic review.

The three original questions and balanced six-call order remain:
asyncio installed/compact, CSV compact/installed, missing price installed/compact.
The sources are read once each and shared unchanged across each pair. The CSV
candidate must prove a complete definition containing the original conversion
condition before any model inference starts. Same model, temperature 0.4,
num_ctx=4096, num_predict=512, think=false, keep_alive=15m, and 90-second stream
deadline. An owned child enforces a 95-second whole-process bound per request.
Only owned test children are terminated on timeout/interruption. A closed client
does not certify immediate cancellation of Ollama's server work.

The original gates stay unchanged: cached tokens at most 8, uncached fraction at
least 98%, and at least 10% fewer uncached input tokens and 10% less native
prefill time in **each** supported pair. All six requests must complete and meet
their original case shapes. Missing-price abstention still requires inference
and a genuinely empty claims array; no keyword shortcut replaces that case.

No warm-up, model unload, cooling wait, repeated generation, thermal-based row
exclusion, changed benchmark question, global option change, private vault read,
or automatic installation occurs. Thermal readings remain diagnostic; low
limits do not cause an unfavorable result to be dropped. First JSON is not
accepted or painted UI text. No universal/statistical speed claim follows from
this finite comparison. Ollama version must remain 0.35.1 throughout.

490 relevant program regressions passed, including 24 new selector/protocol
tests, previous observed failures, complete exception-tail retention, the 6000
cap, nested and duplicate entries, hidden/malformed definitions, full-context
fallback, omitted-reference rejection, exact bundled-source parity, owned child
cleanup, and the unchanged six-request gate. Test fixtures/mock timings do not
measure Mac model latency. Actual Mac answers and native metrics remain pending.

## Upstream and primary sources consulted for this task

- [OpenJarvis context implementation](https://github.com/open-jarvis/OpenJarvis/blob/main/src/openjarvis/tools/storage/context.py)
  and [context tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/memory/test_context.py):
  bounded context selection, whole retrieved results and source attribution.
- [OpenJarvis chunking](https://github.com/open-jarvis/OpenJarvis/blob/main/src/openjarvis/tools/storage/chunking.py)
  and [retrieval quality tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/memory/test_retrieval_quality.py):
  preserve source tails and evaluate retrieval against a fixed corpus. The local
  selector keeps exact source bytes rather than reconstructing whitespace tokens.
- [OpenJarvis Ollama tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_ollama.py)
  and [engine](https://github.com/open-jarvis/OpenJarvis/blob/main/src/openjarvis/engine/ollama.py):
  bounded streaming, applied timeouts and mid-stream disconnect behavior.
- [CPython CSV documentation source](https://github.com/python/cpython/blob/3.14/Doc/library/csv.rst):
  the complete reader entry includes the default rule, exception and field type.
- [Ollama API usage](https://docs.ollama.com/api/usage),
  [model placement FAQ](https://docs.ollama.com/faq),
  [Apple temperature guidance](https://support.apple.com/en-us/102336), and
  [Apple pmset manual](https://github.com/apple-oss-distributions/PowerManagement/blob/main/pmset/pmset.1):
  distinguish context evaluation from loading/generation, model placement from
  process utilization, and CPU limits from a measured temperature or frequency.

The upstream context budgeting/provenance pattern is adapted to a bounded web
snapshot. No private memory ingestion or dependency installation is introduced.
