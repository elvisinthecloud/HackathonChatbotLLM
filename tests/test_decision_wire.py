"""Current transport envelope checks; no live model quality claims."""
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import support as helpers
import flexible_support as f
from test_architecture_acceptance import decision


class DecisionWireTests(unittest.IsolatedAsyncioTestCase):
    async def transport(self,value):
        client=MagicMock();client.__aenter__.return_value=client
        response=MagicMock(status_code=200)
        response.json.return_value={'message':{'content':json.dumps(value)}}
        client.post=AsyncMock(return_value=response)
        schema=f.decision_schema([],wire_format=True)
        with patch.object(helpers.rag,'langfuse',MagicMock()),patch.object(f.httpx,'AsyncClient',return_value=client):
            result=await f.model_json(helpers.rag,'support_decision',f.DECISION_PROMPT,
                {'current_user':'Help with my course','role':'Student'},schema)
        return result,client.post.await_args.kwargs['json']

    async def test_wire_roundtrip_preserves_selection_and_internal_validation(self):
        flat=decision('question',question={'frame':'What are you trying to do{topic}?','topic_quote':None},
            clarification={'missing_detail':'course','why_needed':'identify course','evidence_id':None})
        wire={'move':flat['reply_mode'],'selection':{k:v for k,v in flat.items() if k!='reply_mode'}}
        result,request=await self.transport(wire)
        self.assertEqual(result,flat)
        self.assertEqual(sorted(request['format']['properties']),['move','selection'])
        self.assertNotIn('reply_mode',request['format']['properties']['selection']['properties'])
        self.assertEqual(request['format'],f.decision_schema([],wire_format=True))
        self.assertIsNone(f.validate_decision(result,[],['Help with my course'],{'task_known':False},{'conversation':{}}))
        self.assertEqual(f.decision_wire_candidate(result),wire)

    async def test_malformed_envelopes_cannot_hide_or_override_fields(self):
        flat=decision('source_gap')
        valid={'move':'source_gap','selection':{k:v for k,v in flat.items() if k!='reply_mode'}}
        variants=[flat,[],{**valid,'extra':'discard me'},
            {**valid,'move':'invented'}, {**valid,'move':[]},
            {**valid,'selection':[]},
            {**valid,'selection':{**valid['selection'],'reply_mode':'passages'}},
            {**valid,'selection':{k:v for k,v in valid['selection'].items() if k!='applicability'}}]
        for malformed in variants:
            with self.subTest(value=malformed):
                result,_=await self.transport(malformed)
                self.assertIsNone(result)

    async def test_envelope_does_not_relax_mode_validation(self):
        sources=[helpers.chunk('MCELE-ECDEP-001')]
        eid=next(iter(f.evidence_spans(sources)))
        flat=decision('question',evidence_ids=[eid],question={'frame':'Which course do you mean{topic}?','topic_quote':None},
            clarification={'missing_detail':'course','why_needed':'identify course','evidence_id':eid})
        result,_=await self.transport(f.decision_wire_candidate(flat))
        self.assertEqual(f.validate_decision(result,sources,['Help with my course'],
            {'task_known':True},{'conversation':{}}),'evidence_mode_mismatch')
        self.assertIn('reply_mode',f.decision_schema([])['properties'])
