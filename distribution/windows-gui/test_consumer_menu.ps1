# SPDX-License-Identifier: GPL-3.0-only
# Production scalar policy fixture. UIA names/geometry are retained from
# WaveWeft run 34694396308; native owner/foreground facts below are synthetic
# negative-test inputs, not a claim that the repaired Windows route ran.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
Add-Type -Path (Join-Path $PSScriptRoot 'ConsumerInput.cs')
function SampleMenu {
    $s=[WaveQuayQualification.ConsumerMenuSnapshot]::new()
    $s.target=[WaveQuayQualification.ConsumerInputSnapshot]::new()
    $t=$s.target
    $t.name='Special Menu';$t.role='MenuItem';$t.title='Audacity4';$t.identity='observed-menu-item'
    $t.pid=6484;$t.nativePid=6484;$t.foregroundPid=6484;$t.hitPid=6484;$t.matches=1
    $t.window=393616;$t.foreground=262212;$t.hitRoot=393616;$t.main=262212;$t.owned=$true;$t.enabled=$true
    $t.targetBounds=@(699,445,209,32);$t.windowBounds=@(691,119,225,442);$t.desktopBounds=@(0,0,1920,1080);$t.point=@(803,461)
    $s.mainPid=6484;$s.mainTitle='Dawn-thread * - WaveWeft 1.0.1';$s.mainBounds=@(377,89,1166,839)
    $s.popupIdentity='observed-menu-root';$s.popupRole='Window';$s.popupClass='QQuickView'
    $s.popupAutomationId='muse::accessibility::AccessibleAppRootObject.MenuView_WindowView_QQuickView'
    $s.popupEnabled=$true;$s.popupVisible=$true;$s.targetInPopup=$true
    $a=[WaveQuayQualification.ConsumerMenuOwner]::new();$a.window=393616;$a.owner=262212;$a.pid=6484
    $b=[WaveQuayQualification.ConsumerMenuOwner]::new();$b.window=262212;$b.owner=0;$b.pid=6484
    $s.owners=@($a,$b);return $s
}
$a=SampleMenu
[WaveQuayQualification.ConsumerInput]::MenuStable($a,(SampleMenu),'Special Menu',6484,262212)
# The actual failure stopped solely on focused-role mismatch. A visible,
# exact menu target is now a pointer route: no fabricated MenuItem focus.
$b=SampleMenu;$b.target.name='Reverse'
[WaveQuayQualification.ConsumerInput]::Menu($b,'Reverse',6484,262212)
$mutations=@{
    name={param($s)$s.target.name='Legacy Menu'};role={param($s)$s.target.role='Text'};title={param($s)$s.target.title='Foreign'}
    pid={param($s)$s.target.pid=99};nativePid={param($s)$s.target.nativePid=99};foregroundPid={param($s)$s.target.foregroundPid=99}
    hitPid={param($s)$s.target.hitPid=99};mainPid={param($s)$s.mainPid=99};duplicate={param($s)$s.target.matches=2}
    disabled={param($s)$s.target.enabled=$false};hidden={param($s)$s.target.offscreen=$true};owner={param($s)$s.target.owned=$false}
    foreground={param($s)$s.target.foreground=393616};hitRoot={param($s)$s.target.hitRoot=262212};window={param($s)$s.target.window=262212}
    identity={param($s)$s.target.identity='replaced'};popupIdentity={param($s)$s.popupIdentity='replaced'}
    popupRole={param($s)$s.popupRole='Pane'};popupClass={param($s)$s.popupClass='Foreign'};popupId={param($s)$s.popupAutomationId='foreign'}
    popupDisabled={param($s)$s.popupEnabled=$false};popupHidden={param($s)$s.popupVisible=$false};outside={param($s)$s.targetInPopup=$false}
    foreignOwner={param($s)$s.owners[0].pid=99};changedOwner={param($s)$s.owners[0].owner=99};missingOwner={param($s)$s.owners=@($s.owners[0])}
    duplicateOwner={param($s)$s.owners=@($s.owners[0],$s.owners[0],$s.owners[1])};ownerTooDeep={param($s)$s.owners=@($s.owners[0])*13}
    point={param($s)$s.target.point[0]++};geometry={param($s)$s.target.targetBounds[0]++};clipped={param($s)$s.target.windowBounds[3]=1000}
    infinite={param($s)$s.target.targetBounds[0]=[double]::PositiveInfinity};mainGeometry={param($s)$s.mainBounds[0]++}
    mainTitle={param($s)$s.mainTitle='foreign'};desktop={param($s)$s.target.desktopBounds[2]=1024}
}
foreach($name in $mutations.Keys){$b=SampleMenu;& $mutations[$name] $b;$failed=$false
    try{[WaveQuayQualification.ConsumerInput]::MenuStable($a,$b,'Special Menu',6484,262212)}catch{$failed=$true}
    if(-not $failed){throw "Unsafe menu pointer accepted: $name"}
}
Write-Output ('PASS: production owned non-activating menu boundary and '+$mutations.Count+' ownership/role/geometry mutations; native pointer flow remains pending.')
