"""The control client consumes streaming and preserves review boundaries."""
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/andrea"))
import collaudo


class Response(io.BytesIO):
    headers = {"x-openjarvis-request-id": "test-id"}


class ControlClientTests(unittest.TestCase):
    def test_response_sources_roles_usage_and_text_are_distinguished(self):
        body = (b'event: local_sources\ndata: {"sources":[{"id":"N1","text":"PRIVATE NOTE"}]}\n\n'
                b'data: {"choices":[{"delta":{"role":"assistant"}}]}\n\n'
                b'data: {"choices":[{"delta":{"content":"SYNTHETIC [N1]."}}]}\n\n'
                b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n')
        records = b'{"records":[{"id":"test-id","status":"completed"}]}'
        for keep in (False, True):
            requests = []
            def open_local(request, **kwargs):
                requests.append(request)
                return Response(body if len(requests) == 1 else records)
            with patch.object(collaudo, "urlopen", open_local):
                result = collaudo.run_request({"stream": True}, keep_answer=keep)
            self.assertEqual(result["sources"], ["N1"])
            self.assertEqual(result["server"]["id"], "test-id")
            self.assertTrue(result["done"])
            self.assertEqual(result["answer"], "SYNTHETIC [N1]." if keep else None)
            self.assertNotIn("PRIVATE NOTE", json.dumps(result))
            self.assertEqual(requests[0].get_header("Origin"), collaudo.BASE)

    def test_quality_suite_always_requires_review_even_when_formal_checks_pass(self):
        with patch.object(sys, "argv", ["collaudo.py", "quality"]), patch.object(collaudo, "run_request") as run, patch("sys.stdout", new_callable=io.StringIO) as output:
            def response(payload, **kwargs):
                return {"answer":"Zero libri [N1] [N2].", "done":True, "finishReason":"stop"}
            run.side_effect = response
            collaudo.main()
        raw = output.getvalue()
        data = json.loads(raw[raw.index('{\n'):])
        self.assertEqual(len(data["rows"]), 6)
        self.assertTrue(all(r["qualityVerdict"] == "pending_review" for r in data["rows"]))
        self.assertTrue(all("criteria" in r for r in data["rows"]))
        cases = json.loads(Path(collaudo.__file__).with_name("quality_cases.json").read_text())
        for call, case in zip(run.call_args_list, cases):
            self.assertEqual(call.args[0]["notes_query"], case["query"])
            self.assertEqual(call.args[0]["notes_sources"], case["sources"])
            self.assertEqual(call.args[0]["messages"], [{"role": "user", "content": case["query"]}])

    def test_unknown_and_missing_citations_fail_formal_checks(self):
        case = {"sources":[{"id":"N1"}], "expectedCitations":["N1"]}
        result = {"answer":"Dato [N7].", "done":True, "finishReason":"stop"}
        checks = collaudo.formal_checks(case, result)
        self.assertFalse(checks["noUnknownCitations"])
        self.assertFalse(checks["expectedCitationsPresent"])


if __name__ == "__main__":
    unittest.main()
