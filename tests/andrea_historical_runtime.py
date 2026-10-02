"""Read a public historical runtime fixture without weakening probe hashes."""
from pathlib import Path
import tempfile


def historical_messages(probe, root):
    with tempfile.TemporaryDirectory() as temp:
        project = Path(temp)
        file = project/'scripts/andrea/runtime.py'
        file.parent.mkdir(parents=True)
        file.write_bytes((root/'tests/fixtures/runtime-before-structured.txt').read_bytes())
        return probe.messages_from_runtime(project)
