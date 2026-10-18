import json,sys,tempfile,time,unittest
from pathlib import Path
from clses_mvas_v1.autonomy import AutonomousLoop
from clses_mvas_v1.copilot import LifecycleCopilot
from clses_mvas_v1.engine import Engine

class CopilotTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);Engine(self.root).init(system_id='copilot-test');self.copilot=LifecycleCopilot(self.root)
    def tearDown(self):self.tmp.cleanup()
    def session(self,principal):
        credential=(self.root/'.clses-v1/keys'/(principal+'.key')).read_text();opened=self.copilot.open_session(principal,credential);return opened['session_id'],opened['token']
    def test_only_human_principal_can_open_session(self):
        credential=(self.root/'.clses-v1/keys/agent.key').read_text()
        with self.assertRaises(PermissionError):self.copilot.open_session('agent',credential)
    def test_session_requires_matching_principal_credential(self):
        with self.assertRaises(PermissionError):self.copilot.open_session('release-owner','00'*32)
    def test_conversational_approval_has_no_authority_effect(self):
        session,token=self.session('engineering-reviewer');result=self.copilot.say(session,token,'I approve the build');self.assertFalse(result['authoritative']);self.assertIn('not authority',result['response']);self.assertFalse((self.root/'.clses-v1/authorizations').exists())
    def test_bad_token_is_rejected(self):
        session,_=self.session('operator')
        with self.assertRaises(PermissionError):self.copilot.say(session,'wrong','status')
    def test_session_can_be_explicitly_revoked(self):
        session,token=self.session('owner');result=self.copilot.close_session(session,token);self.assertEqual(result['state'],'revoked')
        with self.assertRaises(PermissionError):self.copilot.say(session,token,'status')
    def test_status_conversation_is_non_authoritative(self):
        session,token=self.session('operator');result=self.copilot.say(session,token,'Where are we and what is next?');self.assertIn('initialized',result['response']);self.assertFalse(result['authoritative'])
    def test_external_facilitator_is_advisory_only(self):
        owner,owner_token=self.session('owner');script="import json;print(json.dumps({'response':'I can explain the next gate.','suggested_action':{'kind':'prepare_mandate'}}))";profile=self.copilot.register_facilitator(owner,owner_token,'helper','generic',[sys.executable,'-c',script,'{prompt}']);self.assertEqual(profile['authority'],'none');operator,operator_token=self.session('operator');result=self.copilot.say(operator,operator_token,'Please help','helper');self.assertFalse(result['authoritative']);self.assertEqual(result['suggested_action']['kind'],'prepare_mandate');self.assertFalse((self.root/'.clses-v1/authorizations').exists())
    def test_only_owner_can_register_facilitator(self):
        operator,token=self.session('operator')
        with self.assertRaises(PermissionError):self.copilot.register_facilitator(operator,token,'bad','generic',['tool','{prompt}'])
    def test_exact_confirmation_and_principal_are_required(self):
        eng,eng_token=self.session('engineering-reviewer');proposal=self.copilot.propose_mandate(eng,eng_token,self.mandate())
        with self.assertRaises(PermissionError):self.copilot.decide(eng,eng_token,proposal['decision_id'],'approve','looks good')
        release,release_token=self.session('release-owner')
        with self.assertRaises(PermissionError):self.copilot.decide(release,release_token,proposal['decision_id'],'approve',proposal['challenge'])
    def test_rejected_decision_cannot_be_replayed(self):
        eng,token=self.session('engineering-reviewer');proposal=self.copilot.propose_mandate(eng,token,self.mandate());result=self.copilot.decide(eng,token,proposal['decision_id'],'reject',proposal['reject_challenge'],'objective is incomplete');self.assertEqual(result['outcome'],'reject')
        with self.assertRaises(ValueError):self.copilot.decide(eng,token,proposal['decision_id'],'reject',proposal['reject_challenge'],'duplicate')
    def test_arbitrary_authorization_scope_is_rejected(self):
        eng,token=self.session('engineering-reviewer')
        with self.assertRaises(PermissionError):self.copilot.propose_authorization(eng,token,'deploy:invented')
    def test_specification_change_is_facilitated_but_requires_two_authorities(self):
        from clses_mvas_v1.engine import default_spec
        owner,owner_token=self.session('owner');eng,eng_token=self.session('engineering-reviewer');release,release_token=self.session('release-owner');spec=default_spec('copilot-test','Changed purpose','users');proposed=self.copilot.propose_specification(owner,owner_token,'spec-2',spec);self.assertTrue(proposed['authority_required'])
        eng_decision=self.copilot.propose_authorization(eng,eng_token,proposed['engineering_scope']);self.approve(eng,eng_token,eng_decision);release_decision=self.copilot.propose_authorization(release,release_token,proposed['acceptance_scope']);self.approve(release,release_token,release_decision);applied=self.copilot.apply_specification(release,release_token,'spec-2');self.assertTrue(applied['reassessment_required'])
        with self.assertRaises(PermissionError):self.copilot.propose_authorization(release,release_token,proposed['acceptance_scope'])
    def mandate(self):return {'run_id':'run-1','objective':'Verify the bounded lifecycle','driver':'test-driver','allowed_paths':['tests/*'],'requirements':['test_pass_rate'],'max_iterations':2,'max_changes':2,'max_bytes':2000,'expires_at':int(time.time())+3600}
    def approve(self,session,token,proposal):return self.copilot.decide(session,token,proposal['decision_id'],'approve',proposal['challenge'])
    def test_complete_conversationally_facilitated_cycle(self):
        script="import json;print(json.dumps({'status':'done','summary':'existing implementation passes','changes':[]}))";AutonomousLoop(self.root).register_driver('test-driver','generic',[sys.executable,'-c',script,'{prompt}'])
        eng,eng_token=self.session('engineering-reviewer');release,release_token=self.session('release-owner')
        mandate=self.copilot.propose_mandate(eng,eng_token,self.mandate());self.approve(eng,eng_token,mandate)
        first=self.copilot.resume(eng,eng_token,'run-1')['result'];self.assertEqual(first['phase'],'build');build=self.copilot.propose_authorization(eng,eng_token,first['required_scopes'][0]);self.approve(eng,eng_token,build)
        second=self.copilot.resume(eng,eng_token,'run-1')['result'];self.assertEqual(second['phase'],'acceptance_and_release')
        for scope in second['required_scopes']:
            proposal=self.copilot.propose_authorization(release,release_token,scope);self.approve(release,release_token,proposal)
        final=self.copilot.resume(release,release_token,'run-1')['result'];self.assertTrue(final['valid']);self.assertEqual(final['intrinsic'],'conformant');self.assertEqual(final['relational'],'locally_demonstrated_not_production_adequacy')
if __name__=='__main__':unittest.main()
