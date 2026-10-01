"""Read-only, bounded vault adapter for the personal OpenJarvis profile.

Reuses upstream frontmatter parsing; adds body-only evidence, original line
numbers and no-follow file access. No ingestion database or embedding model.
"""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from functools import wraps
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import threading
import time
import unicodedata
from urllib.parse import parse_qs

from openjarvis.connectors.obsidian import _parse_frontmatter

SKIP = {"node_modules", "dist", "__pycache__"}
CURRENT = {"unspecified", "active", "current", "confirmed", "approved", "published", "attiva", "attivo", "confermata", "confermato"}
STOP = set("a al alla alle allo ai agli che chi come con da dal dalla dalle dei del della delle di e è ed gli i il in la le lo ma mi mie miei nel nella nelle non o per quale quali se si su sul sulla sulle un una uno usare usando cosa sono delle note obsidian cerca riassumi rispondi".split())


def normalized(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)).lower()


def words(text):
    return re.findall(r"[^\W_]+", normalized(text))


class VaultError(ValueError):
    def __init__(self, detail, status=400):
        super().__init__(detail)
        self.status = status


def body_info(text):
    lines = text.split("\n")
    start, metadata, status_name = 0, {}, "unspecified"
    if lines and lines[0].lstrip("\ufeff").strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() in {"---", "..."}), None)
        if end is None:
            return len(lines), "ambiguous", "", ""
        # Supply an exact delimiter to the upstream scalar parser.
        scalars = [line for line in lines[1:end] if re.match(r"^(title|status)\s*:", line)]
        metadata, _ = _parse_frontmatter("---\n" + "\n".join(scalars) + "\n---\n")
        start = end + 1
        declarations = [line for line in lines[1:end] if re.match(r"^\s*status\s*:", line)]
        status_name = normalized(str(metadata.get("status", "unspecified"))).strip()
        if len(declarations) > 1 or any(line[:1].isspace() for line in declarations) or not status_name:
            status_name = "ambiguous"
    body = "\n".join(lines[start:])
    heading = re.search(r"(?m)^#\s+(.+)$", body)
    title = str(metadata.get("title") or (heading.group(1) if heading else ""))[:160]
    return start, status_name[:80], body, title


def locked(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return call


class VaultNotes:
    MAX_NOTE = 256 * 1024
    MAX_BYTES = 8 * 1024 * 1024
    MAX_FILES = 1000
    MAX_ENTRIES = 8000

    def __init__(self, state: Path, *, home: Path | None = None):
        self.state = state
        self._lock = threading.RLock()
        self.home = (home or Path.home()).resolve()
        self.config_file = state / "obsidian.json"
        self.vault = ""
        self.cache = {}
        if self.config_file.exists():
            try:
                data = json.loads(self.config_file.read_text())
                self.vault = data["vault"] if isinstance(data, dict) and isinstance(data.get("vault"), str) else ""
            except (OSError, ValueError, TypeError):
                self.vault = ""

    def root(self):
        if not self.vault:
            raise VaultError("Scegli la cartella delle note per abilitare la lettura.")
        path = Path(self.vault)
        if not path.is_absolute() or ".." in path.parts or any(p.startswith(".") for p in path.parts[1:]):
            raise VaultError("Scegli un percorso assoluto, senza cartelle nascoste o risalite.")
        if path == self.home or not path.is_relative_to(self.home):
            raise VaultError("Scegli una cartella di note dentro la tua cartella utente, non l'intera cartella utente.", 403)
        return path

    @contextmanager
    def root_fd(self):
        path = self.root()
        fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
        try:
            for component in path.parts[1:]:
                try:
                    nxt = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                except OSError as exc:
                    raise VaultError("Cartella non accessibile o collegamento simbolico: controlla percorso e permessi.", 403) from exc
                os.close(fd)
                fd = nxt
            yield path, fd
        finally:
            os.close(fd)

    @locked
    def status(self):
        try:
            with self.root_fd() as (root, _):
                return {"configured": True, "available": True, "vault": str(root), "mode": "read-only"}
        except VaultError as exc:
            return {"configured": bool(self.vault), "available": False, "mode": "read-only", "detail": str(exc)}

    @locked
    def configure(self, value):
        if not isinstance(value, str) or len(value) > 1000:
            raise VaultError("Percorso non valido.")
        before = self.vault
        self.vault = value.strip()
        try:
            if self.vault:
                with self.root_fd():
                    pass
        except BaseException:
            self.vault = before
            raise
        self.state.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix="obsidian-", suffix=".tmp", dir=self.state)
        try:
            with os.fdopen(fd, "w") as f:
                json.dump({"vault": self.vault}, f)
            os.replace(name, self.config_file)
        except OSError as exc:
            self.vault = before
            raise VaultError("Impossibile salvare la configurazione locale.", 500) from exc
        finally:
            if os.path.exists(name):
                os.unlink(name)
        self.cache.clear()
        return self.status()

    @staticmethod
    def validate_path(relative):
        if not isinstance(relative, str) or not relative or len(relative) > 500 or "\\" in relative or "\x00" in relative:
            raise VaultError("Percorso della nota non valido.")
        parts = relative.split("/")
        if any(not p or p.startswith(".") or p in SKIP for p in parts) or PurePosixPath(relative).is_absolute() or not relative.lower().endswith(".md"):
            raise VaultError("Usa il percorso relativo di una nota .md, senza collegamenti o cartelle nascoste.", 403)
        return parts

    @locked
    def read(self, relative):
        parts = self.validate_path(relative)
        try:
            with self.root_fd() as (root, rootfd):
                fd = os.dup(rootfd)
                try:
                    for component in parts[:-1]:
                        nxt = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                        os.close(fd)
                        fd = nxt
                    note_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                    try:
                        before = os.fstat(note_fd)
                        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                            raise VaultError("Nota non regolare o collegata ad altri percorsi.", 403)
                        if before.st_size > self.MAX_NOTE:
                            raise VaultError("Nota troppo grande per questa versione.", 413)
                        key = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                        cache_id = (str(root), relative)
                        cached = self.cache.get(cache_id)
                        if cached and cached[0] == key:
                            return dict(cached[1])
                        data = bytearray()
                        while len(data) <= self.MAX_NOTE:
                            chunk = os.read(note_fd, min(65536, self.MAX_NOTE + 1 - len(data)))
                            if not chunk:
                                break
                            data.extend(chunk)
                        after = os.fstat(note_fd)
                        if len(data) > self.MAX_NOTE:
                            raise VaultError("Nota troppo grande per questa versione.", 413)
                        if (after.st_size, after.st_mtime_ns, after.st_ctime_ns) != (before.st_size, before.st_mtime_ns, before.st_ctime_ns):
                            raise VaultError("La nota è cambiata durante la lettura. Riprova.", 409)
                        try:
                            text = data.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
                        except UnicodeError as exc:
                            raise VaultError("La nota non è un file UTF-8 valido.") from exc
                        start, status_name, body, title = body_info(text)
                        substantive = any(line.strip() and not re.match(r"^\s*#", line) for line in body.splitlines())
                        note = {"path": relative, "title": title or Path(relative).stem, "status": status_name, "text": text, "body": body, "bodyStart": start, "hasContent": substantive, "bytes": len(data), "modifiedAt": datetime.fromtimestamp(after.st_mtime, timezone.utc).isoformat()}
                        self.cache[cache_id] = (key, note)
                        return dict(note)
                    finally:
                        os.close(note_fd)
                finally:
                    os.close(fd)
        except FileNotFoundError as exc:
            raise VaultError("Nota non trovata: potrebbe essere stata eliminata o rinominata.", 404) from exc
        except OSError as exc:
            raise VaultError("Nota non accessibile o collegamento simbolico.", 403) from exc

    @staticmethod
    def fragment(note, terms, limit=900):
        lines = note["text"].split("\n")
        start = note["bodyStart"]
        if start < len(lines):
            line_terms = [set(words(line)) for line in lines[start:]]
            scores = [
                sum(t in set().union(*line_terms[i:i+4]) for t in terms) * 10
                + sum(t in line_terms[i] for t in terms)
                for i in range(len(line_terms))
            ]
            start += max(range(len(scores)), key=scores.__getitem__)
        chosen, count = [], 0
        for line in lines[start:]:
            if count >= limit:
                break
            if not chosen and len(line) > limit:
                index = next((normalized(line).find(t) for t in terms if normalized(line).find(t) >= 0), 0)
                line = line[max(0, index - 100):]
            piece = line[:limit-count]
            chosen.append(piece)
            count += len(piece) + 1
        return {"path": note["path"], "title": note["title"], "status": note["status"], "startLine": start+1, "endLine": start+len(chosen), "text": "\n".join(chosen), "modifiedAt": note["modifiedAt"], "eligible": note["hasContent"] and note["status"] in CURRENT}

    @locked
    def search(self, query):
        if not isinstance(query, str) or not query.strip() or len(query) > 200:
            raise VaultError("Scrivi una ricerca di massimo 200 caratteri.")
        terms = list(dict.fromkeys(t for t in words(query) if t not in STOP))[:16]
        if not terms:
            raise VaultError("Aggiungi una parola specifica alla ricerca.")
        with self.root_fd() as (root, _):
            pass
        results, seen = [], set()
        scanned = entries = total_bytes = skipped = 0
        partial = False
        started = time.monotonic()
        for folder, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in SKIP and not (Path(folder)/d).is_symlink())
            entries += len(dirs) + len(files)
            if entries > self.MAX_ENTRIES or time.monotonic()-started > 10:
                partial = True
                break
            for name in sorted(files):
                if name.startswith(".") or not name.lower().endswith(".md"):
                    continue
                if scanned >= self.MAX_FILES or total_bytes >= self.MAX_BYTES or time.monotonic()-started > 10:
                    partial = True
                    break
                relative = (Path(folder)/name).relative_to(root).as_posix()
                try:
                    note = self.read(relative)
                except VaultError:
                    skipped += 1
                    continue
                scanned += 1
                total_bytes += note["bytes"]
                seen.add((str(root), relative))
                body_terms = set(words(note["body"]))
                title_terms = set(words(note["title"] + " " + relative))
                matches = set(terms) & (body_terms | title_terms)
                if matches:
                    score = len(matches)*10 + len(set(terms)&body_terms)*2 + len(set(terms)&title_terms)*8
                    results.append((score, self.fragment(note, terms)))
            if partial:
                break
        self.cache = {key: value for key, value in self.cache.items() if key in seen}
        results.sort(key=lambda pair: (-pair[0], not pair[1]["eligible"], pair[1]["path"]))
        matches = [item for _, item in results]
        return {"query": query.strip(), "vault": str(root), "results": matches[:10], "total": len(matches), "scanned": scanned, "skipped": skipped, "partial": partial, "excluded": sum(not m["eligible"] for m in matches), "elapsedMs": round((time.monotonic()-started)*1000)}

    @locked
    def grounding(self, query):
        result = self.search(query)
        if result["partial"]:
            raise VaultError("Ricerca incompleta: il riassunto non è stato avviato. Restringi la ricerca o controlla i limiti di scansione.")
        candidates = [s for s in result["results"] if s["eligible"]]
        terms = list(dict.fromkeys(t for t in words(query) if t not in STOP))[:16]
        # A query naming a note is more precise than incidental body mentions.
        exact = [s for s in candidates if list(dict.fromkeys(t for t in words(s["title"]) if t not in STOP)) == terms]
        sources = (exact or candidates)[:3]
        if not sources:
            raise VaultError("Nessuna fonte attiva con contenuto utilizzabile. Leggi le note o modifica la ricerca.")
        return {"query": query, "sources": [{**s, "id": f"N{i+1}"} for i, s in enumerate(sources)], "excluded": result["excluded"], "partial": result["partial"]}

    async def api(self, scope, send, payload=None):
        params = parse_qs(scope.get("query_string", b"").decode(errors="replace"))
        try:
            path = scope["path"]
            if path == "/api/andrea/notes/status" and scope["method"] == "GET":
                data = await asyncio.to_thread(self.status)
            elif path == "/api/andrea/notes/search" and scope["method"] == "GET":
                data = await asyncio.to_thread(self.search, params.get("q", [""])[0])
            elif path == "/api/andrea/notes/read" and scope["method"] == "GET":
                note = await asyncio.to_thread(self.read, params.get("path", [""])[0])
                data = {k: v for k, v in note.items() if k not in {"body", "bytes"}}
            elif path == "/api/andrea/notes/config" and scope["method"] == "POST":
                data = await asyncio.to_thread(self.configure, (payload or {}).get("vault"))
            else:
                raise VaultError("Operazione non disponibile.", 404)
            status_code = 200
        except VaultError as exc:
            data, status_code = {"detail": str(exc)}, exc.status
        raw = json.dumps(data, ensure_ascii=False).encode()
        await send({"type": "http.response.start", "status": status_code, "headers": [(b"content-type", b"application/json; charset=utf-8"), (b"cache-control", b"no-store")]})
        await send({"type": "http.response.body", "body": raw})
