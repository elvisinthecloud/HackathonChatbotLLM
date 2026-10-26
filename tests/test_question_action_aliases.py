"""User topic quotes cannot be assumed to be grammatical verb phrases."""
import unittest
import support as helpers
import flexible_support as f
from test_architecture_acceptance import decision


class QuestionActionAliasTests(unittest.TestCase):
    def test_nouns_and_verbs_render_same_neutral_question_with_real_provenance(self):
        expected=('Which course do you mean?','What happens when you try?','Which part do you need help with?')
        for frame,rendered in zip(f.ACTION_QUESTION_FORMS,expected):
            for topic in ('seminar request','push their seminar request forward','enroll'):
                question={'frame':frame,'topic_quote':topic}
                with self.subTest(frame=frame,topic=topic):
                    self.assertEqual(f.question_text(question),rendered)
                    self.assertTrue(f.safe_question(question,['I need help with '+topic]))
                    self.assertFalse(f.safe_question(question,['Unrelated user words']))
        for frame in f.ACTION_QUESTION_FORMS:
            self.assertNotIn(frame,f.QUESTION_GRAMMAR['frames'])
            self.assertNotIn(frame,f.question_schema()['properties']['frame']['enum'])

    def test_alias_preserves_known_course_clarification_guard(self):
        question={'frame':f.ACTION_QUESTION_FORMS[0],'topic_quote':'seminar request'}
        value=decision('question',question=question,clarification={
            'missing_detail':'course','why_needed':'select course guidance','evidence_id':None})
        self.assertEqual(f.question_purpose(question),'course')
        self.assertEqual(f.validate_decision(value,[],['seminar request'],{'task_known':True},
            {'course_id':'5500','conversation':{}}),'answered_context_question')
        self.assertEqual(f.question_purpose({'frame':f.ACTION_QUESTION_FORMS[2]}),'goal')

    def test_alias_never_hides_unsafe_or_invented_quote(self):
        for quote in ('Invented wording','line\nbreak','https://example.com','x'*81,3):
            question={'frame':f.ACTION_QUESTION_FORMS[0],'topic_quote':quote}
            self.assertFalse(f.safe_question(question,['seminar request']))
