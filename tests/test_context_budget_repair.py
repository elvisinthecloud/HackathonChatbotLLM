"""Real corpus payloads exercise the production byte guard, without model calls."""
import copy
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import support as helpers
import flexible_support as f
from test_architecture_acceptance import ProductionHarness, interpretation, decision

OPENER='Hello! i need help with a marine of mine i am trying to push their seminar request forward.'


class ContextBudgetRepairTests(unittest.IsolatedAsyncioTestCase):
    async def test_first_turn_real_corpus_decision_and_repair_reach_transport(self):
        harness=ProductionHarness(lambda stage,payload,schema:
            interpretation(OPENER,activity='enrollment') if stage=='support_interpretation'
            else decision('source_gap'), ('MCELE-ECDEP-001',))
        await harness.turn(helpers.make_session('training-manager'),OPENER)
        call=next(c for c in harness.calls if c['stage']=='support_decision')
        payload=call['payload'];schema=call['schema']
        self.assertTrue(payload['evidence_spans'])
        self.assertEqual(set(schema['properties']),{'move','selection'})
        self.assertEqual(payload['history'],[])
        original=copy.deepcopy(payload)
        # A schema-valid but semantically invalid candidate can be much larger
        # than the small residual budget of a freshly packed evidence shortlist.
        invalid=decision('question')
        invalid['clarification']={'missing_detail':'x'*240,'why_needed':'y'*240,'evidence_id':next(iter(payload['evidence_spans']))}
        invalid['evidence_ids']=[invalid['clarification']['evidence_id']]
        invalid['applicability']=[{'evidence_id':invalid['evidence_ids'][0],'task_quote':OPENER,
            'condition_quote':None,'user_basis':None}]
        client=MagicMock()
        client.post=AsyncMock(side_effect=[
            MagicMock(status_code=200,json=lambda:{'message':{'content':json.dumps(f.decision_wire_candidate(invalid))}}),
            MagicMock(status_code=200,json=lambda:{'message':{'content':json.dumps(f.decision_wire_candidate(decision('source_gap')))}})])
        manager=MagicMock()
        manager.__aenter__=AsyncMock(return_value=client)
        manager.__aexit__=AsyncMock(return_value=False)
        with patch.object(helpers.rag,'langfuse',MagicMock()),patch.object(f.httpx,'AsyncClient',return_value=manager):
            value,reason,events,left=await f.checked_call(helpers.rag,'support_decision',f.DECISION_PROMPT,
                payload,schema,lambda v: f.validate_decision(v,harness.documents,[OPENER],
                    {'task_known':True},{'conversation':{}},payload['evidence_spans']),1)
        self.assertIsNone(reason)
        self.assertEqual(client.post.await_count,2)
        self.assertEqual(payload,original)
        self.assertEqual([e['decision'] for e in events],['evidence_mode_mismatch','accepted'])
        repair=client.post.await_args_list[1].kwargs['json']
        self.assertIn('evidence_mode_mismatch',str(repair['messages']))
        self.assertIn('For question: evidence_ids=[] and applicability=[]',repair['messages'][-2]['content'])
        self.assertIn('source anchor only in clarification.evidence_id',repair['messages'][-2]['content'])
        for request in client.post.await_args_list:
            body=request.kwargs['json']
            bound=len(json.dumps({'messages':body['messages'],'format':body['format']},ensure_ascii=False).encode())+512
            self.assertLessEqual(bound+body['options']['num_predict'],body['options']['num_ctx'])
        # Evidence and immutable role survive fitting; no evidence is swapped
        # between the initial choice and its repair.
        self.assertEqual(repair['messages'][0],client.post.await_args_list[0].kwargs['json']['messages'][0])
        self.assertIn('Training Manager',repair['messages'][0]['content'])

    def test_optional_candidate_removed_without_mutation_or_evidence_loss(self):
        payload={'current_user':OPENER,'role':'Training Manager','history':[],
            'evidence_spans':{'stable-id':{'quote':'Exact approved text'}},
            'repair_feedback':{'rejection':'unoffered_evidence','instruction':f.REPAIR_INSTRUCTION,
                'rejected_candidate':{'untrusted':'é'*20000}}}
        original=copy.deepcopy(payload);schema=f.decision_schema([])
        fitted=f.fit_payload('support_decision_repair',f.DECISION_PROMPT,payload,schema,16384)
        self.assertIsNotNone(fitted)
        self.assertNotIn('rejected_candidate',fitted['repair_feedback'])
        self.assertEqual(fitted['evidence_spans'],payload['evidence_spans'])
        self.assertEqual(payload,original)
        self.assertIsNone(f.fit_payload('support_decision_repair',f.DECISION_PROMPT,
            {**payload,'current_user':'é'*20000},schema,16384))

    def test_interpretation_does_not_receive_response_question_grammar(self):
        payload={'current_user':OPENER,'role':'Training Manager','question_grammar':{'sentinel':'unused grammar'}}
        for stage in ('support_interpretation','support_interpretation_repair'):
            messages=f.model_messages(stage,f.dialogue.PROMPT,payload)
            self.assertNotIn('unused grammar',str(messages))
            self.assertNotIn('Answer the current user using approved evidence',str(messages))
            self.assertIn('Extract user reports into the interpretation JSON only',messages[-2]['content'])
            self.assertIn('Training Manager',messages[-2]['content'])
        self.assertIn('unused grammar',str(f.model_messages('support_decision',f.DECISION_PROMPT,payload)))

        self.assertIn('Answer the current user using approved evidence',str(f.model_messages('support_decision',f.DECISION_PROMPT,payload)))
