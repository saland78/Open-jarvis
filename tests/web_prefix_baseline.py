"""Frozen installed baseline for historically pinned prefix probes/installers.

These experiments compared against this exact version. Current production
behavior is exercised by separate production/service integration regressions.
"""
import importlib.machinery
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'tests/fixtures/andrea/web_sentence_contract.py_before_prefix_reuse'
loader=importlib.machinery.SourceFileLoader('web_prefix_frozen_baseline',str(FIXTURE))
spec=importlib.util.spec_from_loader(loader.name,loader)
contract=importlib.util.module_from_spec(spec)
loader.exec_module(contract)

def source(relative):
    path=FIXTURE if relative=='scripts/andrea/web_sentence_contract.py' else ROOT/relative
    return path.read_bytes()
