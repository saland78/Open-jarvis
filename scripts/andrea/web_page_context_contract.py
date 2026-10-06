"""Live facade for the reviewed compact v9 web evidence pipeline.

Source parsing and streaming keep their existing public interfaces. No benchmark
or model transport is imported by the pipeline. Technical acceptance still
requires separate semantic review.
"""
from web_candidate_pipeline import CONTRACT_REVISION, context, contract as fidelity, prepare, validate
