"""Offline linguistic provenance and bounded memory regressions."""
import unittest
from test_dialogue_state_revision import interpretation, revision
import dialogue_state as d


class ContextGapTests(unittest.TestCase):
    def context(self, text, field, token, quote=None):
        value=interpretation(text, **{field:token})
        value['context_evidence'][field]=quote or text
        return d.validate(value, {}, text, [text], {})

    def test_failed_outcome_does_not_negate_environment(self):
        for text,field,token in [
            ('I am using Moodle but it won’t launch','reported_platform','Moodle'),
            ('I opened the browser but it did not work','access_method','browser'),
            ('I am using Chrome, however the course is not opening','access_method','browser'),
            ('I am using Safari and it does not work','access_method','browser'),
            ('I am using Moodle and it will not launch','reported_platform','Moodle'),
            ('I use Safari but it could be the course failing','access_method','browser'),
        ]:
            with self.subTest(text=text):
                self.assertIsNone(self.context(text,field,token))

    def test_task_questions_can_name_context_without_identity_uncertainty(self):
        for text,token in (
            ('How do I access the CSC course in MCeLE?','MCeLE'),
            ('How do I download my certificate in MCeLE?','MCeLE'),
            ('How do I open Moodle?','Moodle'),
        ):
            self.assertIsNone(self.context(text,'reported_platform',token))
        for text,field,token in (
            ('Am I using Moodle?','reported_platform','Moodle'),
            ('Is this Safari?','access_method','browser'),
            ('Do I use Safari?','access_method','browser'),
            ('If I use Safari, will it launch?','access_method','browser'),
        ):
            self.assertIsNotNone(self.context(text,field,token))

    def test_aliases_require_actual_user_words(self):
        for alias in ('Safari','Chrome','Firefox','Edge'):
            with self.subTest(alias=alias):
                self.assertIsNone(self.context('I am using '+alias,'access_method','browser'))
                self.assertIsNotNone(self.context('I am not using '+alias,'access_method','browser',alias))
                self.assertIsNotNone(self.context('If I use '+alias+', I can open it','access_method','browser',alias))
        for alias,token in [('Moodlle','Moodle'),('MCE-LE','MCeLE')]:
            self.assertIsNone(self.context('I am on '+alias,'reported_platform',token))
            self.assertIsNotNone(self.context('Maybe I am on '+alias,'reported_platform',token,alias))
        self.assertIsNotNone(self.context('I use my phone','access_method','app'))
        self.assertIsNotNone(self.context('I use my phone','access_method','browser','Safari'))

    def test_negation_uncertainty_and_hypothetical_scope(self):
        for text in (
            'I am not using Safari but I opened the course',
            'If I use Safari, the browser opens the course',
            'If I use the app, but then use Safari, it works',
            'If I use Safari, the course might launch',
            'If I use the app and I use Safari, it works',
            'I am not using Chrome and Safari',
            'Maybe I use Safari but it does not work',
            'I could use Safari but it does not work',
            'I am unsure whether Safari works',
            'I use Safari but actually I am not using Safari',
        ):
            with self.subTest(text=text):
                self.assertIsNotNone(self.context(text,'access_method','browser','Safari'))
        self.assertIsNone(self.context('I am not using the app but I am using Safari','access_method','browser','Safari'))

    def test_retained_excerpt_uses_full_original_scope(self):
        for original in ('If I use Safari, will it launch?', 'I am not using Safari.'):
            m=d.reconcile({},interpretation(original,[revision('Safari','environment','reported')]),original)
            value=interpretation('It still fails.',access_method='browser')
            value['context_evidence']['access_method']='Safari'
            self.assertEqual(d.validate(value,m,'It still fails.',
                ['It still fails.','Safari',original],{}),'context_provenance')
        original='I am using Safari and it does not work.'
        m=d.reconcile({},interpretation(original,[revision('Safari','environment','reported')]),original)
        value=interpretation('It still fails.',access_method='browser')
        value['context_evidence']['access_method']='Safari'
        self.assertIsNone(d.validate(value,m,'It still fails.',
            ['It still fails.','Safari',original],{}))

    def test_superseded_context_cannot_return(self):
        old='I am using Safari.'
        m=d.reconcile({},interpretation(old,[revision(old,'environment','reported')]),old)
        text='Actually I use the app.'
        value=interpretation(text,[revision(text,'environment','reported',[m['facts'][0]['id']])],access_method='browser')
        value['context_evidence']['access_method']=old
        self.assertEqual(d.validate(value,m,text,[text,old],{}),'superseded_context_provenance')

    def test_long_session_reserves_task_and_keeps_bounded_audit(self):
        m={}
        for kind,text in [('goal','I want to launch the course.'),('parent_goal','I want to finish my training.'),('obstacle','The course stalls.')]:
            m=d.reconcile(m,interpretation(text,[revision(text,kind,'reported')]),text)
        for i in range(60):
            text=f'I completed step {i}.'
            m=d.reconcile(m,interpretation(text,[revision(text)]),text)
            if i % 2 == 0:
                fact=next(f for f in reversed(m['facts']) if f['status']=='completed' and f['active'])
                correction=f'I did not complete step {i}.'
                m=d.reconcile(m,interpretation(correction,[revision(correction,status='retracted',supersedes=[fact['id']])]),correction)
        self.assertEqual(m['goal'],'I want to launch the course.')
        self.assertEqual(m['parent_goal'],'I want to finish my training.')
        self.assertEqual(m['obstacle'],'The course stalls.')
        self.assertLessEqual(sum(f['active'] for f in m['facts']),24)
        self.assertLessEqual(sum(not f['active'] for f in m['facts']),24)
        ids={f['id'] for f in m['facts']}
        for f in m['facts']:
            self.assertTrue(set(f['supersedes']) <= ids)
            if 'superseded_by' in f:
                self.assertIn(f['superseded_by'],ids)
        latest=next(f for f in reversed(m['facts']) if f['status']=='retracted')
        self.assertTrue(latest['supersedes'])
        self.assertIn(latest['supersedes'][0],ids)
        text='New task: find my receipt.'
        m=d.reconcile(m,interpretation(text,[revision(text,'goal','reported')],transition='switch',change_quote=text),text)
        self.assertEqual(m['goal'],text)
        self.assertNotIn('parent_goal',m)
        self.assertNotIn('obstacle',m)

    def test_answered_error_purpose_snapshots_reconciled_obstacle(self):
        m={'pending_question':'What error appears?', 'pending_purpose':{'purpose':'error_message'}}
        text='The course stalls.'
        m=d.reconcile(m,interpretation(text,[revision(text,'obstacle','reported')],pending_answered=True),text)
        self.assertEqual(m['answered_questions'][-1]['obstacle_quote'],text)

    def test_answered_purpose_is_bounded_and_cleared_on_switch(self):
        m={}
        for i in range(12):
            m.update(pending_question='Which method?',pending_purpose={'purpose':'access_method'})
            m=d.reconcile(m,interpretation('Safari',pending_answered=True),'Safari')
        self.assertEqual(len(m['answered_questions']),8)
        self.assertEqual(m['answered_questions'][-1],{'purpose':'access_method','question':'Which method?','answer_quote':'Safari','turn':12,'obstacle_quote':None})
        self.assertNotIn('pending_question',m)
        m=d.reconcile(m,interpretation('New task',transition='switch',change_quote='New task'),'New task')
        self.assertNotIn('answered_questions',m)


if __name__=='__main__': unittest.main()
