import json,tempfile,unittest
from pathlib import Path
from clses_mvas_v1.store import Store,read,write

class StoreTest(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.store=Store(self.root);self.store.bootstrap()
    def tearDown(self):self.temp.cleanup()
    def test_signed_content_addressed_record_verifies(self):
        identifier=self.store.commit('test','agent','agent','test_record',{'value':1});self.assertEqual(self.store.get(identifier,'test_record','agent')['payload']['value'],1);self.assertTrue(self.store.verify_ledger()[0])
    def test_record_tampering_is_detected(self):
        identifier=self.store.put('agent','agent','test_record',{'value':1});path=self.store.state/'objects'/(identifier+'.json');value=read(path);value['payload']['value']=2;write(path,value)
        with self.assertRaises(ValueError):self.store.get(identifier)
    def test_ledger_tampering_is_detected(self):
        self.store.commit('test','agent','agent','test_record',{'value':1});path=self.store.state/'ledger.jsonl';entry=json.loads(path.read_text());entry['kind']='changed';path.write_text(json.dumps(entry)+'\n');self.assertFalse(self.store.verify_ledger()[0])
    def test_wrong_role_cannot_sign(self):
        with self.assertRaises(PermissionError):self.store.put('agent','release_authorizer','x',{})
if __name__=='__main__':unittest.main()
