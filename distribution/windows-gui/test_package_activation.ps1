# SPDX-License-Identifier: GPL-3.0-only
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$helper=Join-Path $PSScriptRoot 'PackageActivation.cs'
if(-not (Test-Path -LiteralPath $helper)){throw 'Missing production installed activation boundary'}
Add-Type -Path $helper
function Check($Value,$Message){if(-not $Value){throw $Message}}
function Reject([scriptblock]$Action){$failed=$false;try{& $Action}catch{$failed=$true};Check $failed 'Foreign package identity was accepted'}
$family='1659hashfunction.WaveQuay_r3hxytd7jt6c4'
$full='1659hashfunction.WaveQuay_1.0.1.0_x64__r3hxytd7jt6c4'
Check ([WaveQuayQualification.PackageActivation]::ValidateIdentity('store',$full,$family) -ceq ($family+'!WaveQuay')) 'Assigned AUMID changed'
foreach($case in @(
    @('qualification',$full,$family), @('STORE',$full,$family),
    @('store',$full.Replace('1.0.1.0','1.0.2.0'),$family),
    @('store',$full.Replace('x64','x86'),$family),
    @('store',$full,$family.Replace('r3hxytd7jt6c4','a3hxytd7jt6c4')),
    @('store',$full.Replace('WaveQuay','WaveWeft'),$family),
    @('store',$full.Replace('__','_foreign_'),$family)
)) {Reject { [WaveQuayQualification.PackageActivation]::ValidateIdentity($case[0],$case[1],$case[2]) }}
$time=[DateTime]::UtcNow
[WaveQuayQualification.PackageActivation]::ValidateLifetime(4242,@(1,2,3),$time.AddMilliseconds(1),$time)
Reject { [WaveQuayQualification.PackageActivation]::ValidateLifetime(4242,@(4242),$time.AddMilliseconds(1),$time) }
Reject { [WaveQuayQualification.PackageActivation]::ValidateLifetime(4242,@(1),$time.AddSeconds(-1),$time) }
Reject { [WaveQuayQualification.PackageActivation]::ValidateLifetime(0,@(1),$time,$time) }
if($env:OS -eq 'Windows_NT') {
    Check ([WaveQuayQualification.PackageActivation]::FamilyForMode('store') -ceq $family) 'Native Store family derivation differs from authenticated identity'
    $testFamily=[WaveQuayQualification.PackageActivation]::FamilyForMode('qualification')
    Check ($testFamily -cmatch '^Trieflow\.WaveQuay\.Qualification_[0-9a-hjkmnp-tv-z]{13}$') 'Native qualification family is invalid'
    $self=[Diagnostics.Process]::GetCurrentProcess()
    try {Reject { [WaveQuayQualification.PackageActivation]::FullName($self) }} finally {$self.Dispose()}
}
Write-Output 'PASS: fixed package identity/AUMID and fresh retained-process lifetime; foreign/reused/stale process rejected. Native app activation remains a Windows installed test.'
