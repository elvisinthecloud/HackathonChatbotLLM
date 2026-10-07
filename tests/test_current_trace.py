"""Actual v3 answer metadata must satisfy deployment trace verification offline."""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import support
import flexible_support as f
import verify_deployment
from test_architecture_acceptance import interpretation, decision


class CurrentTraceTests(unittest.IsolatedAsyncioTestCase):
    async def reply(self,mode):
        message='In MCeLE, what does Download Certificate do in My Courses?'
        sources=[{**support.chunk(aid),'applicability':{'applicable':True,'missing':[],'conflicts':[]}}
                 for aid in ('MCELE-COURSES-001','MCELE-FIND-001')]
        stages=[]
        async def model(rag,stage,prompt,payload,schema):
            stages.append(stage)
            if stage=='support_interpretation':return interpretation(message,reported_platform='MCeLE')
            if mode!='passages':return decision(mode)
            eid=next(key for key,part in payload['evidence_spans'].items() if '**Download Certificate:**' in part['quote'])
            return decision('passages',evidence_ids=[eid],applicability=[{
                'evidence_id':eid,'task_quote':message,'condition_quote':None,'user_basis':None}])
        tracing=MagicMock()
        with patch.object(support.rag,'langfuse',tracing),patch.object(f,'retrieve',AsyncMock(return_value=sources)),patch.object(f,'model_json',side_effect=model):
            result=await f.answer(support.rag,message,support.make_session('student'),None)
        metadata=next(call.kwargs['metadata'] for call in reversed(tracing.update_current_trace.call_args_list) if 'metadata' in call.kwargs)
        trace={'tags':['curated-demo'],'metadata':metadata,'observations':[{'name':name} for name in ['rag_answer','embed_text','article_candidate_search',*stages]]}
        return result,trace

    async def test_actual_cited_answer_trace_passes_current_deployment_verifier(self):
        result,trace=await self.reply('passages')
        self.assertIn('**Download Certificate:**',result['answer'])
        self.assertEqual([s['source_path'] for s in result['sources']],['MCELE-COURSES-001'])
        self.assertEqual(trace['metadata'].get('cited_source_ids'),['MCELE-COURSES-001'])
        self.assertIn('MCELE-FIND-001',trace['metadata']['retrieved_source_ids'])
        with patch.object(verify_deployment,'fetch',return_value=trace),patch.object(verify_deployment,'trace_headers',return_value={}),patch.object(verify_deployment.time,'sleep'):
            observed=verify_deployment.verify_trace('offline','Student','MCELE-COURSES-001')
        self.assertIn('support_decision',observed)

    async def test_retrieval_without_citation_is_not_a_verified_answer_trace(self):
        result,trace=await self.reply('source_gap')
        self.assertEqual(result['sources'],[])
        self.assertEqual(trace['metadata'].get('cited_source_ids'),[])
        with patch.object(verify_deployment,'fetch',return_value=trace),patch.object(verify_deployment,'trace_headers',return_value={}),patch.object(verify_deployment.time,'sleep'):
            with self.assertRaises(RuntimeError):verify_deployment.verify_trace('offline','Student','MCELE-COURSES-001')
