"""Local-only entry point for the personal fork; upstream modules stay intact."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def isolated_environment(root: Path, state: Path) -> dict[str, str]:
    state = state.expanduser().resolve()
    if state.is_relative_to(root.resolve()) or state == Path.home() or state.name in {".jarvis-local", ".openjarvis"}:
        raise ValueError("La cartella dati deve essere nuova e fuori dal progetto.")
    env = {key: os.environ[key] for key in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "TZ", "SYSTEMROOT") if key in os.environ}
    env.update(OPENJARVIS_HOME=str(state), OPENJARVIS_CONFIG=str(root / "profiles/andrea-local.toml"), JARVIS_NUM_CTX="4096")
    return env


class LocalMode:
    """First milestone: same-origin text chat; other mutations remain unavailable."""
    def __init__(self, app, model: str, port: int, timeout: float = 90):
        self.app, self.model, self.port, self.timeout = app, model, port, timeout
        self.busy = False

    async def reply(self, send, status: int, detail: str):
        await send({"type": "http.response.start", "status": status, "headers": [(b"content-type", b"application/json"), (b"cache-control", b"no-store")]})
        await send({"type": "http.response.body", "body": json.dumps({"detail": detail}).encode()})

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            return await self.app(scope, receive, send)
        if scope["type"] != "http":
            return await send({"type": "websocket.close", "code": 1008})
        headers = dict(scope.get("headers", []))
        hosts = {f"127.0.0.1:{self.port}", f"localhost:{self.port}"}
        origins = {"http://" + host for host in hosts}
        host = headers.get(b"host", b"").decode()
        origin = headers.get(b"origin", b"").decode()
        if host not in hosts or (origin and origin not in origins) or headers.get(b"sec-fetch-site") == b"cross-site":
            return await self.reply(send, 403, "Richiesta consentita solo dall'interfaccia locale.")
        if scope["method"] in {"GET", "HEAD"}:
            return await self.app(scope, receive, send)
        if scope["method"] != "POST" or scope["path"] != "/v1/chat/completions":
            return await self.reply(send, 403, "Strumenti e modifiche non sono ancora attivi nel profilo locale.")
        if not origin or not headers.get(b"content-type", b"").startswith(b"application/json"):
            return await self.reply(send, 403, "Usa l'interfaccia locale per inviare messaggi.")
        raw = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            raw.extend(message.get("body", b""))
            if len(raw) > 65536:
                return await self.reply(send, 413, "Messaggio troppo grande.")
            if not message.get("more_body", False):
                break
        try:
            payload = json.loads(raw)
            messages = payload["messages"]
            if payload.get("model") != self.model or payload.get("tools"):
                raise ValueError("Questo profilo usa soltanto il modello locale configurato, senza strumenti.")
            if payload.get("stream") is not True:
                raise ValueError("Questo profilo richiede una risposta streaming.")
            if not isinstance(messages, list) or not 1 <= len(messages) <= 24:
                raise ValueError("Conversazione troppo lunga: inizia una nuova chat.")
            if any(not isinstance(m, dict) or m.get("role") not in {"system", "user", "assistant"} or not isinstance(m.get("content"), str) for m in messages):
                raise ValueError("Formato dei messaggi non valido.")
            if sum(len(m["content"]) for m in messages) > 18000:
                raise ValueError("Conversazione troppo lunga: inizia una nuova chat.")
            if messages[-1]["role"] != "user":
                raise ValueError("Manca la richiesta dell'utente.")
        except (ValueError, KeyError, TypeError) as exc:
            return await self.reply(send, 400, str(exc))
        if self.busy:
            return await self.reply(send, 429, "Jarvis sta già rispondendo. Interrompi o attendi.")
        self.busy = True
        # Request defaults override intelligence config upstream: enforce our budget here.
        payload = {"model": self.model, "messages": messages, "stream": True, "temperature": 0.4, "max_tokens": 512}
        sent = False
        started = False
        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": json.dumps(payload).encode(), "more_body": False}
            return await receive()
        async def tracked(event):
            nonlocal started
            if event["type"] == "http.response.start":
                started = True
            await send(event)
        try:
            async with asyncio.timeout(self.timeout):
                await self.app(scope, replay, tracked)
        except TimeoutError:
            if started:
                data = json.dumps({"error": {"message": "Risposta non completata entro 90 secondi."}})
                await send({"type": "http.response.body", "body": f"data: {data}\n\ndata: [DONE]\n\n".encode(), "more_body": False})
            else:
                await self.reply(send, 504, "Risposta non completata entro 90 secondi.")
        finally:
            self.busy = False


def build_app(ollama_host: str | None = None):
    from openjarvis._rust_bridge import get_rust_module
    get_rust_module()  # Fail before serving if mandatory native enforcement is unavailable.
    from openjarvis.core.config import load_config
    from openjarvis.core.events import EventBus
    from openjarvis.engine.ollama import OllamaEngine
    from openjarvis.security import setup_security
    from openjarvis.server.app import create_app
    cfg = load_config()
    cfg.agent.default_system_prompt = cfg.agent.system_prompt
    cfg.security.capabilities.policy_path = str(ROOT / "profiles/andrea-capabilities.json")
    cfg.compression.enabled = False
    bus = EventBus(record_history=False)
    # Instantiate only Ollama. No CLI engine discovery, credentials import or cloud fallback.
    class BudgetOllama(OllamaEngine):
        @staticmethod
        def bounded(kwargs):
            return {**kwargs, "max_tokens": 512, "num_ctx": 4096, "think": False, "temperature": 0.4}

        def generate(self, messages, **kwargs):
            return super().generate(messages, **self.bounded(kwargs))

        async def stream(self, messages, **kwargs):
            async for item in super().stream(messages, **self.bounded(kwargs)):
                yield item

        async def stream_full(self, messages, **kwargs):
            async for item in super().stream_full(messages, **self.bounded(kwargs)):
                yield item

    engine = BudgetOllama(host=ollama_host or cfg.engine.ollama.host, timeout=90)
    sec = setup_security(cfg, engine, bus)
    app = create_app(sec.engine, cfg.server.model, config=cfg, bus=bus, engine_name="ollama", agent_name="", capability_policy=sec.capability_policy, rate_limiter=sec.rate_limiter, audit_logger=sec.audit_logger, cors_origins=[])
    return LocalMode(app, cfg.server.model, cfg.server.port)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(build_app(), host="127.0.0.1", port=8008, log_level="warning")
