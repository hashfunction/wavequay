# SPDX-License-Identifier: GPL-3.0-only
"""Source-defined input/readback policy fixtures, not Windows observations."""
import copy
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'msix'))
from consumer_records import validate_action_groups

class ConsumerReleaseInputTests(unittest.TestCase):
    def fixture(self):
        rows=[];action=''
        def key(values,**extra):rows.append(dict(action=action,kind='keys',keys=values,**extra))
        def click(name,role='Button'):rows.append(dict(action=action,kind='click',before=dict(name=name,role=role)))
        def text():key([17,65]);rows.append(dict(action=action,kind='unicode'))
        def picker():click('File name:','Edit');text();key([13])
        def field(name):click(name+' current','Edit');text();key([9])
        def choice(name,value):click(name+' current','ComboBox');key([13],focusRole='ControlType.ListItem',focusName=value,focusIdentity='exact-item')
        action='import-local-wav';key([17,16,73]);picker();click('Clip: Dawn-thread')
        action='reverse-selected-audio';key([17,65]);click('Effect');rows.extend([dict(action=action,kind=kind) for kind in ('menu-hover','menu-click')])
        action='save-local-project';key([17,83]);picker()
        action='configure-wav-recipe';key([17,16,69]);choice('Encoding ','Signed 16-bit PCM');click('Stereo','RadioButton');field('Folder: ');field('File name: ')
        click('Save recipe');click('Recipe name','Edit');text();click('Save recipe')
        action='apply-saved-recipe';click('Mono','RadioButton');choice('Spoken-audio export recipe','Dawn thread stereo')
        action='export-reversed-wav';click('Export')
        action='close-project-and-reopen';key([17,87])
        action='project-closed';key([17,79]);picker()
        action='export-reopened-project';key([17,16,69]);choice('Spoken-audio export recipe','Dawn thread stereo');field('File name: ');field('Folder: ');click('Export')
        action='normal-close';key([18,115])
        return rows
    def test_complete_source_action_groups(self):validate_action_groups(self.fixture())
    def test_optional_local_save_page_and_bounded_combo_navigation(self):
        rows=self.fixture();index=next(i for i,row in enumerate(rows) if row['action']=='save-local-project')+1
        rows.insert(index,dict(action='save-local-project',kind='click',before=dict(name='On your computer',role='Button')))
        selected=next(i for i,row in enumerate(rows) if row.get('focusName')=='Signed 16-bit PCM')
        for i in range(49):
            rows.insert(selected+i,dict(action='configure-wav-recipe',kind='keys',keys=[40],focusRole='ControlType.ListItem',
                focusName='other option '+str(i),focusIdentity='other-item-'+str(i)))
        validate_action_groups(rows)
        changed=copy.deepcopy(rows);changed.insert(selected,copy.deepcopy(changed[selected]))
        with self.assertRaises(ValueError):validate_action_groups(changed)
        changed=copy.deepcopy(rows);changed[selected]['keys']=[38]
        with self.assertRaises(ValueError):validate_action_groups(changed)
    def test_omitted_or_reordered_actions_clicks_and_choice_readback(self):
        rows=self.fixture()
        for index in range(len(rows)):
            altered=copy.deepcopy(rows);altered.pop(index)
            with self.subTest(index=index),self.assertRaises(ValueError):validate_action_groups(altered)
        for change in [lambda r:r[0].update(keys=[17,79]),lambda r:r[-1].update(keys=[18,114]),
                       lambda r:r[5]['before'].update(name='foreign'),lambda r:r[7].update(action='import-local-wav'),
                       lambda r:next(row for row in r if row.get('focusName')=='Dawn thread stereo').update(focusName='Other recipe')]:
            altered=copy.deepcopy(rows);change(altered)
            with self.assertRaises(ValueError):validate_action_groups(altered)

class ConsumerTextReleaseTests(unittest.TestCase):
    def fixture(self):
        fixture=r'D:\work\install\gui\consumer-fixture'
        rows=[('import-local-wav',fixture+r'\Dawn-thread.wav',True),('save-local-project',fixture+r'\Dawn-thread.aup4',True),
              ('configure-wav-recipe',fixture,False),('configure-wav-recipe','reversed',False),
              ('configure-wav-recipe','Dawn thread stereo',False),('project-closed',fixture+r'\Dawn-thread.aup4',True),
              ('export-reopened-project','reopened',False),('export-reopened-project',fixture,False)]
        flow=dict(fixture=fixture,processId=123,mainWindowHandle=10,inputs=[],textReadbacks=[])
        for index,(action,value,native) in enumerate(rows):
            window=20+index;control=100+index;identity='42,'+str(control)
            snapshot=dict(pid=123,foregroundPid=123,nativeFocusPid=123,uiaFocusPid=123,main=10,window=window,
                foreground=window,nativeFocusRoot=window,nativeFocus=control,owned=True,enabled=True,offscreen=False,
                expectedTargetContainsFocus=True,identity=identity)
            flow['inputs'].append(dict(action=action,kind='unicode',targetIdentity=identity,window=window,characters=len(value),guardedCharacters=len(value)))
            flow['textReadbacks'].append(dict(action=action,kind='owned-WM_GETTEXT' if native else 'uia-value-or-text',
                expected=value,confirmed=True,targetIdentity=identity,window=window,control=control if native else 0,
                confirmation=dict(Attempts=1,ElapsedMs=6),reads=[dict(completed=True,error=0,value=value,copied=len(value),matched=True,
                elapsedMs=6,before=snapshot,final=copy.deepcopy(snapshot),
                packet=dict(Window=control,Message=13,Capacity=4096,Flags=35,TimeoutMs=500) if native else None)]))
        return flow
    def test_complete_actual_text_confirmation_shape(self):
        from consumer_records import validate_readbacks
        validate_readbacks(self.fixture())
    def test_missing_fabricated_foreign_stale_and_partial_text_records(self):
        from consumer_records import validate_readbacks
        changes=[lambda f:f['textReadbacks'].pop(),lambda f:f['inputs'].pop(),
            lambda f:f['textReadbacks'][0].update(expected=r'C:\foreign.wav'),
            lambda f:f['textReadbacks'][0].update(confirmed=1),lambda f:f['textReadbacks'][0]['reads'][0].update(matched=False),
            lambda f:f['textReadbacks'][0]['reads'][0].update(value='wrong'),lambda f:f['textReadbacks'][0]['reads'][0].update(completed=False),
            lambda f:f['textReadbacks'][0]['reads'][0]['packet'].update(Window=65535),
            lambda f:f['textReadbacks'][0]['reads'][0]['packet'].update(TimeoutMs=501),
            lambda f:f['textReadbacks'][0]['confirmation'].update(Attempts=2),lambda f:f['textReadbacks'][0]['confirmation'].update(ElapsedMs=5001),
            lambda f:f['textReadbacks'][0]['reads'][0]['final'].update(owned=False),lambda f:f['textReadbacks'][0]['reads'][0]['final'].update(nativeFocus=999),
            lambda f:f['textReadbacks'][0]['reads'][0]['final'].update(pid=999),lambda f:f['inputs'][0].update(guardedCharacters=0),
            lambda f:f['inputs'][0].update(targetIdentity='foreign'),lambda f:f['textReadbacks'][3].update(expected='reopened')]
        for change in changes:
            flow=self.fixture();change(flow)
            with self.subTest(change=change),self.assertRaises(ValueError):validate_readbacks(flow)
