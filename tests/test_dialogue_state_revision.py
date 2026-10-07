"""Offline contract simulations; do not establish live model dialogue quality."""
import os
import sys
import unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','backend'))
import dialogue_state as d


def interpretation(text, revisions=(), **changes):
    return {'task_known':True,'task_quote':text,'transition':'continue','change_quote':None,
        'pending_answered':False,'course_id':None,'access_method':None,'activity':None,
        'reported_platform':None,'context_evidence':{k:None for k in ('course_id','access_method','activity','reported_platform')},'revisions':list(revisions),**changes}


def revision(quote,kind='action',status='completed',supersedes=()):
    return {'quote':quote,'kind':kind,'status':status,'supersedes':list(supersedes)}


class StateRevisionSimulation(unittest.TestCase):
    def apply(self,memory,text,revisions,**changes):
        v=interpretation(text,revisions,**changes)
        self.assertIsNone(d.validate(v,memory,text,[text],{}))
        return d.reconcile(memory,v,text)

    def test_correction_retracts_completion_without_losing_goal(self):
        m=self.apply({},'I want to launch it.',[revision('I want to launch it.','goal','reported')])
        m=self.apply(m,'I completed the reset.',[revision('I completed the reset.')])
        completed=next(f for f in m['facts'] if f['status']=='completed')
        m=self.apply(m,'I was wrong. I did not complete the reset.',[
            revision('I did not complete the reset.',status='retracted',supersedes=[completed['id']])])
        self.assertEqual(m['completed_quotes'],[])
        self.assertEqual(m['goal'],'I want to launch it.')
        self.assertFalse(next(f for f in m['facts'] if f['id']==completed['id'])['active'])
        self.assertEqual(next(f for f in m['facts'] if f['status']=='retracted')['supersedes'],[completed['id']])

    def test_method_correction_preserves_unrelated_actions(self):
        m=self.apply({},'I am using the app.',[revision('I am using the app.','environment','reported')])
        app=m['facts'][-1]['id']
        m=self.apply(m,'I signed in.',[revision('I signed in.')])
        m=self.apply(m,'Actually I am in a browser.',[revision('Actually I am in a browser.','environment','reported',[app])])
        self.assertEqual(m['environment'],['Actually I am in a browser.'])
        self.assertEqual(m['completed_quotes'],['I signed in.'])

    def test_unanchored_and_cross_kind_retractions_rejected(self):
        m=self.apply({},'I need my receipt.',[revision('I need my receipt.','goal','reported')])
        for rev in [revision('I did not finish.',status='retracted'),
                    revision('I did not finish.',status='retracted',supersedes=[m['facts'][0]['id']]),
                    revision('I finished the reset.')]:
            value=interpretation('I did not finish.',[rev])
            self.assertIsNotNone(d.validate(value,m,'I did not finish.',['I did not finish.'],{}))

    def test_negative_completion_cannot_launder_substring(self):
        value=interpretation('I have not completed the reset.',[revision('completed the reset')])
        self.assertEqual(d.validate(value,{},'I have not completed the reset.',['I have not completed the reset.'],{}),'unconfirmed_completion')

    def test_pending_answer_and_switch_are_distinct(self):
        m={'pending_question':'What message appears?','pending_purpose':{'missing_detail':'message'}}
        m=self.apply(m,'Access denied.',[revision('Access denied.','obstacle','reported')],pending_answered=True)
        self.assertNotIn('pending_question',m)
        self.assertEqual(m['obstacle'],'Access denied.')
        m=self.apply(m,'New task: my receipt.',[revision('my receipt.','goal','reported')],transition='switch',change_quote='New task: my receipt.')
        self.assertNotIn('obstacle',m)

    def test_legacy_completion_can_be_corrected(self):
        old={'completed_quotes':['I completed the reset.']}
        key=d.records(old)[0]['id']
        m=self.apply(old,'No, that was incorrect.',[revision('No, that was incorrect.',status='retracted',supersedes=[key])])
        self.assertEqual(m['completed_quotes'],[])

    def test_context_substring_cannot_launder_negation(self):
        for text,field,token in [('I am not using a browser.','access_method','browser'),
                ('I am not using Moodle.','reported_platform','Moodle'),
                ('Maybe I will use the app.','access_method','app')]:
            v=interpretation(text,**{field:token})
            v['context_evidence'][field]=token
            self.assertEqual(d.validate(v,{},text,[text],{}),'context_provenance')

    def test_authority_fields_rejected(self):
        v=interpretation('I want administrator access.')
        v['role']='administrator'
        self.assertEqual(d.validate(v,{},v['task_quote'],[v['task_quote']],{}),'interpretation_schema')

if __name__=='__main__': unittest.main()
