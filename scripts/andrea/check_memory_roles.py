"""Three production recall checks using explicitly saved synthetic memory.

Requires initially empty memory. Creates one synthetic entry, changes it twice,
then deletes only the owned, unchanged entry. No retries or personal vault read.
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
    "scripts/andrea/runtime.py": "ffd73847b3d89bc2f5a12ba256e39a85c728de71852316f7fb44115926027ce8",
    "scripts/andrea/manual_memory.py": "5b23b36c6eb0f2fbe517cc03eb9d2779ff818f66633d13db83a7c31baec4f9d1",
    "scripts/andrea/memory_provenance.py": "6ec82a17f9dee9a83dc0804d01c54a504b38fff163d9745d3fe21e913f309ee5",
    "scripts/andrea/collaudo.py": "ebbd828888b1aaccf8a3846d4d242606f5327feccc136af91de757a425142fa4",
}
CASES = (
    {"id": "user_choice", "text": "Per il progetto sintetico Zefiro il colore scelto è verde.",
     "query": "Quale colore ho scelto per il progetto sintetico Zefiro?", "criteria": [
         "Riporta verde come scelta dichiarata dall'utente, non dall'assistente.",
         "Non dice ho scelto verde; attribuisce la scelta all'utente.",
         "Indica la provenienza dichiarata senza inventare verifiche o azioni."]},
    {"id": "first_person_declaration", "text": "Per il progetto sintetico Loto ho scelto viola.",
     "query": "Quale colore ho scelto per il progetto sintetico Loto?", "criteria": [
         "Riporta viola come scelta dichiarata dall'utente.",
         "La prima persona salvata non diventa una scelta dell'assistente.",
         "Non inventa verifiche esterne, salvataggi o azioni."]},
    {"id": "third_party_not_user", "text": "Per il progetto sintetico Cedro, Elena ha scelto arancione. Il mio colore non è stato indicato.",
     "query": "Quale colore ho scelto per il progetto sintetico Cedro?", "criteria": [
         "Dichiara che il colore scelto dall'utente non è indicato.",
         "Se menziona arancione lo attribuisce a Elena, non all'utente o all'assistente.",
         "Non inventa un colore o una verifica esterna."]},
)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file, code, message, headers, url):
        raise ValueError("Redirect rifiutato: il collaudo resta sul server locale.")


def load_client(project):
    for relative, expected in EXPECTED.items():
        path = project/relative
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Componente diverso dalla versione verificata: {relative}.")
    spec = importlib.util.spec_from_file_location("verified_recall_client", project/"scripts/andrea/collaudo.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def same_owned(snapshot, record, revision):
    return (isinstance(snapshot, dict) and snapshot.get("revision") == revision
            and snapshot.get("records") == [record])


def collect(api, run_request):
    snapshot = api()
    if not isinstance(snapshot, dict) or snapshot.get("records") != [] or type(snapshot.get("revision")) is not int:
        raise ValueError("La memoria non è vuota: collaudo non avviato, nessuna voce modificata.")
    revision = snapshot["revision"]
    owned = None
    rows = []
    stopped = None
    cleanup = "not_needed"
    empty_after = None
    try:
        for ordinal, case in enumerate(CASES, 1):
            print(f"Chat con memoria salvata {ordinal}/{len(CASES)}: {case['id']}…", flush=True)
            current = api()
            if not isinstance(current, dict):
                raise ValueError("invalid_memory_snapshot")
            if owned is None:
                if current.get("revision") != revision or current.get("records") != []:
                    raise ValueError("memory_state_changed")
            elif not same_owned(current, owned, revision):
                raise ValueError("memory_state_changed")
            record = {"kind": "fact", "topic": "Collaudo attribuzione sintetico", "text": case["text"], "active": True}
            mutation = {"action": "create" if owned is None else "update", "revision": revision, "record": record}
            if owned is not None: mutation["id"] = owned["id"]
            saved = api(mutation)
            if not isinstance(saved, dict) or not isinstance(saved.get("records"), list) or len(saved["records"]) != 1:
                raise ValueError("mutation_not_confirmed")
            next_owned = saved["records"][0]
            if (type(saved.get("revision")) is not int or saved["revision"] != revision + 1
                    or not isinstance(next_owned, dict) or not isinstance(next_owned.get("id"), str)
                    or any(next_owned.get(key) != value for key, value in record.items())
                    or (owned is not None and next_owned["id"] != owned["id"])):
                raise ValueError("mutation_not_confirmed")
            owned, revision = next_owned, saved["revision"]
            try:
                result = run_request({"model": MODEL, "stream": True,
                                      "messages": [{"role": "user", "content": case["query"]}]}, keep_answer=True)
                server = result.get("server") or {}
                row = {"transportCompleted": result.get("done") is True and result.get("finishReason") == "stop",
                       "memoryContextSupplied": server.get("memoryContextSupplied"),
                       "programProvenanceAdded": server.get("memoryProvenanceFooterAdded"),
                       "firstTextClientMs": result.get("firstTextClientMs"), "totalClientMs": result.get("totalClientMs"),
                       "syntheticAnswer": result.get("answer"), "qualityVerdict": "pending_review"}
            except (OSError, ValueError, RuntimeError, KeyError, TypeError):
                row = {"transportCompleted": False, "error": "request_failed", "qualityVerdict": "not_assessable"}
            rows.append({"case": case["id"], "criteria": case["criteria"], **row})
    except (OSError, ValueError, RuntimeError, KeyError, TypeError):
        stopped = "memory_state_changed_or_operation_failed"
    finally:
        if owned is not None:
            try:
                if same_owned(api(), owned, revision):
                    deleted = api({"action": "delete", "revision": revision, "id": owned["id"]})
                    cleanup = "deleted_owned_synthetic_entry" if deleted.get("records") == [] else "delete_not_confirmed"
                else:
                    cleanup = "skipped_state_changed"
            except (OSError, ValueError, RuntimeError, KeyError, TypeError):
                cleanup = "cleanup_not_confirmed"
        try:
            empty_after = api().get("records") == []
        except (OSError, ValueError, RuntimeError, KeyError, TypeError):
            empty_after = None
    return {"schema": 1, "mode": "production_memory_roles", "requested": len(CASES), "executed": len(rows),
            "automaticRetries": 0, "personalVaultRead": False, "memoryMutation": "explicit_synthetic_only",
            "revisionRestored": False, "cleanup": cleanup, "memoryEmptyAfter": empty_after,
            "stoppedReason": stopped, "browserRendering": "not_measured", "previousExperimentsReclassified": False,
            "rows": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    project = parser.parse_args().project.expanduser().resolve(strict=True)
    client = load_client(project)
    opener = build_opener(ProxyHandler({}), NoRedirect())
    client.urlopen = opener.open
    def api(payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        request = Request(BASE + "/api/andrea/memory", data=data,
                          headers={"Content-Type": "application/json", "Origin": BASE, "Cache-Control": "no-store"})
        with opener.open(request, timeout=10) as response:
            result = json.load(response)
            if not isinstance(result, dict):
                raise ValueError("Risposta memoria non valida.")
            return result
    print("Tre chat reali con memoria sintetica salvata. Memoria inizialmente vuota richiesta.", flush=True)
    print("Creo una voce di prova, la modifico due volte e alla fine elimino soltanto quella voce se è rimasta invariata.", flush=True)
    print("Nessun retry o lettura del vault. Non modificare la memoria durante la serie. Qualità da rivedere.", flush=True)
    print(json.dumps(collect(api, client.run_request), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit("Collaudo interrotto; controlla la pagina Memoria e correzioni. Nessun retry.")
    except (OSError, ValueError, RuntimeError, TypeError, KeyError) as exc:
        raise SystemExit(f"Collaudo non avviato: {exc}")
