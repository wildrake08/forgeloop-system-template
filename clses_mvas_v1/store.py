"""Content-addressed signed records and a hash-chained audit ledger."""
from __future__ import annotations
import hashlib,hmac,json,os,secrets,time
from pathlib import Path

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def digest(value):return hashlib.sha256(value if isinstance(value,bytes) else canonical(value)).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n');tmp.replace(path)

class Store:
    def __init__(self,root):self.root=Path(root).resolve();self.state=self.root/'.clses-v1'
    def bootstrap(self):
        if self.state.exists():raise ValueError('workspace already initialized')
        principals={'owner':['trust_admin','product_authorizer'],'agent':['agent','builder'],'engineering-reviewer':['engineering_authorizer'],'release-owner':['spec_acceptor','artifact_acceptor','release_authorizer','assessor'],'operator':['deployer'],'monitor':['observer']};trust={'format':'CLSES-trust/v1','model':'local-hmac-sha256','principals':{}}
        for name,roles in principals.items():
            key=secrets.token_bytes(32);path=self.state/'keys'/(name+'.key');path.parent.mkdir(parents=True,exist_ok=True);path.write_text(key.hex()+'\n');os.chmod(path,0o600);trust['principals'][name]={'roles':roles,'key_id':digest(key)[:24],'active':True}
        write(self.state/'trust.json',trust)
    def require(self,actor,role):
        try:p=read(self.state/'trust.json')['principals'][actor]
        except (FileNotFoundError,KeyError) as exc:raise PermissionError('unknown principal: '+actor) from exc
        if not p['active'] or role not in p['roles']:raise PermissionError(f'{actor} lacks role {role}')
    def _key(self,actor):return bytes.fromhex((self.state/'keys'/(actor+'.key')).read_text().strip())
    def put(self,actor,role,purpose,payload):
        self.require(actor,role);body={'format':'CLSES-signed-record/v1','actor':actor,'role':role,'purpose':purpose,'created_at':int(time.time()),'payload':payload};record={**body,'signature':hmac.new(self._key(actor),canonical(body),hashlib.sha256).hexdigest()};identifier=digest(record);path=self.state/'objects'/(identifier+'.json')
        if not path.exists():write(path,record)
        return identifier
    def get(self,identifier,purpose=None,role=None):
        record=read(self.state/'objects'/(identifier+'.json'));body={k:v for k,v in record.items() if k!='signature'};self.require(record['actor'],record['role'])
        expected=hmac.new(self._key(record['actor']),canonical(body),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected,record['signature']) or digest(record)!=identifier:raise ValueError('record integrity failure')
        if purpose and record['purpose']!=purpose:raise ValueError('record purpose mismatch')
        if role and record['role']!=role:raise PermissionError('record role mismatch')
        return record
    def point(self,name,identifier):write(self.state/'refs'/(name+'.json'),{'digest':identifier})
    def deref(self,name,purpose=None,role=None):
        pointer=read(self.state/'refs'/(name+'.json'));return pointer['digest'],self.get(pointer['digest'],purpose,role)
    def event(self,kind,actor,record_digest):
        path=self.state/'ledger.jsonl';previous='GENESIS'
        if path.exists():
            lines=[json.loads(x) for x in path.read_text().splitlines() if x];previous=lines[-1]['hash'] if lines else previous
        body={'sequence':0 if previous=='GENESIS' else len(lines),'time':int(time.time()),'kind':kind,'actor':actor,'record_digest':record_digest,'previous':previous};entry={**body,'hash':digest(body)}
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('a') as stream:stream.write(json.dumps(entry,sort_keys=True)+'\n')
        return entry['hash']
    def verify_ledger(self):
        path=self.state/'ledger.jsonl';previous='GENESIS';count=0
        try:
            for line in path.read_text().splitlines():
                entry=json.loads(line);body={k:v for k,v in entry.items() if k!='hash'}
                if body['previous']!=previous or digest(body)!=entry['hash']:return False,count
                self.get(body['record_digest']);previous=entry['hash'];count+=1
        except (FileNotFoundError,ValueError,KeyError,json.JSONDecodeError):return False,count
        return True,count
    def commit(self,kind,actor,role,purpose,payload,ref=None):
        identifier=self.put(actor,role,purpose,payload);self.event(kind,actor,identifier)
        if ref:self.point(ref,identifier)
        return identifier
