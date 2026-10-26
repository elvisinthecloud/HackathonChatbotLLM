"""Exact-source rendering contracts; model doubles do not prove selection accuracy."""
from test_architecture_acceptance import ProductionHarness, interpretation, decision, MANIFEST
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import support as helpers
import flexible_support as f
from demo_policy import ACCESS
rag, chunk = helpers.rag, helpers.chunk
make_session = helpers.make_session


def selection(sources=None, contains='Select **Request**', mode='passages', question=None):
    sources=sources or [chunk('MCELE-FIND-001')]
    ids=[key for key,part in f.evidence_spans(sources).items() if contains in part['quote']][:1] if mode=='passages' else []
    return {'reply_mode':mode,'evidence_ids':ids,'question':question,'goal_quote':None,'parent_goal_quote':None}


class ExactSelectionTests(unittest.TestCase):

    def test_unknown_ids_and_free_answer_prose_rejected(self):
        value=selection();value['evidence_ids']=['invented']
        self.assertEqual(f.validate_draft(value,[chunk('MCELE-FIND-001')],[]),'unoffered_evidence')
        value=selection();value['text']='Clear cache and try both email addresses.'
        self.assertEqual(f.validate_draft(value,[chunk('MCELE-FIND-001')],[]),'schema')

    def test_source_modes_cannot_omit_or_smuggle_passages(self):
        value=selection();value['evidence_ids']=[]
        self.assertEqual(f.validate_draft(value,[chunk('MCELE-FIND-001')],[]),'missing_evidence')
        value=selection();value['reply_mode']='source_gap'
        self.assertEqual(f.validate_draft(value,[chunk('MCELE-FIND-001')],[]),'evidence_mode_mismatch')

    def test_natural_advice_disguised_as_question_cannot_render(self):
        for text in ['Have you tried clearing the cache?', 'Could you use your work email?', 'Is your account automatically denied?']:
            value=selection(mode='question',question=text)
            self.assertEqual(f.validate_draft(value,[chunk('MCELE-FIND-001')],[]),'not_pure_question')
        self.assertIsNone(f.validate_draft(selection(mode='question',question='Which screen are you on?'),[chunk('MCELE-FIND-001')],[]))


    def test_exact_conditions_scope_and_heading_survive(self):
        sources=[{'source_path':'TEST','content':'Only for locked accounts.\n\n### After waiting\n\nIf the error remains:\n\n1. Restart the browser.\n2. Contact support.','title':'Test'}]
        value=selection(sources,contains='Restart the browser')
        text,used,_=f.render_selection(value,sources,{})
        for phrase in ['Only for locked accounts.','After waiting','If the error remains:','Restart the browser.']:
            self.assertIn(phrase,text)
        self.assertNotIn('Contact support.',text);self.assertEqual(used,{1})

    def test_step_continuation_is_not_dropped(self):
        sources=[{'source_path':'TEST','title':'Test','content':'Scope.\n\n1. Open the form.\nThis does not submit it.\n2. Review it.'}]
        value=selection(sources,contains='Open the form')
        text,_,_=f.render_selection(value,sources,{})
        self.assertIn('This does not submit it.',text);self.assertNotIn('Review it.',text)

    def test_renderer_method_guard_blocks_unconfirmed_app_instruction(self):
        sources=[chunk('MOODLE-APP-001')];value=selection(sources,contains='Download the Moodle app')
        text,used,pending=f.render_selection(value,sources,{'access_method':None})
        self.assertEqual(text,'Are you using the Moodle app or opening Moodle in a web browser?');self.assertEqual(used,set());self.assertTrue(pending)
        text,used,_=f.render_selection(value,sources,{'access_method':'app'})
        self.assertIn('Download the Moodle app',text);self.assertEqual(used,{1})

    def test_role_limit_is_profile_coverage_not_product_capability(self):
        text,used,_=f.render_selection(selection(mode='role_limit'),[chunk('MCELE-FIND-001')],{})
        self.assertIn('selected profile',text);self.assertNotIn('system does not support',text);self.assertEqual(used,set())

    def test_gap_does_not_quote_tangential_procedure(self):
        text,used,_=f.render_selection(selection(mode='source_gap'),[chunk('MCELE-FIND-001')],{})
        self.assertIn('does not establish',text);self.assertNotIn('Request',text);self.assertEqual(used,set())


class ExactProductionTests(unittest.IsolatedAsyncioTestCase):
    async def turn(self,value,message='I see Request',current=None,sources=None):
        source_list=[{**s,'applicability':{'applicable':True,'missing':[],'conflicts':[]}} for s in (sources or [chunk('MCELE-FIND-001')])]
        candidate=decision(value.get('reply_mode','passages'), evidence_ids=value.get('evidence_ids',[]),question=value.get('question'))
        if value.get('invalid'): candidate={'invalid':True}
        for key in value:
            if key not in {'reply_mode','evidence_ids','question','goal_quote','parent_goal_quote'}: candidate[key]=value[key]
        if candidate.get('reply_mode')=='passages':
            candidate['applicability']=[{'evidence_id':eid,'task_quote':message,'condition_quote':None,'user_basis':None} for eid in candidate['evidence_ids']]
        with patch.object(rag,'langfuse',MagicMock()),patch.object(f,'retrieve',AsyncMock(return_value=source_list)),patch.object(f,'model_json',AsyncMock(side_effect=[interpretation(message),candidate,candidate])) as model:
            result=await rag.answer_question(message,current or make_session('student'),None)
        return result,model

    async def test_factual_answer_is_canonical_source_text(self):
        result,model=await self.turn(selection())
        self.assertIn('Select **Request**',result['answer']);self.assertEqual(model.await_count,2)
        self.assertEqual(result['sources'][0]['source_path'],'MCELE-FIND-001')

    async def test_extra_generated_prose_is_rejected_at_decision_schema(self):
        value=selection();value['answer']='Try personal and work emails, clear cache, and deny the request.'
        result,model=await self.turn(value)
        self.assertNotIn('personal',result['answer']);self.assertEqual(result['sources'],[])
        self.assertEqual([call.args[1] for call in model.await_args_list],
                         ['support_interpretation', 'support_decision', 'support_decision_repair'])


    async def test_gap_renders_without_citations_or_automatic_question(self):
        result,_=await self.turn(selection(mode='source_gap'))
        self.assertIn('does not establish',result['answer']);self.assertNotIn('What exact message',result['answer'])
        self.assertEqual(result['sources'],[]);self.assertFalse(result['needs_clarification'])


    async def test_invalid_decision_preserves_goal_and_current_user_report(self):
        current=make_session('student');current['context']={'conversation':{'goal':'Recover access','user_reports':['MCeLE locked']}}
        result,_=await self.turn({'invalid':True},message='Actually it is the CAC PIN box',current=current)
        self.assertEqual(result['context']['conversation']['goal'],'Recover access')
        self.assertEqual(result['context']['conversation']['user_reports'][-1],'Actually it is the CAC PIN box')


class ConstraintRegressionTests(unittest.IsolatedAsyncioTestCase):


    def test_current_context_loader_accepts_existing_session_shape(self):
        self.assertEqual(f.clean_context(None)['conversation'],{})
        context=f.clean_context({'course_id':'5500','moodle_access_method':'app','conversation':None})
        self.assertEqual(context['access_method'],'app');self.assertEqual(context['course_id'],'5500')
        context=f.clean_context({'course_id':'unknown','conversation':{'goal':None,'user_reports':None}})
        self.assertIsNone(context['course_id']);self.assertEqual(context['conversation'],{})


    def test_pool_authorizes_roles_and_separates_scope_and_error(self):
        from article_retrieval import applicability_status
        context={'course_id':'5500','system_area':'MCeLE','activity':'enrollment'}
        ids=f.permitted_pool('Student',context,'I am an AO now')
        for aid in ('MOODLE-COPY-001','MCELE-ECDEP-001'): self.assertNotIn(aid,ids)
        for aid in ('MCELE-FIND-001','MCELE-LAUNCH-001','MCELE-EPME-001'): self.assertIn(aid,ids)
        self.assertIn('MCELE-ECDEP-001',f.permitted_pool('Training Manager',context,''))
        from demo_dataset import load_dataset
        docs={d['source_path']:d for d in load_dataset(MANIFEST)}
        self.assertFalse(applicability_status(docs['MCELE-LAUNCH-001']['metadata'],context)['applicable'])
        self.assertFalse(applicability_status(docs['MCELE-FIND-001']['metadata'],context)['applicable'])


    async def test_retrieval_is_role_filtered_diverse_and_hydrates_canonical_sources(self):
        from demo_dataset import load_dataset
        documents=[d for d in load_dataset(MANIFEST) if d['source_path'] in ('MCELE-FIND-001','MCELE-COURSES-001','MOODLE-ACCESS-001','MCELE-CAC-ASSOC-001')]
        allowed=tuple(d['source_path'] for d in documents);seen=[]
        def search(query,limit):
            access=ACCESS.get();seen.append(access)
            return [{**d,'content':'Untrusted retrieval-only ranking text','score':1-i/10,'article_metadata':d['metadata']} for i,d in enumerate(documents) if d['source_path'] in access.article_ids]
        with patch.object(rag,'embed_text',AsyncMock(return_value=[0.1])),patch.object(rag,'search_article_candidates',side_effect=search),patch.object(rag,'search_lexical_article_candidates',side_effect=search),patch.object(f,'load_dataset',return_value=documents):
            result=await f.retrieve(rag,'find a course',[],{'conversation':{}},'Student',allowed)
        self.assertEqual(len(result),4);self.assertEqual(len({r['source_path'] for r in result}),4)
        self.assertNotIn('Untrusted retrieval-only',str(result))
        self.assertTrue(all(a.role=='Student' for a in seen));self.assertIsNone(ACCESS.get())
        self.assertEqual({a.delivery_area for a in seen},{'MCeLE','Moodle'})

    async def test_transport_errors_do_not_escape_trace_context(self):
        client=MagicMock();client.__aenter__.return_value=client;client.post=AsyncMock(side_effect=f.httpx.ConnectError('private endpoint must stay private'))
        generation=MagicMock()
        with patch.object(rag,'langfuse',MagicMock()) as tracing,patch.object(f.httpx,'AsyncClient',return_value=client):
            tracing.start_as_current_generation.return_value.__enter__.return_value=generation
            with self.assertRaises(rag.OllamaError) as failure:
                await f.model_json(rag,'support_decision',f.DECISION_PROMPT,{},f.decision_schema([]))
        self.assertNotIn('private endpoint',str(failure.exception))
        self.assertNotIn('private endpoint',str(generation.mock_calls))


class GoalGateRevisionTests(unittest.IsolatedAsyncioTestCase):


    def test_compositional_question_renders_grounded_topic(self):
        question={'frame':'What help do you need{topic}?','topic_quote':'course'}
        self.assertTrue(f.safe_question(question,['Need help with course']))
        self.assertEqual(f.question_text(question),'What help do you need with "course"?')
        self.assertFalse(f.safe_question({**question,'topic_quote':'reset the password'},['Need help with course']))
        self.assertFalse(f.safe_question({**question,'frame':'Try clearing cache {topic}?'},['Need help with course']))


class BoundedConversationFixTests(unittest.IsolatedAsyncioTestCase):


    def test_question_connector_is_not_duplicated(self):
        question={'frame':'What are you trying to do{topic}?','topic_quote':'with course'}
        self.assertTrue(f.safe_question(question,['Need help with course']))
        self.assertEqual(f.question_text(question),'What are you trying to do with "course"?')
