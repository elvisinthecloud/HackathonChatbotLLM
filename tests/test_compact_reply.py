import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import compact_reply as c
import evidence_conditions


class CompactReplyTests(unittest.TestCase):
    def contract(self, **overrides):
        args = dict(question_frames={
            'goal': {'frame': 'What do you need help with{topic}?', 'purpose': 'goal'},
            'course': {'frame': 'Which course do you mean{topic}?', 'purpose': 'course'},
            'method': {'frame': 'How are you accessing it{topic}?', 'purpose': 'access_method'},
            'error': {'frame': 'What message appears{topic}?', 'purpose': 'error_message'},
            'screen': {'frame': 'Which screen are you on{topic}?', 'purpose': 'screen'},
            'outcome': {'frame': 'What happened next{topic}?', 'purpose': 'observation', 'outcome': True}},
            evidence_spans={'canonical:plain': {'quote': 'Open the page.', 'conditions': []},
                'canonical:conditional': {'quote': 'Contact support.', 'conditions': [
                    {'kind': 'elapsed_wait', 'condition_quote': 'After 60 minutes', 'minimum_minutes': 60, 'relation': 'after'}]}},
            understanding={'task_known': True, 'task_quote': 'unlock my account'},
            context={'course_id': 'known', 'access_method': 'browser', 'conversation': {}},
            reports={'r1': 'I waited 60 minutes', 'r2': 'I waited 10 minutes'})
        args.update(overrides)
        return c.build_contract(**args)

    def test_filter_known_and_repeated_questions(self):
        contract = self.contract(context={'course_id': 'known', 'access_method': 'browser', 'conversation': {
            'obstacle':'Account is locked','turn': 3, 'answered_questions': [{'purpose': 'error_message', 'turn': 3}]}})
        self.assertEqual(set(contract.questions), {'screen', 'outcome'})
        for key in ('goal', 'course', 'method', 'error'):
            with self.assertRaisesRegex(ValueError, 'unoffered_question'):
                contract.compile({'action': 'question', 'question_id': key, 'evidence_id': 'e1'})

    def test_known_request_does_not_require_observation_or_identity(self):
        contract=self.contract()
        self.assertEqual(set(contract.questions),{'outcome'})

    def test_unknown_task_only_goal(self):
        contract = self.contract(understanding={'task_known': False, 'task_quote': None})
        self.assertEqual(set(contract.questions), {'goal'})

    def test_compile_plain_and_outcome(self):
        result = self.contract().compile({'action': 'passages', 'evidence_ids': ['e1'], 'outcome_question_id': 'outcome'})
        self.assertEqual(result['evidence_ids'], ['canonical:plain'])
        self.assertEqual(result['applicability'], [{'evidence_id': 'canonical:plain', 'task_quote': 'unlock my account', 'condition_quote': None, 'user_basis': None}])
        self.assertEqual(result['clarification']['evidence_id'], 'canonical:plain')
        self.assertIsNone(result['question']['topic_quote'])

    def test_mixed_modes_and_unknown_ids_fail(self):
        invalid = [
            {'action': 'source_gap', 'evidence_ids': ['e1']},
            {'action': 'question', 'question_id': 'screen', 'evidence_id': 'e1', 'basis': []},
            {'action': 'passages', 'evidence_ids': ['canonical:plain']},
            {'action': 'passages', 'evidence_ids': ['e1', 'e1']},
            {'action': 'passages', 'evidence_ids': ['e1'], 'source_ids': ['anything']},
            {'action': 'passages', 'evidence_ids': ['e1'], 'outcome_question_id': 'screen'},
            {'action': 'question', 'question_id': 'outcome', 'evidence_id': 'e1'},
            {'action': 'passages', 'evidence_ids': ['e1'], 'basis': [{'evidence_id': 'e1', 'report_id': 'r1'}]},
            {'action': 'passages', 'evidence_ids': ['e2'], 'basis': [{'evidence_id': 'e2', 'report_id': 'unknown'}]},
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.contract().compile(value)

    def test_condition_requires_model_selected_report_and_server_quote(self):
        contract = self.contract()
        with self.assertRaisesRegex(ValueError, 'missing_condition_basis'):
            contract.compile({'action': 'passages', 'evidence_ids': ['e2']})
        result = contract.compile({'action': 'passages', 'evidence_ids': ['e2'], 'basis': [{'evidence_id': 'e2', 'report_id': 'r1'}]})
        claim = result['applicability'][0]
        self.assertEqual(claim['condition_quote'], 'After 60 minutes')
        self.assertEqual(claim['user_basis'], 'I waited 60 minutes')
        self.assertIsNone(evidence_conditions.validate(contract.conditions['e2'], claim, 'I waited 60 minutes'))
        # Adapter provenance alone cannot override the existing time/context gate.
        self.assertEqual(evidence_conditions.validate(contract.conditions['e2'], claim, 'Actually I waited 10 minutes', ['I waited 60 minutes']), 'contradicted_elapsed_wait')

    def test_question_requires_missing_field_in_anchored_source(self):
        contract=self.contract(context={'source_missing_fields':['exact_launch_error'],
            'source_missing_by_id':{1:[],2:['exact_launch_error']},'conversation':{}},
            evidence_spans={'a':{'source':1,'quote':'Enrollment instructions.','conditions':[]},
                            'b':{'source':2,'quote':'Specific launch error.','conditions':[]}})
        with self.assertRaisesRegex(ValueError,'question_source_mismatch'):
            contract.compile({'action':'question','question_id':'error','evidence_id':'e1'})
        with self.assertRaisesRegex(ValueError,'question_source_mismatch'):
            contract.compile({'action':'question','question_id':'error','evidence_id':None})
        self.assertEqual(contract.compile({'action':'question','question_id':'error','evidence_id':'e2'})['reply_mode'],'question')

    def test_empty_relevant_sources_cannot_offer_unrelated_questions(self):
        contract=self.contract(context={'relevance_empty':True,'conversation':{'obstacle':'unavailable procedure'}})
        self.assertEqual(contract.questions,{})
        self.assertEqual(contract.compile({'action':'source_gap'})['reply_mode'],'source_gap')

    def test_observation_answer_stays_answered_until_new_action(self):
        memory={'turn':4,'obstacle':'Locked','answered_questions':[{'purpose':'screen','turn':2,'obstacle_quote':'Locked'}]}
        self.assertNotIn('screen',self.contract(context={'conversation':memory}).questions)
        memory['facts']=[{'kind':'action','active':True,'turn':3}]
        self.assertIn('screen',self.contract(context={'conversation':memory}).questions)

    def test_ambiguous_course_answer_allows_id_refinement(self):
        contract=self.contract(context={'source_missing_fields':['course_id'],'conversation':{
            'turn':2,'answered_questions':[{'purpose':'course','turn':2,'answer_quote':'school'}]}},
            question_frames={'id':{'frame':'What is the course number or ID{topic}?','purpose':'course'},
                             'course':{'frame':'Which course do you mean{topic}?','purpose':'course'}})
        self.assertIn('id',contract.questions)
        self.assertNotIn('course',contract.questions)

    def test_pause_cannot_assert_facts_or_completion(self):
        from flexible_support import validate_decision,render_selection
        decision=self.contract().compile({'action':'pause'})
        self.assertIsNone(validate_decision(decision,[],['hang on, be right back'],
            {'task_known':True,'task_quote':'unlock my account'},{'conversation':{}}))
        answer,used,question=render_selection(decision,[],{})
        self.assertEqual(answer,'No problem. Take your time.')
        self.assertEqual(used,set())
        self.assertFalse(question)
        self.assertFalse(__import__('flexible_support').social_report('pause','It is still 5500. What address do I enter?'))
        self.assertFalse(__import__('flexible_support').social_report('pause','I am not pausing now. What address do I enter?'))
        with self.assertRaises(ValueError):
            self.contract().compile({'action':'pause','evidence_ids':['e1']})

    def test_admitted_evidence_fits_specific_repair_feedback(self):
        import flexible_support as f
        understanding={'task_known':True,'task_quote':'Help launch my enrolled course.'}
        context={'conversation':{}}
        payload={'current_user':'Help launch my enrolled course.','role':'Student','constraints':{},
            'memory':{},'understanding':understanding,'sources':[], 'history':[]}
        source={'title':'Course launch','source_path':'test-source','content':'Course launch guidance.\n\n'+
            '\n\n'.join(str(i)+'. '+('A bounded source instruction. '*5) for i in range(1,60)),
            'applicability':{'applicable':True,'missing':[],'conflicts':[]}}
        result,contract,offered=f.compact_reply_payload(payload,[source],understanding,context,
            [payload['current_user']],16384)
        self.assertTrue(offered)
        repair={**result,'repair_feedback':{'rejection':'missing_condition_basis','instruction':'x'*500}}
        self.assertIsNotNone(f.fit_payload('compact_reply_repair',c.PROMPT,repair,contract.schema,16384))

    def test_paired_selection_preserves_condition_provenance(self):
        result=self.contract().compile({'action':'passages','selections':[
            {'evidence_id':'e1','report_id':None},{'evidence_id':'e2','report_id':'r1'}]})
        self.assertEqual(result['evidence_ids'],['canonical:plain','canonical:conditional'])
        self.assertEqual(result['applicability'][1]['user_basis'],'I waited 60 minutes')
        for choices in ([{'evidence_id':'e2','report_id':None}],
                        [{'evidence_id':'e2','report_id':'invented'}],
                        [{'evidence_id':'e1','report_id':'r1'}],
                        [{'evidence_id':'e2','report_id':'r1'},{'evidence_id':'e2','report_id':'r2'}]):
            with self.subTest(choices=choices),self.assertRaises(ValueError):
                self.contract().compile({'action':'passages','selections':choices})
        branch=next(b for b in self.contract().schema['properties']['response']['anyOf'] if b['properties']['action']['enum']==['passages'])
        variants=branch['properties']['selections']['items']['anyOf']
        self.assertEqual(variants[0]['properties']['report_id'],{'type':'null'})
        self.assertEqual(variants[1]['properties']['evidence_id']['enum'],['e2'])

    def test_terminal_fields_constructed_server_side(self):
        for action in c.TERMINALS:
            result = self.contract().compile({'action': action})
            self.assertEqual(result['evidence_ids'], [])
            self.assertEqual(result['applicability'], [])
            self.assertIsNone(result['question'])
            self.assertIsNone(result['clarification'])

    def test_schema_disjoint_modes_and_strict_fields(self):
        for branch in self.contract().schema['properties']['response']['anyOf']:
            self.assertFalse(branch['additionalProperties'])
            mode = branch['properties']['action']['enum'][0]
            self.assertEqual(set(branch['required']), {'action','selections'} if mode=='passages' else set(branch['properties']))
            if mode == 'question':
                self.assertNotIn('evidence_ids', branch['properties'])
            elif mode in c.TERMINALS:
                self.assertEqual(set(branch['properties']), {'action'})


if __name__ == '__main__':
    unittest.main()
