import copy,unittest
from clses_mvas_v1.release_assessment import load_policy,policy_checks

class AssessmentPolicyTest(unittest.TestCase):
    def setUp(self):
        self.policy=load_policy();self.evidence={'format':self.policy['assessment_format'],'version':self.policy['version'],'parts':{name:{} for name in self.policy['required_parts']},'dimensions':{name:True for name in self.policy['required_dimensions']},'tests':{'tests':self.policy['minimum_tests']},'inventory':[{'path':name} for name in self.policy['required_documents']],'claim_boundary':'; '.join(self.policy['required_claim_boundary_terms'])}
    def test_complete_evidence_shape_passes(self):self.assertTrue(all(policy_checks(self.evidence,self.policy).values()))
    def test_missing_part_fails(self):
        changed=copy.deepcopy(self.evidence);changed['parts'].pop(next(iter(changed['parts'])));self.assertFalse(policy_checks(changed,self.policy)['exact_parts'])
    def test_extra_part_fails(self):
        changed=copy.deepcopy(self.evidence);changed['parts']['unreviewed']=dict();self.assertFalse(policy_checks(changed,self.policy)['exact_parts'])
    def test_missing_dimension_fails(self):
        changed=copy.deepcopy(self.evidence);changed['dimensions'].pop(next(iter(changed['dimensions'])));self.assertFalse(policy_checks(changed,self.policy)['exact_dimensions'])
    def test_test_floor_fails(self):
        changed=copy.deepcopy(self.evidence);changed['tests']['tests']=self.policy['minimum_tests']-1;self.assertFalse(policy_checks(changed,self.policy)['minimum_tests'])
    def test_missing_boundary_disclosure_fails(self):
        changed=copy.deepcopy(self.evidence);changed['claim_boundary']='';self.assertFalse(policy_checks(changed,self.policy)['claim_boundary'])
if __name__=='__main__':unittest.main()
