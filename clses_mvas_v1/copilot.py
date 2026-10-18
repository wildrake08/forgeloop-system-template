"""Lifecycle-aware conversational facilitation with non-conversational authority gates."""
from __future__ import annotations
import json,os,secrets,subprocess,tempfile,time,uuid
from pathlib import Path
from .autonomy import AutonomousLoop
from .engine import Engine
from .store import digest,read,write

HUMAN_PRINCIPALS={'owner','engineering-reviewer','release-owner','operator'}
FACILITATOR_SCHEMA={'type':'object','additionalProperties':False,'properties':{'response':{'type':'string'},'suggested_action':{'type':['object','null']}},'required':['response','suggested_action']}

class LifecycleCopilot:
    """A facilitation layer. Messages never count as authority; explicit decisions can."""
    def __init__(self,root):
        self.root=Path(root).resolve();self.engine=Engine(root);self.store=self.engine.store;self.base=self.store.state/'copilot'
        if not (self.store.state/'trust.json').exists():raise FileNotFoundError('CLSES workspace is not initialized')

    def open_session(self,principal,credential,ttl=3600):
        if principal not in HUMAN_PRINCIPALS:raise PermissionError('copilot sessions require a human principal')
        trust=read(self.store.state/'trust.json')['principals'];entry=trust.get(principal)
        if not entry or not entry['active']:raise PermissionError('unknown or inactive principal')
        try:credential_id=digest(bytes.fromhex(credential.strip()))[:24]
        except (ValueError,AttributeError) as exc:raise PermissionError('invalid principal credential') from exc
        if not secrets.compare_digest(credential_id,entry['key_id']):raise PermissionError('invalid principal credential')
        ttl=int(ttl)
        if ttl<60 or ttl>86400:raise ValueError('session ttl must be between 60 and 86400 seconds')
        token=secrets.token_urlsafe(32);session_id=str(uuid.uuid4());now=int(time.time());role=entry['roles'][0];payload={'session_id':session_id,'principal':principal,'role':role,'opened_at':now,'expires_at':now+ttl,'token_sha256':digest(token.encode()),'authentication':'local-principal-key-possession','status':'active'};record=self.store.commit('copilot_session_opened',principal,role,'copilot_session',payload);write(self.base/'sessions'/(session_id+'.json'),{'record_digest':record,'token_sha256':payload['token_sha256'],'principal':principal,'role':role,'expires_at':payload['expires_at'],'status':'active'});return {'session_id':session_id,'token':token,'principal':principal,'expires_at':payload['expires_at'],'warning':'token is shown once; conversation is not authorization'}

    def _session(self,session_id,token):
        session=read(self.base/'sessions'/(session_id+'.json'))
        if session['status']!='active' or session['expires_at']<int(time.time()) or not secrets.compare_digest(session['token_sha256'],digest(token.encode())):raise PermissionError('invalid or expired copilot session')
        self.store.get(session['record_digest'],'copilot_session',session['role']);return session

    def _record_message(self,session,text,direction):
        actor=session['principal'] if direction=='human' else 'agent';role=session['role'] if direction=='human' else 'agent';payload={'session_id':session.get('session_id'),'direction':direction,'text':text,'authoritative':False,'recorded_at':int(time.time())};return self.store.commit('copilot_message_recorded',actor,role,'copilot_message',payload)

    def register_facilitator(self,session_id,token,name,kind='generic',argv=None):
        session=self._session(session_id,token)
        if session['principal']!='owner':raise PermissionError('owner session required to register a facilitator')
        path=self.base/'facilitators'/(name+'.json')
        if path.exists():raise ValueError('facilitator name is immutable and already registered')
        if kind=='codex':command=['codex','exec','--sandbox','read-only','--ephemeral','--skip-git-repo-check','--output-schema','{schema}','--output-last-message','{output}','{prompt}'];mode='file'
        elif kind=='generic':
            if not isinstance(argv,list) or not argv or not all(isinstance(item,str) and item for item in argv) or not any('{prompt}' in item for item in argv):raise ValueError('generic facilitator requires a nonempty argv array containing {prompt}')
            command=argv;mode='file' if any('{output}' in item for item in argv) else 'stdout'
        else:raise ValueError('unknown facilitator kind')
        payload={'name':name,'kind':kind,'argv':command,'output_mode':mode,'shell':False,'registered_at':int(time.time()),'authority':'advisory_only'};record=self.store.commit('copilot_facilitator_registered',session['principal'],'trust_admin','copilot_facilitator',payload);write(path,{'digest':record});return {'name':name,'kind':kind,'record_digest':record,'authority':'none'}

    def _facilitate(self,name,message,state):
        pointer=read(self.base/'facilitators'/(name+'.json'));profile=self.store.get(pointer['digest'],'copilot_facilitator','trust_admin')['payload'];context={'human_message':message,'lifecycle':state,'specification':self.engine._spec()[1],'rules':['conversation is never authority','do not claim an approval occurred','recommend only active, bounded next actions','state uncertainty and claim boundaries']}
        with tempfile.TemporaryDirectory(prefix='clses-copilot-view-') as folder:
            view=Path(folder);write(view/'context.json',context);write(view/'response.schema.json',FACILITATOR_SCHEMA);output=view/'response.json';prompt='Act as the CLSES lifecycle facilitator. Read context.json. Explain the current situation plainly and suggest at most one non-authoritative next action. Return only response.schema.json.';replacement={'{prompt}':prompt,'{schema}':str(view/'response.schema.json'),'{output}':str(output),'{context}':str(view/'context.json')};command=[]
            for item in profile['argv']:
                for old,new in replacement.items():item=item.replace(old,new)
                command.append(item)
            cp=subprocess.run(command,cwd=view,capture_output=True,text=True,timeout=300,env=os.environ.copy())
            if cp.returncode:raise RuntimeError('facilitator failed: '+cp.stderr[-2000:])
            value=json.loads(output.read_text() if profile['output_mode']=='file' else cp.stdout)
            if not isinstance(value,dict) or set(value)!=set(FACILITATOR_SCHEMA['required']) or not isinstance(value['response'],str) or (value['suggested_action'] is not None and not isinstance(value['suggested_action'],dict)):raise ValueError('facilitator response violates protocol')
            evidence={'facilitator_digest':pointer['digest'],'command_digest':digest(command),'response':value,'authoritative':False,'recorded_at':int(time.time())};record=self.store.commit('copilot_facilitator_completed','agent','agent','copilot_facilitator_result',evidence);return value,record

    def status(self):
        active=[]
        runs=self.store.state/'autonomy-runs'
        for path in sorted(runs.glob('*.json')) if runs.exists() else []:
            state=read(path);active.append({'run_id':state['run_id'],'phase':state['phase'],'iteration':state.get('iteration',0),'changes':state.get('changes',0),'build_scope':state.get('build_scope'),'pending':state.get('pending')})
        pending=read(self.store.state/'pending.json') if (self.store.state/'pending.json').exists() else None
        if active:
            phase=active[-1]['phase'];next_action={'engineering':'resume autonomous engineering','awaiting_build':'review and decide exact build authorization','awaiting_release':'review artifact acceptance and deployment decisions','blocked':'resolve the recorded blocker or create a new mandate','budget_exhausted':'review evidence and create a new bounded mandate if justified','complete':'verify closure and monitor declared operating conditions'}.get(phase,'inspect lifecycle state')
        else:phase='initialized';next_action='register an execution driver and prepare a bounded engineering mandate'
        return {'stage':phase,'next_action':next_action,'runs':active,'pending':pending,'authority_rule':'conversation never constitutes approval; only an exact authenticated decision challenge can authorize'}

    def say(self,session_id,token,message,facilitator=None):
        session=self._session(session_id,token);session={**session,'session_id':session_id};text=message.strip()
        if not text:raise ValueError('message must not be empty')
        human_record=self._record_message(session,text,'human');lower=text.lower();state=self.status()
        facilitator_record=None;suggested_action=None
        if facilitator:
            facilitated,facilitator_record=self._facilitate(facilitator,text,state);response=facilitated['response'];suggested_action=facilitated['suggested_action']
        elif any(word in lower for word in ('approve','authorize','accept','deploy','release')):
            response='I recorded that as conversation only, not authority. Ask me to prepare the relevant decision packet, then use its exact challenge through the decision operation.'
        elif 'status' in lower or 'where are we' in lower or 'next' in lower:
            response=f"The lifecycle is in {state['stage']}. The next governed action is to {state['next_action']}."
        elif 'why' in lower and ('approval' in lower or 'authority' in lower):
            response='CLSES separates proposal, execution, verification, and authority. I may explain and prepare a decision, but I cannot infer approval or sign as a human.'
        elif 'evidence' in lower:
            pending=state['pending'];response=('The current artifact is '+pending['artifact_digest']+' and its build record is '+pending['build_digest']+'. Prepare an exact acceptance or deployment packet to inspect the bound evidence.' if pending else 'No pending release artifact exists. Trial, build, deployment, and observation evidence becomes available as the lifecycle advances.')
        elif 'help' in lower:
            response='I can explain status and evidence, prepare a mandate proposal, prepare an exact authorization packet, resume an authorized run, and record explicit approve or reject decisions. Conversational approval is intentionally ineffective.'
        else:
            response='I recorded this as non-authoritative lifecycle input. No specification, mandate, authorization, source, artifact, or deployment state changed.'
        agent_session={'principal':'agent','role':'agent','session_id':session_id};agent_record=self._record_message(agent_session,response,'agent');return {'response':response,'suggested_action':suggested_action,'status':state,'records':{'human':human_record,'agent':agent_record,'facilitator':facilitator_record},'authoritative':False}

    def _expected_scopes(self):
        scopes={};awaiting_release=False
        runs=self.store.state/'autonomy-runs'
        for path in runs.glob('*.json') if runs.exists() else []:
            state=read(path)
            if state.get('phase')=='awaiting_build':scopes[state['build_scope']]={'kind':'engineering','subject':'agent','purpose':'release-grade build of exact change set'}
            if state.get('phase')=='awaiting_release':awaiting_release=True
        pending_path=self.store.state/'pending.json'
        if pending_path.exists() and awaiting_release:
            pending=read(pending_path);scopes[pending['acceptance_scope']]={'kind':'release','subject':'operator','purpose':'accept exact built artifact'};scopes[pending['release_scope']]={'kind':'release','subject':'operator','purpose':'deploy exact accepted artifact'}
        proposals=self.store.state/'spec-proposals'
        current_spec=self.engine._spec()[2]
        for path in proposals.glob('*.json') if proposals.exists() else []:
            record=self.store.get(read(path)['digest'],'spec_proposal','agent')['payload']
            if record['prior_spec_digest']==current_spec:scopes['spec:'+record['change_id']]={'kind':'engineering','subject':'agent','purpose':'approve specification proposal'};scopes['spec-accept:'+record['spec_digest']]={'kind':'release','subject':'operator','purpose':'accept exact proposed specification'}
        return scopes

    def _proposal(self,kind,payload,required_principal,summary):
        decision_id=str(uuid.uuid4());core={'decision_id':decision_id,'kind':kind,'payload':payload,'required_principal':required_principal,'summary':summary,'created_at':int(time.time()),'status':'proposed'};proposal_digest=digest(core);body={**core,'proposal_digest':proposal_digest,'challenge':'APPROVE '+decision_id+' '+proposal_digest,'reject_challenge':'REJECT '+decision_id};record=self.store.commit('copilot_decision_proposed','agent','agent','copilot_decision_proposal',body);write(self.base/'decisions'/(decision_id+'.json'),{'proposal_record':record,'status':'proposed'});return body

    def propose_authorization(self,session_id,token,scope,human_evidence=None):
        self._session(session_id,token);expected=self._expected_scopes()
        if scope not in expected:raise PermissionError('scope is not an active lifecycle authority request')
        if human_evidence is not None and not isinstance(human_evidence,dict):raise ValueError('human evidence must be an object')
        item=expected[scope];principal='engineering-reviewer' if item['kind']=='engineering' else 'release-owner';evidence={'scope':scope,'lifecycle':self.status(),'purpose':item['purpose'],'human_evidence':human_evidence or {}}
        pending=evidence['lifecycle']['pending']
        if pending and (scope==pending.get('acceptance_scope') or scope==pending.get('release_scope')):
            build=self.store.get(pending['build_digest'],'build','builder')['payload'];test=self.store.get(build['test_evidence_digest'],'test_evidence','builder')['payload'];evidence['artifact']={'artifact_digest':pending['artifact_digest'],'build_digest':pending['build_digest'],'test_exit_code':test['exit_code'],'test_transcript_sha256':digest(test['transcript'].encode())}
        return self._proposal('authorization',{'scope':scope,'kind':item['kind'],'subject':item['subject'],'evidence':evidence},principal,item['purpose'])

    def propose_specification(self,session_id,token,change_id,spec):
        self._session(session_id,token);result=self.engine.propose_spec(change_id,spec);record=self.store.commit('copilot_specification_facilitated','agent','agent','copilot_specification_result',{'change_id':change_id,'result':result,'recorded_at':int(time.time())});return {**result,'record_digest':record,'authority_required':True}

    def apply_specification(self,session_id,token,change_id):
        session=self._session(session_id,token)
        if session['principal']!='release-owner':raise PermissionError('release-owner session required to apply an accepted specification')
        result=self.engine.apply_spec(change_id,session['principal']);record=self.store.commit('copilot_specification_applied','agent','agent','copilot_specification_result',{'change_id':change_id,'result':result,'recorded_at':int(time.time())});return {**result,'record_digest':record}

    def propose_mandate(self,session_id,token,mandate):
        self._session(session_id,token);required={'run_id','objective','driver','allowed_paths','requirements','max_iterations','max_changes','max_bytes','expires_at'}
        if set(mandate)!=required:raise ValueError('mandate proposal fields must be exact')
        if not isinstance(mandate['allowed_paths'],list) or not isinstance(mandate['requirements'],list):raise ValueError('mandate boundaries must be lists')
        return self._proposal('mandate',mandate,'engineering-reviewer','authorize bounded autonomous engineering mandate')

    def decide(self,session_id,token,decision_id,outcome,confirmation):
        session=self._session(session_id,token);pointer_path=self.base/'decisions'/(decision_id+'.json');pointer=read(pointer_path)
        if pointer['status']!='proposed':raise ValueError('decision has already been resolved')
        proposal_record=self.store.get(pointer['proposal_record'],'copilot_decision_proposal','agent');proposal=proposal_record['payload']
        if session['principal']!=proposal['required_principal']:raise PermissionError('session principal lacks authority for this decision')
        if outcome not in ('approve','reject'):raise ValueError('outcome must be approve or reject')
        required=proposal['challenge'] if outcome=='approve' else proposal['reject_challenge']
        if confirmation!=required:raise PermissionError('exact decision challenge was not confirmed')
        decision_payload={'decision_id':decision_id,'proposal_digest':proposal['proposal_digest'],'outcome':outcome,'confirmation':confirmation,'decided_at':int(time.time())};decision_record=self.store.commit('copilot_decision_recorded',session['principal'],session['role'],'copilot_human_decision',decision_payload)
        write(pointer_path,{'proposal_record':pointer['proposal_record'],'status':'processing','decision_record':decision_record})
        effect=None
        try:
            if outcome=='approve':
                data=proposal['payload']
                if proposal['kind']=='authorization':effect=self.engine.authorize(data['scope'],data['kind'],session['principal'],data['subject'])
                elif proposal['kind']=='mandate':effect=self.engine.mandate(data['run_id'],data['objective'],data['driver'],data['allowed_paths'],data['requirements'],data['max_iterations'],data['max_changes'],data['max_bytes'],data['expires_at'],session['principal'])
                else:raise ValueError('unsupported decision kind')
            result={'decision_id':decision_id,'outcome':outcome,'decision_record':decision_record,'effect':effect};result_record=self.store.commit('copilot_decision_effect_recorded','agent','agent','copilot_decision_result',result);write(pointer_path,{'proposal_record':pointer['proposal_record'],'status':outcome,'decision_record':decision_record,'result_record':result_record});return result
        except Exception as exc:
            failure={'decision_id':decision_id,'outcome':outcome,'decision_record':decision_record,'effect':None,'error':str(exc)};result_record=self.store.commit('copilot_decision_effect_failed','agent','agent','copilot_decision_result',failure);write(pointer_path,{'proposal_record':pointer['proposal_record'],'status':'effect_failed','decision_record':decision_record,'result_record':result_record});raise RuntimeError('authorized decision effect failed: '+str(exc)) from exc

    def resume(self,session_id,token,run_id):
        self._session(session_id,token);result=AutonomousLoop(self.root).run(run_id);record=self.store.commit('copilot_run_resumed','agent','agent','copilot_run_result',{'run_id':run_id,'result':result,'recorded_at':int(time.time())});return {'result':result,'record_digest':record}
