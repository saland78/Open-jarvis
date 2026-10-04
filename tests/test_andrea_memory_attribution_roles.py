"""Identity preservation and literal attribution context; no semantic judge."""
import asyncio
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/andrea"))
import check_memory_attribution as baseline
import check_memory_attribution_roles as candidate
import manual_memory
from runtime import LocalMode

ROOT = Path(__file__).resolve().parents[1]
PROFILE = Path(__file__).resolve().parents[2]/"OpenJarvis-brief-build/profiles/andrea-local.toml"


class RolesCandidateTests(unittest.TestCase):
    def test_previous_candidate_exact_and_criteria_unchanged(self):
        loaded = candidate.load_baseline(ROOT/"scripts/andrea/check_memory_attribution.py")
        self.assertEqual(loaded.CASES, baseline.CASES)
        self.assertEqual(loaded.ROLE_GUIDANCE, baseline.ROLE_GUIDANCE)

    def test_old_baseline_edit_refused_without_using_it(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"old.py"
            path.write_text("raise AssertionError('must not execute')")
            with self.assertRaises(ValueError): candidate.load_baseline(path)

    def test_profile_is_read_only_and_modified_identity_not_replaced(self):
        # Both real checkouts place the public profile under profiles/.
        profile = ROOT/"profiles/andrea-local.toml"
        if not profile.exists(): profile = PROFILE
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            target = project/"profiles/andrea-local.toml"
            target.parent.mkdir()
            original = profile.read_bytes()
            target.write_bytes(original)
            self.assertIn("Sei Jarvis", candidate.profile_identity(project))
            self.assertEqual(target.read_bytes(), original)
            changed = original + b"\n# local change\n"
            target.write_bytes(changed)
            with self.assertRaises(ValueError): candidate.profile_identity(project)
            self.assertEqual(target.read_bytes(), changed)

    def test_literal_json_moves_to_user_without_mutating_payload_or_rewriting_subjects(self):
        for case in baseline.CASES:
            original = baseline.payload(manual_memory, case)
            frozen = json.dumps(original)
            changed = candidate.reframe(original, manual_memory, baseline.ROLE_GUIDANCE, "Sei Jarvis. Identità originale.")
            self.assertEqual(json.dumps(original), frozen)
            self.assertEqual([m["role"] for m in changed["messages"]], ["system", "user", "user"])
            self.assertTrue(changed["messages"][0]["content"].startswith("Sei Jarvis. Identità originale."))
            self.assertEqual(changed["messages"][1]["content"].rsplit("\n", 1)[1], original["messages"][0]["content"].rsplit("\n", 1)[1])
            self.assertEqual(changed["messages"][-1], original["messages"][-1])
            self.assertNotIn(case["text"], changed["messages"][0]["content"])

    def test_same_three_requests_collect_wrong_answer_as_pending_review(self):
        calls = []
        def request(payload, **kwargs):
            calls.append(candidate.reframe(payload, manual_memory, baseline.ROLE_GUIDANCE, "Sei Jarvis."))
            return {"answer": "Ho scelto viola.", "done": True, "finishReason": "stop"}
        with redirect_stdout(io.StringIO()):
            result = baseline.collect(manual_memory, request, lambda: {"records": [], "revision": 3})
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(row["qualityVerdict"] == "pending_review" for row in result["rows"]))
        self.assertEqual([row["criteria"] for row in result["rows"]], [case["criteria"] for case in baseline.CASES])
        self.assertTrue(all(len(call["messages"]) == 3 for call in calls))


class RolesDeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_chat_boundary_keeps_identity_subject_and_no_persistent_write(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)/"state"
            calls = []
            async def sink(scope, receive, send):
                calls.append(json.loads((await receive())["body"]))
                await send({"type": "http.response.start", "status": 200, "headers": []})
                await send({"type": "http.response.body", "body": b"data: [DONE]\n\n"})
            app = LocalMode(sink, baseline.MODEL, 8008, memory=manual_memory.ManualMemory(state))
            for case in baseline.CASES:
                payload = candidate.reframe(baseline.payload(manual_memory, case), manual_memory, baseline.ROLE_GUIDANCE, "Sei Jarvis. Identità originale.")
                body = json.dumps(payload).encode()
                events = []
                async def receive(): return {"type": "http.request", "body": body}
                async def send(event): events.append(event)
                await app({"type": "http", "method": "POST", "path": "/v1/chat/completions",
                           "headers": [(b"host", b"127.0.0.1:8008"), (b"origin", baseline.BASE.encode()),
                                       (b"content-type", b"application/json")]}, receive, send)
                self.assertEqual(events[0]["status"], 200)
                self.assertEqual(calls[-1]["messages"], payload["messages"])
                self.assertEqual(calls[-1]["max_tokens"], 512)
                self.assertFalse(calls[-1].get("tools"))
            self.assertEqual(len(calls), 3)
            self.assertFalse(state.exists())


if __name__ == "__main__": unittest.main()
