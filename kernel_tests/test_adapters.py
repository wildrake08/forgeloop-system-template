import json,sys,tempfile,time,unittest
from pathlib import Path
from clses_mvas_v1.adapters import as_evidence,run_adapter,validate_manifest,validate_result
from clses_mvas_v1.store import digest

class AdapterProtocolTest(unittest.TestCase):
    def setUp(self):
        self.now=2000000000;core={'format':'CLSES-adapter-manifest/v1','id':'test-adapter','version':'1','capabilities':['test_result'],'trust_anchor':'test-key','execution_boundary':'isolated','command':[sys.executable,'-c','import json,sys; r=json.load(open(sys.argv[1])); json.dump({"format":"CLSES-adapter-result/v1","request_id":r["request_id"],"adapter_id":"test-adapter","adapter_digest":sys.argv[3],"evidence_type":"test_result","passed":True,"measurements":{"tests":1},"raw_evidence_sha256":"'+('a'*64)+'","observed_at":'+str(self.now)+',"expires_at":'+str(self.now+100)+'},open(sys.argv[2],"w"))','{request}','{output}','DIGEST'],'timeout_seconds':10};self.manifest={**core,'digest':digest(core)};self.manifest['command'][-1]=self.manifest['digest'];core={k:self.manifest[k] for k in self.manifest if k!='digest'};self.manifest['digest']=digest(core);self.manifest['command'][-1]=self.manifest['digest'];core={k:self.manifest[k] for k in self.manifest if k!='digest'};self.manifest['digest']=digest(core)
        # The command embeds the digest, so use a stable script that reads it from the request instead.
        script='import json,sys; r=json.load(open(sys.argv[1])); json.dump({"format":"CLSES-adapter-result/v1","request_id":r["request_id"],"adapter_id":"test-adapter","adapter_digest":r["inputs"]["adapter_digest"],"evidence_type":"test_result","passed":True,"measurements":{"tests":1},"raw_evidence_sha256":"'+('a'*64)+'","observed_at":'+str(self.now)+',"expires_at":'+str(self.now+100)+'},open(sys.argv[2],"w"))';core={'format':'CLSES-adapter-manifest/v1','id':'test-adapter','version':'1','capabilities':['test_result'],'trust_anchor':'test-key','execution_boundary':'isolated','command':[sys.executable,'-c',script,'{request}','{output}'],'timeout_seconds':10};self.manifest={**core,'digest':digest(core)};self.request={'format':'CLSES-adapter-request/v1','request_id':'r1','system_id':'s1','environment_id':'prod','control_id':'verification-effective','artifact_id':'verification','evidence_type':'test_result','inputs':{'adapter_digest':self.manifest['digest']},'deadline':self.now+100}
    def test_strict_adapter_round_trip(self):
        result=run_adapter(self.manifest,self.request,self.now);self.assertTrue(result['passed']);self.assertEqual(as_evidence(result,self.request)['control_id'],'verification-effective')
    def test_manifest_digest_is_enforced(self):
        value=dict(self.manifest);value['digest']='0'*64
        with self.assertRaises(ValueError):validate_manifest(value)
    def test_expired_request_is_rejected(self):
        value=dict(self.request);value['deadline']=self.now-1
        with self.assertRaises(ValueError):run_adapter(self.manifest,value,self.now)
    def test_failing_result_is_rejected(self):
        result={'format':'CLSES-adapter-result/v1','request_id':'r1','adapter_id':'test-adapter','adapter_digest':self.manifest['digest'],'evidence_type':'test_result','passed':False,'measurements':{'tests':0},'raw_evidence_sha256':'a'*64,'observed_at':self.now,'expires_at':self.now+1}
        with self.assertRaises(ValueError):validate_result(result,self.manifest,self.request,self.now)
    def test_result_cannot_switch_request(self):
        result={'format':'CLSES-adapter-result/v1','request_id':'other','adapter_id':'test-adapter','adapter_digest':self.manifest['digest'],'evidence_type':'test_result','passed':True,'measurements':{'tests':1},'raw_evidence_sha256':'a'*64,'observed_at':self.now,'expires_at':self.now+1}
        with self.assertRaises(ValueError):validate_result(result,self.manifest,self.request,self.now)

if __name__=='__main__':unittest.main()
