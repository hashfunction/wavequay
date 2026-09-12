# SPDX-License-Identifier: GPL-3.0-only
"""Real file-oracle records with synthetic profile metadata, not app execution."""
import copy
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
import unittest
import wave
from contextlib import closing
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[1]/'msix')]
import consumer_audio as audio
from oracle_records import validate_oracle

class OracleRecordTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()/'fixture';self.claim=audio.prepare(self.root,'a'*40)
        self.raw=(self.root/'.owner.json').read_bytes()
        for name in ('reversed.wav','reopened.wav'):
            with wave.open(str(self.root/name),'wb') as output:
                output.setparams((2,2,44100,0,'NONE','not compressed'));output.writeframes(b''.join(reversed(audio.demo_frames())))
        with closing(sqlite3.connect(self.root/'Dawn-thread.aup4')) as db,db:
            db.executescript('PRAGMA application_id=1096107097; CREATE TABLE project(id INTEGER,dict BLOB,doc BLOB); CREATE TABLE sampleblocks(samples BLOB);')
            db.execute('INSERT INTO project VALUES(1,?,?)',(b'dictionary',b'document'))
            db.execute('INSERT INTO sampleblocks VALUES(?)',(bytes(audio.FRAMES*4),))
        self.gui=dict(sourceCommit='a'*40,diagnosticAccessibilityGraph=False,ownedJobEmptyBeforeClose=True,
            consumerProfileClaim=dict(token='11111111-1111-4111-8111-111111111111',marker='.waveweft-consumer-owner',paths=[],registry=[]),userStateBefore=[])
        self.package=dict(schemaVersion=1,sourceCommit='a'*40,token='22222222-2222-4222-8222-222222222222',dataRoot=r'C:\Users\runner\AppData\Local\Packages\fixture',preinstallDataRootAbsent=True)
        recipe=dict(schemaVersion=1,id='33333333-3333-4333-8333-333333333333',name=audio.RECIPE,format='WAV',process=0,channelType=2,channels=2,sampleRate=44100,trimBlankSpace=True,mapping=[],parameters=[dict(id=65536,type=1,value=2)])
        from source_archives import digest
        self.output=r'C:\work\install\gui'
        roots=[r'C:\Users\runner\AppData\Local\Trieflow',r'C:\Users\runner\AppData\Roaming\Trieflow',r'C:\Users\runner\Documents']
        paths=[root+'\\'+name for root in roots for name in ('Audacity4','Audacity4Development')]
        self.gui['userStateBefore']=[dict(path=p,exists=False) for p in paths]
        self.gui['consumerProfileClaim']['paths']=paths+[self.output+r'\private-environment']
        self.gui['consumerProfileClaim']['registry']=[r'Software\Trieflow\Audacity4',r'Software\Trieflow\Audacity4Development']
        self.value=dict(schemaVersion=1,sourceCommit='a'*40,verified=True,errors=[],cleanup=True,
            files=audio.fixture_snapshot(self.root,self.claim),project=audio.validate_project(self.root/'Dawn-thread.aup4'),
            exports={name:audio.validate_audio(self.root/name) for name in ('reversed.wav','reopened.wav')},
            profileFiles=[dict(path=p,entries={'.waveweft-consumer-owner':digest(self.gui['consumerProfileClaim']['token'].encode())}) for p in self.gui['consumerProfileClaim']['paths']],
            profileRegistry={p:{'':'d'*64} for p in self.gui['consumerProfileClaim']['registry']},packageProfileCleanupDelegatedToUninstall=True,
            packageProfileFiles=[dict(path=self.package['dataRoot'],entries={'.waveweft-msix-owner':digest(self.package['token'].encode()),'LocalCache/export-recipes-v1.json':digest(json.dumps(recipe).encode())})],
            recipe=dict(path=self.package['dataRoot']+r'\LocalCache\export-recipes-v1.json',settings=recipe,**digest(json.dumps(recipe).encode())))
    def check(self):return validate_oracle(self.value,self.claim,self.raw,self.gui,self.package,self.output)
    def test_original_complete_records_after_files_removed(self):
        audio.remove_snapshot(self.root,self.value['files']);self.check();self.assertFalse(self.root.exists())
    def test_missing_stale_partial_and_inconsistent_oracles(self):
        changes=[lambda v:v.pop('project'),lambda v:v.update(sourceCommit='b'*40),lambda v:v.update(verified=1),
            lambda v:v.update(cleanup=False),lambda v:v['files'].pop('reopened.wav'),lambda v:v['exports'].pop('reopened.wav'),
            lambda v:v['exports']['reversed.wav'].update(sha256='b'*64),lambda v:v['exports']['reversed.wav'].update(rms=float('nan')),
            lambda v:v['exports']['reversed.wav'].update(frames=True),lambda v:v['exports']['reopened.wav'].update(maximumErrorLsb=5),
            lambda v:v['project'].update(integrity='bad'),lambda v:v['project'].update(sampleBytes=10),
            lambda v:v['recipe']['settings'].update(schemaVersion=True),lambda v:v['recipe'].update(path=r'C:\foreign\export-recipes-v1.json'),
            lambda v:v['packageProfileFiles'][0]['entries'].pop('.waveweft-msix-owner'),lambda v:v.update(profileRegistry={'foreign':{}}),
            lambda v:v['files'].update({'.owner.json':{'bytes':1,'sha256':'b'*64}})]
        for change in changes:
            before=copy.deepcopy(self.value);change(self.value)
            with self.subTest(change=change),self.assertRaises((ValueError,KeyError)):self.check()
            self.value=before
        for flag in (None,True,0,'false'):
            self.gui['diagnosticAccessibilityGraph']=flag
            with self.subTest(flag=flag),self.assertRaises(ValueError):self.check()
