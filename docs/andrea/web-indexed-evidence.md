# Indexed evidence for explicit web synthesis

The web synthesis path now requests `text` and a numeric `passage` reference.
The server partitions the entire current excerpt into exact substrings of
20–300 characters, preferring line or sentence boundaries. A final short tail
overlaps the previous span; it is not discarded. All excerpt content is still
provided. There is no relevance ranking, retrieval from other sources, or
question-dependent deletion.

The program resolves a reference against this request's passage bank and
returns the original passage as `quote` to the unchanged UI. Unknown IDs,
booleans, extra fields, invented numeric tokens, unfinished streams and tool
calls are rejected. Abstention remains available. The model cannot supply its
own quote or redirect the resolver to an external source.

This removes generated quote copying from the accepted wire format. It does
not certify that the generated summary is entailed by the selected passage,
nor guarantee a speed improvement. A false paraphrase without numbers can
still pass structural checks and requires semantic review. The accepted
outcome remains `accepted_pending_semantic_review`.

There is one inference, no retry, no warm-up request, no new provider, and no
change to model options, timeouts, private notes, memory or database. Existing
stream metrics observe the same request. The schema is shorter in output,
but indexed input can add tokens; actual local-model latency must be measured.

Upstream `tests/tools/test_web_search.py` was consulted for isolated test and
provider behavior; it does not implement this personal synthesis contract.

Local deterministic coverage includes full excerpt coverage, short-tail and
Unicode handling, original passage resolution, forged quotes, invalid IDs,
per-passage numeric guard, one-request isolation and incomplete streams.
Live Mac model behavior and semantic quality are pending, not certified by
mocked-stream tests. The previous exact-quote generator is retained only as
an internal compatibility/test path; production uses indexed evidence.
