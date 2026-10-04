"""Program-generated provenance footer, independent of the model's wording.

Adds no text before the model's first content; never rewrites its assertions.
Only a nonempty stream ending with stop is eligible. Notes do not use this.
"""
from __future__ import annotations

import json

NOTICE = (
    "\n\n*Avviso del programma: la memoria dichiarata dall'utente è stata fornita "
    "come contesto, senza verifica esterna. Questo non certifica l'uso di ogni "
    "voce o la correttezza della risposta.*"
)


class MemoryProvenanceFooter:
    def __init__(self):
        self.buffer = bytearray()
        self.has_content = False
        self.has_error = False
        self.added = False

    def feed(self, body: bytes, *, final=False):
        self.buffer.extend(body)
        out = bytearray()
        while True:
            endings = [(self.buffer.find(end), end) for end in (b"\n\n", b"\r\n\r\n")]
            found = [(i, end) for i, end in endings if i >= 0]
            if not found:
                break
            i, separator = min(found, key=lambda item: item[0])
            frame = bytes(self.buffer[:i])
            del self.buffer[:i + len(separator)]
            lines = frame.decode("utf-8").splitlines()
            kind = next((line[6:].strip() for line in lines if line.startswith("event:")), "message")
            data = "\n".join(line[5:].strip() for line in lines if line.startswith("data:"))
            if kind != "message" or not data or data == "[DONE]":
                out.extend(frame + separator)
                continue
            try:
                value = json.loads(data)
            except ValueError:
                # Do not turn an invalid event into a successful answer.
                self.has_error = True
                out.extend(frame + separator)
                continue
            if not isinstance(value, dict):
                self.has_error = True
                out.extend(frame + separator)
                continue
            self.has_error = self.has_error or bool(value.get("error"))
            choices = value.get("choices", [])
            if not isinstance(choices, list):
                choices = []
            self.has_error = self.has_error or any(isinstance(c, dict) and c.get("finish_reason") is not None and c.get("finish_reason") != "stop" for c in choices)
            content_choices = [c for c in choices if isinstance(c, dict) and isinstance(c.get("delta"), dict)
                               and isinstance(c["delta"].get("content"), str) and c["delta"]["content"]]
            self.has_content = self.has_content or any(c["delta"]["content"].strip() for c in content_choices)
            stop = any(isinstance(c, dict) and c.get("finish_reason") == "stop" for c in choices)
            if stop and self.has_content and not self.has_error and not self.added:
                self.added = True
                if content_choices:
                    # A combined final-content/stop frame: keep text before the
                    # footer and preserve every other field including usage.
                    content_choices[-1]["delta"]["content"] += NOTICE
                    frame = b"data: " + json.dumps(value, ensure_ascii=False).encode()
                else:
                    annotation = {"choices": [{"index": 0, "delta": {"content": NOTICE}, "finish_reason": None}]}
                    out.extend(b"data: " + json.dumps(annotation, ensure_ascii=False).encode() + b"\n\n")
            out.extend(frame + separator)
        if len(self.buffer) > 256 * 1024:
            raise ValueError("Evento streaming troppo grande per l'avviso di provenienza.")
        if final:
            out.extend(self.buffer)
            self.buffer.clear()
        return bytes(out)
