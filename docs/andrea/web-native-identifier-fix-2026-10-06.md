# Generate required source identifiers instead of repairing a refused answer

Status: **not yet passed on the Mac; no production adoption**. Both submitted
v2 series fail the asyncio answer. Their original automatic reports and all
six raw answers are preserved in separate [series 1](web-networking-scope-v2-mac-series-1-2026-10-06.json)
and [series 2](web-networking-scope-v2-mac-series-2-2026-10-06.json) records.
The full terminal history is excluded. The earlier installed v1 check and
isolated success retain their original, distinct outcomes.

## Exact failure and observed latency

In both new compact answers, the first point says that asyncio performs
network operations and IPC but omits the I/O identifier in its own source:
`perform network IO and IPC;`. The unchanged guard refuses the entire answer
with `source_identifiers_not_preserved`, `missingIdentifiers: ["I/O"]`.
The remaining raw point is source-supported but is not removed or used to
turn the refused answer into a success.

The full-context reference's first point passes the old technical checks but
reports unqualified I/O rather than the source's narrower network I/O. Its
manual review is unfavorable. CSV's default and conditional float conversion,
and the genuine empty unsupported-price answers, are favorable in both
variants. Each series has four favorable and two unfavorable responses.

| Series | asyncio reference / compact client total | asyncio new-input / native-prefill reduction | CSV new-input / native-prefill reduction |
|---|---:|---:|---:|
| 1 | 46,702.181 / 33,980.198 ms | 19.713% / 24.896% | 65.971% / 69.987% |
| 2 | 44,117.287 / 31,656.726 ms | 19.665% / 20.252% | 65.943% / 69.261% |

All six transports complete and all native cache counts are eligible in both
series. Both supported pairs meet the original 10% input/prefill thresholds.
Their original overall automatic result remains `gates_not_met` because the
asyncio answer shape fails. Faster wrong output is unusable. These two runs
do not establish a statistical or universal speed improvement.

## Upfront native constraint

`web_native_identifier_schema.py` constructs a finite native JSON-schema
constraint before inference. An item's `oneOf` branches have disjoint own-
passage enums. Each branch's text pattern requires the unconditional source
identifiers for that passage, in any order. Patterns use anchored alternatives,
character classes and repetition; they have no unsupported lookaround,
backreferences or hard string length cap. The passage property precedes text.
`oneOf` has no sibling properties, avoiding the unsupported mixed form.

For a source explicitly saying `network IO`, the required I/O name keeps the
network qualifier: finite forms include `I/O di rete`, `IO in rete` and
`network IO`. Generic I/O or networking alone cannot satisfy that branch.
The native constraint cannot borrow an identifier from another point, another
passage or the page title. The compact input retains the v2 networking/rete
guidance so the separate networking catalogue is not rewritten as I/O.

Only identifiers already required unconditionally by the original source
policy are encoded. Multi-sentence passages remain eligible for faithful
partial facts. The source catalogue's conditional OS-signals identifier is
not made mandatory for a valid subprocess-only point. At most three mandatory
identifiers are encoded per branch (six orders); larger inventories are
reported as not natively encoded and retain the original application checks.
Equal patterns group only their own reference numbers.

After the unchanged application validation, a separate additive check verifies
the native pattern was actually observed. An engine that ignores its schema
cannot count as an effective constraint. This check preserves the original
application result in `originalApplicationChecks` and refuses the whole answer
without editing, dropping, merging or regenerating a point. Token-boundary,
type, condition, mechanism, signal-scope, heading and duplicate-rule checks
remain active. Presence alone does not establish meaning: token stuffing,
false statements or unsupported qualifiers still need the existing checks
and source review.

The grammar excludes raw quotes, backslashes and control characters in its
constrained text branches, consistent with the existing request for complete
plain sentences without quotations or citations. It is a bounded experiment,
not a universal paraphrase or semantic entailment system. The 320-character
application limit, complete-sentence rule and 512-token output budget stay
unchanged; no native `maxLength` is introduced.

## Pinned implementation research and verification

Ollama 0.35.1 pins llama.cpp **b11232** and forwards schema-format output to its
native `json_schema` path. The pinned converter supports the chosen simple
pattern constructs. Unsupported lookaround may instead fall back to an ordinary
string rule; merely supplying a JSON-schema pattern is insufficient evidence
of enforcement. JSON-schema restrictions are not themselves added to the
model prompt, so a short source-name instruction is also supplied.

603 relevant Python regressions pass, including 24 new tests. They replay the
two actual IO-omission failures unchanged, exclude the unqualified reference
claim, check own-reference branch selection, preserve conditional partial facts
and genuine abstention, verify one schema delivery with unchanged model options,
and run the balanced series with both success and deliberately ignored-native-
constraint responses. The latter keeps the original acceptance visible while
the additive failure closes the case gate.

The tests compile exact, attributed C++ excerpts of b11232's pattern converter
and its helpers, then convert every pattern in both variant fixtures. A known
unsupported lookahead is exposed as a failure. MIT license and excerpt/source
checksums are recorded with the fixture. **This harness tests pattern conversion
only; it does not execute the full JSON-schema converter, sampler or model.**
Actual decoding and latency remain to be measured on the Mac. See
[validation](web-native-identifier-validation-2026-10-06.json).

## One isolated six-request comparison

Candidate revision: `own_passage_native_identifier_v3`.
`web_native_identifier_probe.py` embeds the original baseline, resource,
definition-context, single-rule-budget and v2 networking sources exactly,
plus the new native adapter. Installed v1 file fingerprints stay fixed.
No updater or live import is added.

Both variants receive the same new native identifier policy, so the timing
comparison includes its decoding cost on both sides. The `production` label
is retained only for the original balanced protocol: its full-context base
preparation is archived from before API integration, **not current installed
v1**. Its messages and schema may receive the explicitly reported common
native policy. This is a new comparison, not a relabelled or byte-identical
old reference run. Neither v2 timings nor v2 model answers are reused.

Original questions, reader source snapshots, numbering, balanced call order,
native model options, array budgets `[2,2,1,2,2,2]`, 90-second native and
95-second owned-worker deadlines, 8-token maximum cache allowance, 98% minimum
uncached input and 10% input/prefill thresholds remain fixed. Every generated
point still needs semantic review. An empty asyncio answer fails its two-point
case; unsupported price succeeds only through genuine model abstention. No
automatic report authorizes adoption.

The probe reads only two public documentation pages. It does not install code,
read personal notes, change configuration or dependencies, warm up/unload the
model, retry, alter thermal settings or wait for cooling. Small thermal reads
do not prove inference phase or causality. Browser rendering is unmeasured.

For this read-only experiment, leave **OpenJarvis** running. Execute the pinned
download/hash/run block in **Controlli**. Do not press Control+C in OpenJarvis.
Wait for `Serie conclusa` and the normal `%` prompt, then supply the output.
This workspace cannot control the Mac's native Terminal. Other tasks remain
paused until this defect is resolved and the installed path is verified.

## Primary sources consulted for this development task

- [OpenJarvis structured-output tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_structured_output.py): request-boundary schema propagation, not proof of source meaning.
- [Ollama 0.35.1 native version pin](https://github.com/ollama/ollama/blob/v0.35.1/LLAMA_CPP_VERSION) and [schema forwarding](https://github.com/ollama/ollama/blob/v0.35.1/llm/llama_server.go).
- [b11232 JSON-schema converter](https://github.com/ggml-org/llama.cpp/blob/b11232/common/json-schema-to-grammar.cpp), [converter tests](https://github.com/ggml-org/llama.cpp/blob/b11232/tests/test-json-schema-to-grammar.cpp) and [grammar guide](https://github.com/ggml-org/llama.cpp/blob/b11232/grammars/README.md): supported patterns, oneOf limitations, skipped features and grammar/prompt separation.
- [Pinned grammar parser](https://github.com/ggml-org/llama.cpp/blob/b11232/src/llama-grammar.cpp): supported hex and Unicode escapes in grammar character classes.

No blanket guarantee of perfect future model answers is claimed.
