#!/usr/bin/env bash
set -euo pipefail
task_root="$(cd -- "$(dirname -- "$0")" && pwd)"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"
cd "$task_root"
if ! command -v uv >/dev/null; then
  echo "Manca uv. Non è stato installato nulla. Comunica questo messaggio per il passaggio guidato."
  exit 1
fi
echo "Preparazione dell'ambiente Python separato di OpenJarvis…"
uv sync --locked --extra server --no-dev --inexact --python 3.12
exec .venv/bin/python scripts/andrea/launch.py
