"""Adversarial server boundaries for the planner; no live model evaluation."""
from test_architecture_acceptance import ProductionHarness, interpretation, decision, MANIFEST
import unittest
from unittest.mock import AsyncMock, patch
import support as helpers
import flexible_support as f


class PlannerBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_uncovered_requests_use_interpretation_and_explicit_searched_gap(self):
        cases=[('student',None,'How do I reset my blocked CAC PIN?'),('training-manager','5500','Must I automatically deny a request without a prerequisite certificate?')]
        for profile,course,message in cases:
            with self.subTest(profile=profile),patch.object(f,'model_json',AsyncMock(side_effect=[interpretation(message),decision('source_gap')])) as model,patch.object(f,'retrieve',AsyncMock(return_value=[])) as retrieve:
                result=await f.answer(helpers.rag,message,helpers.make_session(profile),course)
            self.assertIn('does not establish an answer',result['answer']);self.assertEqual(result['sources'],[])
            self.assertEqual(model.await_count,2);retrieve.assert_awaited_once()


