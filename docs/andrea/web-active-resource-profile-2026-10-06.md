# One web request with contemporaneous resource observations

## Why another idle snapshot cannot choose an engine setting

The read-only Mac diagnostic completed in 3006.43 ms. It reports 8 physical
cores, 16 logical cores, 32 GiB RAM, AC power, low-power mode disabled, 88.43%
aggregate CPU idle, zero swap used, and zero swap/pageout counter changes in
that window. CPU speed/scheduler limits are both reported as 100 and available
CPUs as 16. These are reported limits, not temperatures or proof of CPU
frequency throughout the earlier comparison.

Ollama is now 0.35.1. No model is loaded; the only observed Ollama process uses
0.1% CPU in single-core units. Runner options and model placement cannot be
determined while there is no loaded model. The absent legacy runner name
produces one unavailable-query entry; the current Ollama process is still
found. This snapshot is not a measurement during the 31–56 s prefill and cannot
explain the earlier failed latency gates. No settings or model changes are
justified by it alone.

The next diagnostic records resources during **one** installed-baseline CSV
request. It is not another A/B series or a retry of a rejected answer. The
original 10% input/prefill gates, six original comparison cases, previous
failures and manual quality requirements remain unchanged. The latency task
is open; no unrelated module is started.

## Sources checked for this development task

- [OpenJarvis Ollama tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_ollama.py)
  and [engine](https://github.com/open-jarvis/OpenJarvis/blob/main/src/openjarvis/engine/ollama.py):
  applied deadlines, async streaming and bounded disconnect handling. This
  profiler also places its owned streaming worker behind a whole-process
  deadline; the installed transport is not edited.
- [Ollama usage](https://docs.ollama.com/api/usage) and [running-model metadata](https://docs.ollama.com/api/ps):
  loading, uncached prompt evaluation and output evaluation have distinct
  metrics; loaded-model metadata can be read without inference.
- [Ollama 0.35.1 option definitions](https://github.com/ollama/ollama/blob/v0.35.1/api/types.go):
  the API defines a default batch option of 512 and automatic thread choice.
  These source defaults do not prove effective runner flags on this Mac. The
  diagnostic records numeric flags when observable; neither option is changed.
- [Python 3.12 monotonic clock](https://docs.python.org/3.12/library/time.html#time.monotonic):
  the clock is shared across macOS processes. Only monotonic differences are
  used to align the worker's client window with the observer's window.

## Fixed protocol and limits

`web_request_resource_profile.py` is a self-contained bundle of the already
reviewed type-fidelity probe and read-only resource reader, plus the profiler
body. The bundle's source bytes are checked against those two files in tests.
No downloaded dependency, installed application code, configuration, note,
memory, database, model file or log is changed or read beyond the same four
installed code hash checks. Existing Jarvis/Ollama processes are never signalled.

Normal mode requires macOS, those four installed hashes, Ollama 0.35.1, and
known loaded-state metadata containing zero models or the sole expected model.
An unknown or other loaded model refuses before any inference. It reads only
the same public CSV page through the verified installed fetcher, preserving its
6000-character cap, full text, numbering, required conversion context and HTML
heading roles. The CSV question, installed baseline messages/schema, model,
temperature 0.4, context 4096, output budget 512, think=false and keep-alive 15m
are unchanged. A unique diagnostic nonce isolates prompt reuse as in the
existing experiment; it is not a production prompt change.

There is at most one model worker and one POST /api/chat, with no warm-up,
unload or retry. The inherited socket/stream deadline remains 90 s; the parent
places the entire owned model process, including startup, behind a 95 s
deadline. Timeout or interruption terminates only that owned child and closes
its connection. It does not claim confirmation that the server has finished
any computation after disconnect. If worker confirmation is missing, the
confirmed request count is unknown rather than falsely reported as complete.

A separate observer thread schedules at most three samples at 6, 18 and 36 s
after worker creation. Samples scheduled after worker completion are skipped.
Each observation has an 8 s budget, queries at most 1.5 s individually, and
checks cancellation before another query. Fixed read-only queries inspect VM
counter changes, reported thermal limits, local GET /api/ps, exact Ollama
processes/numeric runner flags, CPU usage, system load and swap usage. The
two-sample top query has process tables and costly framework/memory traversal
disabled. Each API read uses an owned child, so a dribbling response is bounded.
Missing measurements remain unknown; other app names, model names, arguments,
paths, credentials and raw stderr are excluded.

The observer's start/end windows are aligned with the worker's client window.
The report states whether a whole observation occurs before the first JSON
arrival; that interval includes loading and waiting and does **not** prove the
native prefill phase alone. Reads within an observation are not simultaneous.
Observer work has overhead and can affect the measured request. Native model
timings, client timings and resource windows are separate and are not summed.
This diagnostic cannot establish a causal explanation or an unobserved app's
resource consumption, and it does not measure the browser.

The original generated answer and selected quotes remain in the result. The
existing type, field qualifier, condition, identifier, heading and transport
checks are retained, along with the previously prepared finite added-mechanism
rejection. They do not repair, truncate or re-anchor the model text. The report
always has `performanceVerdict: diagnostic_only_no_ab_comparison`,
`qualityVerdict: pending_review` and `integrationAllowed: false`. Current
resources guide the next candidate only after analysis; this profile cannot
turn the failed previous comparison into a pass.

## Validation and remaining work

18 new tests cover byte-exact reviewed bundles and baseline inputs, a single
streaming POST with the original options, whole-worker timeout and interrupt
cleanup, malformed/oversized/duplicate output, unknown request counts, fixed
and cancellable observations, read-only query allowlists and sanitized output,
cross-process timing labels, early version/platform/model/source refusal, and
the retained concrete source-fidelity rejection. Together with the related
suite, **466 program checks pass**. The four installed hashes are unchanged.

No actual Mac profiling request has been executed during development. It is
the next finite collection needed to choose a hardware/engine/context change
from contemporaneous evidence, rather than from an idle snapshot or guesses.
