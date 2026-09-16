"""Focused offline checks for the expanded curated hackathon dataset."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from demo_dataset import load_dataset, validate_taxonomy
from demo_policy import PROFILES, resolve_access, resolve_context


def routed(profile_id: str, question: str, course: str | None = None):
    context, conflict, _ = resolve_context(course, {}, None, question)
    if conflict:
        raise AssertionError(conflict)
    return context, resolve_access(PROFILES[profile_id], context, question)


class ExpandedDatasetTests(unittest.TestCase):
    def test_manifest_loads_exactly_seven_curated_articles(self):
        documents = load_dataset(ROOT / "knowledge/curated/manifest.json")
        self.assertEqual(
            [document["source_path"] for document in documents],
            [
                "MCELE-LAUNCH-001",
                "MOODLE-COPY-002",
                "MOODLE-COPY-001",
                "MOODLE-COPY-003",
                "MCELE-ECDEP-001",
                "MCELE-ENROLLMENT-REPORT-001",
                "MCELE-RRC-001",
            ],
        )
        self.assertEqual(len(validate_taxonomy(ROOT / "knowledge/curated/taxonomy.json")), 5)

    def test_ao_normal_and_stuck_copy_intents_are_separate(self):
        _, normal = routed("ao", "How do I copy a course in Moodle?")
        _, stuck = routed("ao", "My Moodle course copy keeps loading and never submits. What should I do?")
        self.assertEqual(normal.article_ids, ("MOODLE-COPY-001",))
        self.assertEqual(stuck.article_ids, ("MOODLE-COPY-003",))

    def test_instructor_cannot_retrieve_ao_troubleshooting(self):
        _, access = routed("instructor", "My Moodle course copy is stuck and keeps loading.")
        self.assertEqual(access.article_ids, ("MOODLE-COPY-002",))

    def test_enrollment_report_does_not_route_to_ecdep_workflow(self):
        context, access = routed("training-manager", "I want to verify a Marine's enrollment status. How can I do that?")
        self.assertEqual(context["system_area"], "MCeLE")
        self.assertEqual(access.article_ids, ("MCELE-ENROLLMENT-REPORT-001",))

    def test_rrc_question_routes_to_student_credit_article(self):
        context, access = routed("student", "Can I redo a completed course for RRC in a new anniversary year?")
        self.assertEqual(context["activity"], "course-credit")
        self.assertEqual(context["system_area"], "MCeLE")
        self.assertEqual(access.article_ids, ("MCELE-RRC-001",))

        selected_context, selected_access = routed(
            "student",
            "Can I redo this completed course for more Reserve Retirement Credits?",
            "CYBERM0000",
        )
        self.assertEqual(selected_context["system_area"], "MCeLE")
        self.assertEqual(selected_access.article_ids, ("MCELE-RRC-001",))


if __name__ == "__main__":
    unittest.main()
