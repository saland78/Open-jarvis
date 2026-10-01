"""Bounded, content-free measurements for the local ASGI request path.

Durations use one monotonic clock. Chunk arrival is not token arrival and the
first text sent by ASGI is not the first text painted by a browser.
"""
from __future__ import annotations

from collections import deque
import json
import time
import uuid


class RequestMeasurement:
    def __init__(self, kind, model, *, clock=time.perf_counter, started=None):
        self.clock = clock
        self.started = clock() if started is None else started
        self.record = {
            "id": uuid.uuid4().hex, "kind": kind, "model": model,
            "retrievalMs": None, "sources": None, "partial": None,
            "firstTextMs": None, "generationFirstTextMs": None,
            "totalMs": None, "generationMs": None, "status": "running",
            "contentChunks": 0, "usage": None, "finishReason": None,
        }
        self.generation_started = None
        self.buffer = bytearray()
        self.done = False
        self.error = False
        self.http_status = None

    def retrieval(self, started, evidence=None):
        self.record["retrievalMs"] = round((self.clock() - started) * 1000, 2)
        if evidence is not None:
            self.record["sources"] = len(evidence["sources"])
            self.record["partial"] = evidence["partial"]

    def generation(self):
        self.generation_started = self.clock()

    def feed(self, body):
        # No body is retained after an SSE frame has been examined.
        self.buffer.extend(body)
        while b"\n\n" in self.buffer:
            frame, _, rest = self.buffer.partition(b"\n\n")
            self.buffer = bytearray(rest)
            if len(frame) > 65536:
                self.error = True
                continue
            lines = frame.decode("utf-8", errors="replace").splitlines()
            if any(line.startswith("event:") for line in lines):
                continue  # sources are not response text or metrics
            data = "\n".join(line[5:].strip() for line in lines if line.startswith("data:"))
            if data == "[DONE]":
                self.done = True
                continue
            try:
                event = json.loads(data)
            except (ValueError, TypeError):
                continue
            if not isinstance(event, dict):
                continue
            self.error |= bool(event.get("error"))
            choices = event.get("choices") or []
            if not isinstance(choices, list):
                choices = []
            for choice in choices:
                if not isinstance(choice, dict):
                    continue
                delta = choice.get("delta") or {}
                if isinstance(delta, dict) and isinstance(delta.get("content"), str) and delta["content"]:
                    now = self.clock()
                    if self.record["firstTextMs"] is None:
                        self.record["firstTextMs"] = round((now - self.started) * 1000, 2)
                        if self.generation_started is not None:
                            self.record["generationFirstTextMs"] = round((now - self.generation_started) * 1000, 2)
                    self.record["contentChunks"] += 1
                if choice.get("finish_reason"):
                    reason = choice["finish_reason"]
                    self.record["finishReason"] = reason if isinstance(reason, str) and reason in {"stop", "length", "tool_calls", "error", "content_filter"} else "other"
            usage = event.get("usage")
            if isinstance(usage, dict):
                self.record["usage"] = {key: usage[key] for key in
                    ("prompt_tokens", "completion_tokens", "total_tokens")
                    if type(usage.get(key)) is int and usage[key] >= 0}
        if len(self.buffer) > 65536:
            self.buffer.clear()
            self.error = True

    def finish(self, status=None):
        now = self.clock()
        self.record["totalMs"] = round((now - self.started) * 1000, 2)
        if self.generation_started is not None:
            self.record["generationMs"] = round((now - self.generation_started) * 1000, 2)
        if status is None:
            status = "error" if self.error or self.http_status != 200 or self.record["finishReason"] == "error" else (
                "incomplete" if not self.done or not self.record["contentChunks"] else
                "truncated" if self.record["finishReason"] == "length" else "completed")
        self.record["status"] = status
        self.buffer.clear()
        return dict(self.record)


class LocalMeasurements:
    """In-memory only: restart clears the last 50 measurements."""
    def __init__(self):
        self.records = deque(maxlen=50)

    def add(self, record):
        self.records.append(record)

    def snapshot(self):
        return {"schema": 1, "clock": "monotonic", "retention": "last_50_in_memory",
                "firstTextBoundary": "asgi_send", "tokenCounts": "upstream_usage_may_include_estimates",
                "records": list(self.records)}
