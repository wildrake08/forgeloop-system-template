import json,unittest,copy
from pathlib import Path
from clses_mvas_v1.validator import validate,assess
ROOT=Path(__file__).resolve().parents[1]
class ValidationTests(unittest.TestCase):
 def setUp(self):self.m=json.loads((ROOT/'examples/synthetic-valid.json').read_text())
 def artifact(self,name):return next(x for x in self.m['artifacts'] if x['id']==name)
 def assertRejected(self):self.assertTrue(validate(self.m))
 def test_valid(self):self.assertEqual(validate(self.m),[])
 def test_relational_not_self_certified(self):self.assertEqual(assess(self.m)['relational'],'indeterminate')
 def test_duplicate_revision(self):self.m['artifacts'].append(copy.deepcopy(self.m['artifacts'][0]));self.assertRejected()
 def test_dangling_reference(self):self.artifact('work')['references'].append({'id':'absent','version':1});self.assertRejected()
 def test_cross_system_reference(self):self.artifact('design')['subject']='other';self.assertRejected()
 def test_missing_production_approval(self):self.artifact('implementation')['references']=[x for x in self.artifact('implementation')['references'] if x['id']!='prodgrant'];self.assertRejected()
 def test_wrong_production_scope(self):self.artifact('prodgrant')['payload']['scope']='another-release';self.assertRejected()
 def test_engineering_grant_not_prod_grant(self):self.artifact('prodgrant')['payload']['decision_kind']='engineering_authorization';self.assertRejected()
 def test_missing_work_grant(self):self.artifact('work')['payload']['authorization_ref']=None;self.assertRejected()
 def test_future_evidence(self):self.artifact('observation')['payload']['observed_at']=131;self.assertRejected()
 def test_missing_provenance(self):self.artifact('observation')['payload']['source_provenance']=['other'];self.assertRejected()
 def test_inadequate_coverage(self):self.artifact('observation')['payload']['coverage']=.3;self.assertRejected()
 def test_wrong_method_binding(self):self.artifact('method')['payload']['bindings']['variable']='different';self.assertRejected()
 def test_unordered_horizon(self):self.artifact('purpose')['payload']['horizon']={'start':1000,'end':0};self.assertRejected()
 def test_ref_cycle(self):self.artifact('purpose')['references'].append({'id':'observation','version':1});self.assertRejected()
 def test_closure_missing_basis(self):
  self.m['artifacts'].append({'id':'closure','type':'A8','version':1,'subject':'demo','references':[],'payload':{'decision_kind':'closure','actor':'owner','scope':'finding','decision':'closed_verified','decided_at':125,'valid_until':500,'basis_refs':[],'target_ref':None,'authority_source':'policy'}});self.assertRejected()
 def test_invalid_artifact_payload(self):self.artifact('design')['payload']['unexpected']='yes';self.assertRejected()
if __name__=='__main__':unittest.main()
