"""Single decision point for all state-changing operations."""
from __future__ import annotations
import time
from .store import digest,read

ROLES={'spec_propose':'agent','spec_apply':'spec_acceptor','work_request':'agent','work_execute':'agent','build':'builder','accept':'artifact_acceptor','release':'deployer','observe':'observer','close':'assessor'}

class Policy:
    def __init__(self,store):self.store=store
    def require_action(self,action,actor):self.store.require(actor,ROLES[action])
    def authorization(self,scope,kind,subject,required_signer):
        folder=self.store.state/'authorizations';candidates=[]
        for pointer in folder.glob('*.json') if folder.exists() else []:
            try:
                value=read(pointer);record=self.store.get(value['digest'],'authorization',kind+'_authorizer');p=record['payload']
                if p['scope']==scope and p['subject']==subject and p['kind']==kind and p['decision']=='approved' and p['valid_until']>=int(time.time()) and record['actor']==required_signer:candidates.append((value['digest'],record))
            except (ValueError,PermissionError,FileNotFoundError,KeyError):continue
        if not candidates:raise PermissionError(f'missing {kind} authorization for exact scope {scope}')
        return candidates[-1]
    def rejection(self,scope,kind,subject,required_signer):
        pointer=self.store.state/'rejections'/(digest(scope)+'.json')
        if not pointer.exists():raise PermissionError(f'no rejection for exact scope {scope}')
        value=read(pointer);record=self.store.get(value['digest'],'authorization_rejection',kind+'_authorizer');payload=record['payload']
        if payload['scope']!=scope or payload['kind']!=kind or payload['subject']!=subject or payload['decision']!='rejected' or record['actor']!=required_signer:raise ValueError(f'invalid rejection record for exact scope {scope}')
        return value['digest'],record
    def changed_paths_allowed(self,changes,executions,spec_digest):
        indexed={(x['path'],x['after_sha256']):x for x in executions if x['spec_digest']==spec_digest}
        for change in changes:
            if change.get('after_sha256') is None:raise PermissionError('deletion is not an authorized v1 action: '+change['path'])
            evidence=indexed.get((change['path'],change['after_sha256']))
            if not evidence:raise PermissionError('manual, stale, or untraced change: '+change['path'])
            change.update({'work_id':evidence['work_id'],'execution_digest':evidence['execution_digest'],'requirement_keys':evidence['requirement_keys']})
        return changes
