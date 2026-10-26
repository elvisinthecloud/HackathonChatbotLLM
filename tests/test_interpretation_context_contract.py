"""Offline interpretation contracts; live task recognition requires model replay."""
import unittest

from test_dialogue_state_revision import interpretation, revision
import dialogue_state as d


class InterpretationContextContractTests(unittest.TestCase):
    def test_explicit_requests_need_no_optional_context(self):
        for text in (
            'I need to move their request forward.',
            'How do I download my certificate?',
            'I want to update the course description.',
        ):
            with self.subTest(text=text):
                value = interpretation(text, [revision(text, 'goal', 'reported')])
                self.assertIsNone(d.validate(value, {}, text, [text], {}))
                memory = d.reconcile({}, value, text)
                self.assertTrue(memory['goal_resolved'])
                self.assertEqual(memory['goal'], text)

    def test_null_context_rejects_stray_evidence_without_mutating_proposal(self):
        text = 'I need to move their request forward.'
        for field in ('course_id', 'access_method', 'activity', 'reported_platform'):
            with self.subTest(field=field):
                value = interpretation(text)
                value['context_evidence'][field] = text
                self.assertEqual(d.validate(value, {}, text, [text], {}), 'context_provenance')
                self.assertIsNone(value[field])
                self.assertEqual(value['context_evidence'][field], text)
                value['context_evidence'][field] = None
                self.assertIsNone(d.validate(value, {}, text, [text], {}))
                self.assertTrue(value['task_known'])

    def test_filling_a_value_does_not_make_uncertain_context_valid(self):
        for text, field, token in (
            ('Maybe I use Moodle.', 'reported_platform', 'Moodle'),
            ('If I use the app, can I find it?', 'access_method', 'app'),
            ('I am not using a browser.', 'access_method', 'browser'),
        ):
            with self.subTest(text=text):
                value = interpretation(text, **{field: token})
                value['context_evidence'][field] = token
                self.assertEqual(d.validate(value, {}, text, [text], {}), 'context_provenance')

    def test_explicit_current_course_does_not_authenticate_unrelated_old_quote(self):
        from demo_policy import COURSES
        old = 'I need to move their seminar request forward.'
        memory = d.reconcile({}, interpretation(old, [revision(old, 'goal', 'reported')]), old)
        current = '5500 i think'
        value = interpretation(old, course_id='5500')
        value['context_evidence']['course_id'] = old
        self.assertEqual(d.validate(value, memory, current, [current, old], COURSES), 'context_provenance')
        value['context_evidence']['course_id'] = current
        self.assertIsNone(d.validate(value, memory, current, [current, old], COURSES))
        self.assertFalse(d.contextual_course_match('5500', old, '6800', ['6800', old], COURSES))

    def test_complete_multisentence_context_anchor(self):
        text = 'Safari in the browser on my phone. I have already signed into MCeLE.'
        for field, token in (('access_method', 'browser'), ('reported_platform', 'MCeLE')):
            with self.subTest(field=field):
                value = interpretation(text, **{field: token})
                value['context_evidence'][field] = text
                self.assertIsNone(d.validate(value, {}, text, [text], {}))

    def test_contrast_denies_only_the_named_context(self):
        for text, accepted, denied in (
            ('I use Safari, not the app.', 'browser', 'app'),
            ('I use the app, not a browser.', 'app', 'browser'),
        ):
            with self.subTest(text=text):
                self.assertTrue(d.context_reported(accepted, text, [text]))
                self.assertFalse(d.context_reported(denied, text, [text]))
        text = 'Still Safari on my phone, like I said. I am trying to open the 5500 class from MCeLE, not an app.'
        self.assertTrue(d.context_reported('browser', text, [text]))
        self.assertTrue(d.context_reported('MCeLE', text, [text]))
        self.assertFalse(d.context_reported('app', text, [text]))

    def test_multisentence_anchor_preserves_hypothetical_and_correction_scope(self):
        for text in (
            'If I use Safari, not the app, it might work. I need help.',
            'I am not using Safari. I signed in.',
            'I use Safari. Actually I am not using a browser.',
            'I use Safari, not a browser.',
            'Maybe I use Safari. I signed in.',
        ):
            with self.subTest(text=text):
                self.assertFalse(d.context_reported('browser', text, [text]))
                self.assertFalse(d.context_reported('browser', 'Safari', [text]))
        self.assertFalse(d.context_reported('browser', 'Safari. I signed in.', ['If I use Safari. I signed in.']))


if __name__ == '__main__':
    unittest.main()
