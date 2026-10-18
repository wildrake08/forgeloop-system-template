import json,sys,tempfile,unittest
from pathlib import Path
from clses_mvas_v1.autonomy import AutonomousLoop
from clses_mvas_v1.engine import Engine

ITERATING_DRIVER="""import json
c=json.load(open('context.json'))
bad=c['previous_trial'] is None
body='import unittest\\nclass T(unittest.TestCase):\\n def test_auto(self):self.assert'+('False' if bad else 'True')+'(True)\\n'
print(json.dumps({'status':'propose_changes','summary':'iterate from evidence','changes':[{'path':'tests/test_auto.py','instruction':'Add autonomous evidence test','content':body,'requirement_keys':['test_pass_rate']}]}))
"""
ISOLATED_DRIVER="""import json,pathlib
pathlib.Path('src/service.py').write_text('malicious direct edit')
print(json.dumps({'status':'done','summary':'no governed change','changes':[]}))
"""

class AutonomyTest(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.engine=Engine(self.root);self.engine.init(system_id='autonomous-system');self.loop=AutonomousLoop(self.root)
    def tearDown(self):self.temp.cleanup()
    def register(self,name='fake',script=ITERATING_DRIVER):return self.loop.register_driver(name,'generic',[sys.executable,'-c',script,'{prompt}'])
    def mandate(self,**kw):self.register();return self.engine.mandate('run1','Make the governed tests pass','fake',['tests/test_auto.py'],['test_pass_rate'],**kw)
    def test_external_agent_iterates_then_waits_for_authority(self):
        self.mandate(max_iterations=3);result=self.loop.run('run1');self.assertEqual(result['phase'],'build');self.assertEqual(result['iterations'],2);self.assertEqual(result['changes'],2);self.assertEqual(result['state'],'awaiting_non_autonomous_authority')
        self.engine.authorize(result['required_scopes'][0],'engineering','engineering-reviewer','agent');release_wait=self.loop.run('run1');self.assertEqual(release_wait['phase'],'acceptance_and_release');self.assertEqual(len(release_wait['required_scopes']),2)
        self.engine.authorize(release_wait['required_scopes'][0],'release','release-owner','operator');still_waiting=self.loop.run('run1');self.assertEqual(len(still_waiting['required_scopes']),1)
        self.engine.authorize(still_waiting['required_scopes'][0],'release','release-owner','operator');complete=self.loop.run('run1');self.assertTrue(complete['valid']);self.assertEqual(complete['mode'],'canonical_strict_mvas_v1')
    def test_mandate_budget_stops_iteration(self):
        self.mandate(max_iterations=1);result=self.loop.run('run1');self.assertEqual(result['state'],'budget_exhausted');self.assertEqual(result['iterations'],1)
    def test_agent_process_runs_against_isolated_copy(self):
        original=(self.root/'src/service.py').read_text();self.register('isolated',ISOLATED_DRIVER);self.engine.mandate('run2','Inspect only','isolated',['tests/*'],['test_pass_rate']);result=self.loop.run('run2');self.assertEqual(result['phase'],'build');self.assertEqual((self.root/'src/service.py').read_text(),original)
    def test_mandate_rejects_out_of_scope_path(self):
        self.register();self.engine.mandate('run1','Bound path','fake',['tests/other.py'],['test_pass_rate'])
        with self.assertRaises(PermissionError):self.loop.run('run1')
    def test_driver_registration_is_immutable(self):
        self.register()
        with self.assertRaises(ValueError):self.register()
    def test_mandate_requires_human_authorizer(self):
        self.register()
        with self.assertRaises(PermissionError):self.engine.mandate('run1','x','fake',['tests/*'],['test_pass_rate'],signer='agent')
    def test_invalid_driver_protocol_is_rejected(self):
        self.register('bad',"print('{}')");self.engine.mandate('run1','x','bad',['tests/*'],['test_pass_rate'])
        with self.assertRaises(ValueError):self.loop.run('run1')
if __name__=='__main__':unittest.main()
