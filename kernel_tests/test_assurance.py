import base64,copy,json,subprocess,tempfile,unittest
from pathlib import Path
from jsonschema import Draft202012Validator
from clses_mvas_v1.assurance import assess,deployment_inventory,load_profile
from clses_mvas_v1.store import canonical,digest

class AssuranceKernelTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.deployment=self.root/'deployment';self.deployment.mkdir();(self.deployment/'app.py').write_text('print("coffee")\n');self.private=self.root/'private.pem';self.public=self.root/'public.pem';subprocess.run(['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048','-out',str(self.private)],check=True,capture_output=True);subprocess.run(['openssl','pkey','-in',str(self.private),'-pubout','-out',str(self.public)],check=True,capture_output=True);self.now=2000000000;self.profile=load_profile('point-of-sale');self.dossier=self.make_dossier()
    def tearDown(self):self.temp.cleanup()
    def make_dossier(self):
        entries=deployment_inventory(self.deployment);domains=self.profile['domains'];artifacts=[]
        for domain in domains:
            paths=entries if domain=='release' else [];artifacts.append({'id':'artifact-'+domain,'domain':domain,'kind':'release_artifact' if domain=='release' else 'lifecycle_record','version':1,'digest':digest(paths) if paths else digest(domain),'owner':'owner-'+domain,'status':'active','paths':paths})
        relations=[{'from':'artifact-'+x['from'],'to':'artifact-'+x['to'],'type':x['type']} for x in self.profile['required_edges']];types=sorted({kind for c in self.profile['controls'] for kind in c['evidence_types']});adapter_core={'format':'CLSES-adapter-manifest/v1','id':'assurance-adapter','version':'1','capabilities':types,'trust_anchor':'organization-pki','execution_boundary':'external_service'};adapter={**adapter_core,'digest':digest(adapter_core)};evidence=[];decisions=[]
        for control in self.profile['controls']:
            refs=[]
            for kind in control['evidence_types']:
                measurements={'result':1}
                if control['id']=='realized-benefit-observed':measurements['checkout_time_seconds']=40
                item={'id':'e-'+control['id']+'-'+kind,'control_id':control['id'],'artifact_id':'artifact-'+control['domain'],'type':kind,'adapter_id':adapter['id'],'adapter_digest':adapter['digest'],'raw_digest':digest(control['id']+kind),'observed_at':self.now-100,'expires_at':self.now+1000,'environment_id':'prod-coffee','passed':True,'measurements':measurements};evidence.append(item);refs.append(item['id'])
                if control['id']=='realized-benefit-observed':
                    second=copy.deepcopy(item);second['id']=item['id']+'-period-2';second['raw_digest']=digest(second['id']);second['observed_at']=self.now-90;evidence.append(second);refs.append(second['id'])
            decisions.append({'id':'d-'+control['id'],'control_id':control['id'],'target_artifact_id':'artifact-'+control['domain'],'actor':'authority-'+control['authority_role'],'actor_type':'human','authority_role':control['authority_role'],'outcome':'approved','evidence_refs':refs,'decided_at':self.now-50,'expires_at':self.now+1000})
        outcome_evidence='e-realized-benefit-observed-outcome_observation';evaluation={'id':'oe-checkout','hypothesis_id':'faster-checkout','environment_id':'prod-coffee','baseline':80,'periods':[{'start':self.now-300,'end':self.now-200,'value':40,'evidence_ref':outcome_evidence},{'start':self.now-200,'end':self.now-100,'value':40,'evidence_ref':outcome_evidence+'-period-2'}],'counterfactual':'Comparable manual checkout remains at the 80-second baseline','attribution_method':'Before-after comparison with stable menu and staffing','total_cost':5000,'realized_value':9000,'harms':[],'assumptions':[{'statement':'Menu complexity and staffing remain comparable','status':'valid','evidence_ref':outcome_evidence}],'achieved':True,'sustained':True};outcome_decisions=[x['id'] for x in decisions if next(c for c in self.profile['controls'] if c['id']==x['control_id'])['domain']=='outcome_realization']
        return {'format':'CLSES-assurance-dossier/v1','system':{'id':'coffee-pos','class':'point-of-sale','purpose':'Operate a coffee cart point of sale','need':'Operators lose sales and create errors during slow manual checkout','beneficiaries':['cart operator','customer'],'outcome_hypotheses':[{'id':'faster-checkout','statement':'The POS reduces representative checkout time','beneficiary':'cart operator','metric':'checkout_time_seconds','unit':'seconds','operator':'<=','target':45,'minimum_sustained_periods':2,'horizon_seconds':2592000}],'operating_conditions':{'location':'mobile cart','connectivity':'intermittent'}},'profile':{'profile_id':self.profile['profile_id'],'version':self.profile['version'],'composed_digest':digest(self.profile)},'artifacts':artifacts,'relations':relations,'adapters':[adapter],'evidence':evidence,'decisions':decisions,'changes':[],'deployment':{'environment_id':'prod-coffee','artifact_digests':[next(x for x in artifacts if x['domain']=='release')['digest']],'inventory':entries,'authorization_decision_id':'d-release-accepted','deployed_at':self.now-400},'outcome_evaluations':[evaluation],'continuation':{'action':'continue','actor':'outcome-owner','actor_type':'human','authority_role':'outcome_authority','basis_decision_ids':outcome_decisions,'evaluation_ids':['oe-checkout'],'decided_at':self.now-25,'review_by':self.now+1000},'closure':{'decision':'assurance_accepted','actor':'governance-owner','actor_type':'human','authority_role':'governance_authority','control_decision_ids':[x['id'] for x in decisions],'continuation_action':'continue','decided_at':self.now,'expires_at':self.now+1000},'assessed_at':self.now}
    def bundle(self,dossier=None,key=None):
        dossier=copy.deepcopy(dossier or self.dossier);data=self.root/'data';sig=self.root/'sig';data.write_bytes(canonical(dossier));subprocess.run(['openssl','dgst','-sha256','-sign',str(key or self.private),'-out',str(sig),str(data)],check=True,capture_output=True);return {'dossier':dossier,'dossier_sha256':digest(dossier),'signature_base64':base64.b64encode(sig.read_bytes()).decode()}
    def result(self,dossier=None,public=None):return assess(self.bundle(dossier), 'point-of-sale',self.deployment,public or self.public,self.now)
    def test_complete_composed_profile_passes(self):self.assertTrue(self.result()['valid'])
    def test_every_lifecycle_domain_is_required(self):
        value=copy.deepcopy(self.dossier);value['artifacts']=[x for x in value['artifacts'] if x['domain']!='retirement'];self.assertFalse(self.result(value)['checks']['domain_coverage'])
    def test_required_trace_edge_is_required(self):
        value=copy.deepcopy(self.dossier);value['relations'].pop();self.assertFalse(self.result(value)['checks']['relations'])
    def test_every_control_evidence_type_is_required(self):
        value=copy.deepcopy(self.dossier);value['evidence']=[x for x in value['evidence'] if x['type']!='privacy_assessment'];decision=next(x for x in value['decisions'] if x['control_id']=='security-privacy-acceptable');decision['evidence_refs']=[x for x in decision['evidence_refs'] if 'privacy_assessment' not in x];self.assertFalse(self.result(value)['checks']['evidence'])
    def test_agent_cannot_supply_authority(self):
        value=copy.deepcopy(self.dossier);value['decisions'][0]['actor_type']='execution_agent';self.assertFalse(self.result(value)['checks']['authority_decisions'])
    def test_stale_evidence_fails(self):
        value=copy.deepcopy(self.dossier);value['evidence'][0]['expires_at']=self.now-1;self.assertFalse(self.result(value)['checks']['evidence'])
    def test_deployment_drift_fails(self):
        (self.deployment/'app.py').write_text('tampered');self.assertFalse(self.result()['checks']['deployment'])
    def test_material_change_requires_fresh_affected_evidence(self):
        value=copy.deepcopy(self.dossier);value['changes']=[{'id':'c1','kind':'dependency','affected_domains':['supply_chain'],'detected_at':self.now-10,'disposition':'reassessed','reassessment_decision_ids':['d-supply-chain-trusted']}];self.assertFalse(self.result(value)['checks']['changes_reassessed'])
    def test_closure_must_cover_every_control_decision(self):
        value=copy.deepcopy(self.dossier);value['closure']['control_decision_ids'].pop();self.assertFalse(self.result(value)['checks']['closure'])
    def test_unachieved_outcome_fails(self):
        value=copy.deepcopy(self.dossier);value['outcome_evaluations'][0]['periods'][-1]['value']=60;self.assertFalse(self.result(value)['checks']['outcomes_achieved_and_sustained'])
    def test_single_period_is_not_sustained(self):
        value=copy.deepcopy(self.dossier);value['outcome_evaluations'][0]['periods'].pop();self.assertFalse(self.result(value)['checks']['outcomes_achieved_and_sustained'])
    def test_one_observation_cannot_be_reused_as_multiple_periods(self):
        value=copy.deepcopy(self.dossier);value['outcome_evaluations'][0]['periods'][1]['evidence_ref']=value['outcome_evaluations'][0]['periods'][0]['evidence_ref'];self.assertFalse(self.result(value)['checks']['outcomes_achieved_and_sustained'])
    def test_outcome_requires_counterfactual_and_attribution(self):
        value=copy.deepcopy(self.dossier);value['outcome_evaluations'][0]['counterfactual']='';self.assertFalse(self.result(value)['checks']['outcomes_achieved_and_sustained'])
    def test_value_must_justify_cost(self):
        value=copy.deepcopy(self.dossier);value['outcome_evaluations'][0]['realized_value']=1;self.assertFalse(self.result(value)['checks']['outcomes_achieved_and_sustained'])
    def test_unmitigated_harm_fails(self):
        value=copy.deepcopy(self.dossier);value['outcome_evaluations'][0]['harms']=[{'description':'Operators excluded','severity':'high','status':'open'}];self.assertFalse(self.result(value)['checks']['outcomes_achieved_and_sustained'])
    def test_continuation_requires_outcome_authority_and_complete_basis(self):
        value=copy.deepcopy(self.dossier);value['continuation']['basis_decision_ids'].pop();self.assertFalse(self.result(value)['checks']['continuation'])
    def test_external_trust_anchor_is_required(self):
        other=self.root/'other.pem';other_public=self.root/'other-public.pem';subprocess.run(['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048','-out',str(other)],check=True,capture_output=True);subprocess.run(['openssl','pkey','-in',str(other),'-pubout','-out',str(other_public)],check=True,capture_output=True);self.assertFalse(self.result(public=other_public)['checks']['external_signature'])
    def test_duplicate_composed_control_is_rejected(self):
        value=json.loads((Path(__file__).parents[1]/'clses_mvas_v1/profiles/point-of-sale.json').read_text());value['controls'].append(copy.deepcopy(value['controls'][0]));path=self.root/'profile.json';path.write_text(json.dumps(value))
        with self.assertRaises(ValueError):load_profile(path)
    def test_packaged_profiles_satisfy_normative_schema(self):
        package=Path(__file__).parents[1]/'clses_mvas_v1';schema=json.loads((package/'schemas/lifecycle-profile.schema.json').read_text());validator=Draft202012Validator(schema)
        for path in (package/'profiles').glob('*.json'):self.assertEqual(list(validator.iter_errors(json.loads(path.read_text()))),[])

if __name__=='__main__':unittest.main()
