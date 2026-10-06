# Stop reference-prompt iteration and consolidate the reviewed candidate

Status: **consolidation staged; no new probe, installer or live change**.

The [v9 Mac record](web-native-operation-verb-v9-mac-2026-10-06.json) preserves all
six generated responses and the original automatic report. Six transports and
technical case shapes pass. Both original latency gates pass. Meaning review
is favorable for five responses and unfavorable for the archived-reference
asyncio response. That result is not relabelled as six meaning passes.

## What caused the repeated experiments

The comparison field named `production` actually uses the archived full-context
prompt. The report explicitly says `referenceIsCurrentInstalledPrompt: false`.
The `compact` variant is the candidate for adoption. Repeatedly changing common
constraints to make the archived reference produce perfect answers expanded
the experiment without establishing better behavior in the candidate.

The current reference says subprocesses are controlled by executing event loops.
Its own unit describes creating/managing event loops and the asynchronous APIs
they provide. The added execution mechanism is not explicit. The formal checks
accept it, demonstrating that format and vocabulary checks cannot certify
predicate relationships. The v9 control-verb branch was available, but neither
asyncio answer selected its control-only unit; both chose units 10 and 18.
Thus this run does not prove that the new verb starter fixed a selected control
paraphrase. No additional word-specific generation patch is warranted by it.

All three compact answers have favorable reviews in each of v7, v8 and v9:
asyncio operations, the qualified CSV conversion rule and genuine abstention
for the unsupported price. These are observations across different revisions,
not nine independent confirmations of one unchanged build or universal proof.
The original six-answer adoption gate remains unmet and is not silently relaxed.

## Concrete consolidation

`web_candidate_pipeline.py` consolidates exactly the reviewed **compact v9**
preparation and validation behind `prepare(page, question)` and
`validate(raw, bank, completed, page, selection)`. Its messages, schema, bank
and selection match the standalone experiment on all three original cases.
It imports the existing modular source checks without benchmark or model
transport code. The finite CSV alias is isolated from the installed contract.
No prompt change, retry, source rewrite, output repair or timing change is added.

Eight focused tests verify exact preparation parity, replay the actual compact
answers unchanged, retain the unfavorable reference review, recompute the
original performance gates, distinguish failed transport from abstention and
confirm the currently installed contract remains v1. The previously recorded
726 v9 tests are historical local verification, not new Mac evidence.

This module is staged; `web_page_context_contract.py` and the live server still
use v1. No installer is issued and no claim is made that the Mac is updated.
The consolidation creates a reviewable integration boundary without another
experimental prompt revision. The remaining work is production integration and
an explicit end-to-end acceptance protocol for the candidate. The unsuccessful
reference result and the prior six-answer gate must stay visible when that
protocol is settled; they cannot be erased by changing a report label.

## Measured limits

In v9, asyncio total client time is 54.56 seconds for the archived reference
and 45.25 seconds for the candidate. CSV is 63.17 versus 26.88 seconds. Original
native-prefill reductions are 15.470% and 64.444%; original uncached-input
reductions are 14.742% and 60.762%. These pass the existing pair thresholds, but
45 seconds remains substantial latency. This is not a measurement against the
currently installed prompt, screen rendering or the complete voice pipeline.

[OpenJarvis's structured-output tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_structured_output.py)
were consulted again. Schema propagation and JSON structure checks are useful
regressions; they do not establish whether a paraphrase preserves source meaning.

No unrelated roadmap work is advanced. The next step must concern this staged
candidate and its production acceptance, rather than another attempt to repair
the archived reference prompt or a promise of universally perfect synthesis.
