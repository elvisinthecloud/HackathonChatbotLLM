import unittest
import json

import compact_interpretation as c
import dialogue_state as d


def proposal(kind='goal', quote_id='c0', **extra):
    return {'task': {'kind': kind, 'activity': 'unknown', 'quote_id': quote_id}, **extra}


class CompactInterpretationTests(unittest.TestCase):
    def decode(self, text, value, memory=None, courses=None):
        memory = memory or {}
        return c.decode(value, c.payload(text, memory, courses or {}), memory, courses or {})

    def test_task_automatically_retained_and_short_answer_uses_active(self):
        text = 'I want to copy a course.'
        flat, diagnostics = self.decode(text, proposal())
        self.assertEqual(diagnostics, [])
        memory = d.reconcile({}, flat, text)
        offered = c.payload('Safari.', memory, {})
        active = next(q['id'] for q in offered['quotes'] if q['source'] == 'active')
        flat, _ = c.decode(proposal(quote_id=active), offered, memory, {})
        self.assertEqual(flat['revisions'], [])
        self.assertEqual(flat['task_quote'], text)
        self.assertEqual(d.reconcile(memory, flat, 'Safari.')['goal'], text)

    def test_optional_retrieval_hint_never_enters_user_report_state(self):
        text = 'I need to move a seminar request forward.'
        original, _ = self.decode(text, proposal())
        value = proposal(retrieval_query='  seminar enrollment request recommendation  ')
        self.assertEqual(c.retrieval_query(value), 'seminar enrollment request recommendation')
        flat, diagnostics = self.decode(text, value)
        self.assertEqual(flat, original)
        self.assertEqual(diagnostics, [])
        memory = d.reconcile({}, flat, text)
        self.assertNotIn('retrieval_query', memory)
        self.assertEqual(memory['goal'], text)
        rule = c.schema(c.payload(text, {}, {}), {})['properties']['retrieval_query']
        self.assertEqual(rule['maxLength'], 240)
        self.assertIn('null', rule['type'])

    def test_invalid_optional_retrieval_hints_do_not_invalidate_task(self):
        text = 'I want my certificate.'
        original, _ = self.decode(text, proposal())
        for hint in (None, '', '   ', 'x'*241, 42, [], {'role':'Admin'}):
            with self.subTest(hint=hint):
                value = proposal(retrieval_query=hint)
                self.assertIsNone(c.retrieval_query(value))
                flat, _ = self.decode(text, value)
                self.assertEqual(flat, original)
        self.assertIsNone(c.retrieval_query(proposal()))
        self.assertIsNone(c.retrieval_query(None))

    def test_optional_errors_do_not_erase_task(self):
        flat, diagnostics = self.decode('I want to copy a course.', proposal(context={
            'course_id': {'value': 'FAKE', 'quote_id': 'c0'},
            'access_method': {'value': 'app', 'quote_id': 'c0'},
            'reported_platform': {'value': 'Moodle', 'quote_id': 'made-up'},
            'activity': {'value': 'course-management', 'quote_id': 'c0'}}))
        self.assertTrue(flat['task_known'])
        self.assertEqual(len(flat['revisions']), 1)
        self.assertEqual(len(diagnostics), 3)
        self.assertEqual(flat['activity'], 'course-management')
        self.assertIsNone(flat['access_method'])

    def test_problem_and_unknown_are_distinct(self):
        flat, _ = self.decode('My account is locked.', proposal('problem'))
        self.assertEqual(flat['revisions'][0]['kind'], 'obstacle')
        flat, _ = self.decode('Help.', proposal('unknown', None))
        self.assertFalse(flat['task_known'])
        self.assertEqual(flat['revisions'], [])

    def test_quote_units_not_truncated_or_split_on_conjunction(self):
        text = 'If I use the app, I might log in.'
        offered = c.payload(text, {}, {})
        self.assertEqual([q['quote'] for q in offered['quotes']], [text])
        flat, reasons = self.decode(text, proposal(context={'access_method': {'value': 'app', 'quote_id': 'c0'}}))
        self.assertIsNone(flat['access_method'])
        self.assertTrue(reasons)
        self.assertEqual(c.payload('x' * 501, {}, {})['quotes'], [])

    def test_active_original_scope_not_laundered(self):
        memory = {'facts': [{'id': 'old', 'kind': 'environment', 'status': 'reported',
                             'quote': 'the app', 'context_quote': 'I do not use the app.', 'active': True}]}
        offered = c.payload('I want to copy a course.', memory, {})
        active = next(q['id'] for q in offered['quotes'] if q['source'] == 'active')
        flat, reasons = c.decode(proposal(context={'access_method': {'value': 'app', 'quote_id': active}}), offered, memory, {})
        self.assertIsNone(flat['access_method'])
        self.assertTrue(reasons)

    def test_unproven_progress_ignored_without_erasing_task(self):
        flat, reasons = self.decode('I have not opened the form.', proposal('problem', memory={'progress': [
            {'kind': 'action', 'status': 'completed', 'quote_id': 'c0', 'supersedes': []}]}))
        self.assertTrue(flat['task_known'])
        self.assertEqual([r['kind'] for r in flat['revisions']], ['obstacle'])
        self.assertIn('progress:unconfirmed_action', reasons)

    def test_supersession_invalid_ids_discarded(self):
        flat, reasons = self.decode('I opened the form.', proposal(memory={'progress': [
            {'kind': 'action', 'status': 'completed', 'quote_id': 'c0', 'supersedes': ['invented']}]}))
        self.assertEqual(len(flat['revisions']), 2)
        self.assertEqual(flat['revisions'][-1]['supersedes'], [])
        self.assertIn('progress:invalid_supersession', reasons)

    def test_switch_uses_existing_reconcile(self):
        flat, _ = self.decode('Copy a course.', proposal())
        memory = d.reconcile({}, flat, 'Copy a course.')
        text = 'Instead I want my transcript.'
        flat, _ = self.decode(text, proposal(memory={'transition': 'switch', 'change_quote_id': 'c0'}), memory)
        result = d.reconcile(memory, flat, text)
        self.assertEqual(result['goal'], text)
        self.assertFalse(next(f for f in result['facts'] if f['quote'] == 'Copy a course.')['active'])

    def test_current_anchored_switch_needs_no_fixed_transition_phrase(self):
        first, _ = self.decode('Copy a course.', proposal())
        memory = d.reconcile({}, first, 'Copy a course.')
        text = 'Can you help me get my transcript?'
        flat, reasons = self.decode(text, proposal(memory={
            'transition': 'switch', 'change_quote_id': 'c0'}), memory)
        self.assertEqual(reasons, [])
        self.assertEqual(flat['transition'], 'switch')
        result = d.reconcile(memory, flat, text)
        self.assertEqual(result['goal'], text)
        self.assertFalse(next(f for f in result['facts'] if f['quote'] == 'Copy a course.')['active'])

    def test_switch_requires_current_goal_and_current_change_anchors(self):
        first, _ = self.decode('Copy a course.', proposal())
        memory = d.reconcile({}, first, 'Copy a course.')
        current = 'Can you help me get my transcript?'
        offered = c.payload(current, memory, {})
        active = next(q['id'] for q in offered['quotes'] if q['source'] == 'active')
        for task_id, change_id in ((active, 'c0'), ('c0', active), ('c0', None), ('c0', 'invented')):
            with self.subTest(task_id=task_id, change_id=change_id):
                flat, reasons = c.decode(proposal(quote_id=task_id, memory={
                    'transition': 'switch', 'change_quote_id': change_id}), offered, memory, {})
                self.assertEqual(flat['transition'], 'continue')
                self.assertEqual(flat['task_quote'], 'Copy a course.')
                self.assertIn('transition:unanchored_switch', reasons)
                self.assertEqual(d.reconcile(memory, flat, current)['goal'], 'Copy a course.')

    def test_short_context_answer_is_retained(self):
        first, _ = self.decode('I want to copy a course.', proposal())
        memory = d.reconcile({}, first, 'I want to copy a course.')
        offered = c.payload('I am using Safari.', memory, {})
        active = next(q['id'] for q in offered['quotes'] if q['source'] == 'active')
        flat, reasons = c.decode(proposal(quote_id=active, context={
            'access_method': {'value': 'browser', 'quote_id': 'c0'}}), offered, memory, {})
        self.assertEqual(reasons, [])
        result = d.reconcile(memory, flat, offered['current_user'])
        self.assertEqual(result['environment'], ['I am using Safari.'])
        self.assertEqual(result['goal'], 'I want to copy a course.')

    def test_continuation_cannot_overwrite_goal_with_clarification(self):
        first, _ = self.decode('I want to copy a course.', proposal())
        memory = d.reconcile({}, first, 'I want to copy a course.')
        for kind in ('goal', 'unknown'):
            flat, _ = self.decode('5500.', proposal(kind), memory)
            self.assertEqual(flat['task_quote'], 'I want to copy a course.')
            self.assertEqual(flat['revisions'], [])
        flat, _ = self.decode('The screen is blank.', proposal('problem'), memory)
        result = d.reconcile(memory, flat, 'The screen is blank.')
        self.assertEqual(result['goal'], 'I want to copy a course.')
        self.assertEqual(result['obstacle'], 'The screen is blank.')

    def test_unhashable_supersession_is_discarded(self):
        flat, reasons = self.decode('I opened the form.', proposal(memory={'progress': [
            {'kind': 'action', 'status': 'completed', 'quote_id': 'c0', 'supersedes': [{}]}]}))
        self.assertTrue(flat['task_known'])
        self.assertIn('progress:invalid_supersession', reasons)

    def test_catalog_budget_and_empty_supersession_schema(self):
        facts = [{'id': str(i), 'kind': 'goal' if i == 0 else 'environment',
                  'status': 'reported', 'quote': str(i) + 'x' * 490,
                  'context_quote': 'If ' + str(i) + 'x' * 490 + ', maybe later.', 'active': True}
                 for i in range(24)]
        offered = c.payload('Sentence. ' * 400, {'facts': facts}, {})
        self.assertLess(len(json.dumps({'quotes': offered['quotes'], 'active_facts': offered['active_facts']}).encode()), 6000)
        self.assertTrue(any(q.get('kind') == 'goal' for q in offered['quotes']))
        self.assertTrue(all('context_quote' not in q for q in offered['quotes'] if q['source'] == 'current'))
        rule = c.schema(c.payload('Hello.', {}, {}), {})['properties']['memory']['properties']['progress']['items']['properties']['supersedes']
        self.assertEqual(rule['maxItems'], 0)
        self.assertNotIn('enum', rule['items'])

    def test_split_course_name_requires_unique_affirmative_catalog_support(self):
        from demo_policy import COURSES
        prior = "hey i'm trying to push my marines seminar request but help idk how"
        for current, history, expected in [('sergeants school',prior,True),
                ('sergeants school','I need course help',False),
                ('not sergeants school',prior,False),
                ('Sergeants School DEP',prior,False),
                ('sergeants school',prior+' and Sergeants School DEP',False)]:
            with self.subTest(current=current,history=history):
                self.assertEqual(d.contextual_course_match('5500',current,current,[current,history],COURSES),expected)

    def test_new_obstacle_does_not_switch_even_when_model_proposes_switch(self):
        first, _ = self.decode('I need to review a seminar request.', proposal())
        memory = d.reconcile({}, first, 'I need to review a seminar request.')
        text='The form is present, but the certificate is missing.'
        flat,_=self.decode(text,proposal('problem',memory={'transition':'switch','change_quote_id':'c0'}),memory)
        result=d.reconcile(memory,flat,text)
        self.assertEqual(result['goal'],'I need to review a seminar request.')
        self.assertEqual(result['obstacle'],text)

    def test_task_activity_is_required_and_anchored(self):
        value = proposal()
        value['task']['activity'] = 'enrollment'
        flat, reasons = self.decode('I want to recommend a Marine for a seminar.', value)
        self.assertEqual(flat['activity'], 'enrollment')
        self.assertEqual(flat['context_evidence']['activity'], flat['task_quote'])
        self.assertEqual(reasons, [])
        del value['task']['activity']
        with self.assertRaises(ValueError):
            self.decode('I want to recommend a Marine.', value)
        task_schema = c.schema(c.payload('Help.', {}, {}), {})['properties']['task']
        self.assertIn('activity', task_schema['required'])

    def test_duplicate_claims_drop_field_without_last_wins(self):
        value = proposal(context_claims=[
            {'field': 'access_method', 'value': 'browser', 'quote_id': 'c0'},
            {'field': 'access_method', 'value': 'app', 'quote_id': 'c0'}])
        flat, reasons = self.decode('I use Safari and the app.', value)
        self.assertIsNone(flat['access_method'])
        self.assertIn('access_method:duplicate_claim', reasons)
        self.assertTrue(flat['task_known'])

    def test_valid_current_course_survives_duplicate_old_claim(self):
        from demo_policy import COURSES
        first, _ = self.decode('I need to move their seminar request forward.', proposal())
        memory = d.reconcile({}, first, 'I need to move their seminar request forward.')
        text = '5500 i think'
        offered = c.payload(text, memory, COURSES)
        active = next(q['id'] for q in offered['quotes'] if q['source'] == 'active')
        claims = [{'field':'course_id','value':'5500','quote_id':'c0'},
                  {'field':'course_id','value':'5500','quote_id':active}]
        for ordered in (claims, list(reversed(claims))):
            flat, reasons = c.decode(proposal(quote_id=active, context_claims=ordered), offered, memory, COURSES)
            self.assertEqual(flat['course_id'], '5500')
            self.assertEqual(flat['context_evidence']['course_id'], text)
            self.assertIn(text, d.reconcile(memory, flat, text)['environment'])

    def test_valid_current_method_survives_invalid_old_duplicate(self):
        first, _ = self.decode('I need to open my course.', proposal())
        memory = d.reconcile({}, first, 'I need to open my course.')
        text = 'I use Safari.'
        offered = c.payload(text, memory, {})
        active = next(q['id'] for q in offered['quotes'] if q['source'] == 'active')
        claims = [{'field':'access_method','value':'browser','quote_id':'c0'},
                  {'field':'access_method','value':'browser','quote_id':active}]
        for ordered in (claims, list(reversed(claims))):
            flat, reasons = c.decode(proposal(quote_id=active, context_claims=ordered), offered, memory, {})
            self.assertEqual(flat['access_method'], 'browser')
            self.assertEqual(flat['context_evidence']['access_method'], text)
            self.assertIn('access_method:context_provenance', reasons)

    def test_identical_valid_duplicates_prefer_current_anchor(self):
        first, _ = self.decode('I use Safari.', proposal())
        memory = d.reconcile({}, first, 'I use Safari.')
        text = 'Still using Safari.'
        offered = c.payload(text, memory, {})
        active = next(q['id'] for q in offered['quotes'] if q['source'] == 'active')
        claims = [{'field':'access_method','value':'browser','quote_id':active},
                  {'field':'access_method','value':'browser','quote_id':'c0'},
                  {'field':'access_method','value':'browser','quote_id':'c0'}]
        flat, reasons = c.decode(proposal(quote_id=active, context_claims=claims), offered, memory, {})
        self.assertEqual(flat['access_method'], 'browser')
        self.assertEqual(flat['context_evidence']['access_method'], text)
        self.assertEqual(reasons, [])

    def test_conflicting_valid_duplicates_do_not_use_majority(self):
        browser = {'field':'access_method','value':'browser','quote_id':'c0'}
        app = {'field':'access_method','value':'app','quote_id':'c0'}
        flat, reasons = self.decode('I use Safari and the app.', proposal(context_claims=[browser, browser, app]))
        self.assertIsNone(flat['access_method'])
        self.assertIsNone(flat['context_evidence']['access_method'])
        self.assertIn('access_method:duplicate_claim', reasons)

    def test_optional_activity_can_refine_unknown_classification(self):
        flat, reasons = self.decode('I want to recommend a Marine.', proposal(context_claims=[
            {'field': 'activity', 'value': 'enrollment', 'quote_id': 'c0'}]))
        self.assertEqual(flat['activity'], 'enrollment')
        self.assertEqual(reasons, [])

    def test_course_correction_and_denial_scope(self):
        from demo_policy import COURSES
        self.assertEqual(d.asserted_course_mentions('Actually, I meant 6800, not 5500.',COURSES),['6800'])
        self.assertEqual(d.asserted_course_mentions("I can't launch CYBERM0000 in MCeLE.",COURSES),['CYBERM0000'])
        for text in ('Not 5500.','Maybe 5500','I am unsure whether 5500','If I were in 5500'):
            self.assertEqual(d.asserted_course_mentions(text,COURSES),[])
        flat,reasons=self.decode('Actually, I meant 6800, not 5500.',proposal(context_claims=[
            {'field':'course_id','value':'6800','quote_id':'c0'}]),courses=COURSES)
        self.assertEqual(flat['course_id'],'6800')

    def test_completion_survives_supersession_of_wrong_kind(self):
        first, _ = self.decode('I want to recommend a Marine.', proposal())
        memory = d.reconcile({}, first, 'I want to recommend a Marine.')
        text = 'I selected Recommend and completed that request. Thanks.'
        flat, reasons = self.decode(text, proposal(memory={'progress': [
            {'kind': 'action', 'status': 'completed', 'quote_id': 'c0', 'supersedes': ['t1f0']}]}), memory)
        self.assertEqual(flat['revisions'][-1]['status'], 'completed')
        self.assertEqual(flat['revisions'][-1]['supersedes'], [])
        self.assertIn('progress:invalid_supersession', reasons)
        self.assertEqual(d.reconcile(memory, flat, text)['goal'], 'I want to recommend a Marine.')

    def test_retraction_still_requires_valid_supersession(self):
        flat, reasons = self.decode('I never completed that.', proposal(memory={'progress': [
            {'kind': 'action', 'status': 'retracted', 'quote_id': 'c0', 'supersedes': ['missing']}]}))
        self.assertFalse(any(r['status'] == 'retracted' for r in flat['revisions']))
        self.assertIn('progress:unanchored_retraction', reasons)

    def test_same_error_retains_exact_obstacle(self):
        original = 'The sts1 error prevents launching my course.'
        first, _ = self.decode(original, proposal('problem'))
        memory = d.reconcile({}, first, original)
        current = 'The same error still remains after that full procedure. Where do I get further help?'
        flat, _ = self.decode(current, proposal('problem'), memory)
        result = d.reconcile(memory, flat, current)
        self.assertEqual(flat['task_quote'], original)
        self.assertEqual(result['obstacle'], original)
        self.assertIn(current, result['environment'])
        corrected = 'The same error is gone; now a different issue prevents login.'
        flat, _ = self.decode(corrected, proposal('problem'), memory)
        self.assertEqual(d.reconcile(memory, flat, corrected)['obstacle'], corrected)

    def test_schema_uses_only_offered_ids_and_course_registry(self):
        schema = c.schema(c.payload('Help.', {}, {'CUSTOM': {}}), {'CUSTOM': {}})
        self.assertEqual(schema['properties']['task']['properties']['quote_id']['enum'], [None, 'c0'])
        self.assertEqual(schema['properties']['context_claims']['items']['anyOf'][0]['properties']['value']['enum'], ['CUSTOM'])


if __name__ == '__main__':
    unittest.main()
