# SPDX-License-Identifier: GPL-3.0-only
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'distribution/msix'))


class RunContextTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('run_context'),'Exact native/package/install workflow run binding absent')
        import run_context
        self.m=run_context;self.commit='a'*40
        self.env=dict(CI='true',GITHUB_REPOSITORY='hashfunction/wavequay',GITHUB_SHA=self.commit,GITHUB_RUN_ID='34700392536',GITHUB_RUN_ATTEMPT='2')

    def test_exact_current_repository_source_run_and_attempt(self):
        record=self.m.current(self.commit,self.env)
        self.assertEqual(record,dict(repository='hashfunction/wavequay',sourceCommit=self.commit,runId='34700392536',runAttempt=2))
        self.m.validate(record,record)

    def test_missing_foreign_stale_and_noncanonical_environment_refused(self):
        for key,value in [('CI','false'),('GITHUB_REPOSITORY','foreign/wavequay'),('GITHUB_SHA','b'*40),
                          ('GITHUB_RUN_ID',''),('GITHUB_RUN_ID','01'),('GITHUB_RUN_ID','1e3'),
                          ('GITHUB_RUN_ATTEMPT','0'),('GITHUB_RUN_ATTEMPT','2.0'),('GITHUB_RUN_ATTEMPT','+2')]:
            env=dict(self.env);env[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.m.current(self.commit,env)

    def test_original_attempt_wrong_type_missing_or_extra_fields_refused(self):
        expected=self.m.current(self.commit,self.env)
        for key,value in [('runAttempt','2'),('runAttempt',True),('runAttempt',1),('runId',34700392536),
                          ('runId','34700392535'),('sourceCommit','b'*40),('repository','foreign/wavequay'),('extra',False)]:
            record=dict(expected);record[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.m.validate(record,expected)
        record=dict(expected);record.pop('runAttempt')
        with self.assertRaises(ValueError):self.m.validate(record,expected)


if __name__=='__main__':unittest.main()
