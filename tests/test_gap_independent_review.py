"""Independent adversarial checks: scripted offline contracts, not model quality."""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from test_architecture_acceptance import interpretation, decision, MANIFEST
from test_dialogue_state_revision import revision
import support as helpers
import dialogue_state as d
import evidence_conditions as conditions
import flexible_support as f
from demo_dataset import load_dataset


class IndependentDecisionChecks(unittest.TestCase):
    def check(self, value, text, memory=None, sources=(), **context):
        return f.validate_decision(value, list(sources), [text],
            {'task_known':True,'task_quote':text},
            {'conversation':memory or {'obstacle':'It fails.'}, **context})

    def test_farewells_and_partial_success_do_not_resolve(self):
        for text in ('Thanks', 'Goodbye', 'That worked once but fails now.',
                     'If that worked, thanks.', 'That worked for login; launch still fails.',
                     'I completed the password reset.', 'It might work now.'):
            with self.subTest(text=text):
                self.assertEqual(self.check(decision('resolved'),text),'unconfirmed_conversational_act')
        self.assertIsNone(self.check(decision('resolved'),'That worked, thanks!'))
        self.assertIsNone(self.check(decision('acknowledge'),'Thanks for your help.'))
        self.assertIsNotNone(self.check(decision('acknowledge'),'Thanks, but it still fails.'))

    def test_known_goal_cannot_be_reasked(self):
        value=decision('question',question={'frame':'What are you trying to do{topic}?','topic_quote':None},
            clarification={'missing_detail':'task','why_needed':'Choose guidance','evidence_id':None})
        self.assertEqual(self.check(value,'Launch the course.'),'answered_goal_question')

    def test_answered_error_purpose_does_not_block_new_observation(self):
        memory={'turn':3,'obstacle':'Access denied.', 'answered_questions':[
            {'purpose':'error_message','turn':3,'answer_quote':'Access denied.'}]}
        clarification={'missing_detail':'result','why_needed':'Identify current outcome','evidence_id':None}
        repeated=decision('question',question={'frame':'What message appears{topic}?','topic_quote':None},clarification=clarification)
        observation=decision('question',question={'frame':'What happened next{topic}?','topic_quote':None},clarification=clarification)
        self.assertEqual(self.check(repeated,'Access denied.',memory),'repeated_answered_question')
        self.assertIsNone(self.check(observation,'Access denied.',memory))

    def test_delayed_error_repeat_requires_changed_obstacle(self):
        memory={'turn':5,'obstacle':'Access denied.', 'answered_questions':[
            {'purpose':'error_message','turn':3,'answer_quote':'Access denied.',
             'obstacle_quote':'Access denied.'}]}
        value=decision('question',question={'frame':'What message appears{topic}?','topic_quote':None},
            clarification={'missing_detail':'error','why_needed':'Choose guidance','evidence_id':None})
        self.assertEqual(self.check(value,'It still fails.',memory),'repeated_answered_question')
        changed={**memory,'obstacle':'The page is now blank.'}
        self.assertIsNone(self.check(value,'The page is now blank.',changed))

    def test_passage_followup_is_bound_to_selected_source(self):
        text='Find a course.'
        source={'source_path':'SYNTHETIC','content':'1. Open the course search.\n\n2. Choose the course.',
            'applicability':{'applicable':True,'missing':[],'conflicts':[]}}
        ids=list(f.evidence_spans([source]));selected=ids[0]
        value=decision('passages',evidence_ids=[selected],
            applicability=[{'evidence_id':selected,'task_quote':text,'condition_quote':None,'user_basis':None}],
            question={'frame':'What happened next{topic}?','topic_quote':None},
            clarification={'missing_detail':'result','why_needed':'Continue from the outcome','evidence_id':selected})
        self.assertIsNone(self.check(value,text,sources=[source]))
        value['clarification']['evidence_id']=ids[1]
        self.assertEqual(self.check(value,text,sources=[source]),'unsupported_followup')

    def test_unrelated_duration_cannot_justify_after_waiting(self):
        doc=next(doc for doc in load_dataset(MANIFEST) if doc['source_path']=='MCELE-UNLOCK-001')
        section='Account still appears locked after waiting'
        descriptors=conditions.for_unit(doc,section,'Action')
        for text in ('I waited 10 minutes, my friend waited 60 minutes.',
                     'I waited 10 minutes and the article says 60 minutes.'):
            with self.subTest(text=text):
                self.assertIsNotNone(conditions.validate(descriptors,
                    {'condition_quote':section,'user_basis':text},text))

    def test_before_wait_basis_cannot_launder_hypothetical(self):
        doc=next(doc for doc in load_dataset(MANIFEST) if doc['source_path']=='MCELE-UNLOCK-001')
        section='Need access before the wait ends'
        descriptors=conditions.for_unit(doc,section,'Action')
        basis='I need access before the wait ends'
        for text in ('If I need access before the wait ends, what happens?',
                     'Maybe I need access before the wait ends.'):
            with self.subTest(text=text):
                self.assertIsNotNone(conditions.validate(descriptors,
                    {'condition_quote':section,'user_basis':basis},text))


class IndependentProductionChecks(unittest.IsolatedAsyncioTestCase):
    async def test_wrong_wait_branch_rejected_and_matching_branch_rendered(self):
        doc=next(doc for doc in load_dataset(MANIFEST) if doc['source_path']=='MCELE-UNLOCK-001')
        source={**doc,'article_metadata':doc['metadata'],'chunk_index':0,'score':1.,
            'applicability':{'applicable':True,'missing':[],'conflicts':[]}}
        text='My account is locked. I waited 60 minutes.'
        for section,accepted in [('Need access before the wait ends',False),
                                 ('Account still appears locked after waiting',True)]:
            with self.subTest(section=section):
                selected=next(eid for eid,part in f.evidence_spans([source]).items() if part['section']==section)
                proposed=decision('passages',evidence_ids=[selected],applicability=[{
                    'evidence_id':selected,'task_quote':text,'condition_quote':section,'user_basis':'I waited 60 minutes.'}])
                async def model(_rag,stage,prompt,payload,schema):
                    return interpretation(text) if stage.startswith('support_interpretation') else proposed
                with patch.object(helpers.rag,'langfuse',MagicMock()), \
                     patch.object(f,'retrieve',AsyncMock(return_value=[source])), \
                     patch.object(f,'model_json',side_effect=model):
                    result=await f.answer(helpers.rag,text,helpers.make_session('student'),None)
                if accepted:
                    self.assertEqual([s['source_path'] for s in result['sources']],[doc['source_path']])
                    self.assertIn(f.evidence_spans([source])[selected]['quote'],result['answer'])
                else:
                    self.assertEqual(result['sources'],[])
                    self.assertIn('could not validate',result['answer'])

    async def test_social_acts_use_production_renderer(self):
        for text,mode,resolved in [('That worked, thanks!','resolved',True),
                                   ('Thank you.','acknowledge',False)]:
            with self.subTest(mode=mode),patch.object(helpers.rag,'langfuse',MagicMock()), \
                 patch.object(f,'retrieve',AsyncMock(return_value=[])), \
                 patch.object(f,'model_json',AsyncMock(side_effect=[interpretation(text),decision(mode)])):
                result=await f.answer(helpers.rag,text,helpers.make_session('student'),None)
            self.assertEqual(result['context']['conversation']['issue_resolved'],resolved)
            self.assertFalse(result['needs_clarification'])
            self.assertEqual(result['sources'],[])
            self.assertNotIn('could not validate',result['answer'])

    async def test_retained_hypothetical_environment_cannot_become_constraint(self):
        old='If I use Safari, the course may open.'
        memory=d.reconcile({},interpretation(old,revisions=[revision('Safari','environment','reported')]),old)
        session=helpers.make_session('student')
        session['context']={'conversation':memory}
        value=interpretation('Continue.',access_method='browser')
        value['context_evidence']['access_method']='Safari'
        with patch.object(helpers.rag,'langfuse',MagicMock()), \
             patch.object(f,'model_json',AsyncMock(return_value=value)), \
             patch.object(f,'retrieve',AsyncMock(return_value=[])) as retrieve:
            result=await f.answer(helpers.rag,'Continue.',session,None)
        retrieve.assert_not_awaited()
        self.assertIn('could not validate',result['answer'])
        self.assertNotEqual(result['context'].get('access_method'),'browser')

    async def test_fifth_compatible_candidate_survives_four_conflicts(self):
        documents=load_dataset(MANIFEST)
        conflicts=[doc for doc in documents if doc['metadata']['service_area']=='MCeLE'
            and 'Student' in doc['metadata']['allowed_roles']][:4]
        compatible=next(doc for doc in documents if doc['source_path']=='MOODLE-ACCESS-001')
        docs=[*conflicts,compatible]
        ranked=[{**doc,'article_metadata':doc['metadata'],'score':1.} for doc in docs]
        with patch.object(helpers.rag,'embed_text',AsyncMock(return_value=[0.])), \
             patch.object(helpers.rag,'search_article_candidates',return_value=[]), \
             patch.object(helpers.rag,'search_lexical_article_candidates',return_value=[]), \
             patch('article_retrieval.hybrid_rank',return_value=ranked), \
             patch.object(f,'load_dataset',return_value=docs):
            result=await f.retrieve(helpers.rag,'Open Moodle',[],
                {'conversation':{},'system_area':'Moodle','access_method':'browser'},
                'Student',tuple(doc['source_path'] for doc in docs))
        self.assertEqual([doc['source_path'] for doc in result],[compatible['source_path']])


if __name__=='__main__': unittest.main()
