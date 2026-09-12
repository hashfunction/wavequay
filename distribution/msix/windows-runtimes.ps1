# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Trieflow LLC
[CmdletBinding()]
param([string]$Configuration,[string]$Stage,[string]$Output,[string]$SourceCommit,[switch]$LibraryOnly)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'file-io.ps1')

function ConvertTo-WaveWeftWindowsRuntimePath([string]$Value) {
    $path=$Value.Replace('\','/').TrimEnd('/')
    if($path -notmatch '^[A-Za-z]:/[^/]' -or $path.Substring(3) -match '[:<>"|?*\x00-\x1f]'){throw 'Invalid absolute Windows runtime path'}
    foreach($part in $path.Substring(3).Split('/')){
        if(-not $part -or $part -in @('.','..') -or $part.EndsWith('.') -or $part.EndsWith(' ')){throw 'Aliased Windows runtime path'}
    }
    return $path
}

function Get-WaveWeftWindowsRuntimePlan($Context,[string]$ProgramFiles,[string]$ProgramFilesX86) {
    if(($Context.schemaVersion -isnot [int] -and $Context.schemaVersion -isnot [long]) -or $Context.schemaVersion -ne 1 -or
        $Context.debugRuntimes -isnot [bool] -or $Context.debugRuntimes){throw 'Expected current release-only CMake runtime configuration'}
    $vc=(ConvertTo-WaveWeftWindowsRuntimePath $ProgramFiles)+'/Microsoft Visual Studio/2022/Enterprise/VC'
    if((ConvertTo-WaveWeftWindowsRuntimePath $Context.vcInstallDir) -ine $vc){throw 'Runtime configuration does not belong to the active Windows runner toolchain'}
    $redist=ConvertTo-WaveWeftWindowsRuntimePath $Context.msvcRedistDir
    if($redist -notmatch ('^'+[regex]::Escape($vc)+'/Redist/MSVC/[0-9]+\.[0-9]+\.[0-9]+$')){throw 'CMake runtime root is not a release VC redistributable directory'}
    $crt=$redist+'/x64/Microsoft.VC143.CRT'
    if((ConvertTo-WaveWeftWindowsRuntimePath $Context.msvcCrtDir) -ine $crt){throw 'CMake runtime architecture/CRT directory differs'}
    $sdk=(ConvertTo-WaveWeftWindowsRuntimePath $ProgramFilesX86)+'/Windows Kits/10'
    if((ConvertTo-WaveWeftWindowsRuntimePath $Context.windowsSdkDir) -ine $sdk -or
        $Context.windowsSdkVersion.TrimEnd('\','/') -cne '10.0.26100.0'){throw 'Exact Windows SDK 10.0.26100.0 redistributable origin required'}
    $leaves=@('msvcp140.dll','msvcp140_1.dll','msvcp140_2.dll','msvcp140_atomic_wait.dll','msvcp140_codecvt_ids.dll','vcruntime140.dll','vcruntime140_1.dll','concrt140.dll')
    if($Context.libraries -isnot [array] -or $Context.libraries.Count -ne $leaves.Count){throw 'Exact configured VC runtime set differs'}
    $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    $expected=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach($leaf in $leaves){[void]$expected.Add($crt+'/'+$leaf)}
    foreach($path in $Context.libraries){
        $value=ConvertTo-WaveWeftWindowsRuntimePath $path
        if(-not $seen.Add($value) -or -not $expected.Contains($value)){throw 'Foreign/duplicate configured runtime path'}
    }
    foreach($leaf in $leaves){if(-not $seen.Contains($crt+'/'+$leaf)){throw 'Foreign/missing configured runtime origin'}}
    foreach($leaf in $leaves){[pscustomobject]@{leaf=$leaf;origin=$crt+'/'+$leaf;owner='Microsoft.VC143.CRT'}}
    [pscustomobject]@{leaf='d3dcompiler_47.dll';origin=$sdk+'/Redist/D3D/x64/d3dcompiler_47.dll';owner='Microsoft.WindowsSDK.D3D'}
}

function Get-WaveWeftRuntimeSignatureInfo([string]$Path) {
    $signature=Get-AuthenticodeSignature -LiteralPath $Path
    if($null -eq $signature.SignerCertificate){throw 'Microsoft runtime has no observed signing certificate'}
    $version=(Get-Item -LiteralPath $Path -Force).VersionInfo
    return [ordered]@{status=[string]$signature.Status;signerSubject=$signature.SignerCertificate.Subject;
        signerIssuer=$signature.SignerCertificate.Issuer;signerThumbprint=$signature.SignerCertificate.Thumbprint;
        signerCertificateSha256=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($signature.SignerCertificate.RawData)).ToLowerInvariant();
        companyName=$version.CompanyName;fileVersion=$version.FileVersion;productVersion=$version.ProductVersion;originalFilename=$version.OriginalFilename}
}

function Get-WaveWeftWindowsRuntimeFiles([array]$Plan,[string]$Release) {
    $files=[ordered]@{}
    foreach($row in $Plan){
        $deployed=Join-Path $Release ('bin/'+$row.leaf)
        $original=Get-WaveWeftFile $row.origin;$staged=Get-WaveWeftFile $deployed
        if($original.bytes -ne $staged.bytes -or $original.sha256 -cne $staged.sha256){
            throw "Configured runtime differs: $($row.origin) bytes=$($original.bytes) sha256=$($original.sha256); staged $($row.leaf) bytes=$($staged.bytes) sha256=$($staged.sha256)"
        }
        $signature=Get-WaveWeftRuntimeSignatureInfo $row.origin
        if($signature.status -cne 'Valid' -or $signature.signerSubject -notmatch '(?:^|,\s*)O=Microsoft Corporation(?:,|$)' -or
            $signature.companyName -cne 'Microsoft Corporation' -or $signature.signerCertificateSha256 -cnotmatch '^[0-9a-f]{64}$' -or
            $signature.signerThumbprint -notmatch '^[0-9a-f]{40}$' -or -not $signature.fileVersion -or -not $signature.productVersion -or -not $signature.originalFilename){
            $detail=($signature | ConvertTo-Json -Compress -Depth 3)
            if($detail.Length -gt 2048){$detail=$detail.Substring(0,2048)}
            throw "Configured runtime lacks valid original Microsoft signature/metadata: $($row.leaf); $detail"
        }
        Assert-WaveWeftFile $row.origin $original;Assert-WaveWeftFile $deployed $staged
        if($files.Contains('bin/'+$row.leaf)){throw 'Duplicate observed Windows runtime'}
        $files['bin/'+$row.leaf]=[ordered]@{owner=$row.owner;origin=$row.origin;file=$original;signature=$signature}
    }
    return $files
}

if($LibraryOnly){return}
if(-not $IsWindows -or $env:CI -cne 'true' -or $SourceCommit -cnotmatch '^[0-9a-f]{40}$' -or $SourceCommit -cne $env:GITHUB_SHA){throw 'Exact-source Windows CI required for original runtime observation'}
$runText=& python (Join-Path $PSScriptRoot 'run_context.py') --source-commit $SourceCommit
if($LASTEXITCODE -ne 0){throw 'Current runtime observation run/attempt identity unavailable'}
$runContext=$runText | ConvertFrom-Json
$before=Get-WaveWeftFile $Configuration
if($before.bytes -gt 65536){throw 'Oversized configured runtime record'}
$context=Get-Content -LiteralPath $Configuration -Raw | ConvertFrom-Json
$plan=@(Get-WaveWeftWindowsRuntimePlan $context $env:ProgramFiles ${env:ProgramFiles(x86)})
$files=Get-WaveWeftWindowsRuntimeFiles $plan $Stage
Assert-WaveWeftFile $Configuration $before
Write-WaveWeftJson $Output ([ordered]@{schemaVersion=1;sourceCommit=$SourceCommit;runContext=$runContext;configuredRuntimes=$before;
    files=$files;nativeFileCount=$files.Count;sourceLicenseClosure=$false})
