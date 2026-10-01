"""Manual browser fixture: real OpenJarvis/Rust backend, simulated Ollama only.

Run from the serving venv. No real model or personal data is used.
"""
import json
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
        for text in ("Risposta di prova ", "locale."):
            self.wfile.write((json.dumps({"model": MODEL, "message": {"role": "assistant", "content": text}, "done": False}) + "\n").encode())
            self.wfile.flush()
            time.sleep(0.05)
        self.wfile.write((json.dumps({"model": MODEL, "message": {"role": "assistant", "content": ""}, "done": True, "prompt_eval_count": 20, "eval_count": 7, "eval_duration": 500000000}) + "\n").encode())


if __name__ == "__main__":
    fixture = ThreadingHTTPServer(("127.0.0.1", 0), Fixture)
    threading.Thread(target=fixture.serve_forever, daemon=True).start()
    with tempfile.TemporaryDirectory(prefix="openjarvis-browser-fixture-") as state:
        env = isolated_environment(ROOT, Path(state))
        os.environ.clear()
        os.environ.update(env)
        print(f"Fixture Ollama: http://127.0.0.1:{fixture.server_port}/captured", flush=True)
        import uvicorn
        try:
            uvicorn.run(build_app(f"http://127.0.0.1:{fixture.server_port}"), host="127.0.0.1", port=8008, log_level="warning")
        finally:
            fixture.shutdown()
