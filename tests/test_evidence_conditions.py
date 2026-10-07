import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import evidence_conditions as c
from demo_dataset import load_dataset

class ConditionsTests(unittest.TestCase):
    def setUp(self):
        self.doc=next(d for d in load_dataset(ROOT/'knowledge/curated/manifest.json') if d['source_path']=='MCELE-UNLOCK-001')
    def check(self, section, speech, basis=None, active=()):
        conditions=c.for_unit(self.doc,section,'1. Restart the browser.')
        claim={'condition_quote':section,'user_basis':speech if basis is None else basis}
        return c.validate(conditions,claim,speech,active)
    def test_paired_elapsed_wait(self):
        for speech in ['I waited60minutes','I waited 60 minutes','I waited one hour',"I've waited an hour"]:
            self.assertIsNone(self.check('Account still appears locked after waiting',speech))
            self.assertEqual(self.check('Need access before the wait ends',speech),'contradicted_elapsed_wait')
        self.assertIsNone(self.check('Need access before the wait ends','I waited 20 minutes'))
        self.assertEqual(self.check('Account still appears locked after waiting','I waited 20 minutes'),'contradicted_elapsed_wait')
    def test_null_condition_cannot_bypass(self):
        for section in ['After three failed login attempts','Need access before the wait ends','Account still appears locked after waiting','Unsure of your credentials']:
            descriptors=c.for_unit(self.doc,section,'Action')
            self.assertTrue(descriptors)
            self.assertEqual(c.validate(descriptors,{'condition_quote':None,'user_basis':None},'I waited 60 minutes'),'missing_condition_basis')
    def test_negated_hypothetical_and_stale(self):
        section='Account still appears locked after waiting'
        for speech in ["I haven't waited 60 minutes",'If I waited 60 minutes','I would have waited 60 minutes','Have I waited 60 minutes?', 'I waited almost 60 minutes']:
            self.assertIsNotNone(self.check(section,speech))
        self.assertIsNotNone(self.check(section,'Actually I waited 10 minutes','I waited 60 minutes',['I waited 60 minutes']))
        self.assertIsNotNone(self.check(section,"Actually I haven't waited",'I waited 60 minutes',['I waited 60 minutes']))
    def test_active_basis_and_unknown_condition(self):
        self.assertIsNone(self.check('Account still appears locked after waiting','Still locked','I waited 60 minutes',['I waited 60 minutes']))
        self.assertTrue(c.for_unit({},'Before restarting','Restart it'))
        self.assertTrue(c.for_unit({},'Troubleshooting','3. If the message persists, clear cache.'))
    def test_direct_report_binding_and_outcomes(self):
        section='Account still appears locked after waiting'
        self.assertIsNone(self.check(section,'I waited 60 minutes but it did not work'))
        for text in ['I waited 10 minutes, my friend waited 60 minutes.', 'I waited 10 minutes and the article says 60 minutes']:
            self.assertEqual(self.check(section,text),'contradicted_elapsed_wait')
        before='Need access before the wait ends'
        self.assertIsNone(self.check(before,'I need access before the wait ends'))
        self.assertEqual(self.check(before,'I need access before the wait ends','I need access before the wait ends',['I waited 60 minutes']),'contradicted_elapsed_wait')
    def test_basis_substring_does_not_strip_context(self):
        before='Need access before the wait ends'
        basis='I need access before the wait ends'
        for speech in ['If '+basis+', what happens?', 'Someone said "'+basis+'"', 'Maybe '+basis]:
            self.assertIsNotNone(self.check(before,speech,basis))
        after='Account still appears locked after waiting'
        basis='I waited 60 minutes'
        for speech in ['I did not say '+basis, 'Someone said "'+basis+'"', 'If '+basis+', what happens?']:
            self.assertIsNotNone(self.check(after,speech,basis))
    def test_future_step_condition_is_not_claimed_user_completion(self):
        descriptors=c.for_unit({},'', '7. After the browsing data has been cleared, restart your computer.')
        self.assertEqual(descriptors[0]['kind'],'instruction')
        self.assertIsNone(c.validate(descriptors,{'condition_quote':None,'user_basis':None},'Show the complete procedure.'))
        # A section applicability requirement cannot disappear behind an inline condition.
        descriptors=c.for_unit(self.doc,'Account still appears locked after waiting', '3. If the lockout persists, clear cache.')
        self.assertEqual(c.validate(descriptors,{'condition_quote':None,'user_basis':None},'Show the complete procedure.'),'missing_condition_basis')

    def test_uncertain_wait_is_not_an_elapsed_report(self):
        section='Account still appears locked after waiting'
        self.assertIsNone(self.check(section,'I waited 60 minutes.'))
        for prefix in ['Maybe', 'Perhaps', 'I am unsure whether', 'It is unknown whether']:
            self.assertIsNotNone(self.check(section,prefix+' I waited 60 minutes.','I waited 60 minutes'))
    def test_metadata_integrity(self):
        descriptors=self.doc['metadata']['section_conditions']
        c.validate_metadata(self.doc['content'],descriptors)
        for key,value in [('section','Fabricated'),('condition_quote','Fabricated'),('minimum_minutes',True),('relation','maybe')]:
            bad=copy.deepcopy(descriptors);bad[1][key]=value
            with self.assertRaises(ValueError):c.validate_metadata(self.doc['content'],bad)

if __name__=='__main__': unittest.main()
