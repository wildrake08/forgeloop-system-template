import copy,json,tempfile,unittest
from pathlib import Path
from clses_mvas_v1.intake import AUTHORITY_ROLES,answer,public_result,reassess,start

def complete_facts():
    return {'system_name':'Coffee Cart POS','problem':'Manual checkout is slow and error prone','beneficiaries':['operator','customer'],'outcome_statement':'Reduce representative checkout time','outcome_metric':'checkout_time_seconds','outcome_unit':'seconds','outcome_operator':'<=','outcome_target':45,'outcome_baseline':80,'data_classes':['payment token','transaction record'],'compliance_obligations':['payment-provider contract'],'operating_conditions':{'location':'mobile cart','connectivity':'intermittent'},'authorities':{role:'person-'+role for role in AUTHORITY_ROLES}}

class MinimalIntakeTest(unittest.TestCase):
    def test_empty_context_batches_exactly_five_must_have_questions(self):
        state=start('point-of-sale',now=100);self.assertEqual([x['id'] for x in state['pending_questions']],['ask-need','ask-outcome','ask-risk','ask-conditions','ask-authority'])
    def test_complete_context_asks_nothing_and_prepares_non_authoritative_baseline(self):
        state=start('point-of-sale',{'facts':complete_facts()},now=100);result=public_result(state);self.assertEqual(result['question_count'],0);self.assertEqual(result['status'],'ready_for_consolidated_human_review');self.assertEqual(result['baseline']['decision'],'proposed_not_authorized')
    def test_profile_and_safe_reversible_defaults_are_derived(self):
        state=start('point-of-sale',{'facts':complete_facts()},now=100);self.assertEqual(state['facts']['system_class']['value'],'point-of-sale');self.assertEqual(state['facts']['system_id']['value'],'coffee-cart-pos');self.assertEqual(state['baseline']['outcome_hypothesis']['minimum_sustained_periods'],2);self.assertIn('implementation_language',state['deferred'])
    def test_only_missing_group_is_asked(self):
        facts=complete_facts();del facts['authorities'];state=start('point-of-sale',{'facts':facts},now=100);self.assertEqual([x['id'] for x in state['pending_questions']],['ask-authority'])
    def test_partial_answer_does_not_duplicate_question(self):
        state=start('point-of-sale',now=100);state=answer(state,{'system_name':'Coffee POS'},101);self.assertEqual(len(state['asked_question_ids']),5);self.assertEqual(state['pending_questions'][0]['id'],'ask-need')
    def test_unrequested_answer_is_rejected(self):
        state=start('point-of-sale',now=100)
        with self.assertRaises(ValueError):answer(state,{'implementation_language':'Rust'},101)
    def test_consequential_authority_has_no_default(self):
        facts=complete_facts();del facts['authorities'];state=start('point-of-sale',{'facts':facts},now=100);self.assertNotIn('authorities',state['facts']);self.assertEqual(state['status'],'awaiting_minimum_required_facts')
    def test_answering_all_questions_produces_one_review_packet(self):
        state=start('point-of-sale',now=100);state=answer(state,complete_facts(),101);self.assertEqual(state['status'],'ready_for_consolidated_human_review');self.assertEqual(state['pending_questions'],[]);self.assertIsNotNone(state['baseline'])
    def test_material_change_reopens_only_affected_engagement(self):
        state=start('point-of-sale',{'facts':complete_facts()},now=100);state=reassess(state,{'change_id':'c1','kind':'operating_change','affected_facts':['operating_conditions'],'reason':'cart now works outdoors'},200);self.assertEqual([x['id'] for x in state['pending_questions']],['resolve-conditions']);self.assertIsNone(state['baseline'])
    def test_conflict_is_not_silently_resolved(self):
        context={'facts':complete_facts(),'conflicts':{'outcome_target':[45,60]}};state=start('point-of-sale',context,now=100);self.assertIn('resolve-outcome',[x['id'] for x in state['pending_questions']]);self.assertIsNone(state['baseline'])
    def test_silence_never_authorizes(self):
        state=start('point-of-sale',{'facts':complete_facts()},now=100);self.assertNotIn(state['baseline']['decision'],('approved','authorized'))
    def test_invalid_authority_map_is_rejected(self):
        facts=complete_facts();facts['authorities']={'product_authority':'owner'}
        with self.assertRaises(ValueError):start('point-of-sale',{'facts':facts},now=100)
    def test_required_facts_are_derived_from_composed_profile_controls(self):
        with tempfile.TemporaryDirectory() as folder:
            profile={'format':'CLSES-lifecycle-profile/v1','profile_id':'minimal','version':'1','extends':[],'system_classes':['general'],'domains':['intent'],'required_edges':[],'controls':[]};Path(folder,'minimal.json').write_text(json.dumps(profile));state=start('minimal',profile_dir=folder,now=100);self.assertEqual(state['required_facts'],['system_name']);self.assertEqual([x['fact_ids'] for x in state['pending_questions']],[['system_name']])
    def test_expired_safe_assumptions_are_explicitly_reevaluated(self):
        state=start('point-of-sale',{'facts':complete_facts()},now=100);state['assumptions']['implementation_language']['expires_at']=101;state=reassess(state,{'change_id':'c2','kind':'review','affected_facts':['problem'],'reason':'periodic review'},200);assumption=state['assumptions']['implementation_language'];self.assertEqual(assumption['renewal_count'],1);self.assertEqual(assumption['last_reviewed_at'],200)
    def test_invalidated_assumption_is_escalated_not_silently_redefaulted(self):
        state=start('point-of-sale',{'facts':complete_facts()},now=100);state=reassess(state,{'change_id':'c3','kind':'policy_change','affected_facts':['implementation_language'],'reason':'runtime policy changed'},200);self.assertEqual([x['id'] for x in state['pending_questions']],['review-assumption-implementation_language']);self.assertNotIn('implementation_language',state['facts']);self.assertIsNone(state['baseline'])

if __name__=='__main__':unittest.main()
