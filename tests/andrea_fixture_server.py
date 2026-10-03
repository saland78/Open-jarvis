"""Manual browser fixture: real OpenJarvis/Rust backend, simulated Ollama only.

Run from the serving venv. No real model or personal data is used.
"""
import json
import argparse
from contextlib import ExitStack
import os
from pathlib import Path
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/andrea"))
from runtime import isolated_environment, build_app

MODEL = "qwen3:4b-instruct-2507-q4_K_M"
REQUESTS = []


class Fixture(BaseHTTPRequestHandler):
    def handle(self):
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError):
            pass  # Expected when the browser cancels an inference stream.

    def log_message(self, *args):
        pass

    def do_GET(self):
        data = {"models": [{"name": MODEL, "model": MODEL, "size": 2500000000, "details": {"parameter_size": "4B", "quantization_level": "Q4_K_M"}}]}
        if self.path == "/captured":
            data = REQUESTS
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        REQUESTS.append(data)
        assert data["model"] == MODEL
        assert data["think"] is False
        assert data["options"]["num_predict"] == 512
        assert data["options"]["num_ctx"] == 4096
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.end_headers()
        notes_mode = '"estratti"' in data["messages"][-1]["content"]
        for text in ("Risposta di prova ", "locale. [N1]" if notes_mode else "locale."):
            self.wfile.write((json.dumps({"model": MODEL, "message": {"role": "assistant", "content": text}, "done": False}) + "\n").encode())
            self.wfile.flush()
            time.sleep(0.5 if "SLOW_TEST" in data["messages"][-1]["content"] else 0.05)
        self.wfile.write((json.dumps({"model": MODEL, "message": {"role": "assistant", "content": ""}, "done": True, "prompt_eval_count": 20, "eval_count": 7, "eval_duration": 500000000}) + "\n").encode())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--notes", action="store_true", help="Create synthetic vault for browser tests")
    args = parser.parse_args()
    fixture = ThreadingHTTPServer(("127.0.0.1", 0), Fixture)
    threading.Thread(target=fixture.serve_forever, daemon=True).start()
    with ExitStack() as stack:
        state = stack.enter_context(tempfile.TemporaryDirectory(prefix="openjarvis-browser-fixture-"))
        if args.notes:
            vault_dir = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="OpenJarvis-Notes-Fixture-", dir=Path.home())))
            (vault_dir / "Gioiello.md").write_text('---\ntitle: Gioiello\nsummary: SOLO_METADATI\nstatus: active\n---\n# Gioiello\nDecisione: catalogo prima, vendita online dopo.\n<img src="https://invalid.example/x" onerror="window.noteInjected=true">\n')
            (vault_dir / "Bozza-Gioiello.md").write_text('---\nstatus: draft\n---\n# Gioiello\nDecisione_BOZZA_NON_USARE\n')
            (vault_dir / "Superata-Gioiello.md").write_text('---\nstatus: superseded\n---\n# Gioiello\nDecisione_SUPERATA_NON_USARE\n')
            (vault_dir / "Gioiello-vuota.md").write_text('')
            print(f"Fixture vault: {vault_dir}", flush=True)
        env = isolated_environment(ROOT, Path(state))
        os.environ.clear()
        os.environ.update(env)
        print(f"Fixture Ollama: http://127.0.0.1:{fixture.server_port}/captured", flush=True)
        import uvicorn
        try:
            uvicorn.run(build_app(f"http://127.0.0.1:{fixture.server_port}"), host="127.0.0.1", port=8008, log_level="warning")
        finally:
            fixture.shutdown()
