"""Offline regression checks for deterministic social replies and support routing."""
import asyncio
import os
from pathlib import Path
import sys
import unittest
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "tests")]

from test_backend import test_env
from test_grounding import chunk

with patch.dict(os.environ, test_env()):
    import app
    import conversation
    import demo_sessions
    import rag
    from demo_policy import PROFILES


def session(profile="ao", context=None, selected=None, version=0, turns=None):
    return {
        "id": "offline-session",
        "profile": PROFILES[profile],
        "selected_course_id": selected,
        "context": context or {},
        "version": version,
        "turns": list(turns or []),
    }


class ConversationalReplyTests(unittest.TestCase):
    def test_supported_social_intents_have_stable_replies(self):
        examples = [
            "Hi",
            "Thanks!",
            "Thank you for your help.",
            "Can you help me?",
            "What else can you help me with?",
            "What can you do?",
        ]
        for text in examples:
            with self.subTest(text=text):
                first = conversation.conversational_reply(text)
                self.assertIsInstance(first, str)
                self.assertTrue(first.strip())
                self.assertEqual(first, conversation.conversational_reply(text))

    def test_support_or_mixed_intents_are_not_swallowed_as_social(self):
        examples = [
            "I'm still stuck copying a Moodle course as the Academics Officer.",
            "Thanks, but the course still says sts1.auth.ecuf.deas.mil refused to connect.",
            "Thanks! Can you tell me why my Moodle lesson will not launch?",
            "I appreciate it. Should I enroll in 5500?",
        ]
        for text in examples:
            with self.subTest(text=text):
                self.assertIsNone(conversation.conversational_reply(text))


class ConversationRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_personalized_greetings_use_only_server_profile_and_skip_retrieval(self):
        expected = {
            "student": ("Sgt Rodriguez", "mateo.a.rodriguez", "E-5", "Student"),
            "instructor": ("MSgt Thompson", "james.thompson", "E-8", "Adjunct Faculty"),
            "ao": ("LtCol Walker", "daniel.r.walker", "O-5", "Academics Officer"),
            "training-manager": ("GySgt Bennett", "alicia.m.bennett", "E-7", "Training Manager"),
            "regional-director": ("Col Mitchell", "rebecca.mitchell", "O-6", "Regional Director"),
        }
        with patch.object(rag, "langfuse", self.fake_langfuse()), \
             patch.object(rag, "retrieve_chunks", new_callable=AsyncMock) as retrieve, \
             patch.object(rag, "generate_answer", new_callable=AsyncMock) as generate:
            for profile_id, (greeting, username, grade, role) in expected.items():
                with self.subTest(profile=profile_id):
                    profile = PROFILES[profile_id]
                    self.assertEqual((profile['username'], profile['pay_grade'], profile['role']), (username, grade, role))
                    result = await rag.answer_question("Hello!", session(profile_id), None)
                    self.assertEqual(result['answer'], f"Hello, {greeting}! What would you like help with?")
                    self.assertEqual(result['sources'], [])
            retrieve.assert_not_called()
            generate.assert_not_called()

    @contextmanager
    def fake_span(self, *args, **kwargs):
        yield MagicMock()

    def fake_langfuse(self):
        client = MagicMock()
        client.start_as_current_span.side_effect = self.fake_span
        client.get_current_trace_id.return_value = "offline-trace"
        return client

    async def test_social_turn_skips_all_external_work_and_marks_response_kind(self):
        current = session(context={"course_id": "5500", "system_area": "Moodle"}, selected="5500", version=4)
        with patch.object(rag, "langfuse", self.fake_langfuse()), \
             patch.object(rag, "extract_image_context", new_callable=AsyncMock) as vision, \
             patch.object(rag, "retrieve_chunks", new_callable=AsyncMock) as retrieve, \
             patch.object(rag, "generate_answer", new_callable=AsyncMock) as generate, \
             patch.object(rag, "embed_text", new_callable=AsyncMock) as embed:
            result = await rag.answer_question("Thanks!", current, "5500")

        self.assertEqual(result["response_kind"], "conversation")
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["retrieved_count"], 0)
        self.assertFalse(result["needs_clarification"])
        self.assertEqual(result["context"], current["context"])
        self.assertFalse(result["_context_changed"])
        for operation in (vision, retrieve, generate, embed):
            operation.assert_not_called()

    async def test_mixed_thanks_and_support_continues_through_role_filtered_retrieval(self):
        current = session("ao")
        source = chunk("MOODLE-COPY-003")
        access_seen = []
        async def retrieve(*args, **kwargs):
            access_seen.append(rag.ACCESS.get())
            return [source], None, 1.0, []

        with patch.object(rag, "langfuse", self.fake_langfuse()), \
             patch.object(rag, "retrieve_chunks", side_effect=retrieve) as retrieve_mock, \
             patch.object(rag, "generate_answer", new_callable=AsyncMock,
                          return_value="Please contact a user with the AO role."):
            result = await rag.answer_question(
                "Thanks, I'm still stuck copying this Moodle course.", current, None
            )

        self.assertEqual(result["response_kind"], "support")
        retrieve_mock.assert_awaited_once()
        self.assertEqual(access_seen[0].role, "Academics Officer")
        self.assertIn("MOODLE-COPY-003", access_seen[0].article_ids)
        self.assertEqual(result["sources"][0]["source_path"], "MOODLE-COPY-003")

    async def test_social_turn_after_old_launch_error_does_not_erase_evidence(self):
        turns = [("The lesson says sts1.auth.ecuf.deas.mil refused to connect", "support reply", "", 0, {})]
        turns += [("Thanks!", "You're welcome!", "", 0, {"_response_kind": "conversation"}) for _ in range(7)]
        context = {"course_id": "CYBERM0000", "activity": "course-content", "system_area": "MCeLE",
                   "delivery_area": "MCeLE", "course_query": "CYBERM0000"}
        current = session("student", context=context, selected="CYBERM0000", turns=turns)
        with patch.object(rag, "langfuse", self.fake_langfuse()), \
             patch.object(rag, "retrieve_chunks", new_callable=AsyncMock) as retrieve:
            # The delayed launch statement is still relevant to a follow-up, even
            # though social exchanges must not consume the six-turn support window.
            history, evidence = demo_sessions.context_memory(current, False)
            self.assertNotIn("You're welcome!", str(history))
            self.assertIn("sts1.auth.ecuf.deas.mil refused to connect", evidence)
            source = chunk("MCELE-LAUNCH-001")
            retrieve.return_value = ([source], None, 1.0, [])
            with patch.object(rag, "generate_answer", new_callable=AsyncMock,
                              return_value="Check the selected MCeLE course."):
                result = await rag.answer_question("It still fails; what next?", current, "CYBERM0000")

        self.assertEqual(result["response_kind"], "support")
        retrieve.assert_awaited_once()
        self.assertIn("The lesson says sts1.auth.ecuf.deas.mil refused to connect", evidence)

    async def test_nine_approved_article_routes_survive_seven_social_turns(self):
        """Route policy is exercised offline with retrieval/generation stubbed."""
        cases = [
            ("student", "MCELE-LAUNCH-001", "MCeLE", "course-content", "CYBERM0000",
             "The lesson says sts1.auth.ecuf.deas.mil refused to connect", "It still fails to launch."),
            ("instructor", "MOODLE-COPY-002", "Moodle", "course-management", None,
             "I need to copy a Moodle course.", "Can I copy this Moodle course?"),
            ("ao", "MOODLE-COPY-001", "Moodle", "course-management", None,
             "I need to copy a Moodle course.", "How do I copy a Moodle course?"),
            ("ao", "MOODLE-COPY-003", "Moodle", "course-management", None,
             "The Moodle copy is stuck.", "I'm still stuck copying this Moodle course."),
            ("training-manager", "MCELE-ECDEP-001", "MCeLE", "enrollment", "5500",
             "Review this Marine's ECDEP enrollment request for 5500.", "Should I recommend or deny this 5500 request?"),
            ("training-manager", "MCELE-ENROLLMENT-REPORT-001", "MCeLE", "enrollment", None,
             "I need to verify an Enrollment Report enrollment status.", "How do I check the Enrollment Report?"),
            ("student", "MCELE-RRC-001", "MCeLE", "course-credit", None,
             "I need Reserve Retirement Credits for this year.", "How do I check my RRC?"),
            ("student", "MCELE-EPME-001", "MCeLE", "enrollment", "EPME5000",
             "I need to enroll in the EPME5000 Sergeants School DEP.", "Can I enroll in EPME5000?"),
            ("student", "MCELE-CSC-001", "MCeLE", "enrollment", "CSC",
             "I cannot find Command and Staff (CSC) in My Courses.", "How do I access CSC?"),
        ]
        for profile_id, article_id, area, activity, course_id, prior_question, followup in cases:
            with self.subTest(article_id=article_id):
                context = {"course_id": course_id, "course_query": course_id,
                           "activity": activity, "system_area": area,
                           "delivery_area": area, "course_known": bool(course_id)}
                turns = [(prior_question, "Earlier support response.", "", 0, {})]
                turns += [("Thanks!", "You're welcome!", "", 0,
                           {"_response_kind": "conversation"}) for i in range(7)]
                current = session(profile_id, context=context, selected=course_id, turns=turns)
                source = chunk(article_id)
                seen = []

                async def retrieve(*args, **kwargs):
                    seen.append((rag.ACCESS.get(), kwargs.get("history"), kwargs.get("image_context")))
                    return [source], None, 1.0, []

                with patch.object(rag, "langfuse", self.fake_langfuse()), \
                     patch.object(rag, "retrieve_chunks", side_effect=retrieve), \
                     patch.object(rag, "generate_answer", new_callable=AsyncMock,
                                  return_value=source["content"]):
                    result = await rag.answer_question(followup, current, course_id)

                self.assertEqual(result["response_kind"], "support")
                self.assertEqual(result["retrieved_count"], 1)
                self.assertEqual(len(seen), 1)
                expected_ids = (("MOODLE-COPY-001", "MOODLE-COPY-003")
                                if article_id in ("MOODLE-COPY-001", "MOODLE-COPY-003")
                                else (article_id,))
                self.assertEqual(seen[0][0].article_ids, expected_ids)
                self.assertTrue(seen[0][1])
                self.assertNotIn("You're welcome!", str(seen[0][1]))
                self.assertIn(prior_question, str(seen[0][1]))

    def test_role_denials_and_ambiguous_contexts_remain_closed_or_clarified(self):
        from demo_policy import resolve_access, resolve_context
        rd_context = {"course_id": None, "activity": None, "system_area": None}
        rd_access = resolve_access(PROFILES["regional-director"], rd_context, "help")
        self.assertEqual(rd_access.article_ids, ())
        instructor_context = {"course_id": None, "activity": "course-management",
                              "system_area": "Moodle", "unresolved": False}
        instructor_access = resolve_access(PROFILES["instructor"], instructor_context,
                                           "copy Moodle course")
        self.assertEqual(instructor_access.article_ids, ("MOODLE-COPY-002",))
        student_access = resolve_access(PROFILES["student"], instructor_context,
                                        "copy Moodle course")
        self.assertEqual(student_access.article_ids, ())
        no_instructor_ecdep = resolve_access(PROFILES["instructor"],
            {**instructor_context, "activity": "enrollment", "system_area": "MCeLE", "course_id": "5500"},
            "5500 ECDEP enrollment")
        self.assertEqual(no_instructor_ecdep.article_ids, ())

        _, conflict, _ = resolve_context("5500", {}, "5500",
            "I need to enroll in 5500 and copy a Moodle course")
        self.assertIsNotNone(conflict)
        _, mapping_question, _ = resolve_context("6800", {}, "6800",
            "I need to launch course content for 6800")
        self.assertIsNotNone(mapping_question)

    async def test_course_change_clears_old_evidence_and_preserves_no_old_course(self):
        current = session("student", context={"course_id": "CYBERM0000"}, selected="CYBERM0000", version=2,
                          turns=[("old course details", "old answer", "old screenshot", 2, {})])
        with patch.object(rag, "langfuse", self.fake_langfuse()), \
             patch.object(rag, "context_memory") as memory:
            result = await rag.answer_question("Thanks!", current, "5500")

        self.assertEqual(result["response_kind"], "conversation")
        memory.assert_not_called()
        self.assertTrue(result["_context_changed"])
        self.assertEqual(result["context"]["course_id"], "5500")
        self.assertIsNone(result["context"]["system_area"])

    async def test_greeting_capability_sequence_after_ao_stuck_support(self):
        context = {"course_id": None, "course_query": None, "activity": "course-management",
                   "system_area": "Moodle", "delivery_area": None}
        current = session("ao", context=context, turns=[
            ("The Moodle course copy is stuck.", "Contact an AO.", "", 0, {})
        ])
        self.assertIsNone(conversation.conversational_reply("I'm still stuck copying this Moodle course."))
        source = chunk("MOODLE-COPY-003")
        seen = []

        async def retrieve(*args, **kwargs):
            seen.append(rag.ACCESS.get())
            return [source], None, 1.0, []

        with patch.object(rag, "langfuse", self.fake_langfuse()), \
             patch.object(rag, "retrieve_chunks", side_effect=retrieve), \
             patch.object(rag, "generate_answer", new_callable=AsyncMock,
                          return_value=source["content"]):
            for message in ("Hello!", "Thanks, I appreciate it.",
                            "Oh okay, thank you! Are you able to help me with other things?"):
                result = await rag.answer_question(message, current, None)
                self.assertEqual(result["response_kind"], "conversation")
                self.assertEqual(result["sources"], [])
                self.assertEqual(seen, [])
                if "other things" in message:
                    self.assertEqual(result["answer"], "Yes. What would you like help with?")
                current["turns"].append((message, result["answer"], "", current["version"],
                                          {"_response_kind": result["response_kind"]}))
            # The next real follow-up still goes through the Academics Officer grant.
            response = await rag.answer_question(
                "I'm still stuck copying this Moodle course.", current, None
            )
        self.assertEqual(response["response_kind"], "support")
        self.assertEqual(response["sources"][0]["source_path"], "MOODLE-COPY-003")
        self.assertEqual(seen[-1].role, "Academics Officer")

    async def test_unresolved_selection_preserves_context_and_version(self):
        prior = {"course_id": "5500", "system_area": "Moodle", "unresolved": "task"}
        current = session("student", context=prior, selected="5500", version=3)
        with patch.object(rag, "langfuse", self.fake_langfuse()), \
             patch.object(rag, "resolve_context") as resolve:
            result = await rag.answer_question("Thanks!", current, "5500")
        self.assertEqual(result["context"], prior)
        self.assertFalse(result["_context_changed"])
        resolve.assert_not_called()

    async def test_exact_student_sequence_delays_retrieval_until_error(self):
        current = session("student")
        source = chunk("MCELE-LAUNCH-001")

        async def turn(message, course=None):
            result = await rag.answer_question(message, current, course)
            current["version"] += int(result["_context_changed"])
            current["context"] = result["context"]
            current["selected_course_id"] = course
            current["turns"].append((message, result["answer"], result["_image_text"],
                current["version"], {**result["context"], "_response_kind": result["response_kind"]}))
            return result

        with patch.object(rag, "langfuse", self.fake_langfuse()), \
             patch.object(rag, "retrieve_chunks", new_callable=AsyncMock,
                          return_value=([source], None, 1.0, [])) as retrieve, \
             patch.object(rag, "generate_answer", new_callable=AsyncMock,
                          return_value="Follow the approved guidance. [1]") as generate:
            for message in ("Hello!", "How are you today?", "Thanks, I appreciate it."):
                result = await turn(message)
                self.assertEqual(result["response_kind"], "conversation")
                self.assertFalse(result["needs_clarification"])
            result = await turn("I cannot launch my CYBERM0000 course.")
            self.assertTrue(result["needs_clarification"])
            self.assertIn("exact error", result["answer"])
            await turn("Okay, thank you!")
            retrieve.assert_not_called()
            generate.assert_not_called()
            result = await turn("The error says sts1.auth.ecuf.deas.mil refused to connect.")
            retrieve.assert_awaited_once()
            self.assertEqual(result["sources"][0]["source_path"], "MCELE-LAUNCH-001")
            # A course change during a greeting must invalidate old error evidence.
            await turn("Hello!", "CDETBAIC01")
            result = await turn("Thanks, but I still cannot launch the course.", "CDETBAIC01")
            self.assertTrue(result["needs_clarification"])
            self.assertEqual(result["retrieved_count"], 0)
            retrieve.assert_awaited_once()
            self.assertNotIn("sts1.auth", demo_sessions.context_memory(current, False)[1])

    async def test_screenshot_turn_is_always_support(self):
        current = session("student")
        source = chunk("MCELE-LAUNCH-001")
        with patch.object(rag, "langfuse", self.fake_langfuse()), \
             patch.object(rag, "extract_image_context", new_callable=AsyncMock,
                          return_value={"description": "login error"}) as vision, \
             patch.object(rag, "retrieve_chunks", new_callable=AsyncMock,
                          return_value=([source], None, 1.0, [])), \
             patch.object(rag, "generate_answer", new_callable=AsyncMock,
                          return_value="Check the selected MCeLE course."):
            result = await rag.answer_question("Hi", current, None, image="eA==")
        self.assertEqual(result["response_kind"], "support")
        vision.assert_awaited_once()

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

        @contextmanager
        def connection():
            yield FakeConnection()

        current = session("ao", context={"course_id": None}, version=5)
        result = {"answer": "You're welcome!", "response_kind": "conversation", "trace_id": None}
        with patch.object(demo_sessions, "get_connection", side_effect=connection):
            demo_sessions.save_turn(current, None, {"course_id": None}, False,
                                    "Thanks!", "", False, result)

        per_turn_context = statements[0][1][-1].obj
        session_context = statements[1][1][1].obj
        self.assertEqual(per_turn_context["_response_kind"], "conversation")
        self.assertNotIn("_response_kind", session_context)


if __name__ == "__main__":
    unittest.main()
