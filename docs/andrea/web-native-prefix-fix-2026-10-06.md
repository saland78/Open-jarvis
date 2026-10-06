# Remove the unbounded path before mandatory source names

Status: **not yet passed on the Mac; no installation**. The submitted v3 run
attempts two of six requests. One reference transport completes with two
source-faithful points. The compact transport times out after 90,117.091 ms
and the remaining four requests are not executed. All original raw diagnostics
and automatic outcomes are retained in the [interrupted Mac report](web-native-identifier-v3-interrupted-mac-2026-10-06.json).
The full submitted terminal history is excluded.

## The observed problem is a deferred grammar obligation

The reference preserves both network I/O/IPC and subprocess control. Its
client total is 46,986.12 ms, first content 38,251.174 ms, and native prefill
30,296.678 ms. That favorable response does not certify the other variant.

The compact response starts sending content after 25,995.896 ms but omits
I/O in the text selected from `perform network IO and IPC;`. The native
pattern cannot permit that string's normal ASCII closing quote before the
missing identifier. It nevertheless permits arbitrary other characters
before the mandatory I/O. The model emits a curly quote, pseudo-JSON using
single quotes and repeated markdown-like punctuation, still inside the first
JSON string. It never completes the stream before the unchanged 90-second
deadline. The diagnostic is **not an accepted or complete answer**.

This is demonstrated with a concrete completion witness: take all 768
characters after the actual first `text` opening delimiter, then append
` I/O di rete IPC`. The v3 pattern accepts that hypothetical string value.
There can be arbitrarily more punctuation before those identifiers; the
grammar keeps a future completion possible while postponing the required
names. The witness is solely a language/grammar test and is never returned
as a repaired answer. It also exceeds the unchanged application length
limit and would remain unusable.

No native completion metrics exist for the compact request. Its prefill
reduction, input/cache eligibility and the six-request latency comparison
are inconclusive. Read-only thermal observations show changing CPU limits
but do not establish the cause of the repetitive path or a causal latency
effect. The old automatic field `completed: 2` counts collected rows; the
review explicitly distinguishes two attempts from one completed transport.

## Finite names first, then the model's predicate

The separate `web_native_identifier_prefix.py` adapter replaces only the
experimental native text pattern and its matching guidance. Every constrained
point must start with its own source names, in a fixed order, followed by a
colon and the model's paraphrased predicate. The network-I/O/IPC unit uses
`I/O di rete e IPC: `. Generic IO units use `I/O: `; other required uppercase
names retain their spelling. These labels are derived from the source
inventory, **not model-generated predicates or full answers**.

The matching own-reference `requiredStarts` inventory is explicitly supplied
to the model because the schema alone is not injected into the prompt.
The native pattern has no wildcard before or between the compulsory names.
Free text comes only after the finite literal label. A final period follows
the already existing complete-sentence requirement. There is no new native
hard string-length cap, token-budget reduction, temperature change or longer
timeout. A normal closing quote is available once the body ends with a period;
completion cannot depend on inserting a missing source name later.

The actual wrong prefix, even followed by its former completion witness, is
not a prefix of a value allowed by this new literal-start rule. That removes
the observed deferral path. **It does not guarantee every future generation
will complete or mean the right thing.** The free predicate can still be wrong
or incomplete and remains subject to the original source checks and review.

Own-source branches, original eligible reference numbers, source bytes,
conditional identifier policy, allowed subprocess-only partial facts,
single-CSV-rule limit and genuine empty-price abstention are preserved. No
names are forced into a passage where the previous policy had no unconditional
requirements. Conditional OS names are not borrowed from the neighboring
signals item. The name-order and label-format restrictions are explicitly
reported changes, not claimed to be unrestricted free-prose synthesis.

The frozen v3 source validator still validates every generated point. Its
additional native-promise check uses the new pattern after the unchanged
application checks. A correct label does not license a wrong predicate or
an identifier from another source. Whole-answer refusals are retained. No
generated point is rewritten, shortened, dropped, merged or retried.

## Verification and the next isolated comparison

619 relevant Python regressions pass, including 16 new cases. The new tests
preserve the actual incomplete run, construct the old-pattern deferral witness,
exclude it from the new rule, compile all actual source-prefix inventories
with the exact pinned b11232 pattern-converter excerpts, check complete valid
source predicates and refusal of unsupported identifiers, and verify unchanged
request options, questions, source fingerprints and deadlines.

The C++ output places the entire literal prefix before the first repeated
character class. The original native pattern fixture and MIT provenance remain
unchanged. This tests the exact pattern converter, **not the full schema
converter, native sampler or new Mac inference**. See [validation](web-native-prefix-validation-2026-10-06.json).

Mocked balanced comparisons retain the original array budgets `[2,2,1,2,2,2]`,
pending semantic review and prohibition on automatic adoption. A mocked replay
of the actual timeout stops after its second attempt, does not execute the
remaining four calls and separately reports attempts, completed transports
and not-executed requests. Historical automatic reports are not relabelled.

Candidate revision: `own_passage_identifier_prefix_v4`.
`web_native_prefix_probe.py` embeds all six previous sources exactly and adds
the tested prefix adapter. It fingerprints the same installed v1 project.
Both full-context archived reference and compact candidate use the new prefix
policy; neither is relabelled as the current installed prompt. This is a new
comparison with new model answers and measurements, not reused v3 timing.

The same six balanced positions, original three questions, source snapshots,
90-second native/95-second worker bounds, original model options, maximum eight
cached tokens, minimum 98% uncached input and minimum 10% input/prefill reduction
per supported pair remain fixed. All six outputs require source review. A
valid JSON stream or copied label is insufficient. No automatic report allows
adoption. Browser paint and end-to-end voice latency remain unmeasured.

This read-only probe reads two public documentation pages and no personal
notes. It installs no code or dependencies, changes no configuration, has no
retry/warm-up/unload/cooling step and modifies no thermal settings. Leave the
**OpenJarvis** Terminal running; execute the verified block in **Controlli**.
Do not press Control+C in OpenJarvis. Wait for `Serie conclusa` and `%` before
providing the result file. Other tasks remain paused until this defect and
the eventual installed path are verified.

## Primary sources consulted for this task

- [OpenJarvis structured-output tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_structured_output.py): schema propagation at the request boundary, not semantic truth.
- [Pinned llama.cpp grammar guide](https://github.com/ggml-org/llama.cpp/blob/b11232/grammars/README.md): repetition constructs, performance caveats, schema/prompt separation and unsupported schema features.
- [Pinned native grammar implementation](https://github.com/ggml-org/llama.cpp/blob/b11232/src/llama-grammar.cpp): valid grammar prefixes, repetition paths and completion handling.
- [Pinned pattern converter](https://github.com/ggml-org/llama.cpp/blob/b11232/common/json-schema-to-grammar.cpp): literal prefix followed by the chosen simple character-class repetition.

## Subsequent actual v4 Mac evidence

The latest complete v4 run now finishes all six transports without timeout.
Both original input/native-prefill pair thresholds and cache eligibility pass,
but its overall report remains `gates_not_met`: the compact asyncio point
borrows a foreign `I/O:` label and the compact CSV point is refused for `CSV`
despite its own literal `csv file` source. The reference also drops `often`
from its perfection statement during meaning review. All raw checks and
outputs are retained in the [complete report](web-native-prefix-v4-mac-2026-10-06.json).
A separate earlier interrupted v4 attempt is preserved without inventing
missing request-five metrics. No installation was made. The next isolated
[source-label correction](web-source-label-scope-fix-2026-10-06.md) retains
the original questions and performance thresholds; its new Mac run is pending.
