"""Prepare a project-local environment, then run the same-origin local UI."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import webbrowser

from runtime import ROOT, isolated_environment


def run(args, env, cwd=ROOT):
    subprocess.run([str(a) for a in args], cwd=cwd, env=env, check=True)


def digest(paths):
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(str(p.relative_to(ROOT)).encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def main():
    probe = socket.socket()
    probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        probe.bind(("127.0.0.1", 8008))
    except OSError:
        probe.close()
        raise RuntimeError("Porta 8008 occupata. Nessun processo è stato fermato: comunica questo messaggio.")
    state = Path.home() / ".openjarvis-andrea"
    env = isolated_environment(ROOT, state)
    for tool in ("npm", "node", "uv"):
        if not shutil.which(tool):
            raise RuntimeError(f"Manca {tool}. Comunica questo messaggio per il passaggio guidato.")
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    env["VIRTUAL_ENV"] = str(ROOT / ".venv")
    env["PATH"] = str(ROOT / ".venv/bin") + os.pathsep + env.get("PATH", "")
    env["CARGO_TARGET_DIR"] = str(state / "build/rust")
    native = digest([ROOT / "rust/Cargo.lock", *ROOT.glob("rust/crates/**/*.rs"), *ROOT.glob("rust/**/Cargo.toml")])
    stamp = state / "andrea-native.sha256"
    imported = subprocess.run([sys.executable, "-c", "import openjarvis_rust"], env=env, capture_output=True).returncode == 0
    if not imported or not stamp.exists() or stamp.read_text() != native:
        if not shutil.which("cargo", path=env["PATH"]):
            raise RuntimeError("Manca Cargo/Rust. Non è stato installato automaticamente: comunica questo messaggio.")
        print("Compilazione dell'estensione Rust: la prima volta può richiedere diversi minuti.", flush=True)
        run(["uv", "pip", "install", "--python", sys.executable, "maturin==1.12.6"], env)
        run([sys.executable, "-m", "maturin", "develop", "--locked", "--release", "-m", ROOT / "rust/crates/openjarvis-python/Cargo.toml"], env)
        run([sys.executable, "-c", "import openjarvis_rust"], env)
        stamp.write_text(native)
    frontend = ROOT / "frontend"
    sources = [frontend / "package-lock.json", frontend / "package.json", frontend / "vite.config.ts", frontend / "index.html", *frontend.glob("tsconfig*.json"), *frontend.glob("src/**/*"), *frontend.glob("public/**/*")]
    source_hash = digest([p for p in sources if p.is_file()])
    build_stamp = state / "andrea-ui.sha256"
    built = ROOT / "src/openjarvis/server/static/index.html"
    if not built.exists() or not build_stamp.exists() or build_stamp.read_text() != source_hash:
        print("Preparazione e compilazione dell'interfaccia…", flush=True)
        npm = ["npm", "exec", "--yes", "--package=npm@11.19.0", "--", "npm"]
        run([*npm, "ci", "--ignore-scripts", "--no-audit", "--no-fund"], env, frontend)
        env["VITE_ANDREA_LOCAL"] = "true"
        env["VITE_API_URL"] = ""
        run([*npm, "run", "build"], env, frontend)
        if not built.is_file():
            raise RuntimeError("Compilazione conclusa senza interfaccia: comunica questo messaggio.")
        build_stamp.write_text(source_hash)
    print("Avvio OpenJarvis — http://127.0.0.1:8008 (il browser si aprirà dopo il controllo)", flush=True)
    print("Lascia aperto QUESTO Terminale. Control+C ferma solo OpenJarvis.", flush=True)
    # Open after liveness; do not declare ready from the printed URL alone.
    import threading, time, urllib.request
    def open_when_ready():
        for _ in range(60):
            try:
                with urllib.request.urlopen("http://127.0.0.1:8008/health", timeout=1):
                    webbrowser.open("http://127.0.0.1:8008")
                    return
            except OSError:
                time.sleep(0.5)
    threading.Thread(target=open_when_ready, daemon=True).start()
    os.environ.clear()
    os.environ.update(env)
    from runtime import build_app
    import uvicorn
    server = uvicorn.Server(uvicorn.Config(build_app(), host="127.0.0.1", port=8008, log_level="warning"))
    server.run(sockets=[probe])


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ImportError, OSError, subprocess.CalledProcessError) as exc:
        print(f"Avvio interrotto: {exc}", file=sys.stderr)
        sys.exit(1)
