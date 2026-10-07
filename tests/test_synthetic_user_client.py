"""Contracts for the real API synthetic conversation harness."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from synthetic_user_client import (  # noqa: E402
    AdvisoryFileLock,
    LockTimeout,
    SyntheticUserClient,
    _validate_api_base_url,
)


SESSION_ID = "S" * 43


class _FakeAPI(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args):
        return

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length))
        if self.path == "/api/sessions":
            body = {"session_id": SESSION_ID}
            status = 200
        elif self.path == "/api/chat" and payload.get("message") == "fail":
            body = {"detail": "synthetic server error"}
            status = 502
        elif self.path == "/api/chat":
            body = {
                "response_kind": "conversation",
                "suggested_replies": ["Follow up"],
                "context": {"course_id": payload.get("course_id")},
                "session_id": SESSION_ID,
                "answer": "real answer from test API",
                "sources": [{"source_path": "ARTICLE-1", "preview": "actual source"}],
                "retrieved_count": 1,
                "trace_id": "a" * 32,
                "needs_clarification": False,
                "matched_bucket_id": None,
            }
            status = 200
        else:
            body = {"detail": "unknown endpoint"}
            status = 404
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class SyntheticUserClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeAPI)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}/api"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()
        cls.server.server_close()

    def test_full_response_and_adaptive_turn_are_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            transcript = Path(directory) / "scenario.json"
            lock = Path(directory) / "api.lock"
            client = SyntheticUserClient(self.base_url, lock_path=lock, timeout_s=2)
            session = client.start_session("student", scenario_id="adaptive", transcript_path=transcript)
            first = client.append_turn(session, "hello")
            second = client.append_turn(session, first.suggested_replies[0])
            self.assertEqual(first.answer, "real answer from test API")
            self.assertEqual(second.record["turn"], 2)
            report = json.loads(transcript.read_text())
            self.assertEqual(report["profile"], "student")
            self.assertEqual(report["session_id"], SESSION_ID)
            self.assertEqual(report["turns"][0]["suggested_replies"], ["Follow up"])
            self.assertEqual(report["turns"][0]["sources"][0]["source_path"], "ARTICLE-1")
            self.assertEqual(report["turns"][0]["context"], {"course_id": None})
            self.assertEqual(report["turns"][0]["status"], 200)
            self.assertIsInstance(report["turns"][0]["elapsed_ms"], int)

    def test_http_error_has_no_invented_assistant_answer(self):
        with tempfile.TemporaryDirectory() as directory:
            transcript = Path(directory) / "error.json"
            client = SyntheticUserClient(self.base_url, lock_path=Path(directory) / "api.lock", timeout_s=2)
            session = client.start_session("ao", scenario_id="error", transcript_path=transcript)
            result = client.append_turn(session, "fail")
            self.assertEqual(result.status, 502)
            self.assertIsNone(result.response)
            self.assertIsNone(result.answer)
            record = json.loads(transcript.read_text())["turns"][0]
            self.assertNotIn("answer", record)
            self.assertEqual(record["error"], {"detail": "synthetic server error"})

    def test_loopback_and_shared_lock_guards(self):
        with self.assertRaises(ValueError):
            _validate_api_base_url("http://example.invalid/api")
        with tempfile.TemporaryDirectory() as directory:
            lock_path = Path(directory) / "api.lock"
            with AdvisoryFileLock(lock_path, timeout_s=1):
                with self.assertRaises(LockTimeout):
                    with AdvisoryFileLock(lock_path, timeout_s=0.05):
                        pass


if __name__ == "__main__":
    unittest.main()
