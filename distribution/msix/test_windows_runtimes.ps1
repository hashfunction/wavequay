# SPDX-License-Identifier: GPL-3.0-only
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$helper=Join-Path $PSScriptRoot 'windows-runtimes.ps1'
if(-not (Test-Path -LiteralPath $helper)){throw 'Current Windows runtime origin collector absent'}
. $helper -LibraryOnly
function Check($Value,$Message){if(-not $Value){throw $Message}}
$failed=$false
try{& $helper -Configuration missing -Stage missing -Output missing -SourceCommit invalid}catch{$failed=$true}
Check $failed 'A non-library invocation silently skipped actual Windows/source validation'
$vc='C:/Program Files/Microsoft Visual Studio/2022/Enterprise/VC'
$crt=$vc+'/Redist/MSVC/14.44.35112/x64/Microsoft.VC143.CRT'
$context=[ordered]@{schemaVersion=1;msvcRedistDir=$vc+'/Redist/MSVC/14.44.35112';msvcCrtDir=$crt;vcInstallDir=$vc;
    windowsSdkDir='C:/Program Files (x86)/Windows Kits/10';windowsSdkVersion='10.0.26100.0\';debugRuntimes=$false;
    libraries=@('msvcp140.dll','msvcp140_1.dll','msvcp140_2.dll','msvcp140_atomic_wait.dll','msvcp140_codecvt_ids.dll','vcruntime140.dll','vcruntime140_1.dll','concrt140.dll' | ForEach-Object {$crt+'/'+$_})}
$plan=@(Get-WaveWeftWindowsRuntimePlan $context 'C:/Program Files' 'C:/Program Files (x86)')
Check ($plan.Count -eq 9) 'Expected exactly eight configured VC runtime files and one SDK D3D compiler'
Check ($plan[-1].origin -ceq 'C:/Program Files (x86)/Windows Kits/10/Redist/D3D/x64/d3dcompiler_47.dll') 'D3D origin differs from exact SDK redistributable location'
$mutations=@(
    {param($c) $c.debugRuntimes=$true}, {param($c) $c.debugRuntimes='false'},
    {param($c) $c.schemaVersion=$true}, {param($c) $c.windowsSdkVersion='10.0.19041.0'},
    {param($c) $c.windowsSdkDir='C:/Windows/System32'}, {param($c) $c.vcInstallDir='C:/foreign/VC'},
    {param($c) $c.msvcRedistDir=$c.msvcRedistDir+'/../14.44.35112'},
    {param($c) $c.msvcCrtDir=$c.msvcCrtDir.Replace('/x64/','/x86/')},
    {param($c) $c.libraries=@($c.libraries | Select-Object -Skip 1)},
    {param($c) $c.libraries=@($c.libraries)+@($c.libraries[0])},
    {param($c) $c.libraries[1]=$c.libraries[0].ToUpperInvariant()},
    {param($c) $c.libraries[0]='C:/foreign/msvcp140.dll'},
    {param($c) $c.libraries[0]=$c.libraries[0]+':stream'},
    {param($c) $c.libraries[0]=$c.libraries[0].Replace('msvcp140.dll','msvcp140d.dll')})
foreach($mutate in $mutations){
    $copy=$context | ConvertTo-Json -Depth 10 | ConvertFrom-Json -AsHashtable
    & $mutate $copy;$failed=$false
    try{Get-WaveWeftWindowsRuntimePlan $copy 'C:/Program Files' 'C:/Program Files (x86)' | Out-Null}catch{$failed=$true}
    Check $failed 'Foreign/debug/missing/aliased configured runtime origin accepted'
}
$temporaryRoot=if($IsMacOS){'/private/tmp'}else{[IO.Path]::GetTempPath()}
$temporary=Join-Path $temporaryRoot ('waveweft-runtime-test-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory((Join-Path $temporary 'stage/bin'));[void][IO.Directory]::CreateDirectory((Join-Path $temporary 'redist'))
try {
    $origin=Join-Path $temporary 'redist/msvcp140.dll';$staged=Join-Path $temporary 'stage/bin/msvcp140.dll'
    [IO.File]::WriteAllBytes($origin,[Text.Encoding]::UTF8.GetBytes('MZ original fixture bytes'));[IO.File]::Copy($origin,$staged)
    $script:signature=[ordered]@{status='Valid';signerSubject='CN=Microsoft Windows, O=Microsoft Corporation, C=US';
        signerIssuer='CN=Microsoft test fixture issuer';signerThumbprint=('1'*40);signerCertificateSha256=('2'*64);
        companyName='Microsoft Corporation';fileVersion='fixture';productVersion='fixture';originalFilename='MSVCP140.dll'}
    $script:changeOrigin=$false
    function Get-WaveWeftRuntimeSignatureInfo([string]$Path){
        if($script:changeOrigin){[IO.File]::AppendAllText($Path,'changed during observation')}
        return $script:signature
    }
    $fixture=@([pscustomobject]@{leaf='msvcp140.dll';origin=$origin;owner='Microsoft.VC143.CRT'})
    $record=Get-WaveWeftWindowsRuntimeFiles $fixture (Join-Path $temporary 'stage')
    Check ($record['bin/msvcp140.dll'].file.sha256 -ceq (Get-FileHash -LiteralPath $origin -Algorithm SHA256).Hash.ToLowerInvariant()) 'Actual origin/stage bytes not retained'
    foreach($field in @('status','signerSubject','companyName','signerCertificateSha256')){
        $old=$script:signature[$field];$script:signature[$field]='foreign';$failed=$false
        try{Get-WaveWeftWindowsRuntimeFiles $fixture (Join-Path $temporary 'stage') | Out-Null}catch{$failed=$true}
        Check $failed ('Foreign signature metadata accepted: '+$field);$script:signature[$field]=$old
    }
    [IO.File]::AppendAllText($staged,'substitution');$failed=$false
    try{Get-WaveWeftWindowsRuntimeFiles $fixture (Join-Path $temporary 'stage') | Out-Null}catch{$failed=$true}
    Check $failed 'Changed staged runtime accepted';[IO.File]::Copy($origin,$staged,$true)
    $script:changeOrigin=$true;$failed=$false
    try{Get-WaveWeftWindowsRuntimeFiles $fixture (Join-Path $temporary 'stage') | Out-Null}catch{$failed=$true}
    Check $failed 'Runtime changing during signature observation accepted'
} finally {Remove-Item -LiteralPath $temporary -Recurse -Force}
Write-Output 'PASS: exact configured runtime plan and 14 negative path/mode cases; real file equality, four signature-policy negatives, staged substitution and concurrent origin mutation. Signature provider is a fixture; actual Windows provenance remains required.'
