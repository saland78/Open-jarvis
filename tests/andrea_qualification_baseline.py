"""Reconstruct the immutable pre-integration install for historical probe tests.

The original probes retain all production hash checks. Only the reviewed old
bridge is archived; other unchanged components must still match their hashes.
Do not load this fixture from the production runtime or a Mac installer.
"""
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = 'scripts/andrea/note_facts.py'
OLD_BRIDGE = ROOT/'tests/fixtures/andrea/note_facts_before_sentence.py'


def source(relative):
    if relative == 'scripts/andrea/runtime.py':
        return ROOT/'tests/fixtures/andrea/runtime_before_manual_memory.py'
    return OLD_BRIDGE if relative == BRIDGE else ROOT/relative


def load_modules(probe):
    with tempfile.TemporaryDirectory() as folder:
        project = Path(folder)
        for relative in probe.EXPECTED:
            target = project/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source(relative).read_bytes())
        return probe.load_modules(project)
