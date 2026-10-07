"""Wire-format boundary regressions, not a substitute for live model evaluation."""
from test_architecture_acceptance import ProductionHarness, interpretation, decision, MANIFEST
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import support as helpers
import flexible_support as f


class ModelTransportTests(unittest.IsolatedAsyncioTestCase):

    async def test_mixed_question_and_evidence_never_renders_after_repair_exhausted(self):
        message='Help me find courses';sources=[{**helpers.chunk('MCELE-FIND-001'),'applicability':{'applicable':True,'missing':[],'conflicts':[]}}]
        evidence=next(iter(f.evidence_spans(sources)))
        mixed=decision('question',evidence_ids=[evidence],question={'frame':'What happened{topic}?','topic_quote':None},clarification={'missing_detail':'task','why_needed':'needed','evidence_id':None})
        with patch.object(f,'model_json',AsyncMock(side_effect=[interpretation(message),mixed,mixed])) as model,patch.object(f,'retrieve',AsyncMock(return_value=sources)):
            result=await f.answer(helpers.rag,message,helpers.make_session('student'),None)
        self.assertEqual(model.await_count,3);self.assertEqual(result['sources'],[])
        self.assertNotIn('What happened',result['answer']);self.assertNotIn('Course Catalog',result['answer'])


    async def test_actual_current_requests_disable_thinking_and_keep_budgets(self):
        client=MagicMock();client.__aenter__.return_value=client;client.post=AsyncMock()
        response=MagicMock(status_code=200)
        response.json.return_value={'message':{'content':'{}'}}
        client.post.return_value=response
        for stage, prompt, schema in (
            ('support_interpretation', f.dialogue.PROMPT, f.dialogue.SCHEMA),
            ('support_decision', f.DECISION_PROMPT, f.decision_schema([])),
            ('support_decision_repair', f.DECISION_PROMPT, f.decision_schema([])),
        ):
            with patch.object(helpers.rag,'langfuse',MagicMock()),patch.object(f.httpx,'AsyncClient',return_value=client):
                await f.model_json(helpers.rag,stage,prompt,{'current_user':'help'},schema)
            request=client.post.await_args.kwargs['json']
            self.assertIs(request['think'],False)
            self.assertEqual(request['format'],schema)
            self.assertEqual(request['options'],{'temperature':0,'num_ctx':helpers.rag.settings.num_ctx,'num_predict':1800})
            self.assertEqual(request['messages'][-1],{'role':'user','content':'help'})


if __name__=='__main__':
    unittest.main()
