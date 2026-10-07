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
    if relative=='scripts/andrea/web_sentence_contract.py':
        return FIXTURE.read_bytes()
    return before_api_context_source(relative)


def before_api_context_source(relative):
    """Replay old pins against their actual source, never the new live service.

    The new complete-API integration has its own live-service, updater and
    checker tests. Historical manifests and gates are not rewritten.
    """
    fixtures = {'scripts/andrea/web_page_local.py': 'web_page_local.py_before_api_context',
                'frontend/src/pages/AndreaWebPage.tsx': 'AndreaWebPage.tsx_before_api_context'}
    path = ROOT/'tests/fixtures/andrea'/fixtures[relative] if relative in fixtures else ROOT/relative
    return path.read_bytes()
