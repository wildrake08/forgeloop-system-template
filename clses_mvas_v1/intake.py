"""Minimum-question intake for a viable governed software-system baseline."""
from __future__ import annotations
import argparse,json,re,time,uuid
from pathlib import Path
from jsonschema import Draft202012Validator
from .assurance import load_profile
from .store import digest,write

FORMAT='CLSES-minimal-intake/v1'
GROUPS={
 'need':('system_name','problem','beneficiaries'),
 'outcome':('outcome_statement','outcome_metric','outcome_unit','outcome_operator','outcome_target','outcome_baseline'),
 'risk':('data_classes','compliance_obligations'),
 'conditions':('operating_conditions',),
 'authority':('authorities',),
}
PROMPTS={
 'need':'What system are you considering, what problem must it solve, and who is affected?',
 'outcome':'What measurable result would make it worthwhile, including metric, unit, target, comparison direction, and current baseline?',
 'risk':'What personal, payment, confidential, safety-relevant, or regulated data and obligations are involved?',
 'conditions':'Where and under what operating conditions must it work?',
 'authority':'Who may approve product intent, engineering, security, release, operations, outcomes, and governance decisions?',
}
CORE_REQUIRED={'system_name'}
CONTROL_FACTS={
 'purpose-approved':{'problem','beneficiaries'},
 'outcomes-measurable':set(GROUPS['outcome']),
 'security-privacy-acceptable':set(GROUPS['risk']),
 'operations-effective':set(GROUPS['conditions']),
 'authority-separated':set(GROUPS['authority']),
}
FACT_POLICY={fact_id:{'material':True,'reversible':False,'deferrable':False,'derivable':False} for values in GROUPS.values() for fact_id in values}
AUTHORITY_ROLES={'product_authority','engineering_authority','security_authority','release_authority','operations_authority','outcome_authority','governance_authority'}
SAFE_DEFAULTS={
 'minimum_sustained_periods':(2,'base profile requires multiple distinct periods',0.99,31536000),
 'continuation_review_days':(30,'bounded initial review interval',0.8,2592000),
 'architecture_status':('to_be_proposed','architecture is reversible before approval',1.0,604800),
 'implementation_language':('defer_until_architecture','technology choice is not required for viable intake',1.0,604800),
}

def _present(value):return value is not None and value!='' and value!=[] and value!={}
def _schema_validate(name,value):
    schema=json.loads((Path(__file__).resolve().parent/'schemas'/name).read_text());errors=list(Draft202012Validator(schema).iter_errors(value))
    if errors:raise ValueError('normative '+name+' failure: '+errors[0].message)
def _slug(value):
    text=re.sub(r'[^a-z0-9]+','-',str(value).lower()).strip('-');return text or 'new-system'
def _fact(value,source,now,confidence=1.0):return {'value':value,'source':source,'confidence':confidence,'recorded_at':now,'status':'current'}
def _validate(fact_id,value):
    if not _present(value):raise ValueError('empty answer for '+fact_id)
    if fact_id=='beneficiaries' and (not isinstance(value,list) or not all(isinstance(x,str) and x for x in value)):raise ValueError('beneficiaries must be a non-empty string list')
    if fact_id in ('data_classes','compliance_obligations') and not isinstance(value,list):raise ValueError(fact_id+' must be a list; use an empty explicit category such as ["none identified"]')
    if fact_id=='operating_conditions' and not isinstance(value,dict):raise ValueError('operating_conditions must be an object')
    if fact_id=='authorities' and (not isinstance(value,dict) or not AUTHORITY_ROLES<=set(value) or not all(isinstance(value[x],str) and value[x] for x in AUTHORITY_ROLES)):raise ValueError('all consequential authority roles require named principals')
    if fact_id in ('outcome_target','outcome_baseline') and (not isinstance(value,(int,float)) or isinstance(value,bool)):raise ValueError(fact_id+' must be numeric')
    if fact_id=='outcome_operator' and value not in ('>=','>','<=','<','=='):raise ValueError('unsupported outcome operator')
    return value

def _derive(state,now):
    facts=state['facts'];profile=load_profile(state['profile']['profile_id'],state['profile_dir'])
    for fact_id,assumption in state['assumptions'].items():
        if assumption['status']=='active' and assumption['expires_at']<now and fact_id in SAFE_DEFAULTS:
            value,basis,confidence,ttl=SAFE_DEFAULTS[fact_id];assumption.update({'basis':basis,'confidence':confidence,'expires_at':now+ttl,'last_reviewed_at':now,'renewal_count':assumption.get('renewal_count',0)+1})
    if 'system_class' not in facts:
        classes=[x for x in profile['system_classes'] if x!='general']
        if len(classes)==1:facts['system_class']=_fact(classes[0],'profile_derivation',now)
    if 'system_name' in facts and 'system_id' not in facts:facts['system_id']=_fact(_slug(facts['system_name']['value']),'deterministic_derivation',now)
    if 'problem' in facts and 'purpose' not in facts:facts['purpose']=_fact('Address: '+facts['problem']['value'],'deterministic_draft',now,0.8)
    for fact_id,(value,basis,confidence,ttl) in SAFE_DEFAULTS.items():
        if fact_id not in facts and state['assumptions'].get(fact_id,{}).get('status')!='invalidated':
            facts[fact_id]=_fact(value,'safe_default',now,confidence);state['assumptions'][fact_id]={'fact_id':fact_id,'value':value,'basis':basis,'confidence':confidence,'owner':'product_authority','expires_at':now+ttl,'last_reviewed_at':now,'renewal_count':0,'confirmation_required':False,'status':'active'}

def _question_allowed(fact_id,state):
    """Machine-enforced: required, material, not known/derivable, and unsafe to defer."""
    policy=FACT_POLICY[fact_id]
    return fact_id in state['required_facts'] and policy['material'] and not policy['deferrable'] and not policy['derivable'] and fact_id not in state['facts'] and fact_id not in SAFE_DEFAULTS

def _plan(state,now):
    _derive(state,now);profile=load_profile(state['profile']['profile_id'],state['profile_dir']);missing=[x for x in state['required_facts'] if _question_allowed(x,state)];pending=[]
    conflicts=state.get('conflicts',{})
    for group,fact_ids in GROUPS.items():
        needed=[x for x in fact_ids if x in missing or x in conflicts]
        if not needed:continue
        qid='resolve-'+group if any(x in conflicts for x in needed) else 'ask-'+group
        prior=next((x for x in state.get('pending_questions',[]) if x['id']==qid),None)
        pending.append(prior or {'id':qid,'fact_ids':needed,'prompt':PROMPTS[group],'reason':'material required facts cannot be safely inferred or deferred','authority_effect':'none; answers prepare a proposal only'})
        if qid not in state['asked_question_ids']:state['asked_question_ids'].append(qid)
    for fact_id,assumption in state['assumptions'].items():
        if assumption['status']=='invalidated':
            qid='review-assumption-'+fact_id;pending.append({'id':qid,'fact_ids':[fact_id],'prompt':'The prior '+fact_id+' assumption is no longer valid. Confirm or replace it.','reason':'an invalidated assumption cannot be silently reused','authority_effect':'none; the answer updates the proposal only'})
            if qid not in state['asked_question_ids']:state['asked_question_ids'].append(qid)
    state['pending_questions']=pending
    complete=not missing and not conflicts and not pending
    if complete:
        values={key:value['value'] for key,value in state['facts'].items() if value['status']=='current'};outcome_keys={'outcome_statement','outcome_metric','outcome_unit','outcome_operator','outcome_target','outcome_baseline'};outcome={'statement':values['outcome_statement'],'metric':values['outcome_metric'],'unit':values['outcome_unit'],'operator':values['outcome_operator'],'target':values['outcome_target'],'baseline':values['outcome_baseline'],'minimum_sustained_periods':values['minimum_sustained_periods']} if outcome_keys<=set(values) else None;state['baseline']={'format':'CLSES-minimum-viable-baseline/v1','system_id':values['system_id'],'system_name':values['system_name'],'system_class':values.get('system_class','profile-defined'),'need':values.get('problem'),'purpose':values.get('purpose'),'beneficiaries':values.get('beneficiaries',[]),'outcome_hypothesis':outcome,'data_classes':values.get('data_classes',[]),'compliance_obligations':values.get('compliance_obligations',[]),'operating_conditions':values.get('operating_conditions',{}),'authorities':values.get('authorities',{}),'profiles':profile['lineage'],'assumptions':[x for x in state['assumptions'].values() if x['status']=='active'],'decision':'proposed_not_authorized'};state['status']='ready_for_consolidated_human_review'
    else:state['baseline']=None;state['status']='awaiting_minimum_required_facts'
    state['updated_at']=now;state['state_digest']=digest({k:v for k,v in state.items() if k!='state_digest'})
    if state['baseline'] is not None:_schema_validate('minimal-viable-baseline.schema.json',state['baseline'])
    _schema_validate('minimal-intake-state.schema.json',state);return state

def start(profile,context=None,profile_dir=None,now=None):
    now=int(time.time()) if now is None else int(now);profile_dir=str(profile_dir or (Path(__file__).resolve().parent/'profiles'));composed=load_profile(profile,profile_dir);control_ids={x['id'] for x in composed['controls']};required=set(CORE_REQUIRED)
    for control_id,fact_ids in CONTROL_FACTS.items():
        if control_id in control_ids:required|=fact_ids
    context=context or {};known=context.get('facts',context);conflicts=context.get('conflicts',{}) if isinstance(context,dict) else {};facts={}
    for key,value in known.items():
        if key=='conflicts' or not _present(value):continue
        if key in required or key in ('system_class','system_id','purpose'):facts[key]=_fact(_validate(key,value) if key in required else value,'provided_context',now)
    state={'format':FORMAT,'session_id':str(uuid.uuid4()),'profile':{'profile_id':composed['profile_id'],'version':composed['version'],'composed_digest':digest(composed)},'profile_dir':profile_dir,'required_facts':sorted(required),'fact_policy_digest':digest(FACT_POLICY),'facts':facts,'assumptions':{},'conflicts':conflicts,'pending_questions':[],'asked_question_ids':[],'deferred':sorted(SAFE_DEFAULTS),'baseline':None,'status':'new','updated_at':now,'state_digest':''};return _plan(state,now)

def answer(state,answers,now=None):
    now=int(time.time()) if now is None else int(now)
    if state.get('format')!=FORMAT:raise ValueError('invalid intake state')
    allowed={fact for question in state.get('pending_questions',[]) for fact in question['fact_ids']}
    unknown=set(answers)-allowed
    if unknown:raise ValueError('answers were not requested: '+','.join(sorted(unknown)))
    for fact_id,value in answers.items():
        state['facts'][fact_id]=_fact(_validate(fact_id,value),'human_answer',now);state['conflicts'].pop(fact_id,None)
        if fact_id in state['assumptions'] and state['assumptions'][fact_id]['status']=='invalidated':state['assumptions'][fact_id]['status']='replaced_by_human'
    return _plan(state,now)

def reassess(state,change,now=None):
    now=int(time.time()) if now is None else int(now)
    if not isinstance(change,dict) or set(change)!={'change_id','kind','affected_facts','reason'} or not change['affected_facts']:raise ValueError('invalid engagement change')
    for fact_id in change['affected_facts']:
        if fact_id in state['facts']:
            state['facts'][fact_id]['status']='stale';del state['facts'][fact_id]
        if fact_id in state['assumptions']:state['assumptions'][fact_id]['status']='invalidated'
        if fact_id in state['required_facts']:state['conflicts'][fact_id]=[{'change_id':change['change_id'],'reason':change['reason']}]
    state.setdefault('change_log',[]).append({**change,'detected_at':now});return _plan(state,now)

def public_result(state):
    return {'session_id':state['session_id'],'status':state['status'],'questions':state['pending_questions'],'question_count':len(state['pending_questions']),'assumptions':list(state['assumptions'].values()),'deferred':state['deferred'],'baseline':state['baseline'],'state_digest':state['state_digest']}

def main():
    parser=argparse.ArgumentParser(prog='clses-intake');sub=parser.add_subparsers(dest='command',required=True);p=sub.add_parser('start');p.add_argument('--profile',required=True);p.add_argument('--context');p.add_argument('--output',required=True);p.add_argument('--profile-dir');p=sub.add_parser('answer');p.add_argument('state');p.add_argument('answers');p.add_argument('--output');p=sub.add_parser('status');p.add_argument('state');p=sub.add_parser('reassess');p.add_argument('state');p.add_argument('change');p.add_argument('--output');args=parser.parse_args()
    if args.command=='start':state=start(args.profile,json.loads(Path(args.context).read_text()) if args.context else {},args.profile_dir);write(args.output,state)
    elif args.command=='answer':state=answer(json.loads(Path(args.state).read_text()),json.loads(Path(args.answers).read_text()));write(args.output or args.state,state)
    elif args.command=='reassess':state=reassess(json.loads(Path(args.state).read_text()),json.loads(Path(args.change).read_text()));write(args.output or args.state,state)
    else:state=json.loads(Path(args.state).read_text())
    print(json.dumps(public_result(state),indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
