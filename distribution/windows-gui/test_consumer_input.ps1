# SPDX-License-Identifier: GPL-3.0-only
# Actual scalar input boundary, not native product execution.
$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
Add-Type -Path (Join-Path $PSScriptRoot 'ConsumerInput.cs')
function Sample {
    $s=[WaveQuayQualification.ConsumerInputSnapshot]::new()
    $s.name='Export';$s.role='Button';$s.title='Export audio';$s.identity='42,1,3'
    $s.pid=10;$s.nativePid=10;$s.foregroundPid=10;$s.hitPid=10;$s.matches=1
    $s.window=200;$s.foreground=200;$s.hitRoot=200;$s.main=100;$s.owned=$true;$s.enabled=$true
    $s.targetBounds=@(300,500,80,30);$s.windowBounds=@(100,100,700,800);$s.desktopBounds=@(0,0,1920,1080)
    $s.point=@(340,515); return $s
}
$a=Sample
[WaveQuayQualification.ConsumerInput]::Stable($a,(Sample),'Export','Button','Export audio',10,100,200)
$mutations=@{
    foreignPid={param($s)$s.pid=11};nativePid={param($s)$s.nativePid=11};foregroundPid={param($s)$s.foregroundPid=11}
    hitPid={param($s)$s.hitPid=11};foreignWindow={param($s)$s.window=201};foreignForeground={param($s)$s.foreground=201}
    foreignHit={param($s)$s.hitRoot=201};foreignMain={param($s)$s.main=101};owner={param($s)$s.owned=$false}
    duplicate={param($s)$s.matches=2};disabled={param($s)$s.enabled=$false};hidden={param($s)$s.offscreen=$true}
    name={param($s)$s.name='Export to cloud'};role={param($s)$s.role='Text'};title={param($s)$s.title='Foreign'}
    identity={param($s)$s.identity='42,2,3'};point={param($s)$s.point[0]+=1};bounds={param($s)$s.targetBounds[0]+=1}
    desktop={param($s)$s.desktopBounds[2]=1280};clipped={param($s)$s.windowBounds[3]=1000};nan={param($s)$s.targetBounds[0]=[double]::NaN}
}
foreach($key in $mutations.Keys){$b=Sample;& $mutations[$key] $b;$rejected=$false
    try{[WaveQuayQualification.ConsumerInput]::Stable($a,$b,'Export','Button','Export audio',10,100,200)}catch{$rejected=$true}
    if(-not $rejected){throw "Accepted unsafe consumer input: $key"}
}
Write-Output 'PASS: real consumer input policy and 21 ownership/geometry/identity mutations; Windows UI pending.'
function Keyboard {
    $s=[WaveQuayQualification.ConsumerKeyboardSnapshot]::new()
    $s.pid=10;$s.foregroundPid=10;$s.nativeFocusPid=10;$s.uiaFocusPid=10
    $s.window=200;$s.main=100;$s.foreground=200;$s.active=200;$s.nativeFocus=210;$s.nativeFocusRoot=200
    $s.owned=$true;$s.enabled=$true;$s.expectedTargetContainsFocus=$true;$s.identity='42,5,1';$s.title='Save project'
    $s.windowBounds=@(100,100,700,800);$s.desktopBounds=@(0,0,1920,1080);return $s
}
$a=Keyboard
[WaveQuayQualification.ConsumerInput]::KeyboardStable($a,(Keyboard),10,100,200)
$mutations=@{
    pid={param($s)$s.pid=99};foregroundPid={param($s)$s.foregroundPid=99};nativeFocusPid={param($s)$s.nativeFocusPid=99};uiaFocusPid={param($s)$s.uiaFocusPid=99}
    window={param($s)$s.window=201};main={param($s)$s.main=101};foreground={param($s)$s.foreground=201};active={param($s)$s.active=201};focusRoot={param($s)$s.nativeFocusRoot=201}
    focusChanged={param($s)$s.nativeFocus=211};identityChanged={param($s)$s.identity='42,6,1'};target={param($s)$s.expectedTargetContainsFocus=$false}
    owner={param($s)$s.owned=$false};disabled={param($s)$s.enabled=$false};offscreen={param($s)$s.offscreen=$true};title={param($s)$s.title='Foreign'}
    geometry={param($s)$s.windowBounds[0]+=1};desktop={param($s)$s.desktopBounds[2]=1280};clipped={param($s)$s.windowBounds[3]=1000}
}
foreach($key in $mutations.Keys){$b=Keyboard;& $mutations[$key] $b;$rejected=$false
    try{[WaveQuayQualification.ConsumerInput]::KeyboardStable($a,$b,10,100,200)}catch{$rejected=$true}
    if(-not $rejected){throw "Accepted unsafe consumer keyboard input: $key"}
}
Write-Output 'PASS: real consumer keyboard policy and 19 focus/owner/geometry mutations; Windows UI pending.'
function FilenameNode([long]$window,[long]$parent,[int]$id,[string]$className) {
    $n=[WaveQuayQualification.ConsumerFilenameNode]::new();$n.window=$window;$n.parent=$parent;$n.id=$id;$n.className=$className;$n.pid=7644;return $n
}
function LegacyFilename {
    # Actual Tint 34681764386 picker_fields.native, not invented Wave evidence.
    return @((FilenameNode 131644 131648 1148 Edit),(FilenameNode 131648 131650 1148 ComboBox),(FilenameNode 131650 131666 1148 ComboBoxEx32))
}
function ModernFilename {
    # The same actual artifact's Save Image File filename-validation record.
    return @((FilenameNode 393394 131768 1001 Edit),(FilenameNode 131768 197302 0 ComboBox),
        (FilenameNode 197302 131736 0 FloatNotifySink),(FilenameNode 131736 131740 0 DirectUIHWND),(FilenameNode 131740 197202 0 DUIViewWndClassName))
}
if(-not [WaveQuayQualification.ConsumerInput]::FilenameChain((LegacyFilename),7644,131666,131644)){throw 'Observed legacy filename chain rejected'}
if(-not [WaveQuayQualification.ConsumerInput]::FilenameChain((ModernFilename),7644,197202,393394)){throw 'Observed modern filename chain rejected'}
foreach($factory in @('LegacyFilename','ModernFilename')) {
    $dialog=if($factory -eq 'LegacyFilename'){131666}else{197202};$edit=if($factory -eq 'LegacyFilename'){131644}else{393394}
    $nodes=& $factory
    for($index=0;$index -lt $nodes.Count;$index++) {
        foreach($property in @('pid','id','parent','window','className')) {
            $altered=& $factory
            if($property -eq 'className'){$altered[$index].className='Foreign'}else{$altered[$index].$property+=1}
            if([WaveQuayQualification.ConsumerInput]::FilenameChain($altered,7644,$dialog,$edit)){throw "Changed filename ancestry accepted: $factory/$index/$property"}
        }
    }
    $nodes[1]=$null
    if([WaveQuayQualification.ConsumerInput]::FilenameChain($nodes,7644,$dialog,$edit)){throw 'Missing filename ancestor accepted'}
}
if([WaveQuayQualification.ConsumerInput]::FilenameChain(@((FilenameNode 131644 131666 1148 Edit)),7644,131666,131644)){throw 'Unobserved direct 1148 route accepted'}
Write-Output 'PASS: two observed filename chains, 40 per-node mutations, two null ancestors and direct 1148 rejection; Wave still needs live ownership proof.'

& (Join-Path $PSScriptRoot "test_consumer_typing_focus.ps1")
