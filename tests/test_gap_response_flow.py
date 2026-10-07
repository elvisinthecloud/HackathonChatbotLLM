"""Current response flow: genuine repair and outcome follow-up; no live model."""
import unittest
from test_architecture_acceptance import ProductionHarness, interpretation, decision, span_matching, ACCEPTED_STAGES
import support as h
import flexible_support as f


class ResponseFlowGapTests(unittest.IsolatedAsyncioTestCase):
    async def test_bad_goal_question_repairs_to_missing_error(self):
        message='I want to launch my course in MCeLE but an error appears.'
        def script(stage,payload,schema):
            if stage.startswith('support_interpretation'):
                return interpretation(message,reported_platform='MCeLE',revisions=[
                    {'kind':'goal','status':'reported','quote':'launch my course','supersedes':[]},
                    {'kind':'obstacle','status':'reported','quote':'an error appears','supersedes':[]}])
            repaired=stage.endswith('_repair')
            return decision('question',question={'frame':'What exact message do you see{topic}?' if repaired else 'What are you trying to do{topic}?','topic_quote':None},
                clarification={'missing_detail':'error' if repaired else 'goal','why_needed':'Select relevant guidance','evidence_id':None})
        harness=ProductionHarness(script)
        result=await harness.turn(h.make_session('student'),message)
        self.assertEqual(result['answer'],'What exact message do you see?')
        self.assertEqual(harness.last_validations,[ACCEPTED_STAGES[0],
            {'stage':'decision','reason':'answered_goal_question'},ACCEPTED_STAGES[1]])
        self.assertEqual(len(harness.calls),3)
        self.assertEqual(result['context']['conversation']['pending_purpose']['purpose'],'error_message')

    async def test_instruction_and_followup_store_only_question_as_pending(self):
        message='How do I find my courses in MCeLE?'
        def script(stage,payload,schema):
            if stage.startswith('support_interpretation'):return interpretation(message,reported_platform='MCeLE')
            eid=span_matching(payload,'Select **Student Dashboard**')
            return decision('passages',evidence_ids=[eid],question={'frame':'What do you see now{topic}?','topic_quote':None},
                clarification={'missing_detail':'result','why_needed':'Continue from the result of this step','evidence_id':eid},
                applicability=[{'evidence_id':eid,'task_quote':message,'condition_quote':None,'user_basis':None}])
        harness=ProductionHarness(script,['MCELE-COURSES-001'])
        result=await harness.turn(h.make_session('student'),message)
        self.assertEqual(harness.last_validations,ACCEPTED_STAGES)
        self.assertIn('1. Select **Student Dashboard** in the left navigation menu. [1]',result['answer'])
        self.assertTrue(result['answer'].endswith('What do you see now?'))
        self.assertTrue(result['needs_clarification'])
        self.assertEqual(result['context']['conversation']['pending_question'],'What do you see now?')
        self.assertEqual([s['source_path'] for s in result['sources']],['MCELE-COURSES-001'])

    def test_malformed_question_is_rejected_without_exception(self):
        value=decision('question',question='What happened?')
        self.assertEqual(f.validate_decision(value,[],['Help'],{'task_known':True},
            {'conversation':{'obstacle':'Error'}}),'not_pure_question')
