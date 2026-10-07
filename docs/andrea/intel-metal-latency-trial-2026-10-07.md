# Intel Mac: isolated Metal backend trial

The latency task remains open. The completed batch and static-prompt comparisons
did not satisfy their adoption criteria. The hardware inventory now establishes
that Andrea's Intel Mac has an AMD Radeon Pro 5500M with 4 GB reported video
memory. Those trials used Ollama 0.35.1 with `size_vram: 0`. A usable AMD Metal
backend is the next intervention. Native GPU initialization is now confirmed,
but the first GPU request failed with a driver timeout. A complete GPU answer,
its quality and its latency have not yet been measured on this Mac.

## Observed Mac initialization and diagnostic correction

The first submitted command failed with `owned_worker_failed` before compilation.
The subsequent run compiled the pinned server, exposed the Radeon through its
native device list, and loaded the existing model. Its server log reports
`verbosity = 3`, followed by model readiness. The trial then stopped with
`effective_radeon_offload_not_proven_no_inference`, before any of the six model
requests. No CPU/Metal timing comparison was collected, and no GPU model
allocation can be inferred from that short log. The installed app was unchanged.

The trial had a logging defect. In the exact pinned source, the
[library callback](https://github.com/ggml-org/llama.cpp/blob/4d756bc72bf00a4aacf410ae15a2d315f3db400d/common/log.cpp)
maps library INFO messages to trace verbosity. The
[definitions](https://github.com/ggml-org/llama.cpp/blob/4d756bc72bf00a4aacf410ae15a2d315f3db400d/common/log.h)
set trace to 4 and the application default to 3. The
[CLI](https://github.com/ggml-org/llama.cpp/blob/4d756bc72bf00a4aacf410ae15a2d315f3db400d/common/arg.cpp)
supports `--log-verbosity`. Consequently the default suppressed the native
device, layer-offload and model-allocation lines required by the trial's guard.
The corrected trial explicitly requests verbosity 4, rather than weakening the
GPU evidence requirement.

The pinned
[Metal allocation implementation](https://github.com/ggml-org/llama.cpp/blob/4d756bc72bf00a4aacf410ae15a2d315f3db400d/ggml/src/ggml-metal/ggml-metal.cpp)
uses `MTLn`, `MTLn_Private` and `MTLn_Mapped` buffer names. The guard recognizes
those exact forms for the selected device, sums their model allocations after
the final layer-offload report, and still rejects zero allocation, a different
device, missing native evidence or CPU-only loading. Earlier fit estimates are
not evidence for the final loaded model.

To preserve the successful compilation, `--reuse-build` accepts the original
isolated trial folder. It checks the retained build receipt, executable SHA-256,
source commit and tree, clean checkout, effective Metal flags, x86_64 build
setting, native version and actual device inventory. It performs no fetch or
compilation. New runtime logs and results go to a fresh trial folder; the old
receipt and failed log are retained. A mismatch stops the run without silently
rebuilding. Without this option the original bounded first-build route remains
available.

This corrects trial initialization diagnostics. Successful execution on the
Radeon, model-answer quality, latency improvement and application integration
remain unmeasured. The model, weights, source preparation, schema, validators,
six-request order and original adoption thresholds are unchanged.

## Observed GPU timeout and the single-request check

The reused-build v2 run proved that the existing Qwen3 GGUF was loaded on the
Radeon: 34 of 37 layers, `MTL0_Mapped` model allocation 2199.89 MiB, GPU KV
allocation 528 MiB and GPU compute allocation 298.01 MiB. Context remained
4096, with logical and physical batches both 512. The native and Ollama chat
template hashes matched. Partial offload is retained in the result.

The first CPU asyncio request took 59.644 seconds. Its completed answer again
used the unsupported control predicate for the subprocess operation; the
supplementary audit rejected it without repairing the answer. This CPU row is
not a successful quality reference. The following GPU request processed its
first 512 prompt tokens in 3.11 seconds, then failed during the next chunk with
`Caused GPU Timeout Error (00000002:kIOAccelCommandBufferCallbackErrorTimeout)`.
The backend entered an error state and the server returned `Compute error.`.
The remaining four model requests were not attempted. A completed GPU latency
or speedup cannot be derived from partial prompt progress. The native log
reported zero cached prompts before this first GPU request; it does not support
attributing this timeout to cache contents.

The next check uses `--gpu-check --reuse-build ORIGINAL_TRIAL_FOLDER`. It refuses
to compile, reads only the public asyncio source, and makes exactly one GPU
request. There is no CPU model request and no automatic six-request comparison
after success. The verified existing executable and weights are reused, with
the same v9 preparation, question, schema, validators, supplementary audit,
temperature, output limit and context. Every completed raw answer is retained,
including rejection or incomplete output.

The temporary server requests physical batch 64 while retaining logical batch
512. Its own child environment sets `GGML_METAL_CONCURRENCY_DISABLE=1`,
`GGML_METAL_GRAPH_OPTIMIZE_DISABLE=1` and `GGML_METAL_FUSION_DISABLE=1`.
These controls are present in the exact pinned upstream
[Metal context](https://github.com/ggml-org/llama.cpp/blob/4d756bc72bf00a4aacf410ae15a2d315f3db400d/ggml/src/ggml-metal/ggml-metal-context.m)
and
[Metal device](https://github.com/ggml-org/llama.cpp/blob/4d756bc72bf00a4aacf410ae15a2d315f3db400d/ggml/src/ggml-metal/ggml-metal-device.m)
implementations. Native logs must confirm the final physical/logical batches
and all three disabled settings before any inference. `--cache-ram 0` also
disables the server's RAM prompt cache as an isolation setting, not as a claim
about the cause of the previous timeout. Its effective state is likewise
required in the native log. Host environment and production CPU settings are
unchanged. The original six-request mode keeps its original runtime settings.

This is one bundled compatibility hypothesis: smaller physical blocks and
serial, unfused GPU execution might avoid the observed timeout. Neither a fix
nor a causal explanation is established before the Mac result. One POST is
bounded at 90 seconds and its worker at 95 seconds; initialization retains its
150-second bound. There is no warmup, retry or repair. Failure codes from a
bounded native-log tail are included in the result; raw log text and arbitrary
HTTP error bodies are not included. Model HTTP errors preserve a fixed code
such as `local_model_http_500_compute_error`, while readiness HTTP 503 retains
its polling behavior. Setup failures after creation of the trial folder also
save a diagnostic result and close the owned server.

A completed, structurally accepted response remains
`completed_pending_semantic_review`. Rejected answers, incomplete responses
and runtime failures remain explicit. Every single-check outcome has
`integrationAllowed: false`, `latencyComparisonCollected: false` and
`automaticFullComparisonAfterSuccess: false`. No adoption decision or full
application latency measurement follows from this one request.

## Primary sources and the important release limitation

The official OpenJarvis
[structured-output tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_structured_output.py)
were consulted for this task, including exact native JSON-schema forwarding and
engine-response completion checks. This work extends the existing local profile;
it does not replace it with an unrelated fresh installation.

The official llama.cpp Intel archive exists, but its
[pinned release workflow](https://github.com/ggml-org/llama.cpp/blob/4d756bc72bf00a4aacf410ae15a2d315f3db400d/.github/workflows/release.yml)
explicitly sets `GGML_METAL=OFF` for x64. Installing that archive would not test
Radeon acceleration. No such binary is downloaded by this trial.

Instead the script builds the unchanged official source at
`4d756bc72bf00a4aacf410ae15a2d315f3db400d` (release b11461, tree
`52c0e5f1f920046632632b594b7263ad1b7706cd`) with Metal and Accelerate enabled.
The pinned
[Metal build implementation](https://github.com/ggml-org/llama.cpp/blob/4d756bc72bf00a4aacf410ae15a2d315f3db400d/ggml/src/ggml-metal/CMakeLists.txt)
embeds shader **source** when `GGML_METAL_EMBED_LIBRARY=ON`; the library is then
compiled by Metal at runtime. This avoids requiring a separate command-line
Metal shader compiler. It still requires a working Apple compiler and SDK.
Command presence in the inventory does not prove these will build successfully.

Apple's
[default-device documentation](https://developer.apple.com/documentation/metal/getting-the-default-gpu)
describes the discrete GPU as the default on MacBook Pro systems with multiple
GPUs. The trial nevertheless requires the actual native `MTL*` device description
to equal `AMD Radeon Pro 5500M`; a hardware inventory name alone is insufficient.
CoreGraphics is linked explicitly for this command-line application, as specified
in Apple's
[Metal default-device API documentation](https://developer.apple.com/documentation/metal/mtlcreatesystemdefaultdevice()).

The native
[server API and options](https://github.com/ggml-org/llama.cpp/blob/4d756bc72bf00a4aacf410ae15a2d315f3db400d/tools/server/README.md)
and
[response-format parser](https://github.com/ggml-org/llama.cpp/blob/4d756bc72bf00a4aacf410ae15a2d315f3db400d/tools/server/server-common.cpp)
were checked directly. The OpenAI-compatible wrapper passes the original schema
under `response_format.json_schema.schema`, not as a replacement schema.

## What the single Mac command does

Run `scripts/andrea/web_metal_backend_probe.py` from the **Controlli** Terminal
window. **OpenJarvis must be running** to read the two public documentation pages.
Leave it idle during the trial. No Command+R or Control+C is needed for this run.

1. Verify the 24 installed v9 file fingerprints, model name and Ollama version.
2. Obtain the existing GGUF path from `/api/show`, require the expected Qwen3
   family and Q4_K_M quantization, and verify the entire blob against its declared
   SHA-256. No new model, conversion or copy of the weights is performed.
3. Read the two public Python documentation excerpts through OpenJarvis, including
   the CSV condition needed by the test. Both engines receive the same captured
   source bytes. No search provider, vault, memory or conversation is read.
4. Fetch the one official Git commit over HTTPS into a newly created separate
   directory under `~/.openjarvis-andrea/local-engines/`. Check the commit, tree
   and clean working tree. Build only `llama-server`, in Release mode for x86_64,
   with four compilation jobs, static libraries and embedded Metal shader source.
   Do not run `cmake install`, install system packages, change Git settings, fetch
   a UI, or modify the checked-out source.
5. Check the built version and native GPU inventory. Start an owned server bound
   to an ephemeral `127.0.0.1` port with a random API credential, the same verified
   GGUF, context 4096, one slot, requested batch/ubatch 512, automatic model thread
   count, Flash Attention off, reasoning off and no prompt caching or warmup
   inference. Native trace logging (verbosity 4) exposes the evidence required
   for GPU verification. The fit policy keeps a 1024 MiB margin. Context shrinking is refused.
6. Require authenticated model readiness, the expected model path, a positive
   allocation of its tensors on the Radeon and a positive final GPU layer count.
   Fit-estimation log repetitions are distinguished from the final layer count.
   Partial offload is reported explicitly. Missing GPU evidence stops the trial
   before model requests; there is no silent CPU fallback.
7. Make the six fixed requests below, one per worker. Retain every completed raw
   answer and every refusal. Run the unchanged v9 preparation, native schema and
   original validators, followed by the same supplementary control predicate
   audit on both engines. Do not repair, re-anchor, truncate or drop bad claims.
8. Close only the owned temporary Metal server, save `trial-result.json` and a
   build receipt in the trial directory, and leave ordinary OpenJarvis installed
   as before. Compiled files and logs remain available for reviewing this trial.

| Order | Case | Engine |
|---|---|---|
| 1 | Two supported asyncio capabilities | Ollama CPU |
| 2 | Same captured asyncio source and question | llama.cpp Metal |
| 3 | CSV default conversion rule and QUOTE_NONNUMERIC exception | llama.cpp Metal |
| 4 | Same captured CSV source and question | Ollama CPU |
| 5 | Price absent from the CSV source | Ollama CPU |
| 6 | Same unsupported price question | llama.cpp Metal |

The missing-price schema continues to permit claims. Empty output must come
from the model, not from a forced empty schema. A positive-question empty output
does not count as a successful answer.

The source snapshot is read before compilation. Its five-minute app cache is
not used or refreshed for these local model requests. Source hashes, complete
preparation hashes and schema hashes must match within each pair. The original
source numbering and selected complete rules are preserved.

## Deadlines and cleanup

The first build may take approximately 5–20 minutes. Each long setup stage emits
progress every 15 seconds. The compile limit is 20 minutes; Git fetch is bounded
at 150 seconds, configure at 90 seconds, device/version checks at 120 seconds
each, and owned model initialization at 150 seconds. The overall maximum,
including all setup and model stages, is approximately 45 minutes.

After setup, six model requests typically occupy 4–8 minutes on the observed CPU,
but GPU response times are not yet known. Each single POST has a 90-second
deadline, protected by an owned child worker deadline of 95 seconds. No preload
inference, extra reset call, automatic retry or second generation is made.
Completion transport failure stops the remaining series. Validation refusal
retains the bad answer and continues only the independently planned cases.

Compile and server subprocesses have their own process groups. On cancellation
or deadline, only the groups created by this script are signalled. Existing
OpenJarvis and Ollama processes are never terminated. The local GPU endpoint is
authenticated; the credential is passed to model workers through stdin and is
not included in reports. Public source instructions do not authorize tools.

## Interpretation and gates established before collection

Both model transports return a complete JSON response. First-token streaming,
browser rendering, speech stages and audio playback are **not measured**.
Model loading and Metal initialization have their own reported startup time.
Ollama reports its load duration per request. These are retained rather than
presented as a measured complete user-visible latency.

llama.cpp's `prompt_n` is the number of processed tokens, not the total input;
`prompt_n + cache_n` must align with its usage report. Ollama's input and cached
counts are normalized separately. A missing or inconsistent timing measurement
disqualifies the timing comparison while preserving the original model answer.

The two positive cases require at least 20% improvement both in client request
duration and in native prefill plus generation duration. The second condition
prevents CPU model loading alone from creating a favorable speed decision.
The missing-price case must not regress more than 5% in client duration.
Each request permits at most eight cached tokens after a fresh diagnostic cache
marker. The marker is not a production prompt change or source evidence.

GPU allocation, unchanged weights, identical source/schema preparation, the
fixed order and complete transport are also mandatory. Candidate answer shapes
must be 2, 1 and 0 accepted claims respectively. Even satisfying these gates
leaves `qualityVerdict: pending_review` and `integrationAllowed: false`.
Meaning, application integration, startup fairness and browser latency still
need assessment before adopting the backend.

This compares two backend configurations, including their native chat templates,
samplers, grammar implementations and build choices. It does not isolate the
causal contribution of the GPU alone. It is one finite three-case comparison,
not proof of general reliability or speed across all Jarvis functions.

## Development verification

The adapter tests cover unchanged native schemas and source text, original
conditional-rule validators, retained raw output, the observed unsupported
control predicate, genuine abstention, duplicate JSON keys, incomplete/oversized
answers, token accounting, model hashes, GPU evidence, pinned build flags,
bounded cleanup of owned processes, six-call order and adoption gates.

These are local program and fixture tests. The Intel SDK compilation, AMD shader
execution and six model responses require Andrea's Mac and are not claimed as
completed here. The attached inventory itself also states compatibility unknown
and performance not measured.

Development result: **260 targeted tests passed**, including 42 tests of the new
Metal trial adapter and the unchanged production pipeline, source/rule guards,
previous experiment adapters and inventory filter. Python syntax was checked,
and the 24 installed-v9 fingerprints still match in the review workspace. This
does not claim the entire historical repository test suite passes.

Logging/reuse correction: **184 relevant local tests passed**, including 56
Metal-adapter tests and 14 new regression cases. The installed-v9 fingerprints
still match. This result covers trial setup and the unchanged answer pipeline;
it is not a Mac inference or latency measurement.

Single-request timeout check: **197 relevant local tests passed**, including
69 Metal-adapter tests and 13 additional regression cases. These cover the
one-GPU/no-CPU route, reuse-only enforcement, effective native runtime settings,
child-environment isolation, safe HTTP error reporting, unchanged readiness
polling, bounded native timeout evidence, cleanup on failure, saved setup
diagnostics, retained rejection and the absence of automatic comparison or
adoption. Python syntax and the 24 installed-v9 fingerprints still pass.
The smaller-batch Radeon execution itself remains to be tested on the Mac.
