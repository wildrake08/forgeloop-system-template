import copy,unittest
from clses_mvas_v1.release_assessment import _sign,_signature_valid
from clses_mvas_v1.store import digest

class ReleaseCryptoTest(unittest.TestCase):
    def test_release_signature_verifies_and_tampering_fails(self):
        evidence={'version':'test','value':1};bundle={'evidence':evidence,'evidence_sha256':digest(evidence),'signer':_sign(evidence)};self.assertTrue(_signature_valid(bundle));changed=copy.deepcopy(bundle);changed['evidence']['value']=2;self.assertFalse(_signature_valid(changed))
if __name__=='__main__':unittest.main()
