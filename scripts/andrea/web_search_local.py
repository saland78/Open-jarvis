"""Explicit isolated searches; no memory, vault, inference or page fetching."""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

PROVIDERS = {"duckduckgo": "DuckDuckGo HTML", "youcom": "You.com MCP free — valutazione"}
TIMEOUT = 25

class SearchError(ValueError):
    def __init__(self, detail, status=503):
        super().__init__(detail)
        self.status = status

def validate(payload):
    if not isinstance(payload, dict) or set(payload) != {"query", "provider"}:
        raise SearchError("Invia soltanto la ricerca e il fornitore scelto.", 400)
    provider = payload["provider"]
    query = payload["query"]
    if not isinstance(provider, str) or provider not in PROVIDERS:
        raise SearchError("Fornitore di ricerca non supportato.", 400)
    if not isinstance(query, str) or not query.strip() or len(query) > 200 or any(ord(c) < 32 or ord(c) == 127 for c in query):
        raise SearchError("Scrivi una ricerca da 1 a 200 caratteri, su una sola riga.", 400)
    return provider, query.strip()

def worker(provider, query):
    from web_provider_probe import FreeSearchClient, ProbeError as YouError, source_results
    from duckduckgo_provider_probe import DuckSearchClient, ProbeError as DuckError
    try:
        if provider == "youcom":
            client = FreeSearchClient()
            client.initialize()
            rows = source_results(client.search(query, 3))
        elif provider == "duckduckgo":
            rows = DuckSearchClient().search(query)
        else:
            return {"error": "unsupported_provider"}
        return {"sources": rows}
    except (YouError, DuckError) as exc:
        return {"error": str(exc)}
    except Exception:
        return {"error": "invalid_provider_response"}

def checked_sources(value):
    from web_provider_probe import public_url
    if not isinstance(value, list) or len(value) > 3:
        raise SearchError("Formato dei risultati non riconosciuto.")
    for row in value:
        if (not isinstance(row, dict) or set(row) != {"title", "url", "snippet"}
                or not public_url(row["url"]) or not isinstance(row["title"], str)
                or not isinstance(row["snippet"], str) or not 1 <= len(row["title"]) <= 200
                or len(row["snippet"]) > 600):
            raise SearchError("Formato dei risultati non riconosciuto.")
    return value

async def stop_process(process):
    if process.returncode is None:
        try:
            process.kill()
        except ProcessLookupError:
            pass
    await process.wait()

class LocalWebSearch:
    def __init__(self):
        self.last_started = None

    async def search(self, payload):
        provider, query = validate(payload)
        now = time.monotonic()
        if self.last_started is not None and now - self.last_started < 3:
            raise SearchError("Attendi tre secondi fra due ricerche.", 429)
        self.last_started = now
        started = time.perf_counter()
        process = await asyncio.create_subprocess_exec(
            sys.executable, str(Path(__file__).resolve()), "--worker", provider,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        try:
            try:
                stdout, _ = await asyncio.wait_for(process.communicate(json.dumps({"query": query}).encode()), TIMEOUT)
            except asyncio.TimeoutError as exc:
                raise SearchError("Ricerca scaduta dopo 25 secondi. Nessun altro fornitore è stato contattato.", 504) from exc
            if process.returncode != 0 or len(stdout) > 16384:
                raise SearchError("Il collegamento al fornitore non ha restituito un risultato valido.")
            try:
                data = json.loads(stdout)
                if not isinstance(data, dict):
                    raise ValueError()
            except (ValueError, UnicodeError) as exc:
                raise SearchError("Formato dei risultati non riconosciuto.") from exc
            if "error" in data:
                code = data["error"]
                if not isinstance(code, str) or len(code) > 80 or not all(c.isalnum() or c == "_" for c in code):
                    code = "invalid_provider_response"
                raise SearchError(f"Ricerca non riuscita ({code}). Nessun cambio automatico di fornitore.")
            rows = checked_sources(data.get("sources"))
            return {"provider": provider, "providerLabel": PROVIDERS[provider], "query": query,
                    "consultedAt": datetime.now(timezone.utc).isoformat(),
                    "elapsedMs": round((time.perf_counter() - started) * 1000), "sources": rows,
                    "pagesFetched": False, "modelUsed": False, "automaticRetries": 0}
        finally:
            await stop_process(process)

if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "--worker" or sys.argv[2] not in PROVIDERS:
        raise SystemExit(2)
    try:
        raw = sys.stdin.buffer.read(2049)
        if len(raw) > 2048:
            raise ValueError()
        provider, query = validate({"provider": sys.argv[2], **json.loads(raw)})
        result = worker(provider, query)
    except Exception:
        result = {"error": "invalid_request"}
    print(json.dumps(result, ensure_ascii=False))
