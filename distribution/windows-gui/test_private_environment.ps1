# SPDX-License-Identifier: GPL-3.0-only
# Actual filesystem helper checks. Not Windows picker or product evidence.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$helper=Join-Path $PSScriptRoot 'PrivateEnvironment.cs'
if(-not (Test-Path -LiteralPath $helper)){throw 'Missing production private Desktop preparation helper'}
Add-Type -Path $helper
function Check($Value,$Message){if(-not $Value){throw $Message}}
function Reject([scriptblock]$Action){$failed=$false;try{& $Action}catch{$failed=$true};Check $failed 'Invalid private profile was accepted'}
$base=Join-Path ([IO.Path]::GetTempPath()) ('waveweft-private-desktop-'+[guid]::NewGuid().ToString('N'))
try {
    [void][IO.Directory]::CreateDirectory($base)
    $token=[guid]::NewGuid().ToString()
    function Claimed($Name) {
        $path=Join-Path $base $Name;[void][IO.Directory]::CreateDirectory($path)
        [IO.File]::WriteAllText((Join-Path $path '.waveweft-consumer-owner'),$token,[Text.UTF8Encoding]::new($false))
        return $path
    }
    $root=Claimed 'private-environment'
    foreach($name in @('Roaming','Local','Temp')){[void][IO.Directory]::CreateDirectory((Join-Path $root $name))}
    $sentinel=Join-Path $root 'Local/retained.txt';[IO.File]::WriteAllText($sentinel,'unchanged')
    Check (-not [IO.Directory]::Exists((Join-Path $root 'Desktop'))) 'Old four-directory preparation unexpectedly supplied Desktop'
    $desktop=[WaveQuayQualification.PrivateEnvironment]::PrepareDesktop($root,$token)
    Check ($desktop -ceq (Join-Path $root 'Desktop') -and [IO.Directory]::Exists($desktop)) 'Actual private Desktop was not created'
    Check (@([IO.Directory]::EnumerateFileSystemEntries($desktop)).Count -eq 0) 'Private Desktop contains fabricated settings or files'
    Check ([IO.File]::ReadAllText($sentinel) -ceq 'unchanged') 'Existing private environment bytes changed'
    Check ([IO.File]::ReadAllText((Join-Path $root '.waveweft-consumer-owner')) -ceq $token) 'Ownership marker changed'
    Reject { [WaveQuayQualification.PrivateEnvironment]::PrepareDesktop($root,$token) }
    foreach($case in @('unmarked','wrong-token','desktop-file','desktop-directory')) {
        $candidate=Claimed $case;$target=Join-Path $candidate 'Desktop'
        switch($case) {
            'unmarked'{[IO.File]::Delete((Join-Path $candidate '.waveweft-consumer-owner'))}
            'wrong-token'{[IO.File]::WriteAllText((Join-Path $candidate '.waveweft-consumer-owner'),[guid]::NewGuid().ToString())}
            'desktop-file'{[IO.File]::WriteAllText($target,'foreign file')}
            'desktop-directory'{[void][IO.Directory]::CreateDirectory($target);[IO.File]::WriteAllText((Join-Path $target 'original.txt'),'foreign directory')}
        }
        Reject { [WaveQuayQualification.PrivateEnvironment]::PrepareDesktop($candidate,$token) }
        if($case -cin @('unmarked','wrong-token')){Check (-not [IO.Directory]::Exists($target)) 'Unowned Desktop was created'}
        if($case -ceq 'desktop-file'){Check ([IO.File]::ReadAllText($target) -ceq 'foreign file') 'Existing file changed'}
        if($case -ceq 'desktop-directory'){Check ([IO.File]::ReadAllText((Join-Path $target 'original.txt')) -ceq 'foreign directory') 'Existing directory contents changed'}
    }
    Write-Output 'PASS: actual claimed private Desktop creation; empty shell directory, retained existing bytes and refusal of missing/changed owner or existing destination.'
} finally {if(Test-Path -LiteralPath $base){Remove-Item -LiteralPath $base -Recurse -Force}}
