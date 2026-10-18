import tempfile
import unittest
from pathlib import Path
from clses_mvas_v1.engine import Engine
from clses_mvas_v1.template_edition import generate_manifest,verify_scaffold,workspace_status

SERVICE='def calculate(a,b):return a+b\n'
TEST='import unittest\nclass T(unittest.TestCase):\n def test_ok(self):self.assertTrue(True)\n'

class TemplateEditionTests(unittest.TestCase):
    def scaffold(self):
        temporary=tempfile.TemporaryDirectory();root=Path(temporary.name);(root/'src').mkdir();(root/'tests').mkdir();(root/'.clses-template').mkdir();(root/'.github').mkdir();(root/'.github/CODEOWNERS').write_text('# bootstrap placeholder\n');(root/'src/service.py').write_text(SERVICE);(root/'tests/test_service.py').write_text(TEST);(root/'README.md').write_text('template\n');generate_manifest(root);return temporary,root
    def test_exact_nonempty_scaffold_is_adopted(self):
        temporary,root=self.scaffold()
        with temporary:
            result=Engine(root).init(system_id='sample',purpose='Serve users safely',beneficiary='users',template_manifest=root/'.clses-template/template-manifest.json',github_owner='@example/reviewers')
            self.assertEqual(result['state'],'initialized');self.assertTrue(result['template_manifest_digest']);self.assertEqual((root/'.github/CODEOWNERS').read_text(),'* @example/reviewers\n');self.assertTrue(workspace_status(root)['valid'])
    def test_tampered_scaffold_is_rejected(self):
        temporary,root=self.scaffold()
        with temporary:
            (root/'src/service.py').write_text('tampered\n')
            with self.assertRaises(ValueError):Engine(root).init(template_manifest=root/'.clses-template/template-manifest.json',github_owner='@example/reviewers')
    def test_invalid_github_owner_is_rejected(self):
        temporary,root=self.scaffold()
        with temporary:
            with self.assertRaises(ValueError):Engine(root).init(template_manifest=root/'.clses-template/template-manifest.json',github_owner='not-an-owner')
    def test_extra_file_is_rejected_before_adoption(self):
        temporary,root=self.scaffold()
        with temporary:
            (root/'unexpected.txt').write_text('not released\n')
            self.assertFalse(verify_scaffold(root,strict=True)['valid'])
    def test_mutable_app_change_does_not_mask_immutable_tamper(self):
        temporary,root=self.scaffold()
        with temporary:
            (root/'src/service.py').write_text('expected future governed change\n');(root/'.github/CODEOWNERS').write_text('* @example/reviewers\n');self.assertTrue(verify_scaffold(root,strict=False)['valid'])
            (root/'README.md').write_text('tampered\n');self.assertFalse(verify_scaffold(root,strict=False)['valid'])
    def test_symlink_is_rejected(self):
        temporary,root=self.scaffold()
        with temporary:
            (root/'link').symlink_to(root/'README.md')
            self.assertFalse(verify_scaffold(root,strict=True)['valid'])
