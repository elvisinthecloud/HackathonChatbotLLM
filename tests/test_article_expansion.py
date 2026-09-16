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
    def test_manifest_loads_exactly_nine_curated_articles(self):
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
                "MCELE-EPME-001",
                "MCELE-CSC-001",
            ],
        )
        self.assertEqual(len(validate_taxonomy(ROOT / "knowledge/curated/taxonomy.json")), 7)
        by_id = {document["source_path"]: document for document in documents}
        for article_id in ("MOODLE-COPY-001", "MOODLE-COPY-003"):
            self.assertTrue(by_id[article_id]["retrieval_text"])
            self.assertNotIn("retrieval_text", by_id[article_id]["metadata"])

    def test_ao_copy_articles_share_a_semantic_candidate_set(self):
        _, normal = routed("ao", "How do I copy a course in Moodle?")
        _, stuck = routed("ao", "My Moodle course copy keeps loading and never submits. What should I do?")
        expected = ("MOODLE-COPY-001", "MOODLE-COPY-003")
        self.assertEqual(normal.article_ids, expected)
        self.assertEqual(stuck.article_ids, expected)

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

        for year_type in ("calendar year", "fiscal year"):
            with self.subTest(year_type=year_type):
                year_context, year_access = routed(
                    "student",
                    f"Can I redo a completed course for more points in a new {year_type}?",
                )
                self.assertEqual(year_context["activity"], "course-credit")
                self.assertEqual(year_access.article_ids, ("MCELE-RRC-001",))

    def test_epme_policy_routes_general_and_course_specific_questions(self):
        general_context, general_access = routed(
            "student",
            "Is it possible to enroll a Marine into an EPME course once the Marine has been selected and shows on MOL?",
        )
        self.assertEqual(general_context["activity"], "enrollment")
        self.assertEqual(general_context["system_area"], "MCeLE")
        self.assertEqual(general_access.article_ids, ("MCELE-EPME-001",))

        for general_question in (
            "What are the requirements to start an EPME course?",
            "How do I know if I am eligible for EPME?",
        ):
            with self.subTest(general_question=general_question):
                context, access = routed("student", general_question)
                self.assertEqual(context["activity"], "enrollment")
                self.assertEqual(access.article_ids, ("MCELE-EPME-001",))

        cases = (
            ("Can a Sergeant select take EPME5000?", "EPME5000"),
            ("Who is eligible to enroll in EPME6000BA?", "EPME6000"),
            ("What are the enrollment requirements for EPME5500?", "5500"),
            ("What prerequisite is required for EPME6800?", "6800"),
        )
        for question, course_id in cases:
            with self.subTest(question=question):
                context, access = routed("student", question)
                self.assertEqual(context["course_id"], course_id)
                self.assertEqual(access.article_ids, ("MCELE-EPME-001",))

        documents = load_dataset(ROOT / "knowledge/curated/manifest.json")
        article = next(document for document in documents if document["source_path"] == "MCELE-EPME-001")
        self.assertTrue(article["content"].startswith("Use these requirements"))
        self.assertNotIn("source of truth", article["content"].lower())
        self.assertIn("Sergeant selects cannot enroll", article["content"])
        self.assertIn("Staff Sergeant selects and above", article["content"])

    def test_csc_access_routes_both_missing_course_branches(self):
        cases = (
            "How do I access my CSC course?",
            "CSC appears in MCeLE but is missing in Moodle My Courses.",
            "CSC does not appear under MCeLE My Courses at all.",
        )
        for question in cases:
            with self.subTest(question=question):
                context, access = routed("student", question)
                self.assertEqual(context["course_id"], "CSC")
                self.assertEqual(context["activity"], "enrollment")
                self.assertEqual(context["system_area"], "MCeLE")
                self.assertEqual(access.article_ids, ("MCELE-CSC-001",))

        selected_context, selected_access = routed(
            "student",
            "It appears in MCeLE but is missing from Moodle.",
            "CSC",
        )
        self.assertEqual(selected_context["course_id"], "CSC")
        self.assertEqual(selected_access.article_ids, ("MCELE-CSC-001",))

        documents = load_dataset(ROOT / "knowledge/curated/manifest.json")
        article = next(document for document in documents if document["source_path"] == "MCELE-CSC-001")
        self.assertIn("Region first", article["content"])
        self.assertIn("Help Desk first", article["content"])

        _, instructor_access = routed("instructor", "How do I access my CSC course?")
        self.assertEqual(instructor_access.article_ids, ())


if __name__ == "__main__":
    unittest.main()
