"""Exact v1 facade retained for archived payload and observation regression tests."""
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
spec = importlib.util.spec_from_loader('frozen_v1_web_context', SourceFileLoader(
    'frozen_v1_web_context', str(Path(__file__).parent/'fixtures/andrea/web_page_context_contract.py_before_compact_v9')))
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)
