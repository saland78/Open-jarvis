"""Rebuild the immutable installed baseline of the completed Mac A/B probe.

Keep its published hash checks and fixtures intact after production adoption.
These archives are test-only and are never installed by the updater.
"""
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = 'scripts/andrea/note_facts.py'
OLD_BRIDGE = ROOT/'tests/fixtures/andrea/note_facts_before_compact_wire.py'
CANDIDATE = ROOT/'tests/fixtures/andrea/qualification_compact_wire_candidate.py'


def project(probe):
    temporary = tempfile.TemporaryDirectory()
    root = Path(temporary.name)
    for relative in probe.EXPECTED:
        target = root/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        source = OLD_BRIDGE if relative == BRIDGE else ROOT/'tests/fixtures/andrea/runtime_before_manual_memory.py' if relative == 'scripts/andrea/runtime.py' else ROOT/relative
        target.write_bytes(source.read_bytes())
    return temporary, root
