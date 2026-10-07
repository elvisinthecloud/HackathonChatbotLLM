"""Complete canonical procedures fit the bounded evidence selection contract."""
import re
import unittest
from test_focused_passages import article
import flexible_support as f


def draft(ids):
    return {'reply_mode':'passages','evidence_ids':ids,'question':None,
            'goal_quote':None,'parent_goal_quote':None}


class ProcedurePassageTests(unittest.TestCase):
    def test_model_selection_order_cannot_reorder_procedure_steps(self):
        source=article('mcele-course-launch-sts1-student')
        spans=f.evidence_spans([source])
        ids=[key for key,part in spans.items() if re.match(r'^\d+\. ',part['quote'])]
        text,_,_=f.render_selection(draft(list(reversed(ids))),[source],{})
        self.assertEqual(re.findall(r'^(\d+)\. ',text,re.M),[str(i) for i in range(1,9)])

    def test_complete_sts1_procedure_validates_and_renders_all_eight_steps(self):
        source=article('mcele-course-launch-sts1-student')
        spans=f.evidence_spans([source])
        ids=[key for key,part in spans.items() if re.match(r'^\d+\. ',part['quote'])]
        self.assertEqual(len(ids),8)
        self.assertIsNone(f.validate_draft(draft(ids),[source],[]))
        text,used,pending=f.render_selection(draft(ids),[source],{})
        for key in ids:
            self.assertIn(spans[key]['quote'],text)
        self.assertIn('7. After the browsing data has been cleared, **restart your computer**.',text)
        self.assertIn('8. Log back in to **MCeLE** and try launching the course content again.',text)
        self.assertEqual(used,{1})
        self.assertFalse(pending)

    def test_current_decision_and_renderer_share_selection_limit(self):
        source={'source_path':'test','content':'\n'.join(f'{i}. Action {i}.' for i in range(1,18))}
        ids=list(f.evidence_spans([source]))
        schema=f.decision_schema([source])
        self.assertEqual(schema['properties']['evidence_ids']['maxItems'],16)
        for count,reason in [(16,None),(17,'unoffered_evidence')]:
            self.assertEqual(f.validate_draft(draft(ids[:count]),[source],[]),reason)


if __name__=='__main__':
    unittest.main()
