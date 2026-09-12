# SPDX-License-Identifier: GPL-3.0-only
"""Synthetic public API responses; never source availability evidence."""
import copy
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'msix'))
from application_source import verify_responses

class ApplicationSourceTests(unittest.TestCase):
    def setUp(self):
        self.local={'tree':'b'*40,'entries':{'src/main.cpp':dict(mode='100644',type='blob',sha='c'*40)}}
        self.repo=dict(full_name='hashfunction/wavequay',private=False,visibility='public')
        self.commit=dict(sha='a'*40,tree=dict(sha='b'*40))
        self.tree=dict(sha='b'*40,truncated=False,tree=[dict(path='src/main.cpp',mode='100644',type='blob',sha='c'*40)])
    def check(self): return verify_responses('hashfunction/wavequay','a'*40,self.local,self.repo,self.commit,self.tree)
    def test_exact_public_complete_tree(self): self.assertEqual(self.check()['entryCount'],1)
    def test_partial_private_foreign_and_mutations(self):
        changes=[('repo','private',True),('repo','private',0),('repo','visibility','private'),('repo','full_name','other/repo'),
                 ('commit','sha','d'*40),('tree','truncated',True),('tree','truncated',None),('tree','sha','d'*40),('tree','tree',[])]
        for obj,key,value in changes:
            before=copy.deepcopy(getattr(self,obj));getattr(self,obj)[key]=value
            with self.subTest(obj=obj,key=key),self.assertRaises(ValueError):self.check()
            setattr(self,obj,before)
        for key,value in [('mode','120000'),('type','commit'),('sha','e'*40),('path','../src/main.cpp')]:
            before=copy.deepcopy(self.tree);self.tree['tree'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.check()
            self.tree=before
        self.tree['tree']*=2
        with self.assertRaises(ValueError):self.check()
