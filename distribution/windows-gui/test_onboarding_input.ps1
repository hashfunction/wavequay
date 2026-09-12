# SPDX-License-Identifier: GPL-3.0-only
# Exercise the exact production scalar input guard; no native UI claims.
$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
Add-Type -Path (Join-Path $PSScriptRoot 'OnboardingInput.cs')
function Snapshot {
    $s=[WaveQuayQualification.ButtonInputSnapshot]::new()
    $s.name='Next'; $s.controlType='Button'; $s.windowTitle='Getting started'; $s.enabled=$true
    $s.processId=7724; $s.matchingButtons=1; $s.nativeWindowProcessId=7724; $s.foregroundProcessId=7724; $s.hitProcessId=7724
    $s.windowHandle=262498; $s.foregroundHandle=262498; $s.hitRootHandle=262498
    $s.buttonBounds=@(648,547,132,28); $s.windowBounds=@(232,143,560,442); $s.desktopBounds=@(0,0,1024,768); $s.point=@(714,561)
    return $s
}
$before=Snapshot
[WaveQuayQualification.OnboardingInput]::RequireStable($before,(Snapshot),'Next',7724,262498)
$cases=@{
    'foreign-pid'={param($s)$s.processId=999}; 'foreign-native-window'={param($s)$s.nativeWindowProcessId=999}
    'foreign-foreground-pid'={param($s)$s.foregroundProcessId=999}; 'same-pid-other-foreground'={param($s)$s.foregroundHandle=262616}
    'foreign-point-pid'={param($s)$s.hitProcessId=999}; 'same-pid-other-hit-window'={param($s)$s.hitRootHandle=262616}
    'other-window'={param($s)$s.windowHandle=262616}; 'duplicate-next'={param($s)$s.matchingButtons=2}
    'disabled'={param($s)$s.enabled=$false}; 'offscreen'={param($s)$s.offscreen=$true}
    'surrogate'={param($s)$s.name='Clip visualization. Next'}; 'other-role'={param($s)$s.controlType='Text'}
    'other-dialog'={param($s)$s.windowTitle='Foreign'}; 'point-moved'={param($s)$s.point=@(715,561)}
    'nan'={param($s)$s.buttonBounds[0]=[double]::NaN}; 'infinite'={param($s)$s.buttonBounds[0]=[double]::PositiveInfinity}
    'outside-window'={param($s)$s.buttonBounds=@(0,0,132,28)}; 'outside-desktop'={param($s)$s.desktopBounds=@(0,0,700,500)}
    'moved-button'={param($s)$s.buttonBounds=@(647,547,132,28);$s.point=@(713,561)}
    'resized-dialog'={param($s)$s.windowBounds=@(232,143,561,442)}
    'desktop-changed'={param($s)$s.desktopBounds=@(0,0,1920,1080)}
}
foreach($case in $cases.Keys){
    $final=Snapshot; & $cases[$case] $final; $rejected=$false
    try{[WaveQuayQualification.OnboardingInput]::RequireStable($before,$final,'Next',7724,262498)}catch{$rejected=$true}
    if(-not $rejected){throw "Unsafe onboarding input accepted: $case"}
}
$negative=Snapshot; $negative.buttonBounds=@(-852,547,132,28);$negative.windowBounds=@(-1268,143,560,442);$negative.desktopBounds=@(-1920,0,1920,1080);$negative.point=@(-786,561)
[WaveQuayQualification.OnboardingInput]::RequireStable($negative,$negative,'Next',7724,262498)
Write-Output 'PASS actual production guard: observed Next, negative monitor, and 21 ownership/focus/geometry mutations.'
