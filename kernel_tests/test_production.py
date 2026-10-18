import base64,copy,json,subprocess,tempfile,unittest
from pathlib import Path
from clses_mvas_v1.engine import default_spec
from clses_mvas_v1.production import assess,inventory
from clses_mvas_v1.store import canonical,digest

class ProductionProfileTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.deployment=self.root/'deployment';self.deployment.mkdir();(self.deployment/'service.py').write_text('print("healthy")\n');self.spec=default_spec('production-system','Operate correctly','users');self.spec_path=self.root/'spec.json';self.spec_path.write_text(json.dumps(self.spec));self.private=self.root/'private.pem';self.public=self.root/'public.pem';subprocess.run(['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048','-out',str(self.private)],check=True,capture_output=True);subprocess.run(['openssl','pkey','-in',str(self.private),'-pubout','-out',str(self.public)],check=True,capture_output=True);self.now=2000000000;entries=inventory(self.deployment);d='a'*64
        observations=[]
        for item in self.spec['requirements']+self.spec['outcomes']:observations.append({'criterion_key':item['key'],'measurement_key':item['measurement_key'],'value':1.0,'unit':item['unit'],'coverage':1.0,'source':item['source'],'method':'criterion-specific executable evaluation','adapter_digest':d,'raw_evidence_sha256':d,'observed_at':self.now-10,'expires_at':self.now+1000,'environment_id':'prod-1'})
        monitors=[{'domain':name,'status':'current','checked_at':self.now-10,'expires_at':self.now+1000,'evidence_digest':d} for name in ('source','dependencies','infrastructure','runtime','security','regulatory')]
        outcome_periods=[{'criterion_key':item['key'],'minimum_sustained_periods':2,'periods':[{'start':self.now-400,'end':self.now-300,'value':1.0,'raw_evidence_sha256':'b'*64},{'start':self.now-200,'end':self.now-100,'value':1.0,'raw_evidence_sha256':'c'*64}]} for item in self.spec['outcomes']]
        self.evidence={'format':'CLSES-production-evidence/v1','system_id':self.spec['system_id'],'spec_digest':digest(self.spec),'assessed_at':self.now,'artifact':{'digest':digest(entries),'entries':entries},'acceptance':{'artifact_digest':digest(entries),'passed':True,'actor':'release-owner','decision_digest':d,'evidence_digest':d},'deployment':{'artifact_digest':digest(entries),'environment_id':'prod-1','current_inventory':entries,'deployment_digest':d,'authorization_digest':d,'deployed_at':self.now-100},'observations':observations,'outcome_periods':outcome_periods,'change_monitors':monitors,'supply_chain':{'sbom_digest':d,'provenance_digest':d,'dependency_lock_digest':d,'vulnerability_scan_digest':d,'license_scan_digest':d,'critical_vulnerabilities':0,'policy_passed':True},'recovery':{'rollback_tested':True,'restore_tested':True,'rollback_evidence_digest':d,'restore_evidence_digest':d},'operations':{'monitoring_active':True,'open_critical_incidents':0,'observed_from':self.now-500,'observed_until':self.now-1,'telemetry_digest':d},'closure':{'decision':'closed_verified','artifact_digest':digest(entries),'spec_digest':digest(self.spec),'actor':'assessor','decision_digest':d}}
    def tearDown(self):self.tmp.cleanup()
    def bundle(self,evidence=None):
        evidence=copy.deepcopy(evidence or self.evidence);data=self.root/'data';signature=self.root/'sig';data.write_bytes(canonical(evidence));subprocess.run(['openssl','dgst','-sha256','-sign',str(self.private),'-out',str(signature),str(data)],check=True,capture_output=True);return {'evidence':evidence,'evidence_sha256':digest(evidence),'signature_base64':base64.b64encode(signature.read_bytes()).decode()}
    def result(self,evidence=None):return assess(self.bundle(evidence),self.spec_path,self.deployment,self.public,self.now)
    def test_complete_external_evidence_passes(self):self.assertTrue(self.result()['valid'])
    def test_current_deployment_tampering_fails(self):
        (self.deployment/'service.py').write_text('tampered');self.assertFalse(self.result()['checks']['deployment_current'])
    def test_missing_criterion_fails(self):
        value=copy.deepcopy(self.evidence);value['observations'].pop();self.assertFalse(self.result(value)['checks']['criteria_exact'])
    def test_stale_criterion_fails(self):
        value=copy.deepcopy(self.evidence);value['observations'][0]['expires_at']=self.now-1;self.assertFalse(self.result(value)['checks']['criteria_grounded'])
    def test_component_mismatch_fails(self):
        value=copy.deepcopy(self.evidence);value['artifact']['entries'][0]['path']='other.py';value['artifact']['digest']=digest(value['artifact']['entries']);self.assertFalse(self.result(value)['checks']['declared_components_exact'])
    def test_acceptance_evidence_is_required(self):
        value=copy.deepcopy(self.evidence);value['acceptance']['evidence_digest']='';self.assertFalse(self.result(value)['checks']['acceptance'])
    def test_every_change_monitor_is_required(self):
        value=copy.deepcopy(self.evidence);value['change_monitors'].pop();self.assertFalse(self.result(value)['checks']['change_monitors'])
    def test_supply_chain_policy_is_required(self):
        value=copy.deepcopy(self.evidence);value['supply_chain']['critical_vulnerabilities']=1;self.assertFalse(self.result(value)['checks']['supply_chain'])
    def test_recovery_evidence_is_required(self):
        value=copy.deepcopy(self.evidence);value['recovery']['restore_tested']=False;self.assertFalse(self.result(value)['checks']['recovery'])
    def test_active_operations_are_required(self):
        value=copy.deepcopy(self.evidence);value['operations']['open_critical_incidents']=1;self.assertFalse(self.result(value)['checks']['operations'])
    def test_exact_closure_is_required(self):
        value=copy.deepcopy(self.evidence);value['closure']['decision']='open';self.assertFalse(self.result(value)['checks']['closure'])
    def test_external_trust_anchor_rejects_other_signer(self):
        bundle=self.bundle();other=self.root/'other.pem';subprocess.run(['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048','-out',str(other)],check=True,capture_output=True);other_public=self.root/'other-public.pem';subprocess.run(['openssl','pkey','-in',str(other),'-pubout','-out',str(other_public)],check=True,capture_output=True);self.assertFalse(assess(bundle,self.spec_path,self.deployment,other_public,self.now)['checks']['external_signature'])
    def test_future_assessment_time_fails(self):
        value=copy.deepcopy(self.evidence);value['assessed_at']=self.now+1;self.assertFalse(self.result(value)['checks']['assessment_time'])
    def test_single_outcome_period_fails_sustained_gate(self):
        value=copy.deepcopy(self.evidence);value['outcome_periods'][0]['periods'].pop();self.assertFalse(self.result(value)['checks']['outcomes_sustained'])
    def test_duplicate_outcome_evidence_fails_sustained_gate(self):
        value=copy.deepcopy(self.evidence);value['outcome_periods'][0]['periods'][1]['raw_evidence_sha256']=value['outcome_periods'][0]['periods'][0]['raw_evidence_sha256'];self.assertFalse(self.result(value)['checks']['outcomes_sustained'])
    def test_failing_outcome_period_fails_sustained_gate(self):
        value=copy.deepcopy(self.evidence);value['outcome_periods'][0]['periods'][1]['value']=0.0;self.assertFalse(self.result(value)['checks']['outcomes_sustained'])
if __name__=='__main__':unittest.main()
