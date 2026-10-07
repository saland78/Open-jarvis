"""Finite DuckDuckGo HTML evaluation, without local data or installation."""
from __future__ import annotations
import ipaddress
import json
import multiprocessing
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, parse_qs, urlencode
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

ENDPOINT = "https://html.duckduckgo.com/html/"
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

def destination(value):
    if not isinstance(value, str):
        return None
    candidate = "https:" + value if value.startswith("//") else value
    try:
        parts = urlsplit(candidate)
        if parts.scheme == "https" and parts.hostname in {"duckduckgo.com", "html.duckduckgo.com"} and parts.path == "/l/" and not parts.username and not parts.password and parts.port in {None, 443}:
            values = parse_qs(parts.query).get("uddg", [])
            candidate = values[0] if len(values) == 1 else ""
    except ValueError:
        return None
    return public_url(candidate)

class ResultsParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.capture = None
        self.rows = []
        self.current_row = None
        self.no_results = False
        self.blocked = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set(attrs.get("class", "").split())
        identity = attrs.get("id", "")
        if "anomaly" in identity.lower() or any("anomaly" in c.lower() for c in classes):
            self.blocked = True
        if "no-results" in classes or "no-results__message" in classes:
            self.no_results = True
        if tag in {"input", "meta", "link", "img", "br", "hr", "area", "base", "embed", "param", "source", "track", "wbr"}:
            return
        self.stack.append((tag, classes))
        excluded = any(t in {"script", "style"} or "result--ad" in c for t, c in self.stack)
        if excluded or self.capture is not None:
            return
        if tag == "a" and "result__a" in classes:
            self.current_row = None
            self.capture = {"kind": "title", "depth": len(self.stack), "text": [], "url": destination(attrs.get("href"))}
        elif "result__snippet" in classes and self.current_row is not None:
            self.capture = {"kind": "snippet", "depth": len(self.stack), "text": []}

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data):
        if self.capture is not None and not any(t in {"script", "style"} for t, _ in self.stack):
            self.capture["text"].append(data)

    def handle_endtag(self, tag):
        indices = [i for i, (t, _) in enumerate(self.stack) if t == tag]
        if not indices:
            return
        index = indices[-1]
        if self.capture is not None and index < self.capture["depth"]:
            capture, self.capture = self.capture, None
            text = " ".join("".join(capture["text"]).split())
            if capture["kind"] == "title":
                if capture["url"] and text:
                    self.rows.append({"title": text[:200], "url": capture["url"], "snippet": ""})
                    self.current_row = self.rows[-1]
            elif self.current_row is not None:
                self.current_row["snippet"] = text[:600]
        del self.stack[index:]

def parse_results(data):
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise ProbeError("invalid_html_encoding") from exc
    parser = ResultsParser()
    parser.feed(text)
    parser.close()
    if parser.blocked or "bots use DuckDuckGo too" in text or "challenge-form" in text:
        raise ProbeError("provider_challenge")
    if parser.capture is not None:
        raise ProbeError("incomplete_results_html")
    if not parser.rows and not parser.no_results:
        raise ProbeError("unrecognized_results_html")
    rows = []
    for row in parser.rows:
        if not any(s["url"] == row["url"] for s in rows):
            rows.append(row)
        if len(rows) == 3:
            break
    return rows

class DuckSearchClient:
    def __init__(self, opener=None):
        self.opener = opener or build_opener(ProxyHandler({}), NoRedirect())

    def search(self, query):
        request = Request(ENDPOINT, data=urlencode({"q": query}).encode("ascii"), headers={
            "Content-Type": "application/x-www-form-urlencoded", "Accept": "text/html",
            "User-Agent": "OpenJarvis-Andrea-web-evaluation/1.0"})
        try:
            with self.opener.open(request, timeout=8) as response:
                if response.status != 200:
                    raise ProbeError("provider_challenge_or_http_" + str(response.status))
                if response.headers.get("Content-Type", "").split(";", 1)[0].lower() != "text/html":
                    raise ProbeError("unsupported_response_type")
                data = bytearray()
                while True:
                    chunk = response.read1(16384)
                    if not chunk:
                        break
                    data.extend(chunk)
                    if len(data) > LIMIT:
                        raise ProbeError("response_too_large")
                return parse_results(bytes(data))
        except HTTPError as exc:
            raise ProbeError(f"http_{exc.code}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ProbeError("network_or_timeout") from exc

def run(send, client=None):
    client = client or DuckSearchClient()
    try:
        for name, query, expected_domain in CASES:
            started = time.monotonic()
            send({"event": "search_started", "case": name})
            sources = client.search(query)
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
    print("Unico fornitore: DuckDuckGo HTML di valutazione; nessuna chiave, pagamento, redirezione o ripiego.", flush=True)
    context = multiprocessing.get_context("spawn")
    reader, writer = context.Pipe(duplex=False)
    process = context.Process(target=worker, args=(writer,))
    process.start()
    writer.close()
    deadline = time.monotonic() + TOTAL_SECONDS
    report = {"schema": 1, "mode": "web_provider_evaluation", "provider": "duckduckgo_html",
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
