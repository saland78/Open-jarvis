# CPU batch experiment against the installed compact-v9 contract

The installed v9 acceptance has favorable manual review for all three cases.
It remains the production baseline. Its client summary times are 54.104 s for
asyncio, 25.986 s for CSV conversion and 42.160 s for an undocumented price.
Native context evaluation is respectively 35.992, 17.300 and 41.396 seconds;
validation is below 8 milliseconds. The earlier thread experiment did not meet
its speed gate, so automatic thread selection is retained.

A prior contemporaneous resource profile showed CPU speed limits declining to
62–64 with the selected model on CPU and no observed swapping. This does not
prove the cause of the latest acceptance timings or a thermal benefit from a
smaller batch. Batch size is the new hypothesis; another prompt rewrite and a
new model are outside this experiment.

## Primary sources checked for this task

- [Upstream OpenJarvis Ollama tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_ollama.py)
  and [structured-output tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_structured_output.py):
  transport completion and forwarding an actual schema are distinct from meaning.
- [Ollama 0.35.1 options](https://github.com/ollama/ollama/blob/v0.35.1/api/types.go)
  defines default NumBatch 512 and automatic NumThread 0.
- [Ollama 0.35.1 runner](https://github.com/ollama/ollama/blob/v0.35.1/llm/llama_server.go)
  forwards a positive NumBatch to both logical batch (-b) and microbatch (-ub).
  This confirms the request option is implemented, not that 128 is faster.
- [Ollama chat API](https://docs.ollama.com/api/chat) and [FAQ](https://docs.ollama.com/faq):
  options are per request, keep-alive controls residency, and loading a model
  does not certify prompt cache reuse or completion of a disconnected request.

## One finite comparison, no installation

`web_cpu_batch_probe.py` verifies the published installed checker and its 24
fingerprints before importing the production pipeline. It requires macOS and
Ollama 0.35.1. Two public documentation pages are read via the OpenJarvis API;
no search provider, vault, memory, conversation or personal configuration is
read. A missing CSV conversion condition stops before inference. Unknown loaded
state, another model or an already loaded non-CPU model also refuses early.
Post-request residency must describe the expected CPU model for eligibility.
This metadata does not confirm effective batch size or every inference phase.

The three original acceptance questions are unchanged. The six-call order is
asyncio 512/128, CSV 128/512, missing price 512/128. There is no retry, warm-up,
unload or cache-slot manipulation. Both use the current compact-v9 preparation,
source selection, byte-exact quotes, native JSON schema and all validators.
Only options.num_batch differs. Model, temperature 0.4, context 4096, output
cap 512, think=false, keep-alive 15m and automatic threads are held constant.
A same-length random diagnostic marker is prepended to each system message to
prevent a cached prompt from masquerading as faster CPU context evaluation.
The marker is not a source fact or a production change. All original rules,
roles and user bytes remain. Its token count can vary slightly; both raw
prefill duration and cost per uncached token are compared. Prompt/schema/source
hashes before the marker must match within each pair.

The standalone model calls go directly to local Ollama: the installed engine
currently does not forward num_batch. They bypass the server's busy guard, so
OpenJarvis must stay running but idle, with no other Ollama requests during the
collection. Successful results are not installed-server or browser measurements.
API reads are in owned workers with a 35-second whole-process deadline; metadata
reads have 12 seconds. A model worker has a 95-second whole-process deadline,
including its post-request metadata read, so even a stalled or dribbling stream
is bounded. A failure or incomplete transport stops the series without retry.
Timeout or Control+C kills only an owned diagnostic child and closes its socket,
never an existing Jarvis/Ollama process. Server-side cancellation is not certified.
Small fixed pmset queries at 6/18/36 seconds record only numerical reported CPU
limits, not temperatures. Each read has a 1.5-second deadline; missing data stay
unknown. Their windows do not establish the native-prefill phase or causality.

The experiment does not write project files, settings, model files or global
variables. Its requested batch can reload the shared runner or remain in that
runner after a request. The next ordinary app request uses ordinary options;
no extra reset inference is made. A report is saved by the user's tee command.

## Predeclared gates and truthful results

A pair is eligible only if transport completed with stop, CPU residency is
observed, native counters are known, cached tokens are at most 8 per request,
and the two/one/zero original case shapes hold. An empty answer cannot pass a
positive case. A failed claim is retained diagnostically; the entire answer is
refused, without editing or dropping points.

Both positive cases must reduce raw context evaluation time AND cost per
uncached token by at least 10%. All three cases must avoid a client total-time
regression above 5%. Total includes model loading and output generation, not
just prefill. It excludes public page reading, observer startup, post-request
metadata and browser rendering. These are new batch-experiment gates; archived
prompt-comparison gates and their failed results are unchanged.

Even a numeric pass has integrationAllowed=false and qualityVerdict=pending_review.
Every one of the six actual answers must receive favorable meaning review before
an installed-server validation. No automatic adoption, retry until favorable,
forced empty output or universal latency claim is made. Cache contamination,
unknown counters, changed input, missing cases, wrong order or total regressions
prevent adoption. The fixed small sample and unforced resource/load state do not
establish statistical significance or a causal CPU/thermal effect.

## Development validation and next collection

30 new deterministic checks cover exact request/schema/source preservation,
unchanged complete-answer validation, genuine model abstention, stream and
whole-worker deadlines, partial/length/extra frames, duplicate keys, byte bounds,
CPU/cache eligibility, both positive speed gates, total regression, partial
series, truthful review flags, fixed six-call orchestration, source/version and
symlink refusal, and unknown thermal data. Together with the existing live v9
pipeline, integration and installer checks, **58 tests pass**. All 24 installed
fingerprints are independently verified in the development mirror. No actual
Mac inference or measured batch speedup is claimed from those tests.

The next step is exactly one six-call Mac collection. If it fails these gates,
128 is not adopted and this finite experiment is closed as unsuccessful. The
latency objective stays open; the failed experiment is not rerun merely to obtain
favorable numbers. The installed v9 acceptance remains passed.
