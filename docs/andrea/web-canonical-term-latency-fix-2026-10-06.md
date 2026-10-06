# Canonical technical terms with complete-entry latency optimization

Status: corrected isolated candidate passes 496 relevant program regressions.
New Mac inference results are pending. No production change or successful model
quality claim follows from the program tests.

## Diagnosis from the completed Mac comparison

The [original six-request report](web-complete-api-context-mac-2026-10-06.json)
keeps its failed combined gate. Uncached input/native prefill fall by
26.734%/18.688% for asyncio and 68.307%/67.946% for CSV, but two compact answers
are semantically wrong. The generic instruction to translate technical terms
faithfully did not prevent `subprocesses` becoming generic `processi` and
`unquoted` becoming `non incapsulati`. The CSV answer also repeats the same
conditional conversion relation in two claims.

Those are source-fidelity failures, not false rejection by the validators.
`subprocesses` identifies the narrower subprocess concept. `unquoted` specifies
quotation, not encapsulation. The observed default/exception/type/field relation
must be preserved rather than replaced with an approximate meaning.

## Concrete correction

The compact system message explicitly names already-supported equivalents:
`subprocess/subprocesses = sottoprocesso/sottoprocessi` and
`unquoted = non racchiusi tra virgolette`. Their use remains conditional on the
own numbered source passage. No new aliases, known facts, external glossary,
tool calls or repaired model output are inserted.

One conditional rule is one point, with its default and exception together.
The model is explicitly instructed not to repeat the conversion as a second
point. The system now uses 990 characters, or 1157 with the complete-entry
selection notice, versus the previous candidate's 772/939 and the installed
production system's 2202. These are character counts, not new measured token or
latency improvements. The necessary fidelity guidance adds some input work;
the original performance gates must still be met by the new real requests.

The complete HTML API-entry selector, original source bytes, passage numbers,
audit bank, user question, schema, native options and own-source technical
checks are unchanged. Broad or unmatched questions still use the full extract;
incomplete, mixed or oversized entries still cannot narrow the input.

An additional finite check applies identically to both diagnostic variants.
It rejects two positive claims of the same source `QUOTE_NONNUMERIC` relation:
same numbered passage, the source's explicit unquoted-fields-to-float predicate,
and both claims stating that option, qualifier and positive conversion to float.
It does not ban two distinct facts using one passage and is not a general
semantic-similarity or entailment classifier. No duplicate is silently removed,
merged or paraphrased to make a response pass. Other repetition still requires
manual review.

The failed Mac strings remain rejected exactly as submitted. A separate fixture
shows that merely replacing the bad qualifier in both repeated CSV points is
insufficient: the new duplicate-relation check refuses the pair. Counterexample
fixtures preserve correct subprocess terms and a single complete CSV rule;
they are program tests, not repaired Mac answers or model-quality measurements.

## Fixed comparison and validation

Candidate revision: `complete_api_entries_canonical_terms_distinct_rule`.
The one-file runner embeds the exact baseline, resource reader and corrected
candidate. Its hash and revision distinguish it from the failed comparison.

The same three questions, unchanged public sources and balanced six-call order
are retained. Ollama 0.35.1 and `qwen3:4b-instruct-2507-q4_K_M`, temperature 0.4,
context 4096, output 512, `think=false` and `keep_alive=15m` are unchanged.
Cached tokens must remain at most 8, with at least 98% of input uncached;
each supported pair must have at least 10% fewer uncached tokens and 10% less
native prefill. All six transports, existing case shapes and manual source
reviews must pass. The new duplicate guard strengthens the existing requirement
for distinct points; no earlier gate or rejection is weakened.

One inference per variant, no warm-up, unload, automatic retry, thermal-based
exclusion, cooling wait or private note read. The 90-second stream and 95-second
owned-worker deadlines remain. Lightweight thermal samples are diagnostic only.
The automatic report never grants installation, and first JSON is not visible
or accepted browser text.

496 relevant program tests passed, including six new regressions anchored to
the submitted Mac errors and report, exact embedded-source parity, source
selection and omission checks, source qualifiers/types/identifiers, bounded
streaming/worker cleanup and the original gates. No further equivalent program
test run is needed before obtaining the new Mac measurements.

## Upstream consulted again for this correction

- [OpenJarvis Ollama tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_ollama.py):
  original response retention, applied stream timeouts and mid-stream failures.
- [OpenJarvis retrieval quality tests](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/memory/test_retrieval_quality.py):
  fixed corpus, source content and empty retrieval for unsupported queries.
- [CPython CSV source](https://github.com/python/cpython/blob/3.14/Doc/library/csv.rst):
  the actual reader default, `QUOTE_NONNUMERIC`, unquoted fields and float type.
- [CPython asyncio source](https://github.com/python/cpython/blob/3.14/Doc/library/asyncio.rst):
  distinct subprocess control and the event-loop catalogue with subprocesses
  and OS signals. The API index likewise documents spawning subprocesses.

No upstream test certifies arbitrary model paraphrases. Its bounded transport
and source-regression patterns are reused; the two observed lexical errors need
the explicit compact instructions and independent source checks above.
