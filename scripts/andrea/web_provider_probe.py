"""Finite You.com free MCP evaluation; never installs or reads local data.

Only the two public queries below may leave this process. No API key, payment,
credential discovery, alternate provider, model call or page fetch is used.
"""
from __future__ import annotations

import ipaddress
import json
import multiprocessing
import re
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

ENDPOINT = "https://api.you.com/mcp?profile=free&tools=you-search"
PROTOCOL = "2025-03-26"
LIMIT = 1024 * 1024
TOTAL_SECONDS = 45
CASES = (
    ("python_timeout", "site:docs.python.org asyncio wait_for", "docs.python.org"),
    ("ollama_keep_alive", "site:docs.ollama.com keep_alive", "docs.ollama.com"),
)


class ProbeError(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProbeError("duplicate_json_key")
        result[key] = value
    return result


def invalid_constant(value):
    raise ProbeError("invalid_json_number")


def decode(data):
    try:
        return json.loads(data, object_pairs_hook=unique_object, parse_constant=invalid_constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ProbeError("invalid_json") from exc


def rpc_result(value, request_id):
    if not isinstance(value, dict) or value.get("jsonrpc") != "2.0":
        raise ProbeError("invalid_rpc_envelope")
    # Server requests/notifications are never executed. Ignore unrelated IDs.
    if "method" in value or type(value.get("id")) is not int or value["id"] != request_id:
        return None
    if "error" in value:
        raise ProbeError("provider_rpc_error")
    if not isinstance(value.get("result"), dict):
        raise ProbeError("invalid_rpc_result")
    return value["result"]


def read_result(response, request_id):
    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
    if content_type not in {"application/json", "text/event-stream"}:
        raise ProbeError("unsupported_response_type")
    data = bytearray()
    pending = bytearray()
    while True:
        chunk = response.read1(16384)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > LIMIT:
            raise ProbeError("response_too_large")
        if content_type == "text/event-stream":
            pending.extend(chunk)
            # CRLF may be split across reads; normalize after appending.
            normalized = bytes(pending).replace(b"\r\n", b"\n")
            while b"\n\n" in normalized:
                block, normalized = normalized.split(b"\n\n", 1)
                lines = [line[5:].lstrip(b" ") for line in block.split(b"\n") if line.startswith(b"data:")]
                if lines:
                    result = rpc_result(decode(b"\n".join(lines)), request_id)
                    if result is not None:
                        return result
            pending = bytearray(normalized)
    if content_type == "application/json":
        result = rpc_result(decode(bytes(data)), request_id)
        if result is not None:
            return result
    raise ProbeError("missing_complete_rpc_response")


class FreeSearchClient:
    def __init__(self, opener=None):
        self.opener = opener or build_opener(ProxyHandler({}), NoRedirect())
        self.session = None
        self.protocol = None

    def post(self, method, params=None, request_id=None):
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                   "User-Agent": "OpenJarvis-Andrea-web-evaluation/1.0"}
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        if self.protocol:
            headers["MCP-Protocol-Version"] = self.protocol
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        if request_id is not None:
            payload["id"] = request_id
        request = Request(ENDPOINT, data=json.dumps(payload).encode(), headers=headers)
        try:
            with self.opener.open(request, timeout=8) as response:
                if request_id is None:
                    if response.status != 202:
                        raise ProbeError("notification_not_accepted")
                    return None
                if response.status != 200:
                    raise ProbeError("unexpected_http_status")
                result = read_result(response, request_id)
                if method == "initialize":
                    session = response.headers.get("Mcp-Session-Id")
                    if session and (len(session) > 512 or not re.fullmatch(r"[\x21-\x7e]+", session)):
                        raise ProbeError("invalid_session_header")
                    self.session = session
                return result
        except HTTPError as exc:
            # Never print a provider error body, headers, session or URL.
            raise ProbeError(f"http_{exc.code}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ProbeError("network_or_timeout") from exc

    def initialize(self):
        result = self.post("initialize", {"protocolVersion": PROTOCOL, "capabilities": {},
                          "clientInfo": {"name": "openjarvis-andrea-web-evaluation", "version": "1.0"}}, 1)
        if result.get("protocolVersion") != PROTOCOL:
            raise ProbeError("unsupported_negotiated_protocol")
        self.protocol = PROTOCOL
        self.post("notifications/initialized")
        listing = self.post("tools/list", request_id=2)
        tools = listing.get("tools")
        if not isinstance(tools, list) or listing.get("nextCursor"):
            raise ProbeError("unsupported_tool_listing")
        found = [tool for tool in tools if isinstance(tool, dict) and tool.get("name") == "you-search"]
        if len(found) != 1:
            raise ProbeError("search_tool_not_available")
        schema = found[0].get("inputSchema", {})
        if (not isinstance(schema, dict) or schema.get("type") != "object"
                or not isinstance(schema.get("properties"), dict)
                or not {"query", "count"}.issubset(schema["properties"])
                or schema["properties"]["query"].get("type") != "string"
                or schema["properties"]["count"].get("type") != "integer"
                or not isinstance(schema.get("required", []), list)
                or not set(schema.get("required", [])).issubset({"query", "count"})):
            raise ProbeError("unsupported_search_schema")

    def search(self, query, request_id):
        return self.post("tools/call", {"name": "you-search", "arguments": {"query": query, "count": 3}}, request_id)


def public_url(value):
    if not isinstance(value, str) or len(value) > 2048 or any(c.isspace() or ord(c) < 32 for c in value):
        return None
    try:
        url = urlsplit(value)
        host = (url.hostname or "").lower().rstrip(".")
        if url.scheme != "https" or url.username or url.password or url.port not in {None, 443}:
            return None
        if "." not in host or host.endswith((".local", ".localhost", ".internal", ".test")):
            return None
        try:
            if not ipaddress.ip_address(host).is_global:
                return None
        except ValueError:
            pass
        return value
    except ValueError:
        return None


def source_results(result):
    if result.get("isError"):
        raise ProbeError("provider_tool_error")
    payload = result.get("structuredContent")
    if payload is None:
        blocks = result.get("content")
        if not isinstance(blocks, list) or len(blocks) != 1 or blocks[0].get("type") != "text":
            raise ProbeError("unsupported_tool_content")
        payload = decode(blocks[0].get("text", ""))
    # Reuse the upstream known You.com web/news result contract, not text guessing.
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), dict):
        raise ProbeError("unsupported_search_result_shape")
    sources = []
    for section in ("web", "news"):
        items = payload["results"].get(section, [])
        if not isinstance(items, list):
            raise ProbeError("invalid_search_section")
        for item in items:
            if not isinstance(item, dict):
                raise ProbeError("invalid_search_item")
            url = public_url(item.get("url"))
            if not url or any(s["url"] == url for s in sources):
                continue
            title = item.get("title") or "Senza titolo"
            snippets = item.get("snippets", [])
            if not isinstance(title, str) or not isinstance(snippets, list) or any(not isinstance(s, str) for s in snippets):
                raise ProbeError("invalid_search_text")
            snippet = " ".join(snippets) if snippets else item.get("description", "")
            if not isinstance(snippet, str):
                raise ProbeError("invalid_search_text")
            sources.append({"title": title[:200], "url": url, "snippet": snippet[:600]})
            if len(sources) == 3:
                return sources
    return sources


def run(send, client=None):
    client = client or FreeSearchClient()
    try:
        client.initialize()
        send({"event": "initialized"})
        for index, (name, query, expected_domain) in enumerate(CASES, 3):
            started = time.monotonic()
            send({"event": "search_started", "case": name})
            sources = source_results(client.search(query, index))
            send({"event": "row", "case": name, "transportAndFormat": "completed",
                  "elapsedMs": round((time.monotonic() - started) * 1000, 2),
                  "expectedDomainPresent": any(urlsplit(s["url"]).hostname == expected_domain for s in sources),
                  "sources": sources, "qualityVerdict": "pending_review"})
        send({"event": "finished"})
    except (ProbeError, ValueError, TypeError, KeyError, AttributeError) as exc:
        reason = str(exc) if isinstance(exc, ProbeError) else "unsupported_provider_payload"
        send({"event": "failed", "reason": reason})


def worker(pipe):
    try:
        run(pipe.send)
    finally:
        pipe.close()


def main():
    print("Due ricerche pubbliche soltanto. Nessuna lettura di note, memoria, conversazioni o configurazioni private.", flush=True)
    print("Unico fornitore: You.com MCP gratuito di valutazione; nessuna chiave, pagamento, redirezione o ripiego.", flush=True)
    context = multiprocessing.get_context("spawn")
    reader, writer = context.Pipe(duplex=False)
    process = context.Process(target=worker, args=(writer,))
    process.start()
    writer.close()
    deadline = time.monotonic() + TOTAL_SECONDS
    report = {"schema": 1, "mode": "web_provider_evaluation", "provider": "youcom_mcp_free",
              "requested": 2, "attemptedSearchCalls": 0, "automaticRetries": 0, "installed": False,
              "personalDataRead": False, "modelUsed": False, "pagesFetched": False,
              "evaluatedAt": datetime.now(timezone.utc).isoformat(), "rows": [], "completed": False,
              "stoppedReason": None}
    try:
        while time.monotonic() < deadline:
            if not reader.poll(min(.2, max(0, deadline - time.monotonic()))):
                if not process.is_alive():
                    report["stoppedReason"] = "worker_exited_without_completion"
                    break
                continue
            try:
                event = reader.recv()
            except EOFError:
                report["stoppedReason"] = "worker_exited_without_completion"
                break
            if event["event"] == "row":
                report["rows"].append({k: v for k, v in event.items() if k != "event"})
            elif event["event"] == "search_started":
                report["attemptedSearchCalls"] += 1
                print("Ricerca: " + event["case"], flush=True)
            elif event["event"] == "failed":
                report["stoppedReason"] = event["reason"]
                break
            elif event["event"] == "finished":
                report["completed"] = True
                break
        else:
            report["stoppedReason"] = "evaluation_deadline_45s"
    except KeyboardInterrupt:
        report["stoppedReason"] = "interrupted"
    finally:
        if process.is_alive():
            process.terminate()
        process.join(timeout=1)
        if process.is_alive():
            process.kill()
            process.join(timeout=1)
        reader.close()
    report["executed"] = len(report["rows"])
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
