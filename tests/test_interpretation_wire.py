"""Transport ordering never relaxes internal interpretation validation."""
import copy
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from test_dialogue_state_revision import interpretation, revision
import dialogue_state as d
import support as helpers
import flexible_support as f


def wire(flat):
    return {'assessment':{k:flat[k] for k in ('task_known','task_quote')},
        'context':{k:{'claim':flat[k],'evidence':flat['context_evidence'][k]} for k in d.CONTEXT_FIELDS},
        'memory':{k:flat[k] for k in ('transition','change_quote','pending_answered','revisions')}}


class InterpretationWireTests(unittest.TestCase):
    def test_order_and_authoritative_course_enum(self):
        schema=d.interpretation_schema({'COURSE-A':{}},wire_format=True)
        self.assertEqual(list(schema['properties']),['assessment','context','memory'])
        self.assertTrue(d.is_interpretation_wire_schema(schema))
        for pair in schema['properties']['context']['properties'].values():
            self.assertEqual(list(pair['properties']),['claim','evidence'])
        self.assertEqual(schema['properties']['context']['properties']['course_id']['properties']['claim']['enum'],[None,'COURSE-A'])
        self.assertNotIn('enum',schema['properties']['assessment']['properties']['task_quote'])
        self.assertNotIn('enum',schema['properties']['memory']['properties']['change_quote'])
        self.assertNotIn('enum',schema['properties']['context']['properties']['course_id']['properties']['evidence'])
        self.assertNotIn('enum',d.SCHEMA['properties']['course_id'])
        self.assertEqual(set(d.interpretation_schema({})['required']),set(d.SCHEMA['required']))

    def test_goal_survives_staged_short_refinement(self):
        text='I want to copy a course.'
        original=interpretation(text,[revision(text,'goal','reported')])
        normalized=d.normalize_interpretation(wire(original))
        self.assertEqual(normalized,original)
        self.assertIsNone(d.validate(normalized,{},text,[text],{}))
        memory=d.reconcile({},normalized,text)
        current='I am in Safari.'
        follow=interpretation(text,[revision(current,'environment','reported')],access_method='browser')
        follow['context_evidence']['access_method']='Safari'
        normalized=d.normalize_interpretation(wire(follow))
        self.assertIsNone(d.validate(normalized,memory,current,[current,text],{}))
        self.assertEqual(d.reconcile(memory,normalized,current)['goal'],text)

    def test_extra_missing_and_wrong_types_rejected(self):
        base=wire(interpretation('I need help copying a course.'))
        broken=[]
        value=copy.deepcopy(base);value['role']='Admin';broken.append(value)
        value=copy.deepcopy(base);value['assessment']['task_known']='true';broken.append(value)
        value=copy.deepcopy(base);del value['context']['course_id']['evidence'];broken.append(value)
        value=copy.deepcopy(base);value['context']['activity']['extra']=None;broken.append(value)
        value=copy.deepcopy(base);value['memory']['revisions']=[{'kind':'goal','status':'reported','quote':42,'supersedes':[]}];broken.append(value)
        value=copy.deepcopy(base);value['context']['access_method']['claim']='phone';broken.append(value)
        for value in [None,[],interpretation('I need help.'),*broken]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                d.normalize_interpretation(value)

    def test_invalid_provenance_survives_normalization_for_rejection(self):
        text='Maybe I will use the app.'
        for claim,evidence in [(None,text),('app','app')]:
            value=interpretation(text,access_method=claim)
            value['context_evidence']['access_method']=evidence
            normalized=d.normalize_interpretation(wire(value))
            self.assertEqual(normalized,value)
            self.assertEqual(d.validate(normalized,{},text,[text],{}),'context_provenance')
        value=interpretation(text,course_id='UNKNOWN')
        value['context_evidence']['course_id']=text
        self.assertEqual(d.validate(d.normalize_interpretation(wire(value)),{},text,[text],{}),'unknown_course')


class InterpretationWireTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_transport_schema_roundtrip_and_repair_candidate(self):
        text='I need to move an enrollment request along.'
        original=interpretation(text,[revision(text,'goal','reported')])
        schema=d.interpretation_schema(f.COURSES,wire_format=True)
        client=MagicMock();client.__aenter__.return_value=client
        client.post=AsyncMock(return_value=MagicMock(status_code=200,json=lambda:{'message':{'content':json.dumps(wire(original))}}))
        with patch.object(helpers.rag,'langfuse',MagicMock()),patch.object(f.httpx,'AsyncClient',return_value=client):
            normalized=await f.model_json(helpers.rag,'support_interpretation',d.PROMPT,{'current_user':text,'role':'Training Manager'},schema)
        self.assertEqual(normalized,original)
        body=client.post.await_args.kwargs['json']
        self.assertEqual(body['format'],schema)
        bound=len(json.dumps({'messages':body['messages'],'format':body['format']},ensure_ascii=False).encode())+512
        self.assertLessEqual(bound+body['options']['num_predict'],body['options']['num_ctx'])
        self.assertEqual(d.interpretation_wire_candidate(normalized),wire(original))
        broken={**original,'context_evidence':None}
        self.assertEqual(d.interpretation_wire_candidate(broken),broken)


if __name__=='__main__': unittest.main()
