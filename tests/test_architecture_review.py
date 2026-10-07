"""Independent offline architecture boundary probes; no live quality claims."""
import unittest
import support as helpers
import dialogue_state as d
import flexible_support as f
from demo_dataset import load_dataset
from article_retrieval import applicability_status


def interpretation(text, **updates):
    result={'task_known':True,'task_quote':text,'transition':'continue','change_quote':None,
        'pending_answered':False,'course_id':None,'access_method':None,'activity':None,
        'reported_platform':None,'context_evidence':dict.fromkeys(('course_id','access_method','activity','reported_platform')),'revisions':[]}
    result.update(updates)
    return result


class IndependentBoundaryTests(unittest.TestCase):
    def test_negative_method_substring_cannot_satisfy_applicability(self):
        text='I am not using a browser. I want to open Moodle.'
        v=interpretation(text,access_method='browser')
        v['context_evidence']['access_method']='browser'
        self.assertIsNotNone(d.validate(v,{},text,[text],{}))

    def test_negative_platform_substring_cannot_satisfy_applicability(self):
        text='The content is not on Moodle. I want to open it.'
        v=interpretation(text,reported_platform='Moodle')
        v['context_evidence']['reported_platform']='Moodle'
        self.assertIsNotNone(d.validate(v,{},text,[text],{}))

    def test_hypothetical_method_substring_cannot_satisfy_applicability(self):
        text='If I use a browser, can I open the course?'
        v=interpretation(text,access_method='browser')
        v['context_evidence']['access_method']='browser'
        self.assertIsNotNone(d.validate(v,{},text,[text],{}))

    def test_negative_error_substring_cannot_satisfy_requirement(self):
        error=helpers.launch_error()
        text='I do not see '+error+'.'
        v=interpretation(text,revisions=[{'kind':'obstacle','status':'reported','quote':error,'supersedes':[]}])
        reason=d.validate(v,{},text,[text],{})
        if reason is None:
            memory=d.reconcile({},v,text)
            confirmed=any(f.affirmative_exact_error(record) for record in d.records(memory)
                if record.get('active',True) and record['kind']=='obstacle')
            self.assertFalse(confirmed)

    def test_full_negative_error_report_remains_unconfirmed(self):
        error=helpers.launch_error()
        text='I do not see '+error+'.'
        v=interpretation(text,revisions=[{'kind':'obstacle','status':'reported','quote':text,'supersedes':[]}])
        self.assertIsNone(d.validate(v,{},text,[text],{}))
        memory=d.reconcile({},v,text)
        self.assertFalse(any(f.affirmative_exact_error(record) for record in d.records(memory)
            if record.get('active',True) and record['kind']=='obstacle'))

    def test_selected_condition_requires_user_basis(self):
        doc=next(x for x in load_dataset(helpers.ROOT/'knowledge/curated/manifest.json') if x['source_path']=='MCELE-UNLOCK-001')
        source={**doc,'applicability':applicability_status(doc['metadata'],{})}
        spans=f.evidence_spans([source]);eid=next(k for k,v in spans.items() if 'Restart the browser' in v['quote'])
        text='I want to unlock my account.'
        value={'reply_mode':'passages','evidence_ids':[eid],'question':None,'clarification':None,
            'applicability':[{'evidence_id':eid,'task_quote':text,'condition_quote':spans[eid]['quote'],'user_basis':None}]}
        self.assertIsNotNone(f.validate_decision(value,[source],[text],{'task_known':True},{'conversation':{}}))

if __name__=='__main__': unittest.main()
