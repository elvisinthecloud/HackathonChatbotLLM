"""Offline checks for answer grounding and source URL handling."""
import json
import os
from pathlib import Path
import sys
import unittest
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "tests")]

# Reuse the repository's deliberately fake offline settings.  Importing the
# test helper never makes a service call; it only imports the app under patch.
from test_backend import test_env

with patch.dict(os.environ, test_env()):
    import rag
    from demo_policy import RetrievalAccess


def article(article_id: str) -> dict:
    matches = (
        path for path in (ROOT / "knowledge/curated/articles").glob("*.json")
        if not path.name.startswith("._")
    )
    for path in matches:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data["article_id"] == article_id:
            return data
    raise AssertionError(f"curated article not found: {article_id}")


def chunk(article_id: str) -> dict:
    data = article(article_id)
    return {
        "source_path": article_id,
        "chunk_index": 0,
        "title": data["title"],
        "content": data["content"],
        "score": 1.0,
    }


class GroundingTests(unittest.IsolatedAsyncioTestCase):
    def test_ao_copy_family_uses_only_the_semantically_best_article(self):
        token = rag.ACCESS.set(RetrievalAccess(
            "Academics Officer",
            "Moodle",
            None,
            ("MOODLE-COPY-001", "MOODLE-COPY-003"),
        ))
        try:
            chunks = [
                {"source_path": "MOODLE-COPY-003", "score": 0.91, "content": "stuck copy"},
                {"source_path": "MOODLE-COPY-001", "score": 0.72, "content": "normal copy"},
            ]
            self.assertEqual(
                [item["source_path"] for item in rag.select_semantic_article(chunks, "MOODLE-COPY-003")],
                ["MOODLE-COPY-003"],
            )
        finally:
            rag.ACCESS.reset(token)

    def test_instructor_answer_is_rendered_from_its_permission_excerpt(self):
        source = chunk("MOODLE-COPY-002")
        malicious = (
            "You can copy the course yourself.\n\n"
            "1. Open Home. 2. Select Manage courses. 3. Choose Copy course.\n\n"
            "Watch [the tutorial](https://evil.example/tutorial) and complete "
            "MClearn training at https://evil.example/training."
        )

        grounded = rag.ground_answer(malicious, [source])

        self.assertIn("Academics Officer (AO) Moodle role", grounded)
        self.assertIn("contact a user with the AO role", grounded)
        self.assertNotIn("Manage courses", grounded)
        self.assertNotIn("Copy course", grounded)
        self.assertNotIn("MClearn", grounded)
        self.assertNotIn("evil.example", grounded)

    def test_unsupported_url_triggers_source_excerpt_fallback(self):
        source = chunk("MCELE-ECDEP-001")
        answer = "Use the approved process. See https://generated.example/invented-step."

        grounded = rag.ground_answer(answer, [source])

        self.assertIn("5500", grounded)
        self.assertIn("6800", grounded)
        self.assertNotIn("generated.example", grounded)

    def test_approved_ao_urls_match_exactly_including_query_strings(self):
        source = chunk("MOODLE-COPY-001")
        tutorial = "https://portal.mcele.usmc.mil/content/mcele-portal/en/media/detail.html?Id=8527A2A4B6B0"
        training = "https://elearning.mcele.usmc.mil/moodle/course/index.php?categoryid=1264"
        answer = (
            f"Watch [tutorial]({tutorial}) and complete [MClearn]({training}). "
            "Do not use https://portal.mcele.usmc.mil/content/mcele-portal/en/media/"
            "detail.html?Id=8527A2A4B6B0&source=generated."
        )

        grounded = rag.ground_answer(answer, [source])

        self.assertIn(tutorial, grounded)
        self.assertIn(training, grounded)
        self.assertNotIn("&source=generated", grounded)
        self.assertEqual(grounded.count(tutorial), 1)
        self.assertEqual(grounded.count(training), 1)

    def test_generic_source_rejects_modified_query_fragment_or_host(self):
        approved = "https://support.example.test/how-to?article=ecdep#steps"
        source = {
            "source_path": "MCELE-ECDEP-001",
            "chunk_index": 0,
            "title": "ECDEP support",
            "content": f"Use the approved ECDEP process. See {approved}.",
            "score": 1.0,
        }
        answer = (
            f"Use the approved ECDEP process. See {approved}. "
            "Also see https://support.example.test/how-to?article=other#steps "
            "and https://attacker.example.test/how-to?article=ecdep#steps."
        )

        grounded = rag.ground_answer(answer, [source])

        self.assertIn(approved, grounded)
        self.assertNotIn("article=other", grounded)
        self.assertNotIn("attacker.example.test", grounded)

    async def test_answer_question_cannot_return_invented_instructor_steps(self):
        source = chunk("MOODLE-COPY-002")
        malicious = (
            "1. Open Home. 2. Select Manage courses. 3. Choose Copy course. "
            "Complete MClearn training at https://evil.example/training."
        )

        @contextmanager
        def span(*args, **kwargs):
            yield MagicMock()

        session = {
            "id": "offline-session",
            "profile": {
                "id": "instructor",
                "name": "Demo Instructor",
                "role": "Adjunct Faculty",
                "display_role": "Instructor",
                "course_ids": [],
                "delivery_areas": ["Moodle"],
            },
            "selected_course_id": None,
            "context": {},
            "version": 0,
            "turns": [],
        }
        fake_langfuse = MagicMock()
        fake_langfuse.start_as_current_span.side_effect = span
        fake_langfuse.get_current_trace_id.return_value = "offline-trace"

        with patch.object(rag, "langfuse", fake_langfuse), \
             patch.object(rag, "retrieve_chunks", new_callable=AsyncMock,
                          return_value=([source], None, 1.0, [])), \
             patch.object(rag, "generate_answer", new_callable=AsyncMock,
                          return_value=malicious):
            result = await rag.answer_question("Can I copy a Moodle course?", session, None)

        self.assertIn("Academics Officer (AO) Moodle role", result["answer"])
        self.assertNotIn("Manage courses", result["answer"])
        self.assertNotIn("Copy course", result["answer"])
        self.assertNotIn("MClearn", result["answer"])
        self.assertNotIn("evil.example", result["answer"])
        self.assertEqual(result["sources"][0]["source_path"], "MOODLE-COPY-002")


if __name__ == "__main__":
    unittest.main()
