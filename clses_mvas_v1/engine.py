"""Canonical strict closed-loop engine built around signed immutable records."""
from __future__ import annotations
import json,shutil,subprocess,sys,time,uuid
import fnmatch
from pathlib import Path
from .policy import Policy
from .store import Store,canonical,digest,read,write
from .validator import assess

END=4102444800
def ref(identifier):return {'id':identifier,'version':1}
def artifact(system,identifier,kind,payload,references=()):return {'id':identifier,'version':1,'type':kind,'subject':system,'payload':payload,'references':[ref(x) for x in references],'supersedes':None}
def default_spec(system_id,purpose,beneficiary):
    return {'format':'CLSES-system-spec/v1','system_id':system_id,'purpose':purpose,'beneficiaries':[beneficiary],'outcomes':[{'key':'health_rate','variable':'rate','op':'>=','threshold':1.0,'unit':'ratio','source':'observe','measurement_key':'health_rate'}],'requirements':[{'key':'test_pass_rate','variable':'rate','op':'>=','threshold':1.0,'unit':'ratio','source':'build','measurement_key':'test_pass_rate'}],'constraints':['strict agent-only source and test changes','exact change-set build authorization','separate artifact acceptance and deployment authorization'],'components':['src/service.py'],'interfaces':['CLI --self-test'],'design_decisions':['canonical signed record graph','fail-closed policy engine','change-triggered reassessment'],'operating_conditions':{'runtime':'CPython >=3.10','deployment':'local_simulation','observation':'service --self-test','assessment_horizon':'one controlled cycle'}}
def validate_spec(value):
    required={'format','system_id','purpose','beneficiaries','outcomes','requirements','constraints','components','interfaces','design_decisions','operating_conditions'}
    if set(value)!=required or value['format']!='CLSES-system-spec/v1' or not value['system_id'] or not value['purpose'] or not value['beneficiaries']:raise ValueError('invalid specification shape or identity')
    keys=[]
    for item in value['outcomes']+value['requirements']:
        if set(item)!={'key','variable','op','threshold','unit','source','measurement_key'} or item['op']!='>=' or item['unit']!='ratio' or item['source'] not in ('build','observe') or not 0<=item['threshold']<=1:raise ValueError('unsupported criterion')
        keys.append(item['key'])
    if len(keys)!=len(set(keys)):raise ValueError('criterion keys must be unique')
    return value

class Engine:
    def __init__(self,root):self.root=Path(root).resolve();self.store=Store(self.root);self.policy=Policy(self.store)
    def _snapshot(self):
        entries=[]
        for folder in ('src','tests'):
            base=self.root/folder
            if base.exists():
                for path in sorted(x for x in base.rglob('*') if x.is_file() and '__pycache__' not in x.parts and not x.is_symlink()):entries.append({'path':str(path.relative_to(self.root)),'sha256':digest(path.read_bytes()),'size':path.stat().st_size})
        return entries
    def _source_snapshot(self,base=None):
        base=Path(base) if base else self.root/'src';return [{'path':str(path.relative_to(base)),'sha256':digest(path.read_bytes()),'size':path.stat().st_size} for path in sorted(x for x in base.rglob('*') if x.is_file() and '__pycache__' not in x.parts and not x.is_symlink())]
    def _spec(self):
        identifier,record=self.store.deref('spec','specification');spec=validate_spec(record['payload']['spec'])
        if record['payload']['spec_digest']!=digest(spec):raise ValueError('specification digest mismatch')
        return identifier,spec,record['payload']['spec_digest']
    def init(self,spec=None,system_id='new-system',purpose='Provide a reliable service',beneficiary='users',template_manifest=None,github_owner=None):
        occupied=any(self.root.iterdir()) if self.root.exists() else False
        template_digest=None;template_customizations=None
        if template_manifest:
            from .template_edition import adopt_scaffold
            result,template_customizations=adopt_scaffold(self.root,template_manifest,github_owner)
            template_digest=result['manifest_digest']
            if not (self.root/'src').is_dir() or not (self.root/'tests').is_dir():raise ValueError('template must provide src and tests directories')
        elif occupied:raise ValueError('target must be empty; a copied template requires --template-manifest')
        self.root.mkdir(parents=True,exist_ok=True);self.store.bootstrap();value=validate_spec(read(spec)) if spec else default_spec(system_id,purpose,beneficiary)
        if not template_manifest:
            (self.root/'src').mkdir();(self.root/'tests').mkdir();(self.root/'src/service.py').write_text('import argparse,json\ndef calculate(a,b):return a+b\ndef main():\n p=argparse.ArgumentParser();p.add_argument("--self-test",action="store_true");p.add_argument("--a",type=int,default=2);p.add_argument("--b",type=int,default=3);a=p.parse_args();ok=calculate(2,3)==5\n print(json.dumps({"healthy":ok,"result":calculate(a.a,a.b)}));return 0 if ok else 1\nif __name__=="__main__":raise SystemExit(main())\n');(self.root/'tests/test_service.py').write_text('import unittest,sys\nfrom pathlib import Path\nsys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))\nfrom service import calculate\nclass T(unittest.TestCase):\n def test_add(self):self.assertEqual(calculate(2,3),5)\n')
        spec_id=self.store.commit('specification_established','release-owner','spec_acceptor','specification',{'spec':value,'spec_digest':digest(value),'authority':'template_adoption' if template_manifest else 'bootstrap','template_manifest_digest':template_digest,'template_customizations':template_customizations},'spec');baseline={'snapshot':self._snapshot(),'spec_digest':digest(value),'accepted_executions':[],'cycle_digest':None,'template_manifest_digest':template_digest,'template_customizations':template_customizations};self.store.commit('baseline_established','release-owner','assessor','baseline',baseline,'baseline');write(self.store.state/'policy.json',{'format':'CLSES-policy/v1','default':'deny','agent_only_changes':True,'trace_required':True,'exact_change_set_authorization':True,'spec_acceptance_required':True,'artifact_acceptance_required':True,'deployment_authorization_required':True});return {'system_id':value['system_id'],'spec_record_digest':spec_id,'state':'initialized','mode':'strict','template_manifest_digest':template_digest,'template_customizations':template_customizations}
    def authorize(self,scope,kind,signer,subject,valid_until=END):
        role=kind+'_authorizer';self.store.require(signer,role)
        try:self.policy.authorization(scope,kind,subject,signer)
        except PermissionError:pass
        else:raise ValueError('an active authorization already exists for this exact authority domain')
        payload={'authorization_id':str(uuid.uuid4()),'scope':scope,'kind':kind,'subject':subject,'decision':'approved','issued_at':int(time.time()),'valid_until':valid_until};identifier=self.store.commit('authorization_approved',signer,role,'authorization',payload);write(self.store.state/'authorizations'/(identifier+'.json'),{'digest':identifier});return {'scope':scope,'authorization_digest':identifier}
    def mandate(self,run_id,objective,driver,allowed_paths,requirements,max_iterations=5,max_changes=12,max_bytes=50000,expires_at=END,signer='engineering-reviewer'):
        self.store.require(signer,'engineering_authorizer');workflow_path=self.store.state/'operator/workflow.json'
        if workflow_path.exists():
            baseline=read(workflow_path).get('intake',{}).get('baseline');excluded={'decision','authorization_digest','authorized_at','assumptions','resolved_facts'};basis={key:value for key,value in (baseline or {}).items() if key not in excluded};scope='baseline:'+digest(basis)
            if not baseline or baseline.get('decision')!='authorized' or baseline.get('authorization_digest')!=self.policy.authorization(scope,'product','system','owner')[0]:raise PermissionError('the exact product baseline requires explicit owner authorization before engineering')
        _,spec,spec_digest=self._spec();known={x['key'] for x in spec['requirements']+spec['outcomes']}
        if not objective or not allowed_paths or not requirements or not set(requirements)<=known:raise ValueError('mandate must have an objective, path boundaries, and active criteria')
        if min(max_iterations,max_changes,max_bytes)<=0:raise ValueError('mandate budgets must be positive')
        path=self.store.state/'mandates'/(run_id+'.json')
        if path.exists():raise ValueError('autonomy run id is immutable and already used')
        payload={'run_id':run_id,'objective':objective,'driver':driver,'allowed_paths':sorted(set(allowed_paths)),'requirement_keys':sorted(set(requirements)),'max_iterations':max_iterations,'max_changes':max_changes,'max_bytes':max_bytes,'expires_at':expires_at,'spec_digest':spec_digest,'subject':'agent','decision':'approved'};identifier=self.store.commit('autonomy_mandated',signer,'engineering_authorizer','autonomy_mandate',payload);write(path,{'digest':identifier});return {'run_id':run_id,'mandate_digest':identifier,'state':'authorized','authority_boundary':'engineering iteration only; no specification acceptance, artifact acceptance, or deployment authorization'}
    def _mandate(self,run_id):
        pointer=read(self.store.state/'mandates'/(run_id+'.json'));record=self.store.get(pointer['digest'],'autonomy_mandate','engineering_authorizer');payload=record['payload']
        if record['actor']!='engineering-reviewer' or payload['decision']!='approved' or payload['expires_at']<int(time.time()) or payload['spec_digest']!=self._spec()[2]:raise PermissionError('autonomy mandate is invalid, expired, or stale')
        return pointer['digest'],payload
    def propose_spec(self,change_id,spec,actor='agent'):
        self.policy.require_action('spec_propose',actor)
        if (self.store.state/'spec-proposals'/(change_id+'.json')).exists():raise ValueError('specification change id is immutable and already used')
        _,current,current_digest=self._spec();proposed=validate_spec(read(spec) if isinstance(spec,(str,Path)) else spec)
        if proposed['system_id']!=current['system_id']:raise ValueError('system identity is immutable')
        if digest(proposed)==current_digest:raise ValueError('specification is unchanged')
        payload={'change_id':change_id,'prior_spec_digest':current_digest,'spec':proposed,'spec_digest':digest(proposed)};identifier=self.store.commit('specification_proposed',actor,'agent','spec_proposal',payload);write(self.store.state/'spec-proposals'/(change_id+'.json'),{'digest':identifier});return {'change_id':change_id,'proposal_digest':identifier,'engineering_scope':'spec:'+change_id,'acceptance_scope':'spec-accept:'+digest(proposed)}
    def apply_spec(self,change_id,actor='release-owner'):
        self.policy.require_action('spec_apply',actor);_,_,current_digest=self._spec();pointer=read(self.store.state/'spec-proposals'/(change_id+'.json'));proposal=self.store.get(pointer['digest'],'spec_proposal','agent')['payload']
        if proposal['prior_spec_digest']!=current_digest:raise PermissionError('stale specification proposal')
        eng=self.policy.authorization('spec:'+change_id,'engineering','agent','engineering-reviewer');accept=self.policy.authorization('spec-accept:'+proposal['spec_digest'],'release','operator','release-owner');payload={**proposal,'proposal_digest':pointer['digest'],'engineering_authorization':eng[0],'acceptance_authorization':accept[0]};identifier=self.store.commit('specification_applied',actor,'spec_acceptor','specification',payload,'spec');return {'spec_digest':proposal['spec_digest'],'spec_record_digest':identifier,'reassessment_required':True}
    def request(self,work_id,instruction,path,content,requirements,expected_sha256=None,actor='agent'):
        self.policy.require_action('work_request',actor)
        if (self.store.state/'work'/(work_id+'.json')).exists():raise ValueError('work id is immutable and already used')
        _,spec,spec_digest=self._spec();known={x['key'] for x in spec['requirements']+spec['outcomes']}
        if not requirements or not set(requirements)<=known:raise ValueError('work must trace only to active criteria')
        if path.startswith('/') or '..' in Path(path).parts or Path(path).parts[0] not in ('src','tests'):raise ValueError('path outside allowed roots')
        if Path(path).parts[0]=='src' and path not in spec['components']:raise ValueError('source path is not a declared design component')
        payload={'work_id':work_id,'instruction':instruction,'path':path,'content':content,'expected_sha256':expected_sha256,'requirement_keys':sorted(set(requirements)),'spec_digest':spec_digest,'state':'proposed'};identifier=self.store.commit('work_proposed',actor,'agent','work_request',payload);write(self.store.state/'work'/(work_id+'.json'),{'request_digest':identifier,'state':'proposed'});return {'work_id':work_id,'request_digest':identifier,'authorization_scope':'work:'+work_id}
    def execute(self,work_id,actor='agent',mandate_id=None):
        self.policy.require_action('work_execute',actor);pointer=read(self.store.state/'work'/(work_id+'.json'))
        if pointer['state']!='proposed':raise PermissionError('work is not executable')
        request=self.store.get(pointer['request_digest'],'work_request','agent')['payload'];authorization_digest=None
        if mandate_id:
            authorization_digest,mandate=self._mandate(mandate_id)
            if not any(fnmatch.fnmatch(request['path'],pattern) for pattern in mandate['allowed_paths']) or not set(request['requirement_keys'])<=set(mandate['requirement_keys']):raise PermissionError('work exceeds autonomy mandate')
        else:authorization_digest=self.policy.authorization('work:'+work_id,'engineering',actor,'engineering-reviewer')[0]
        _,_,current_spec=self._spec()
        if request['spec_digest']!=current_spec:raise PermissionError('work request traces to stale specification')
        target=(self.root/request['path']).resolve()
        if self.root not in target.parents or target.is_symlink():raise PermissionError('unsafe target')
        before=digest(target.read_bytes()) if target.exists() else None
        if request['expected_sha256']!=before and (request['expected_sha256'] is not None or before is not None):raise PermissionError('reviewed prior digest mismatch')
        target.parent.mkdir(parents=True,exist_ok=True);tmp=target.with_suffix(target.suffix+'.agent-tmp');tmp.write_text(request['content']);tmp.replace(target);after=digest(target.read_bytes());payload={'work_id':work_id,'request_digest':pointer['request_digest'],'path':request['path'],'before_sha256':before,'after_sha256':after,'requirement_keys':request['requirement_keys'],'spec_digest':current_spec,'authorization_digest':authorization_digest,'mandate_id':mandate_id};identifier=self.store.commit('work_executed',actor,'agent','execution',payload);write(self.store.state/'work'/(work_id+'.json'),{'request_digest':pointer['request_digest'],'state':'executed','execution_digest':identifier});return {'work_id':work_id,'execution_digest':identifier,'after_sha256':after}
    def trial(self,run_id,iteration,actor='agent'):
        self.store.require(actor,'builder');self._mandate(run_id);snapshot=self._snapshot();started=int(time.time());cp=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=self.root,capture_output=True,text=True,timeout=120);payload={'run_id':run_id,'iteration':iteration,'source_digest':digest(snapshot),'started_at':started,'finished_at':int(time.time()),'exit_code':cp.returncode,'stdout_sha256':digest(cp.stdout.encode()),'stderr_sha256':digest(cp.stderr.encode()),'transcript':(cp.stdout+'\n'+cp.stderr)[-12000:]};identifier=self.store.commit('autonomous_trial_completed',actor,'builder','trial_evidence',payload);return {**payload,'trial_evidence_digest':identifier,'passed':cp.returncode==0}
    def _executions(self):
        values=[]
        for path in (self.store.state/'work').glob('*.json'):
            pointer=read(path)
            if pointer.get('state')=='executed':
                payload=self.store.get(pointer['execution_digest'],'execution','agent')['payload'];values.append({**payload,'execution_digest':pointer['execution_digest']})
        return values
    def plan(self):
        _,_,spec_digest=self._spec();baseline_id,baseline_record=self.store.deref('baseline','baseline','assessor');before={x['path']:x for x in baseline_record['payload']['snapshot']};after={x['path']:x for x in self._snapshot()};changes=[]
        for path in sorted(set(before)|set(after)):
            if before.get(path)==after.get(path):continue
            changes.append({'path':path,'before_sha256':before.get(path,{}).get('sha256'),'after_sha256':after.get(path,{}).get('sha256')})
        self.policy.changed_paths_allowed(changes,self._executions(),spec_digest);core={'baseline_digest':baseline_id,'spec_digest':spec_digest,'changes':changes};change_set_digest=digest(core);identifier=self.store.commit('change_set_planned','release-owner','assessor','change_set',{**core,'change_set_digest':change_set_digest},'change-set');return {'change_set_digest':change_set_digest,'change_set_record_digest':identifier,'changes':changes,'build_scope':'build:'+change_set_digest}
    def build(self,actor='agent'):
        self.policy.require_action('build',actor);plan=self.plan();auth=self.policy.authorization(plan['build_scope'],'engineering',actor,'engineering-reviewer');snapshot=self._snapshot();started=int(time.time());cp=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=self.root,capture_output=True,text=True,timeout=120);finished=int(time.time());evidence={'source_digest':digest(snapshot),'inputs':snapshot,'command':['python','-m','unittest','discover','-s','tests','-v'],'started_at':started,'finished_at':finished,'exit_code':cp.returncode,'stdout_sha256':digest(cp.stdout.encode()),'stderr_sha256':digest(cp.stderr.encode()),'transcript':(cp.stdout+'\n'+cp.stderr)[-12000:]};evidence_id=self.store.commit('tests_executed',actor,'builder','test_evidence',evidence)
        if cp.returncode:raise RuntimeError('tests failed; release stopped')
        source_entries=self._source_snapshot();_,spec,_=self._spec()
        if {'src/'+entry['path'] for entry in source_entries}!=set(spec['components']):raise ValueError('built source inventory must exactly equal declared design components')
        artifact_digest=digest(source_entries);dest=self.store.state/'artifacts'/artifact_digest;dest.mkdir(parents=True,exist_ok=True)
        for entry in source_entries:
            target=dest/entry['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(self.root/'src'/entry['path'],target)
        if self._source_snapshot(dest)!=source_entries:raise ValueError('built artifact differs from source inputs')
        payload={'change_set_digest':plan['change_set_digest'],'change_set_record_digest':plan['change_set_record_digest'],'source_digest':digest(snapshot),'artifact_digest':artifact_digest,'artifact_entries':source_entries,'test_evidence_digest':evidence_id,'authorization_digest':auth[0],'built_at':finished};build_id=self.store.commit('build_completed',actor,'builder','build',payload,'build');pending={'build_digest':build_id,'change_set_digest':plan['change_set_digest'],'artifact_digest':artifact_digest,'acceptance_scope':'accept:'+artifact_digest,'release_scope':'deploy:'+artifact_digest};write(self.store.state/'pending.json',pending);return pending
    def complete(self,actor='operator'):
        self.policy.require_action('release',actor);pending=read(self.store.state/'pending.json');build_record=self.store.get(pending['build_digest'],'build','builder');build=build_record['payload'];prior_baseline=self.store.deref('baseline','baseline','assessor')[1]['payload'];prior_template=prior_baseline.get('template_manifest_digest');prior_customizations=prior_baseline.get('template_customizations');plan=self.plan()
        if plan['change_set_digest']!=pending['change_set_digest']:raise PermissionError('change set changed after build')
        acceptance=self.policy.authorization(pending['acceptance_scope'],'release',actor,'release-owner');release_auth=self.policy.authorization(pending['release_scope'],'release',actor,'release-owner');source=self.store.state/'artifacts'/pending['artifact_digest']
        if self._source_snapshot(source)!=build['artifact_entries'] or digest(build['artifact_entries'])!=pending['artifact_digest']:raise ValueError('artifact integrity failure')
        deployed=self.store.state/'deployment';deployed.mkdir(parents=True,exist_ok=True)
        for entry in build['artifact_entries']:
            target=deployed/entry['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/entry['path'],target)
        if self._source_snapshot(deployed)!=build['artifact_entries']:raise ValueError('deployment integrity failure')
        deployed_at=int(time.time());deployment={'artifact_digest':pending['artifact_digest'],'build_digest':pending['build_digest'],'acceptance_authorization':acceptance[0],'release_authorization':release_auth[0],'environment':'local_simulation','path':str(deployed.relative_to(self.root)),'deployed_at':deployed_at};deployment_id=self.store.commit('artifact_deployed',actor,'deployer','deployment',deployment,'deployment');cp=subprocess.run([sys.executable,str(deployed/'service.py'),'--self-test'],capture_output=True,text=True,timeout=30);observation={'deployment_digest':deployment_id,'artifact_digest':pending['artifact_digest'],'observed_at':int(time.time()),'exit_code':cp.returncode,'healthy':cp.returncode==0,'output_sha256':digest(cp.stdout.encode())};observation_id=self.store.commit('operation_observed','monitor','observer','observation',observation,'observation')
        if not observation['healthy']:raise RuntimeError('operational observation failed')
        manifest=self._manifest(plan,build,release_auth[1],deployed_at,observation,observation_id);intrinsic=assess(manifest)
        if intrinsic['errors']:raise RuntimeError('normative graph rejected: '+'; '.join(intrinsic['errors']))
        write(self.store.state/'manifest.json',manifest);manifest_digest=digest(manifest);cycle={'cycle_id':str(uuid.uuid4()),'spec_digest':self._spec()[2],'change_set_digest':plan['change_set_digest'],'build_digest':pending['build_digest'],'artifact_digest':pending['artifact_digest'],'deployment_digest':deployment_id,'observation_digest':observation_id,'manifest_digest':manifest_digest,'intrinsic':'conformant','relational':'locally_demonstrated_not_production_adequacy'};cycle_id=self.store.commit('cycle_closed','release-owner','assessor','cycle',cycle,'cycle');baseline={'snapshot':self._snapshot(),'spec_digest':cycle['spec_digest'],'accepted_executions':[x['execution_digest'] for x in plan['changes']],'cycle_digest':cycle_id,'template_manifest_digest':prior_template,'template_customizations':prior_customizations};self.store.commit('baseline_accepted','release-owner','assessor','baseline',baseline,'baseline');return self.verify()
    def _manifest(self,plan,build,release_auth_record,deployed_at,observation,observation_id):
        _,spec,spec_digest=self._spec();system=spec['system_id'];now=max(int(time.time()),observation['observed_at']);build_scope='build:'+plan['change_set_digest'];release_scope='deploy:'+build['artifact_digest'];build_auth=self.policy.authorization(build_scope,'engineering','agent','engineering-reviewer')[1];release_payload=release_auth_record['payload'];items=[artifact(system,'purpose','A1',{'purpose':spec['purpose'],'beneficiaries':spec['beneficiaries'],'outcomes':[{k:x[k] for k in ('key','variable','op','threshold','unit')} for x in spec['outcomes']],'horizon':{'start':build['built_at']-1,'end':END},'authority_source':'signed-spec:'+spec_digest,'context':json.dumps(spec['operating_conditions'],sort_keys=True)}),artifact(system,'requirements','A2',{'purpose_ref':ref('purpose'),'requirements':[{k:x[k] for k in ('key','variable','op','threshold','unit')} for x in spec['requirements']],'constraints':spec['constraints'],'source_refs':['signed-spec:'+spec_digest]},['purpose']),artifact(system,'design','A3',{'requirements_refs':[ref('requirements')],'components':spec['components'],'interfaces':spec['interfaces'],'design_decisions':spec['design_decisions']},['requirements']),artifact(system,'engineering-grant','A8',{'decision_kind':'engineering_authorization','actor':build_auth['actor'],'authorized_actor':'agent','scope':build_scope,'decision':'approved','decided_at':build_auth['payload']['issued_at'],'basis_refs':[],'target_ref':None,'authority_source':'signed-record:'+build['authorization_digest'],'valid_until':build_auth['payload']['valid_until']}),artifact(system,'build-work','A4',{'design_ref':ref('design'),'work_id':build_scope,'instruction':'Build and test the exact governed change set','work_state':'authorized','state_changed_at':build['built_at'],'assigned_actor':'agent','authorization_ref':ref('engineering-grant'),'execution_evidence_refs':[]},['design','engineering-grant']),artifact(system,'production-grant','A8',{'decision_kind':'production_authorization','actor':release_auth_record['actor'],'authorized_actor':None,'scope':release_scope,'decision':'approved','decided_at':release_payload['issued_at'],'basis_refs':[],'target_ref':None,'authority_source':'signed-record:'+build['artifact_digest'],'valid_until':release_payload['valid_until']}),artifact(system,'implementation','A5',{'design_ref':ref('design'),'source_revision':'sha256:'+build['source_digest'],'build_digest':'sha256:'+build['artifact_digest'],'configuration_digest':'sha256:'+spec_digest,'deployment':{'environment':'local_simulation','release_id':release_scope,'deployed_at':deployed_at,'production_authorization_ref':ref('production-grant')}},['design','build-work','production-grant'])]
        test=self.store.get(build['test_evidence_digest'],'test_evidence','builder')['payload']
        supported={('build','test_pass_rate','test_pass_rate'),('observe','health_rate','health_rate')}
        if any((item['source'],item['key'],item['measurement_key']) not in supported for item in spec['requirements']+spec['outcomes']):raise RuntimeError('criterion-specific adapter required; use the production evidence profile')
        for criterion in spec['requirements']+spec['outcomes']:
            key=criterion['key'];method='method-'+key;obs='observation-'+key;decl='requirements' if criterion in spec['requirements'] else 'purpose';source=criterion['source'];value=1.0 if (test['exit_code']==0 if source=='build' else observation['healthy']) else 0.0;source_digest=build['test_evidence_digest'] if source=='build' else observation_id;items.append(artifact(system,method,'A6',{'criterion_ref':ref(decl),'criterion_key':key,'bindings':{'variable':criterion['variable'],'measurement_key':criterion['measurement_key'],'measurement_unit':criterion['unit']},'minimum_sources':1,'max_age':86400,'min_coverage':1.0},[decl]));items.append(artifact(system,obs,'A7',{'target_ref':ref('implementation'),'method_ref':ref(method),'measurements':{criterion['measurement_key']:value},'measurement_units':{criterion['measurement_key']:criterion['unit']},'observed_at':test['finished_at'] if source=='build' else observation['observed_at'],'source_ids':['record-'+source_digest[:16]],'source_provenance':['record-'+source_digest[:16],source_digest],'coverage':1.0,'kind':'test' if source=='build' else 'runtime'},['implementation',method]))
        return {'spec_version':'0.3.1','system_id':system,'assessed_at':now,'artifacts':items}
    def verify(self):
        ledger_ok,count=self.store.verify_ledger();_,spec,spec_digest=self._spec();_,baseline=self.store.deref('baseline','baseline','assessor');checks={'ledger_valid':ledger_ok,'specification_valid':digest(spec)==spec_digest,'accepted_snapshot_current':baseline['payload']['snapshot']==self._snapshot(),'baseline_spec_current':baseline['payload']['spec_digest']==spec_digest,'cycle_present':baseline['payload']['cycle_digest'] is not None};intrinsic='not_assessed';relational='not_assessed'
        if checks['cycle_present']:
            cycle=self.store.get(baseline['payload']['cycle_digest'],'cycle','assessor')['payload'];manifest=read(self.store.state/'manifest.json');result=assess(manifest);deployment=self.store.get(cycle['deployment_digest'],'deployment','deployer')['payload'];build=self.store.get(cycle['build_digest'],'build','builder')['payload'];checks['manifest_binding']=cycle['manifest_digest']==digest(manifest);checks['artifact_level']=result['artifact_level']=='pass';checks['system_level']=result['system_level']=='pass';checks['artifact_binding']=cycle.get('artifact_digest')==build.get('artifact_digest')==deployment.get('artifact_digest') and digest(build.get('artifact_entries',[]))==cycle.get('artifact_digest');checks['deployment_current']=self._source_snapshot(self.store.state/'deployment')==build.get('artifact_entries');intrinsic='conformant' if checks['artifact_level'] and checks['system_level'] else 'nonconformant';relational=cycle['relational'] if all(checks.values()) else 'not_adequate'
        template_digest=baseline['payload'].get('template_manifest_digest')
        if template_digest:
            from .template_edition import verify_scaffold
            template_result=verify_scaffold(self.root,self.root/'.clses-template/template-manifest.json',strict=False)
            checks['template_integrity']=template_result['valid'] and template_result['manifest_digest']==template_digest
            custom=baseline['payload'].get('template_customizations',{});codeowners=self.root/'.github/CODEOWNERS';checks['template_customization_integrity']=bool(custom.get('github_owner')) and custom.get('codeowners_sha256')==digest(codeowners.read_bytes())
        return {'valid':all(checks.values()),'checks':checks,'ledger_records':count,'intrinsic':intrinsic,'relational':relational,'mode':'canonical_strict_mvas_v1','claim_boundary':'signed local identities, CPython tests, local simulated deployment, self-test observation, one controlled cycle'}
