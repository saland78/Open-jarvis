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
