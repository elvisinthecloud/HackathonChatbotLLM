"""Current API response and persisted transcript contracts."""
import unittest
from contextlib import contextmanager
from unittest.mock import patch
from support import api as app, make_session as session
import demo_sessions

class SessionContractTests(unittest.IsolatedAsyncioTestCase):
    def test_api_response_defaults_to_support_and_request_cannot_set_response_kind(self):
        base = {"session_id": "s" * 43, "message": "hello"}
        self.assertEqual(app.ChatResponse(session_id="s" * 43, answer="Hi", sources=[], retrieved_count=0).response_kind,
                         "support")
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            app.ChatRequest(**base, response_kind="conversation")

    async def test_saved_turn_marker_is_per_turn_and_history_excludes_only_marked_social(self):
        # The support turn remains in memory; the following social exchange is
        # retained in the transcript but never sent back as model context.
        turns = [("Can I copy this Moodle course?", "Contact an AO.", "", 0, {}),
                 ("Thanks!", "You're welcome.", "", 0, {"_response_kind": "conversation"}),
                 ("One more support question", "Approved reply.", "", 0, {})]
        history, evidence = demo_sessions.context_memory(session("ao", turns=turns), False)
        self.assertIn("Can I copy this Moodle course?", str(history))
        self.assertNotIn("You're welcome.", str(history))
        self.assertNotIn("Thanks!", evidence)

    def test_save_turn_persists_marker_only_in_the_turn_context(self):
        statements = []

        class FakeConnection:
            def execute(self, statement, parameters):
                statements.append((statement, parameters))
                return type("Result", (), {"fetchone": lambda self: (1,)})()

        @contextmanager
        def connection():
            yield FakeConnection()

        current = session("ao", context={"course_id": None}, version=5)
        current["revision"] = 0
        result = {"answer": "You're welcome!", "response_kind": "conversation", "trace_id": None}
        with patch.object(demo_sessions, "get_connection", side_effect=connection):
            demo_sessions.save_turn(current, None, {"course_id": None}, False,
                                    "Thanks!", "", False, result)

        per_turn_context = statements[1][1][-1].obj
        session_context = statements[0][1][1].obj
        self.assertEqual(per_turn_context["_response_kind"], "conversation")
        self.assertNotIn("_response_kind", session_context)
