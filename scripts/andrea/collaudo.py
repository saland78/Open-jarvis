"""Local end-to-end timing and synthetic quality collection. No model judge.

Quality answers are collected for review, never certified by keyword matching.
Timing mode discards answer text. Both modes use only 127.0.0.1:8008.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import statistics
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8008"
MODEL = "qwen3:4b-instruct-2507-q4_K_M"


def run_request(payload, *, keep_answer=False):
    request = Request(BASE + "/v1/chat/completions", data=json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json", "Origin": BASE})
    started = time.perf_counter()
    first = None
    answer = []
    completed = False
    finish_reason = None
    sources = []
    with urlopen(request, timeout=100) as response:
        request_id = response.headers.get("x-openjarvis-request-id")
        frame = []
        for raw in response:
            line = raw.decode("utf-8").rstrip("\r\n")
            if line:
                frame.append(line)
                continue
            data = "\n".join(x[5:].strip() for x in frame if x.startswith("data:"))
            event_type = next((x[6:].strip() for x in frame if x.startswith("event:")), "message")
            frame.clear()
            if data == "[DONE]":
                completed = True
                continue
            if not data:
                continue
            event = json.loads(data)
            if event_type == "local_sources":
                sources = [s["id"] for s in event.get("sources", [])]
                continue
            if event.get("error"):
                raise RuntimeError("Il backend ha segnalato un errore durante lo streaming.")
            for choice in event.get("choices", []):
                content = choice.get("delta", {}).get("content", "")
                if content:
                    if first is None:
                        first = (time.perf_counter() - started) * 1000
                    if keep_answer:
                        answer.append(content)
                if choice.get("finish_reason"):
                    finish_reason = choice["finish_reason"]
    total = (time.perf_counter() - started) * 1000
    with urlopen(BASE + "/api/andrea/metrics", timeout=5) as response:
        server = next((r for r in json.load(response)["records"] if r["id"] == request_id), None)
    return {"requestId": request_id, "firstTextClientMs": round(first, 2) if first is not None else None,
            "totalClientMs": round(total, 2), "done": completed, "finishReason": finish_reason,
            "server": server, "sources": sources, "answer": "".join(answer) if keep_answer else None}


def formal_checks(case, result):
    citations = set(re.findall(r"\[N(\d+)\]", result["answer"] or ""))
    allowed = {s["id"][1:] for s in case["sources"]}
    expected = {s[1:] for s in case["expectedCitations"]}
    return {"streamCompleted": result["done"], "notTruncated": result["finishReason"] == "stop",
            "expectedCitationsPresent": expected <= citations, "noUnknownCitations": citations <= allowed,
            "nonEmpty": bool((result["answer"] or "").strip())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("quality", "brief", "timings"))
    parser.add_argument("--notes-query", default="kpi self publishing")
    parser.add_argument("--repeats", type=int, default=3, choices=range(1, 11))
    parser.add_argument("--case", choices=("explicit", "unknown", "conflict", "historical", "opinion", "no_answer"))
    args = parser.parse_args()
    if args.case and args.mode != "quality":
        parser.error("--case è disponibile soltanto con quality")
    rows = []
    if args.mode in {"quality", "brief"}:
        cases_file = "brief_cases.json" if args.mode == "brief" else "quality_cases.json"
        cases = json.loads(Path(__file__).with_name(cases_file).read_text())
        if args.case:
            cases = [case for case in cases if case["id"] == args.case]
        if args.mode == "brief":
            print("Modalità passaggi brevi: citazioni originali, senza generazione del modello. Non è il precedente test della sintesi libera.", flush=True)
        print(f"Casi sintetici selezionati: {len(cases)}. Nessuna nota personale letta. Stesso percorso delle risposte sulle note, con estratti forniti; i campi espliciti possono rispondere senza modello. La qualità richiede revisione delle risposte.", flush=True)
        for i, case in enumerate(cases, 1):
            print(f"Caso {i}/{len(cases)}: {case['id']}…", flush=True)
            result = run_request({"model": MODEL, "stream": True,
                                  "messages": [{"role": "user", "content": case["query"]}],
                                  "notes_query": case["query"], "notes_sources": case["sources"],
                                  "notes_brief": args.mode == "brief"}, keep_answer=True)
            rows.append({"case": case["id"], "criteria": case["criteria"], "result": result,
                         "formalChecks": formal_checks(case, result), "qualityVerdict": "pending_review"})
    else:
        print("Misure da client di controllo, non dal browser. Stato freddo/caldo non determinato; nessun modello viene scaricato dalla memoria.", flush=True)
        for kind in ("chat", "notes"):
            for i in range(args.repeats):
                print(f"{kind}: prova {i + 1}/{args.repeats}…", flush=True)
                payload = {"model": MODEL, "stream": True,
                           "messages": [{"role": "user", "content": "Scrivi soltanto: pronto." if kind == "chat" else args.notes_query}]}
                if kind == "notes":
                    payload["notes_query"] = args.notes_query
                result = run_request(payload)
                rows.append({"kind": kind, "result": result})
        for kind in ("chat", "notes"):
            values = [r["result"]["totalClientMs"] for r in rows if r["kind"] == kind and r["result"]["server"] and r["result"]["server"]["status"] == "completed"]
            if values:
                print(f"{kind}: totale mediano {statistics.median(values):.0f} ms; minimo {min(values):.0f}; massimo {max(values):.0f}.")
    print(json.dumps({"schema": 1, "mode": args.mode, "rows": rows}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except HTTPError as exc:
        raise SystemExit(f"Collaudo interrotto: OpenJarvis ha risposto con stato HTTP {exc.code}. Nessuna configurazione modificata.")
    except (URLError, TimeoutError):
        raise SystemExit("Collaudo interrotto: verifica che OpenJarvis sulla porta 8008 sia acceso. Nessuna configurazione modificata.")
    except (ValueError, RuntimeError):
        raise SystemExit("Collaudo interrotto: risposta incompleta o non valida. Nessuna configurazione modificata.")
