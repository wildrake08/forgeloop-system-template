import json,tempfile,unittest
from pathlib import Path
from clses_mvas_v1.engine import Engine
from clses_mvas_v1.store import read,write

class EngineTest(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.engine=Engine(self.root);self.engine.init(system_id='test-system')
    def tearDown(self):self.temp.cleanup()
    def change(self,work_id='w1'):
        content='import unittest\nclass T(unittest.TestCase):\n def test_added(self):self.assertTrue(True)\n';request=self.engine.request(work_id,'Add governed test','tests/test_added.py',content,['test_pass_rate']);self.engine.authorize(request['authorization_scope'],'engineering','engineering-reviewer','agent');self.engine.execute(work_id);return self.engine.plan()
    def built(self):
        plan=self.change();self.engine.authorize(plan['build_scope'],'engineering','engineering-reviewer','agent');return self.engine.build()
    def test_initial_state_is_not_assessed(self):self.assertFalse(self.engine.verify()['valid'])
    def test_manual_change_is_rejected(self):
        (self.root/'src/service.py').write_text((self.root/'src/service.py').read_text()+'#manual\n')
        with self.assertRaises(PermissionError):self.engine.plan()
    def test_unknown_trace_is_rejected(self):
        with self.assertRaises(ValueError):self.engine.request('x','x','tests/x.py','x',['missing'])
    def test_undeclared_source_component_is_rejected(self):
        with self.assertRaises(ValueError):self.engine.request('x','x','src/hidden.py','x',['test_pass_rate'])
    def test_work_id_cannot_be_reused(self):
        self.engine.request('x','x','tests/x.py','x',['test_pass_rate'])
        with self.assertRaises(ValueError):self.engine.request('x','changed','tests/y.py','y',['test_pass_rate'])
    def test_duplicate_authorization_is_rejected(self):
        self.engine.authorize('work:x','engineering','engineering-reviewer','agent')
        with self.assertRaises(ValueError):self.engine.authorize('work:x','engineering','engineering-reviewer','agent')
    def test_path_escape_is_rejected(self):
        with self.assertRaises(ValueError):self.engine.request('x','x','../x.py','x',['test_pass_rate'])
    def test_execution_needs_exact_approval(self):
        self.engine.request('x','x','tests/x.py','x',['test_pass_rate'])
        with self.assertRaises(PermissionError):self.engine.execute('x')
    def test_build_needs_exact_change_set_approval(self):
        self.change()
        with self.assertRaises(PermissionError):self.engine.build()
    def test_release_needs_acceptance(self):
        pending=self.built();self.engine.authorize(pending['release_scope'],'release','release-owner','operator')
        with self.assertRaises(PermissionError):self.engine.complete()
    def test_release_needs_deployment_authorization(self):
        pending=self.built();self.engine.authorize(pending['acceptance_scope'],'release','release-owner','operator')
        with self.assertRaises(PermissionError):self.engine.complete()
    def test_full_cycle_is_intrinsic_and_explicitly_local(self):
        pending=self.built();self.engine.authorize(pending['acceptance_scope'],'release','release-owner','operator');self.engine.authorize(pending['release_scope'],'release','release-owner','operator');result=self.engine.complete();self.assertTrue(result['valid']);self.assertEqual(result['intrinsic'],'conformant');self.assertEqual(result['relational'],'locally_demonstrated_not_production_adequacy')
    def test_deployment_tamper_invalidates_cycle(self):
        pending=self.built();self.engine.authorize(pending['acceptance_scope'],'release','release-owner','operator');self.engine.authorize(pending['release_scope'],'release','release-owner','operator');self.engine.complete();(self.root/'.clses-v1/deployment/service.py').write_text('tampered')
        self.assertFalse(self.engine.verify()['checks']['deployment_current'])
    def test_post_build_change_stops_release(self):
        pending=self.built();self.engine.authorize(pending['acceptance_scope'],'release','release-owner','operator');self.engine.authorize(pending['release_scope'],'release','release-owner','operator');(self.root/'src/service.py').write_text((self.root/'src/service.py').read_text()+'#manual\n')
        with self.assertRaises(PermissionError):self.engine.complete()
    def test_tampered_ledger_fails_verification(self):
        path=self.root/'.clses-v1/ledger.jsonl';lines=path.read_text().splitlines();value=json.loads(lines[0]);value['kind']='altered';lines[0]=json.dumps(value);path.write_text('\n'.join(lines)+'\n');self.assertFalse(self.engine.verify()['checks']['ledger_valid'])
    def test_tampered_signed_object_is_rejected(self):
        pointer=read(self.root/'.clses-v1/refs/spec.json');path=self.root/'.clses-v1/objects'/(pointer['digest']+'.json');value=read(path);value['payload']['spec']['purpose']='tampered';write(path,value)
        with self.assertRaises(ValueError):self.engine.verify()
    def test_spec_change_requires_engineering_and_acceptance(self):
        spec=read(self.root/'.clses-v1/objects'/(read(self.root/'.clses-v1/refs/spec.json')['digest']+'.json'))['payload']['spec'];spec['constraints'].append('new control');proposal=self.engine.propose_spec('s1',spec);self.engine.authorize(proposal['engineering_scope'],'engineering','engineering-reviewer','agent')
        with self.assertRaises(PermissionError):self.engine.apply_spec('s1')
        self.engine.authorize(proposal['acceptance_scope'],'release','release-owner','operator');self.assertTrue(self.engine.apply_spec('s1')['reassessment_required'])
    def test_stale_spec_proposal_is_rejected(self):
        original=read(self.root/'.clses-v1/objects'/(read(self.root/'.clses-v1/refs/spec.json')['digest']+'.json'))['payload']['spec'];one=json.loads(json.dumps(original));one['constraints'].append('one');two=json.loads(json.dumps(original));two['constraints'].append('two');p1=self.engine.propose_spec('s1',one);p2=self.engine.propose_spec('s2',two)
        for change,p in [('s1',p1),('s2',p2)]:self.engine.authorize(p['engineering_scope'],'engineering','engineering-reviewer','agent');self.engine.authorize(p['acceptance_scope'],'release','release-owner','operator')
        self.engine.apply_spec('s1')
        with self.assertRaises(PermissionError):self.engine.apply_spec('s2')
if __name__=='__main__':unittest.main()
