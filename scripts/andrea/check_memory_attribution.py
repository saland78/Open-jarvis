"""Three finite attribution checks with candidate memory guidance.

Production chat transport and memory formatting; only synthetic context in RAM.
No persistent memory mutation, personal vault read, retry or model judge.
The candidate is supplied for these requests only, not installed in the server.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

BASE = "http://127.0.0.1:8008"
MODEL = "qwen3:4b-instruct-2507-q4_K_M"
EXPECTED = {
    "scripts/andrea/manual_memory.py": "1d21caab261f23c882cccca13a4b0f51a23a46e22c9e57af1eff0cd8d96c7647",
    "scripts/andrea/runtime.py": "7cabb75a5e22bce37455b9dda7b52b8ae2baec12500c69f3a6c1261d80b4e878",
    "scripts/andrea/collaudo.py": "ebbd828888b1aaccf8a3846d4d242606f5327feccc136af91de757a425142fa4",
}

# This is a candidate policy addition, not rewriting the model's answer.
# On adoption the identical text must accompany the real memory context.
ROLE_GUIDANCE = (
    " Tu sei Jarvis, l'assistente; sei distinto dall'utente. "
    "Nella domanda dell'utente, io e ho scelto si riferiscono all'utente, non a te. "
    "Il testo della memoria è una dichiarazione dell'utente: la prima persona "
    "nel testo si riferisce a chi la dichiara, salvo un altro soggetto esplicito. "
    "Per una scelta dell'utente usa hai scelto o il colore che hai indicato; "
    "non presentarla come una tua scelta. Conserva i nomi e i soggetti di terze "
    "persone: la loro scelta non diventa quella dell'utente. "
    "Se manca la scelta richiesta, dichiara che non hai quell'informazione. "
    "Indica che il dato disponibile proviene dalla memoria dichiarata "
    "dall'utente, senza suggerire verifiche esterne. "
)

CASES = (
    {
        "id": "user_choice",
        "text": "Per il progetto sintetico Zefiro il colore scelto è verde.",
        "query": "Quale colore ho scelto per il progetto sintetico Zefiro?",
        "criteria": [
            "Riporta verde come scelta dichiarata dall'utente, non dall'assistente.",
            "Non dice ho scelto verde; attribuisce la scelta all'utente.",
            "Indica la provenienza dichiarata senza inventare verifiche o azioni.",
        ],
    },
    {
        "id": "first_person_declaration",
        "text": "Per il progetto sintetico Loto ho scelto viola.",
        "query": "Quale colore ho scelto per il progetto sintetico Loto?",
        "criteria": [
            "Riporta viola come scelta dichiarata dall'utente.",
            "La prima persona salvata non diventa una scelta dell'assistente.",
            "Non inventa verifiche esterne, salvataggi o azioni.",
        ],
    },
    {
        "id": "third_party_not_user",
        "text": "Per il progetto sintetico Cedro, Elena ha scelto arancione. Il mio colore non è stato indicato.",
        "query": "Quale colore ho scelto per il progetto sintetico Cedro?",
        "criteria": [
            "Dichiara che il colore scelto dall'utente non è indicato.",
            "Se menziona arancione lo attribuisce a Elena, non all'utente o all'assistente.",
            "Non inventa un colore o una verifica esterna.",
        ],
    },
)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file, code, message, headers, url):
        raise ValueError("Redirect rifiutato: il controllo resta sul server locale.")


def load_verified(root):
    for relative, expected in EXPECTED.items():
        path = root / relative
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"File diverso dalla versione verificata: {relative}. Nessuna richiesta inviata.")
    modules = []
    for name, relative in (("memory_attribution_client", "scripts/andrea/collaudo.py"),
                           ("memory_attribution_formatter", "scripts/andrea/manual_memory.py")):
        spec = importlib.util.spec_from_file_location(name, root / relative)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules.append(module)
    return tuple(modules)


def payload(memory, case):
    # Only override the synthetic instance's loader. No file is read or written.
    store = memory.ManualMemory(Path("unused-synthetic-memory"))
    store._load = lambda: {"records": [{
        "id": "00000000-0000-0000-0000-000000000001",
        "kind": "fact", "topic": "Prova sintetica", "text": case["text"], "active": True,
    }]}
    messages = store.messages([{"role": "user", "content": case["query"]}])
    text = messages[0]["content"]
    if not text.startswith(memory.POLICY):
        raise ValueError("Formato memoria diverso dal previsto.")
    messages[0]["content"] = memory.POLICY.rstrip("\n") + ROLE_GUIDANCE + "\n" + text[len(memory.POLICY):]
    return {"model": MODEL, "stream": True, "messages": messages}


def empty_revision(snapshot):
    if not isinstance(snapshot, dict) or snapshot.get("records") != [] or type(snapshot.get("revision")) is not int:
        raise ValueError("La memoria deve restare vuota per isolare la prova. Nessuna voce modificata.")
    return snapshot["revision"]


def collect(memory, run_request, read_snapshot):
    revision = empty_revision(read_snapshot())
    rows = []
    stopped = None
    for ordinal, case in enumerate(CASES, 1):
        print(f"Attribuzione {ordinal}/{len(CASES)}: {case['id']}…", flush=True)
        try:
            unchanged = empty_revision(read_snapshot()) == revision
        except (OSError, ValueError, TypeError):
            unchanged = False
        if not unchanged:
            stopped = "memory_state_changed_or_unavailable"
            break
        try:
            result = run_request(payload(memory, case), keep_answer=True)
            row = {
                "transportCompleted": result.get("done") is True and result.get("finishReason") == "stop",
                "nonEmpty": bool((result.get("answer") or "").strip()),
                "firstTextClientMs": result.get("firstTextClientMs"),
                "totalClientMs": result.get("totalClientMs"),
                "syntheticAnswer": result.get("answer"),
                "qualityVerdict": "pending_review",
            }
        except (OSError, ValueError, RuntimeError, KeyError, TypeError):
            row = {"transportCompleted": False, "error": "request_failed",
                   "qualityVerdict": "not_assessable"}
        rows.append({"case": case["id"], "criteria": case["criteria"], **row})
    try:
        state_unchanged = empty_revision(read_snapshot()) == revision
    except (OSError, ValueError, TypeError):
        state_unchanged = False
    return {"schema": 1, "mode": "candidate_memory_attribution", "requested": len(CASES),
            "automaticRetries": 0, "personalVaultRead": False, "memoryMutated": False,
            "emptyMemoryRevisionUnchanged": state_unchanged,
            "executed": len(rows), "stoppedReason": stopped,
            "candidateInstalled": False, "browserRendering": "not_measured", "rows": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    root = parser.parse_args().project.expanduser().resolve(strict=True)
    client, memory = load_verified(root)
    opener = build_opener(ProxyHandler({}), NoRedirect())
    client.urlopen = opener.open
    def snapshot():
        with opener.open(Request(BASE + "/api/andrea/memory", headers={"Cache-Control": "no-store"}), timeout=5) as response:
            return json.load(response)
    print("Tre richieste sintetiche, senza retry. OpenJarvis deve essere acceso e la memoria vuota.", flush=True)
    print("La correzione delle istruzioni è candidata e vale soltanto per queste prove; non viene installata.", flush=True)
    print("Le risposte richiedono revisione: trasporto completato non significa qualità superata.", flush=True)
    print(json.dumps(collect(memory, client.run_request, snapshot), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit("Controllo interrotto: serie non conclusa, nessun retry automatico.")
    except (OSError, ValueError, RuntimeError, TypeError) as exc:
        raise SystemExit(f"Controllo interrotto: {exc}")
