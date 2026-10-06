# Diagnose resource variability before another latency comparison

## Evidence and present outcome

The [six-call type-fidelity comparison](web-type-latency-experiment-2026-10-06.md#mac-collection-completed--original-latency-gates-not-met)
fixes the observed CSV type loss but does not meet the original prefill gate.
Both compact prompts have fewer new tokens; processing throughput is lower per
token, and the prefill gains are 4.175%/0.328% against the unchanged 10% minimum.
Five answers have favorable review; one adds a mechanism absent from its own
selected passage. No variant is adopted and no past failure is changed to a pass.

The actual delay lies mainly in local model work: page reads are below 0.5 s,
whereas prefill is 31–56 s. This observation justifies checking local resources
before another prompt comparison. It does not identify the cause as heat,
another application, threads, memory or batch size. Resource state was not
recorded during the failed comparison, so current values cannot prove its cause.

Primary sources consulted for this task:

- [OpenJarvis Ollama tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_ollama.py)
  and its [engine](https://github.com/open-jarvis/OpenJarvis/blob/main/src/openjarvis/engine/ollama.py):
  nonblocking async streaming, applied deadlines and disconnect error handling.
  The installed streaming runtime is not changed.
- [Ollama usage metrics](https://docs.ollama.com/api/usage): uncached prompt cost
  is reported separately from loading and output generation.
- [Ollama running-model endpoint](https://docs.ollama.com/api/ps) and
  [FAQ](https://docs.ollama.com/faq): inspecting loaded model metadata is not
  a generation request; loaded models do not establish concurrent inference.
- Apple source manuals for [pmset](https://github.com/apple-oss-distributions/PowerManagement/blob/main/pmset/pmset.1),
  [top](https://github.com/apple-oss-distributions/top/blob/main/top.1) and
  [vm_stat](https://github.com/apple-oss-distributions/system_cmds/blob/main/vm_stat/vm_stat.1):
  thermal limits may be unavailable, CPU intervals differ from accumulated
  counters, and swapping activity must be distinguished from since-boot totals.

## Read-only diagnostic

`latency_resource_diagnostic.py` verifies the same four installed code hashes
and requires macOS before any resource query. It makes zero model inference
requests and no public network request. It issues only two local GET requests,
`/api/version` and `/api/ps`, with proxies and redirects disabled; `/api/chat`,
generation, loading, unloading and configuration endpoints are not allowed.

Fixed query commands inspect physical/logical cores, RAM, current power source,
reported low-power settings, system load, CPU usage, swap usage and two VM/thermal
snapshots. Only exact Ollama process names are queried for numeric runner flags
and recent CPU usage. Other model names, application names, arguments, paths,
credentials and raw stderr are not printed. No personal note, memory, database,
conversation, model file or log is read. No configuration, thread count, power
setting, service or installed code is changed.

Queries share a 20-second read budget and each owned process is bounded by at
most three seconds. The two local API reads also run in owned child processes,
so the whole read is bounded even if the server dribbles response bytes. A
timeout terminates only that diagnostic child, never an existing Ollama or
OpenJarvis process. There are no retries, model warm-ups, sleeps to cool the
machine or instructions to close other applications. Top collects two bounded
samples and prints no process table; its memory-map/framework traversal is
disabled. This diagnostic itself has small observation overhead.

Missing or malformed measurements stay null/unknown rather than becoming zero
or a normal CPU limit. Thermal data is a reported limit, not a Celsius
temperature. Ps CPU usage uses units of one core, whereas top reports aggregate
CPU percentages. VM counter deltas are current pages during the observation
window; past accumulated pageouts do not prove current swapping. Loaded model
metadata describes residency, not an active request or a queue.

The report always says `performanceVerdict: not_measured`,
`pastBenchmarkCause: not_determined` and `qualityVerdict: not_evaluated`.
It is a current snapshot, not another benchmark or a pass for the previous run.
Mac measurements for this diagnostic remain pending. The next optimization
must follow what is actually observed, and any fresh latency comparison must
keep the original gates and semantic review. Stable current resources alone
would not reconstruct the past; a later comparison would need contemporaneous
resource observation to interpret variation.

## Added-mechanism correction prepared, not installed

`web_mechanism_latency_candidate.py` wraps the previously verified isolated
contract. It retains every preceding guard and source byte, user payload,
schema, fact reference and selected quote. A single instruction forbids adding
a mechanism/interface absent from the selected passage.

For the known bare `control subprocesses;` unit, a finite lexical guard rejects
an asserted means/interface such as the exact observed added phrase. A different
source unit that explicitly documents a mechanism is not covered by this narrow
extra rule. Another passage cannot license that suffix. A two-point response
with the bad suffix is rejected as a whole; the raw text/quote remains in the
diagnostic. No deletion of the suffix, repair or generation retry is performed.

This is not complete semantic entailment or a guarantee that all possible
unsupported properties are detected. It prevents the concrete observed failure
and preserves manual review. It is program-tested only: no new Mac inference,
performance benefit, installed adoption or UI behavior is claimed for it.

## Validation

22 new checks cover the actual unsupported phrase and its two-point context,
retained original guards and source/schema bytes, narrow source scope, finite
resource parsers, missing thermal/CPU/low-power states, swap counter deltas,
sanitized model/process output, read-only command/GET allowlists, no proxies or
redirects, deadlines for owned API processes, a global exhausted budget, invalid
responses and early platform/version refusal. Together with the existing
related suite: **448 program tests pass**. These are deterministic program
checks, not measurements on the user's Mac.

The installed production contract retains SHA
`5b8a73b2a9d534074ec61eb67b9abd0eb6c73d3abb2783e76149ad6b3b7b2285`.
The broader latency/quality task remains open; no unrelated module is started.
