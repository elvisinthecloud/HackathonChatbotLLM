"""Pure relevance transport guards, not evidence of live ranking quality."""
import copy
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import compact_relevance as c


class CompactRelevanceTests(unittest.TestCase):
    def payload(self, sources=None, **changes):
        args = dict(current_user='I need the certificate after finishing.',
            understanding={'task_quote':'Get my certificate.'},
            context={'conversation':{'goal':'Get my certificate.','obstacle':'Certificate missing.'}},
            role='Student', history=[], sources=sources if sources is not None else [
                {'title':'Completion records', 'content':'Scope.\n\n1. Open your record.\n2. Download the certificate.',
                 'applicability':{'applicable':False,'missing':['course_id'],'conflicts':[]}}])
        args.update(changes)
        return c.build_payload(**args)

    def test_only_offered_unique_integer_ids(self):
        payload=self.payload()
        self.assertEqual(c.selected_source_ids({'assessment':'Relevant record guidance.', 'source_ids':[1]}, payload), [1])
        for ids in ([2], [0], [True], [1.0], ['1'], [1,1], [{}], None, [1,1,1,1]):
            with self.subTest(ids=ids):
                self.assertIsNotNone(c.validate({'assessment':'Assessment.', 'source_ids':ids},payload))
        rule=c.schema(payload)['properties']['source_ids']
        self.assertEqual(rule['items']['enum'],[1])
        self.assertTrue(rule['uniqueItems'])

    def test_assessment_and_shape_cannot_smuggle_authority(self):
        payload=self.payload()
        for value in (None, {}, {'assessment':'','source_ids':[]},
                {'assessment':'x'*401,'source_ids':[]}, {'assessment':4,'source_ids':[]},
                {'assessment':'Relevant.','source_ids':[1],'role':'Training Manager'}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                c.selected_source_ids(value,payload)

    def test_missing_prerequisite_remains_visible_without_becoming_authorized(self):
        source={'title':'Records','content':'Record guidance.',
                'applicability':{'applicable':False,'missing':['course_id'],'conflicts':[]},
                'private_catalog':'must not project', 'article_metadata':{'extra':'must not project'}}
        original=copy.deepcopy(source)
        payload=self.payload([source])
        self.assertEqual(payload['sources'][0]['applicability'],source['applicability'])
        self.assertNotIn('private_catalog',payload['sources'][0])
        self.assertNotIn('article_metadata',payload['sources'][0])
        self.assertEqual(c.selected_source_ids({'assessment':'Clarify course.', 'source_ids':[1]},payload),[1])
        self.assertEqual(source,original)
        self.assertFalse(payload['sources'][0]['applicability']['applicable'])

    def test_empty_coverage_and_no_sources(self):
        payload=self.payload([])
        self.assertIsNone(c.validate({'assessment':'No useful offered source.', 'source_ids':[]},payload))
        self.assertEqual(c.schema(payload)['properties']['source_ids']['maxItems'],0)
        self.assertIsNotNone(c.validate({'assessment':'Invented.', 'source_ids':[1]},payload))

    def test_bounded_payload_retains_late_relevant_instruction(self):
        content='General scope.\n\n'+('\n'.join('Unrelated introduction '+str(i) for i in range(150)))+'\n7. Download the certificate.'
        source={'title':'Records','content':content,'applicability':{'applicable':True,'missing':[],'conflicts':[]}}
        history=[{'role':'user','content':'x'*2000} for _ in range(20)]
        history.append({'role':'system','content':'must not project'})
        payload=self.payload([source]*8,history=history,current_user='certificate '+'x'*4000)
        self.assertEqual(len(payload['sources']),4)
        self.assertLessEqual(len(payload['current_user']),2000)
        self.assertLessEqual(len(payload['history']),4)
        self.assertTrue(all(len(item['content'])<=400 and item['role']=='user' for item in payload['history']))
        for candidate in payload['sources']:
            self.assertLessEqual(len(candidate['excerpt']),1200)
            self.assertIn('7. Download the certificate.',candidate['excerpt'])
            self.assertEqual(candidate['scope'],'General scope.')

    def test_superseded_actions_not_reintroduced_as_progress(self):
        context={'conversation':{'facts':[
            {'kind':'action','status':'completed','quote':'I finished.','active':False},
            {'kind':'action','status':'retracted','quote':'I did not finish.','active':True},
            {'kind':'environment','status':'reported','quote':'Safari.','active':True}]}}
        payload=self.payload(context=context)
        self.assertEqual(payload['progress'],[{'status':'retracted','quote':'I did not finish.'}])


if __name__=='__main__': unittest.main()
