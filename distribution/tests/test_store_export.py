# SPDX-License-Identifier: GPL-3.0-only
"""Synthetic lifecycle records exercise fail-closed release joins, never Windows acceptance."""
import copy
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'msix'))
from store_export import validate_stage,validate_install_state
from package import identity_for_mode
RUN=dict(repository='hashfunction/wavequay',sourceCommit='a'*40,runId='123',runAttempt=2)

class StoreExportTests(unittest.TestCase):
    def stage(self):return dict(source_commit='a'*40,runContext=RUN,diagnosticAccessibilityGraph=False,diagnosticProvenanceErrors=[],
        built=True,native_recipe_tests=True,staged=True,windows_main_window_verified=True,windows_local_file_workflow_verified=True,
        audio_device_tests=False,native_export_tests=False,source_license_closure=False,submitted=False)
    def install(self):
        start=dict(sourceCommit='a'*40,runContext=RUN,identityMode='store',package_full_name='1659hashfunction.WaveQuay_1.0.1.0_x64__r3hxytd7jt6c4',
            package_family_name='1659hashfunction.WaveQuay_r3hxytd7jt6c4',install_location=r'C:\Program Files\WindowsApps\fixture',
            package_data_root=r'C:\Users\runner\AppData\Local\Packages\1659hashfunction.WaveQuay_r3hxytd7jt6c4',
            preflight_package_full_names=[],add_completed=True,installed_by_us=True,preinstall_data_root_absent=True)
        result=dict(start,schemaVersion=1,runId='123',runAttempt='2',identity=identity_for_mode('store'),installation_qualification_passed=True,
            primary_error=None,cleanup_errors=[],residual_package_full_names=[],normal_close=True,uninstall_verified=True,
            package_profile_removed=True,certificate_trust_removed=True,personal_certificate_removed=True,temporary_signing_files_removed=True,
            unsigned_package_unchanged=True,publicRelease=False,licenseClearanceClaimed=False,process_id=123,
            unsigned_package=dict(bytes=1000,sha256='b'*64),signed_copy=dict(bytes=1200,sha256='c'*64))
        return start,result
    def test_current_normal_records(self):
        validate_stage(self.stage(),RUN);s,r=self.install();validate_install_state(s,r,RUN,'store',dict(bytes=1000,sha256='b'*64))
    def test_stage_flags_and_run_attempt_are_typed(self):
        stage=self.stage()
        for key in stage:
            if isinstance(stage[key],bool):
                for value in (not stage[key],int(stage[key]),None,'false'):
                    altered=copy.deepcopy(stage);altered[key]=value
                    with self.subTest(key=key,value=value),self.assertRaises(ValueError):validate_stage(altered,RUN)
        for value in (None,[dict(step='runtime',exception='failed',truncated=False)]):
            altered=copy.deepcopy(stage);altered['diagnosticProvenanceErrors']=value
            with self.assertRaises(ValueError):validate_stage(altered,RUN)
        altered=copy.deepcopy(stage);altered['runContext']['runAttempt']=1
        with self.assertRaises(ValueError):validate_stage(altered,RUN)
    def test_partial_foreign_and_cleanup_lifecycles_rejected(self):
        s,r=self.install()
        for key,value in [('runAttempt','1'),('process_id',True),('installation_qualification_passed',1),('normal_close',False),
            ('uninstall_verified',False),('package_profile_removed',False),('temporary_signing_files_removed',False),
            ('certificate_trust_removed',False),('personal_certificate_removed',False),('unsigned_package_unchanged',False),
            ('cleanup_errors',['failed']),('residual_package_full_names',['foreign']),('publicRelease',True),
            ('package_full_name','foreign'),('signed_copy',r['unsigned_package']),('identityMode','qualification')]:
            changed=copy.deepcopy(r);changed[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_install_state(s,changed,RUN,'store',r['unsigned_package'])
        changed=copy.deepcopy(s);changed['runContext']['runAttempt']=1
        with self.assertRaises(ValueError):validate_install_state(changed,r,RUN,'store',r['unsigned_package'])

class StoreOutputTests(unittest.TestCase):
    def test_exact_output_and_package_mutation_boundary(self):
        import tempfile
        from unittest.mock import patch,Mock
        import store_export as export
        from files import file_record
        for mutate in (False,True):
            with self.subTest(mutate=mutate),tempfile.TemporaryDirectory() as directory:
                root=Path(directory).resolve();package=root/'build-evidence/msix/store/package/WaveWeft_1.0.1.0_x64.msix'
                package.parent.mkdir(parents=True);package.write_bytes(b'preverified container fixture')
                bound=file_record(package)
                if mutate:package.write_bytes(b'changed package after verification')
                output=root/'output';originals=Mock()
                with patch.object(export,'collect',return_value=({},originals,{'store':{'containerVerification':{'package':bound}}})),patch.object(export,'assert_current_checkout'):
                    if mutate:
                        with self.assertRaisesRegex(ValueError,'changed before export'):export.export(root,output,RUN)
                        self.assertFalse(output.exists())
                    else:
                        result=export.export(root,output,RUN)
                        self.assertEqual(set(p.name for p in output.iterdir()),{package.name,'store-export.json'})
                        self.assertEqual(result['package'],dict(path=package.name,**bound))
                        self.assertEqual((output/package.name).read_bytes(),package.read_bytes())
    def test_failed_missing_publication_never_creates_upload(self):
        import tempfile
        from unittest.mock import patch
        import store_export as export
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();output=root/'output'
            with patch.object(export,'collect',side_effect=ValueError('Current public source unavailable')):
                with self.assertRaises(ValueError):export.export(root,output,RUN)
            self.assertFalse(output.exists())
    def test_missing_changed_extra_and_stale_original_snapshot(self):
        import tempfile,json
        from store_export import Originals,validate_hash_bindings
        from files import file_record
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();(root/'original.json').write_text(json.dumps({'source':'original'}))
            value={'original.json':file_record(root/'original.json')};originals=Originals(root)
            validate_hash_bindings(value,('original.json',),originals)
            for altered in ({},dict(value,extra=value['original.json']),{'original.json':dict(bytes=1,sha256='f'*64)}):
                with self.assertRaises(ValueError):validate_hash_bindings(altered,('original.json',),originals)
            (root/'original.json').write_text('changed')
            with self.assertRaises(ValueError):originals.unchanged()
