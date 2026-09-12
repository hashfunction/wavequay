# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Trieflow LLC
"""Independent complete source-defined action/readback checks for release.

The existing verifier replays screenshots, roles, ownership and actual native
input guards. These checks additionally reject a partial list with fabricated
completion flags, and bind original typed file oracles after owned cleanup.
"""
import itertools
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from consumer_audio import validate_flow
from verify_gui_evidence import verify as verify_gui
from source_catalog import require
from oracle_records import integer, path, validate_oracle

ACTIONS=['import-local-wav','reverse-selected-audio','save-local-project','configure-wav-recipe','apply-saved-recipe',
         'export-reversed-wav','close-project-and-reopen','project-closed','export-reopened-project','normal-close']


def validate_action_groups(inputs):
    require(isinstance(inputs,list) and 0<len(inputs)<=1000,'Missing/bounded complete consumer input record')
    groups=[(name,list(rows)) for name,rows in itertools.groupby(inputs,key=lambda row:row['action'])]
    require([name for name,_ in groups]==ACTIONS,'Complete ordered consumer action groups are missing or repeated')
    groups=dict(groups)
    shortcuts={'import-local-wav':[17,16,73],'reverse-selected-audio':[17,65],'save-local-project':[17,83],
        'configure-wav-recipe':[17,16,69],'close-project-and-reopen':[17,87],'project-closed':[17,79],
        'export-reopened-project':[17,16,69],'normal-close':[18,115]}
    for action,keys in shortcuts.items():
        first=groups[action][0]
        require(first['kind']=='keys' and first['keys']==keys and all(type(v) is int for v in first['keys']),
                'Source-defined shortcut is missing or differs: '+action)
    for action in ('normal-close','close-project-and-reopen'):
        require(len(groups[action])==1,'Unexpected repeated close input')
    def complete(action,build):
        rows=groups[action];position=0
        def take(kind):
            nonlocal position
            require(position<len(rows) and rows[position]['kind']==kind,'Missing/reordered native input: '+action+'/'+kind)
            result=rows[position];position+=1;return result
        def key(values):
            row=take('keys');require(row['keys']==values and all(type(v) is int for v in row['keys']),'Exact native key differs: '+action)
            return row
        def click(name,role='Button',prefix=False):
            row=take('click')['before']
            require(row['role']==role and (name is None or (row['name'].startswith(name) if prefix else row['name']==name)),
                    'Exact actual clicked control differs: '+action)
        def text():key([17,65]);take('unicode')
        def field(name):click(name,'Edit',True);text();key([9])
        def picker():click(None,'Edit');text();key([13])
        def choice(name,value):
            click(name,'ComboBox',True);seen=set()
            for _ in range(50):
                row=take('keys')
                require(row.get('focusRole')=='ControlType.ListItem' and isinstance(row.get('focusIdentity'),str)
                        and row['focusIdentity'] and row['focusIdentity'] not in seen,'Choice focus role/unique item identity differs')
                seen.add(row['focusIdentity'])
                if row['keys']==[13]:
                    require(row.get('focusName')==value,'Exact observed combo choice acceptance differs');return
                require(row['keys']==[40] and row.get('focusName')!=value,'Unexpected choice input or skipped exact item')
            raise ValueError('Choice input exceeded the original 50-item bound')
        build(take,key,click,text,field,picker,choice,rows)
        require(position==len(rows),'Unexpected repeated/additional native input: '+action)
    def imported(t,k,c,text,field,picker,choice,rows):k([17,16,73]);picker();c('Clip: Dawn-thread')
    def reversed_audio(t,k,c,text,field,picker,choice,rows):k([17,65]);c('Effect');t('menu-hover');t('menu-click')
    def saved(t,k,c,text,field,picker,choice,rows):
        k([17,83])
        if len(rows)>1 and rows[1]['kind']=='click' and rows[1]['before']['name']=='On your computer':c('On your computer')
        picker()
    def configured(t,k,c,text,field,picker,choice,rows):
        k([17,16,69]);choice('Encoding ','Signed 16-bit PCM');c('Stereo','RadioButton');field('Folder: ');field('File name: ')
        c('Save recipe');c('Recipe name','Edit');text();c('Save recipe')
    def applied(t,k,c,text,field,picker,choice,rows):c('Mono','RadioButton');choice('Spoken-audio export recipe','Dawn thread stereo')
    def exported(t,k,c,text,field,picker,choice,rows):c('Export')
    def closed(t,k,c,text,field,picker,choice,rows):k([17,87])
    def reopened(t,k,c,text,field,picker,choice,rows):k([17,79]);picker()
    def reexported(t,k,c,text,field,picker,choice,rows):
        k([17,16,69]);choice('Spoken-audio export recipe','Dawn thread stereo');field('File name: ');field('Folder: ');c('Export')
    def normal(t,k,c,text,field,picker,choice,rows):k([18,115])
    for action,builder in zip(ACTIONS,(imported,reversed_audio,saved,configured,applied,exported,closed,reopened,reexported,normal)):
        complete(action,builder)


def keyboard(snapshot,flow,window):
    pid=flow['processId'];main=flow['mainWindowHandle']
    require(all(type(snapshot.get(k)) is int and snapshot[k]==pid for k in ('pid','foregroundPid','nativeFocusPid','uiaFocusPid'))
            and snapshot['main']==main and snapshot['window']==snapshot['foreground']==snapshot['nativeFocusRoot']==window
            and snapshot['owned'] is True and snapshot['enabled'] is True and snapshot['offscreen'] is False
            and snapshot['expectedTargetContainsFocus'] is True and bool(snapshot['identity']),
            'Original text confirmation input ownership/focus differs')


def validate_readbacks(flow):
    fixture=path(flow['fixture'])
    expected=[('import-local-wav','owned-WM_GETTEXT',str(fixture/'Dawn-thread.wav')),
        ('save-local-project','owned-WM_GETTEXT',str(fixture/'Dawn-thread.aup4')),
        ('configure-wav-recipe','uia-value-or-text',str(fixture)),('configure-wav-recipe','uia-value-or-text','reversed'),
        ('configure-wav-recipe','uia-value-or-text','Dawn thread stereo'),('project-closed','owned-WM_GETTEXT',str(fixture/'Dawn-thread.aup4')),
        ('export-reopened-project','uia-value-or-text','reopened'),('export-reopened-project','uia-value-or-text',str(fixture))]
    rows=flow['textReadbacks'];typed=[row for row in flow['inputs'] if row['kind']=='unicode']
    require(isinstance(rows,list) and len(rows)==len(expected)==len(typed),'All actual native filename/recipe/export text confirmations are required')
    for receipt,write,(action,kind,value) in zip(rows,typed,expected):
        require((receipt['action'],receipt['kind'],receipt['expected'])==(action,kind,value) and receipt['confirmed'] is True,
                'Actual filename/recipe/export readback differs from source-defined consumer value')
        require(write['action']==action and write['targetIdentity']==receipt['targetIdentity'] and write['window']==receipt['window']
                and write['characters']==write['guardedCharacters']==len(value.encode('utf-16-le'))//2,
                'Actual Unicode input does not bind its exact readback target/value length')
        integer(receipt['window'],1);integer(receipt['control'],0)
        require((receipt['control']>0)==(kind=='owned-WM_GETTEXT'),'Native filename provider/readback control differs')
        reads=receipt['reads'];confirmation=receipt['confirmation']
        require(isinstance(reads,list) and 1<=len(reads)<=101,'Missing/bounded native text observations')
        require(type(confirmation['Attempts']) is int and confirmation['Attempts']==len(reads),'Text confirmation attempts differ')
        integer(confirmation['ElapsedMs'],0,5000);previous=-1
        for index,read in enumerate(reads):
            require(read['completed'] is True and type(read['error']) is int and read['error']==0
                    and isinstance(read['value'],str) and type(read['copied']) is int
                    and read['copied']==len(read['value'].encode('utf-16-le'))//2<4095
                    and read['matched'] is (read['value']==value),'Incomplete actual text readback')
            require(read['matched'] is (index==len(reads)-1),'Text confirmation did not stop at the first exact value')
            integer(read['elapsedMs'],0,420000);require(read['elapsedMs']>=previous,'Text observations reordered');previous=read['elapsedMs']
            for side in ('before','final'):keyboard(read[side],flow,receipt['window'])
            require(read['before']==read['final'],'Text confirmation ownership/focus changed')
            if kind=='owned-WM_GETTEXT':
                packet=read['packet']
                require(set(packet)=={'Window','Message','Capacity','Flags','TimeoutMs'} and packet['Window']==receipt['control']
                        and packet['Message']==13 and packet['Capacity']==4096 and packet['Flags']==35,'Native filename readback packet differs')
                integer(packet['TimeoutMs'],1,500)
                require(read['final']['nativeFocus']==receipt['control'],'Native filename exact edit focus differs')
            else:require(read['packet'] is None,'UIA text readback has a foreign native packet')


def validate(output,gui,flow,oracle,claim,claim_raw,package_claim,inventory,commit,installed):
    require(gui.get('diagnosticAccessibilityGraph') is False and type(gui.get('schemaVersion')) is int and gui['schemaVersion']==1,
            'Diagnostic GUI or untyped schema cannot qualify')
    verify_gui(gui,inventory,output,commit,installed=installed)
    require(type(flow.get('schemaVersion')) is int and flow['schemaVersion']==1 and flow['currentAction']=='normal-close',
            'Consumer source schema/final action differs')
    integer(flow['elapsedMs'],1,435000)
    require(path(flow['fixture'])==path(str(output))/'consumer-fixture','Consumer fixture escaped exact retained evidence directory')
    require(gui['startupModules'] and gui['consumerModules'] and gui['modules']==gui['startupModules']+gui['consumerModules'],
            'Complete before/after consumer module originals are required')
    validate_flow(output,flow,gui);validate_action_groups(flow['inputs']);validate_readbacks(flow)
    require(flow['elapsedMs']>=flow['observations'][-1]['elapsedMs'],'Final consumer elapsed time precedes original observations')
    return validate_oracle(oracle,claim,claim_raw,gui,package_claim,output)
