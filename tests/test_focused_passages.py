"""Focused canonical passages; no model or service calls."""
import json
from pathlib import Path
import unittest
import support  # Initializes the isolated offline runtime.
import flexible_support as f

ARTICLES=Path(__file__).resolve().parents[1]/'knowledge/curated/articles'


def article(name):
    value=json.loads((ARTICLES/(name+'.json')).read_text())
    return {**value, 'source_path': value.get('id',name)}


def render(source, phrase, section=None):
    spans=f.evidence_spans([source])
    key=next(k for k,v in spans.items() if phrase in v['quote'] and (section is None or v['section']==section))
    return f.render_selection({'reply_mode':'passages','evidence_ids':[key],'question':None},[source],{})[0]


class FocusedPassageTests(unittest.TestCase):
    def test_certificate_does_not_offer_sibling_actions(self):
        text=render(article('mcele-view-courses-all'),'**Download Certificate:**')
        self.assertIn('View, download, or print a course certificate or diploma.',text)
        for sibling in ('**Launch:**','**View:**','**Disenroll:**','**Details:**','**Sub-Courses:**','Use this guidance'):
            self.assertNotIn(sibling,text)
        self.assertIn('[1]',text)

    def test_view_preserves_reenrollment_condition_without_siblings(self):
        text=render(article('mcele-view-courses-all'),'**View:**')
        self.assertIn('Selecting **View** does not enroll you in the course again.',text)
        self.assertIn('If you want to take a completed course again',text)
        self.assertNotIn('**Download Certificate:**',text)

    def test_lockout_branches_keep_distinct_conditions(self):
        source=article('mcele-unlock-all')
        before=render(source,'manual unlock')
        self.assertIn('Need access before the wait ends',before)
        self.assertNotIn('Account still appears locked after waiting',before)
        after=render(source,'Restart the browser')
        self.assertIn('Account still appears locked after waiting',after)
        self.assertNotIn('before the wait ends',after)
        self.assertNotIn('manual unlock',after)

    def test_conditional_enrollment_step_stays_whole(self):
        text=render(article('mcele-find-courses-all'),'If available, select')
        self.assertIn('If available, select **Enroll Now**.',text)
        self.assertIn('If you previously completed the course',text)
        self.assertIn('when available.',text)
        self.assertNotIn('Read the course details',text)

    def test_request_form_availability_qualifier_survives(self):
        text=render(article('mcele-find-courses-all'),'Select **Request**')
        self.assertIn('Some courses provide a request form.',text)
        self.assertIn('available form:',text)
        self.assertNotIn('Read the course details',text)

    def test_nested_bullet_conditions_are_not_detached(self):
        source={'source_path':'test','content':'Scope.\n\n### Enrollment\n\nIf eligible:\n\n- Open the form.\n  - If requested, attach the certificate.\n    Keep the signed copy.\n- Cancel the form.'}
        text=render(source,'Open the form')
        for phrase in ('If eligible:', 'If requested, attach the certificate.', 'Keep the signed copy.'):
            self.assertIn(phrase,text)
        self.assertNotIn('Cancel the form',text)

    def test_all_nineteen_articles_offer_only_exact_source_text(self):
        paths=list(ARTICLES.glob('*.json'))
        self.assertEqual(len(paths),19)
        for path in paths:
            source=article(path.stem)
            for part in f.evidence_spans([source]).values():
                for text in [part['quote'],part['scope'],part['section'],*part['context']]:
                    self.assertIn(text,source['content'],(path.name,text))

    def test_previous_unrelated_paragraph_not_rendered(self):
        source={'source_path':'test','content':'General description.\n\n### Current condition\n\nAn unrelated earlier fact.\n\n1. Do the current action.'}
        text=render(source,'Do the current action')
        self.assertNotIn('unrelated',text)
        self.assertNotIn('General description',text)

    def test_validated_question_renders_directly(self):
        question='What are you trying to do?'
        text,used,has_question=f.render_selection({'reply_mode':'question','evidence_ids':[],'question':question},[],{})
        self.assertEqual(text,question)
        self.assertEqual(used,set())
        self.assertTrue(has_question)
