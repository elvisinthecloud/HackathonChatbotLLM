"""Offline checks for the simple gated support path (no model calls)."""
import asyncio
import unittest

import simple_support as ss


class GateTests(unittest.TestCase):
    def test_role_grants_filter_articles(self):
        student = {a['id'] for a in ss.permitted('Student')}
        self.assertIn('MCELE-LAUNCH-001', student)
        self.assertNotIn('MCELE-ECDEP-001', student)
        self.assertEqual(ss.permitted('Nobody'), [])

    def test_prompt_contains_only_permitted_articles(self):
        prompt = ss.system_prompt({'name': 'Sgt Test', 'role': 'Student'})
        self.assertIn('MCELE-LAUNCH-001', prompt)
        self.assertNotIn('MCELE-ECDEP-001', prompt)
        self.assertNotIn('MOODLE-COPY-001', prompt)

    def test_fake_and_forbidden_citations_fail(self):
        v = ss.violations('Call us [MCELE-HELPDESK-001]. Approve it [MCELE-ECDEP-001].', 'Student')
        self.assertIn(('citation', 'MCELE-HELPDESK-001'), v)
        self.assertIn(('citation', 'MCELE-ECDEP-001'), v)

    def test_invented_labels_links_and_phones_fail(self):
        v = ss.violations('Open **Privacy and security** at https://example.com or call 555-123-4567 [MCELE-LAUNCH-001]', 'Student')
        kinds = {k for k, _ in v}
        self.assertEqual(kinds, {'label', 'link', 'phone'})

    def test_article_labels_pass_with_spacing_variants(self):
        reply = 'Select **Delete browsing data**, then contact the **Help Desk** [MCELE-LAUNCH-001].'
        self.assertEqual(ss.violations(reply, 'Student'), [])

    def test_labels_from_other_roles_articles_fail(self):
        self.assertTrue(ss.violations('Expand **Request file list** [MCELE-LOGIN-001].', 'Student'))
        self.assertEqual(ss.violations('Expand **Request file list** [MCELE-ECDEP-001].', 'Training Manager'), [])

    def test_strip_drops_bad_sentences_or_falls_back(self):
        bad = [('label', 'Privacy and security')]
        kept = ss.drop_unsupported('Open **Privacy and security**. Restart your computer [MCELE-LAUNCH-001].', bad)
        self.assertNotIn('Privacy', kept)
        self.assertIn('Restart', kept)
        self.assertEqual(ss.drop_unsupported('Open **Privacy and security**.', bad), ss.FALLBACK)

    def test_quoted_labels_match_article_text(self):
        self.assertEqual(ss.violations('Use the **"Item Has"** filter for **RRC** [MCELE-RRC-001].', 'Student'), [])

    def test_strip_keeps_list_structure(self):
        reply = '1. Go to the **Course Catalog**.\n2. Open **Secret Menu** now.\n3. Use the **Item Has** filter [MCELE-RRC-001].'
        out = ss.drop_unsupported(reply, [('label', 'Secret Menu')])
        self.assertEqual(out, '1. Go to the **Course Catalog**.\n3. Use the **Item Has** filter [MCELE-RRC-001].')

    def test_citations_become_numbers_with_sources(self):
        text, sources = ss.number_citations('A [MCELE-LAUNCH-001]. B [MCELE-LOGIN-001]. C [MCELE-LAUNCH-001]. D [MCELE-ECDEP-001].', 'Student')
        self.assertEqual(text, 'A [1]. B [2]. C [1]. D.')
        self.assertEqual([s['source_path'] for s in sources], ['MCELE-LAUNCH-001', 'MCELE-LOGIN-001'])

    def test_model_written_numeric_citations_are_removed(self):
        text, sources = ss.number_citations('Wait 30 minutes [1]. Then sign in [MCELE-LOGIN-001].', 'Student')
        self.assertEqual(text, 'Wait 30 minutes. Then sign in [1].')
        self.assertEqual(len(sources), 1)

    def test_history_hides_numeric_citations(self):
        session = {'version': 0, 'turns': [('q', 'Restart your computer [1].', '', 0, {})]}
        self.assertEqual(ss.history(session, False)[1]['content'], 'Restart your computer.')

    def test_history_respects_version_and_reset(self):
        session = {'version': 1, 'turns': [('old q', 'old a', '', 0, {}), ('q1', 'a1', 'screen text', 1, {})]}
        h = ss.history(session, False)
        self.assertEqual([m['role'] for m in h], ['user', 'assistant'])
        self.assertIn('screen text', h[0]['content'])
        self.assertEqual(ss.history(session, True), [])


class CourseScopeTests(unittest.TestCase):
    def ids(self, text, role='Student'):
        return {a['id'] for a in ss.in_scope(role, text)}

    def test_other_course_hides_course_scoped_article(self):
        self.assertNotIn('MCELE-CSC-001', self.ids('I cannot find my 5500 seminar tile'))
        self.assertIn('MCELE-EPME-001', self.ids('I cannot find my 5500 seminar tile'))

    def test_matching_course_keeps_article(self):
        self.assertIn('MCELE-CSC-001', self.ids('my CSC course is missing in Moodle'))
        self.assertIn('MCELE-EPME-001', self.ids('trying to enroll in EPME5000'))

    def test_no_course_named_keeps_everything(self):
        self.assertEqual(self.ids('help me log in'), {a['id'] for a in ss.permitted('Student')})


class FakeSpan:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def update(self, **k): pass


class FakeLangfuse:
    def start_as_current_span(self, **k): return FakeSpan()
    def start_as_current_generation(self, **k): return FakeSpan()
    def update_current_trace(self, **k): pass
    def update_current_generation(self, **k): pass
    def get_current_trace_id(self): return 'a' * 32


class AnswerFlowTests(unittest.TestCase):
    def run_answer(self, replies):
        calls = []
        async def fake_chat(rag, name, messages):
            calls.append(name)
            return replies[len(calls) - 1]
        original = ss.chat
        ss.chat = fake_chat
        try:
            rag = type('Rag', (), {'langfuse': FakeLangfuse()})()
            session = {'id': 's', 'profile': {'id': 'student', 'name': 'Sgt T', 'role': 'Student'},
                       'selected_course_id': None, 'version': 0, 'turns': []}
            return asyncio.run(ss.answer(rag, 'help', session, None)), calls
        finally:
            ss.chat = original

    def test_clean_reply_needs_one_call(self):
        result, calls = self.run_answer(['Restart your computer [MCELE-LAUNCH-001].'])
        self.assertEqual(calls, ['simple_reply'])
        self.assertEqual(result['answer'], 'Restart your computer [1].')
        self.assertEqual(result['sources'][0]['source_path'], 'MCELE-LAUNCH-001')

    def test_bad_reply_is_repaired_then_stripped(self):
        result, calls = self.run_answer(['Open **Incognito** [MCELE-LAUNCH-001].',
                                         'Open **Incognito**. Restart your computer [MCELE-LAUNCH-001].'])
        self.assertEqual(calls, ['simple_reply', 'simple_repair'])
        self.assertNotIn('Incognito', result['answer'])
        self.assertIn('Restart', result['answer'])


if __name__ == '__main__':
    unittest.main()
