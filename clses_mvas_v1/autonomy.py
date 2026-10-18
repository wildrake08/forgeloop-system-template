"""Bounded autonomous engineering driven by an external command-line agent."""
from __future__ import annotations
import json,os,shutil,subprocess,tempfile,time
from pathlib import Path
from .engine import Engine
from .store import digest,read,write

OUTPUT_SCHEMA={'type':'object','additionalProperties':False,'properties':{'status':{'enum':['propose_changes','done','blocked']},'summary':{'type':'string'},'changes':{'type':'array','items':{'type':'object','additionalProperties':False,'properties':{'path':{'type':'string'},'instruction':{'type':'string'},'content':{'type':'string'},'requirement_keys':{'type':'array','items':{'type':'string'},'minItems':1}},'required':['path','instruction','content','requirement_keys']}}},'required':['status','summary','changes']}

class AutonomousLoop:
    def __init__(self,root):self.root=Path(root).resolve();self.engine=Engine(root);self.store=self.engine.store
    def register_driver(self,name,kind='generic',argv=None,signer='owner'):
        self.store.require(signer,'trust_admin');path=self.store.state/'drivers'/(name+'.json')
        if path.exists():raise ValueError('driver name is immutable and already registered')
        if kind=='codex':
            command=['codex','exec','--sandbox','read-only','--ephemeral','--skip-git-repo-check','--output-schema','{schema}','--output-last-message','{output}','{prompt}'];output_mode='file'
        elif kind=='generic':
            if not isinstance(argv,list) or not argv or not all(isinstance(x,str) and x for x in argv):raise ValueError('generic driver requires nonempty argv JSON array')
            command=argv;output_mode='file' if any('{output}' in x for x in command) else 'stdout'
        else:raise ValueError('unknown driver kind')
        if not any('{prompt}' in x for x in command):raise ValueError('driver command must contain {prompt}')
        payload={'name':name,'kind':kind,'argv':command,'output_mode':output_mode,'shell':False,'registered_at':int(time.time())};identifier=self.store.commit('driver_registered',signer,'trust_admin','driver_profile',payload);write(path,{'digest':identifier});return {'name':name,'driver_digest':identifier,'kind':kind,'output_mode':output_mode}
    def _driver(self,name):
        pointer=read(self.store.state/'drivers'/(name+'.json'));return pointer['digest'],self.store.get(pointer['digest'],'driver_profile','trust_admin')['payload']
    def _invoke(self,run_id,iteration,mandate,last_trial):
        driver_id,driver=self._driver(mandate['driver']);context={'run_id':run_id,'iteration':iteration,'objective':mandate['objective'],'allowed_paths':mandate['allowed_paths'],'requirement_keys':mandate['requirement_keys'],'budgets':{k:mandate[k] for k in ('max_iterations','max_changes','max_bytes')},'spec':self.engine._spec()[1],'current_snapshot':self.engine._snapshot(),'previous_trial':last_trial,'review_feedback':(last_trial or {}).get('review_feedback')}
        with tempfile.TemporaryDirectory(prefix='clses-agent-view-') as folder:
            view=Path(folder);shutil.copytree(self.root/'src',view/'src');shutil.copytree(self.root/'tests',view/'tests');write(view/'context.json',context);write(view/'response.schema.json',OUTPUT_SCHEMA);output=view/'response.json';prompt=('Act as the autonomous engineering executor for the objective in context.json. Inspect the read-only source and tests, previous trial evidence, and review feedback. Return only a response matching response.schema.json. Propose the smallest bounded changes needed. Never echo or persist raw secrets, credentials, payment-card numbers, or other sensitive input; use categorical redacted errors. Do not authorize, accept, release, deploy, or alter the specification.')
            replacements={'{prompt}':prompt,'{schema}':str(view/'response.schema.json'),'{output}':str(output),'{context}':str(view/'context.json')};command=[]
            for token in driver['argv']:
                for old,new in replacements.items():token=token.replace(old,new)
                command.append(token)
            started=int(time.time())
            try:cp=subprocess.run(command,cwd=view,capture_output=True,text=True,timeout=600,env=os.environ.copy())
            except FileNotFoundError as exc:raise RuntimeError('external agent executable was not found: '+command[0]+'. Install it or register a valid absolute executable path.') from exc
            except subprocess.TimeoutExpired as exc:raise RuntimeError('external agent timed out after 600 seconds; inspect its authentication, connectivity, and prompt configuration') from exc
            finished=int(time.time())
            detail=(cp.stderr or cp.stdout).strip()[-2000:]
            if cp.returncode:raise RuntimeError('external agent exited with code '+str(cp.returncode)+(': '+detail if detail else ' and produced no diagnostic output'))
            if driver['output_mode']=='file' and not output.exists():raise RuntimeError('external agent produced no response file; verify its output option and authentication')
            raw=output.read_text() if driver['output_mode']=='file' else cp.stdout
            if not raw.strip():raise RuntimeError('external agent produced an empty response; verify that the CLI is authenticated and prints JSON in non-interactive mode')
            try:response=json.loads(raw)
            except json.JSONDecodeError as exc:raise RuntimeError('external agent returned non-JSON output: '+raw.strip()[-1000:]) from exc
            self._validate_response(response);payload={'run_id':run_id,'iteration':iteration,'driver_digest':driver_id,'command_digest':digest(command),'started_at':started,'finished_at':finished,'exit_code':cp.returncode,'stdout_sha256':digest(cp.stdout.encode()),'stderr_sha256':digest(cp.stderr.encode()),'response':response};record_id=self.store.commit('external_agent_completed','agent','agent','external_agent_result',payload);return response,record_id,context['current_snapshot']
    def _validate_response(self,value):
        if not isinstance(value,dict) or set(value)!=set(OUTPUT_SCHEMA['required']) or value['status'] not in ('propose_changes','done','blocked') or not isinstance(value['summary'],str) or not isinstance(value['changes'],list):raise ValueError('external agent response violates protocol')
        if value['status']!='propose_changes' and value['changes']:raise ValueError('non-proposal response cannot contain changes')
        for change in value['changes']:
            if not isinstance(change,dict) or set(change)!=set(OUTPUT_SCHEMA['properties']['changes']['items']['required']) or not isinstance(change['requirement_keys'],list) or not change['requirement_keys'] or not all(isinstance(change[x],str) for x in ('path','instruction','content')):raise ValueError('external agent change violates protocol')
    def _state_path(self,run_id):return self.store.state/'autonomy-runs'/(run_id+'.json')
    def run(self,run_id):
        mandate_id,mandate=self.engine._mandate(run_id);state_path=self._state_path(run_id);state=read(state_path) if state_path.exists() else {'run_id':run_id,'mandate_digest':mandate_id,'phase':'engineering','iteration':0,'changes':0,'bytes':0,'last_trial':None,'agent_records':[]}
        if state['mandate_digest']!=mandate_id:raise ValueError('autonomy state mandate mismatch')
        if state['phase']=='complete':return state['result']
        if state['phase']=='revoked':raise PermissionError('autonomy run mandate is revoked')
        if state['phase']=='changes_requested':
            state['last_trial']={**(state.get('last_trial') or {}),'review_feedback':state.get('rejection')};state['phase']='engineering'
        if state['phase']=='awaiting_release':
            pending=read(self.store.state/'pending.json');missing=[]
            for scope in (pending['acceptance_scope'],pending['release_scope']):
                try:self.engine.policy.authorization(scope,'release','operator','release-owner')
                except PermissionError:missing.append(scope)
            if missing:return {'state':'awaiting_non_autonomous_authority','required_scopes':missing,'run_id':run_id,'phase':'acceptance_and_release'}
            result=self.engine.complete();state.update({'phase':'complete','result':result});write(state_path,state);return result
        if state['phase']=='awaiting_build':
            try:self.engine.policy.authorization(state['build_scope'],'engineering','agent','engineering-reviewer')
            except PermissionError:return {'state':'awaiting_non_autonomous_authority','required_scopes':[state['build_scope']],'run_id':run_id,'phase':'build'}
            try:
                pending=self.engine.build();state.update({'phase':'awaiting_release','pending':pending});write(state_path,state);return {'state':'awaiting_non_autonomous_authority','required_scopes':[pending['acceptance_scope'],pending['release_scope']],'run_id':run_id,'phase':'acceptance_and_release'}
            except RuntimeError:
                state['phase']='engineering';state['last_trial']=self.engine.trial(run_id,state['iteration']+1);write(state_path,state)
        while state['iteration']<mandate['max_iterations']:
            iteration=state['iteration']+1;response,agent_record,snapshot=self._invoke(run_id,iteration,mandate,state['last_trial']);state['agent_records'].append(agent_record);state['iteration']=iteration
            if response['status']=='blocked':state['phase']='blocked';state['reason']=response['summary'];write(state_path,state);return {'state':'blocked','reason':response['summary'],'run_id':run_id}
            if response['status']=='propose_changes':
                proposed_bytes=sum(len(x['content'].encode()) for x in response['changes'])
                if state['changes']+len(response['changes'])>mandate['max_changes'] or state['bytes']+proposed_bytes>mandate['max_bytes']:raise PermissionError('external agent proposal exceeds mandate budget')
                before={x['path']:x['sha256'] for x in snapshot}
                for position,change in enumerate(response['changes'],1):
                    work_id=f'{run_id}-{iteration}-{position}';self.engine.request(work_id,change['instruction'],change['path'],change['content'],change['requirement_keys'],before.get(change['path']));self.engine.execute(work_id,mandate_id=run_id)
                state['changes']+=len(response['changes']);state['bytes']+=proposed_bytes
            trial=self.engine.trial(run_id,iteration);state['last_trial']=trial;write(state_path,state)
            if trial['passed']:
                plan=self.engine.plan();scope=plan['build_scope']
                try:rejection=self.engine.policy.rejection(scope,'engineering','agent','engineering-reviewer')
                except PermissionError:rejection=None
                if rejection:
                    reason=rejection[1]['payload']['reason'];state['last_trial']={**trial,'review_feedback':{'scope':scope,'reason':reason,'rejection_digest':rejection[0]}};state['phase']='engineering';write(state_path,state);continue
                state.update({'phase':'awaiting_build','build_scope':scope,'change_set_digest':plan['change_set_digest']});write(state_path,state);return {'state':'awaiting_non_autonomous_authority','required_scopes':[scope],'run_id':run_id,'phase':'build','iterations':state['iteration'],'changes':state['changes']}
        state['phase']='budget_exhausted';write(state_path,state);return {'state':'budget_exhausted','run_id':run_id,'iterations':state['iteration'],'changes':state['changes'],'last_trial':state['last_trial']}
