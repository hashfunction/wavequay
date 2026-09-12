# SPDX-License-Identifier: GPL-3.0-only
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$helper=Join-Path $PSScriptRoot 'qualify-install.ps1'
if(-not (Test-Path $helper)){throw 'Missing installed qualification orchestration'}
. $helper -LibraryOnly
function Check($Value,$Message){if(-not $Value){throw $Message}}
$normal=@('Preflight','SignCopy','Install','Consumer','Uninstall')
$cleanup=@('RemoveOwnedPackage','RemoveCertificateTrust','RemoveCertificate','RemoveTemporary')
foreach($failure in @('')+$normal+$cleanup) {
    $seen=[Collections.Generic.List[string]]::new();$ops=[ordered]@{}
    foreach($step in $normal+$cleanup) {
        $label=$step;$chosen=$failure
        $ops[$step]={ $seen.Add($label); if($label -ceq $chosen){throw ('observed-'+$label)}; 'native stdout' }.GetNewClosure()
    }
    $result=Invoke-WaveWeftInstallCore $ops
    Check (@($result).Count -eq 1) 'Native stdout contaminated the structured receipt'
    Check ($result.passed -eq (-not $failure)) 'Incomplete install was accepted'
    Check (($seen | Select-Object -Last $cleanup.Count) -join ',' -ceq ($cleanup -join ',')) 'Cleanup sequence skipped or changed'
    if($failure -cin $normal){Check ($result.primary_error -ceq ('observed-'+$failure)) 'Primary failure was masked'}
    if($failure -cin $cleanup){Check ($result.cleanup_errors.Count -eq 1) 'Cleanup error was lost'}
}
$identity=Get-WaveWeftInstallIdentity 'store'
Check ($identity.packageName -ceq '1659hashfunction.WaveQuay' -and $identity.publisher -ceq 'CN=B6A2631A-FD32-45CC-AE12-82466975F528') 'Assigned immutable identity differs'
$full='1659hashfunction.WaveQuay_1.0.1.0_x64__r3hxytd7jt6c4';$family='1659hashfunction.WaveQuay_r3hxytd7jt6c4'
$candidate=[pscustomobject]@{Name=$identity.packageName;Publisher=$identity.publisher;Version='1.0.1.0';Architecture='X64';PackageFullName=$full;PackageFamilyName=$family}
Assert-WaveWeftRegistration $candidate $identity $family $true @()
foreach($field in @('Name','Publisher','Version','Architecture','PackageFullName','PackageFamilyName')) {
    $copy=$candidate.PSObject.Copy();$copy.$field='foreign';$failed=$false
    try{Assert-WaveWeftRegistration $copy $identity $family $true @()}catch{$failed=$true}
    Check $failed ('Foreign registration accepted: '+$field)
}
foreach($case in @(@($false,@()),@($true,@('preexisting')))) {
    $failed=$false;try{Assert-WaveWeftRegistration $candidate $identity $family $case[0] $case[1]}catch{$failed=$true}
    Check $failed 'Registration adopted without successful owned Add and empty preflight'
}
Write-Output 'PASS: 10 install/failure sequencing cases and 9 exact registration ownership cases; no actual Windows installation claimed.'
