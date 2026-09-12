# SPDX-License-Identifier: GPL-3.0-only
# Run only after the existing same-source staged consumer qualification.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
if(-not $IsWindows -or $env:CI -cne 'true'){throw 'Requires disposable Windows CI'}
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location $root
$commit=(& git rev-parse HEAD).Trim()
if($LASTEXITCODE -ne 0 -or $commit -cne $env:GITHUB_SHA){throw 'Current source differs from workflow revision'}
$runText=& python (Join-Path $PSScriptRoot 'run_context.py') --source-commit $commit
if($LASTEXITCODE -ne 0){throw 'Current exact run/attempt is unavailable'}
$runContext=$runText | ConvertFrom-Json
$prior=Get-Content build-evidence/result.json -Raw | ConvertFrom-Json
if($prior.source_commit -cne $commit){throw 'Staged qualification belongs to different source'}
foreach($name in @('built','native_recipe_tests','staged','windows_main_window_verified','windows_local_file_workflow_verified')){
    if($prior.$name -isnot [bool] -or $prior.$name -ne $true){throw "Required staged qualification did not pass: $name"}
}
if($prior.diagnosticAccessibilityGraph -isnot [bool] -or $prior.diagnosticAccessibilityGraph -ne $false -or $prior.diagnosticProvenanceErrors.Count -ne 0){throw 'Diagnostic observation cannot proceed to installed qualification'}
foreach($name in @('repository','sourceCommit','runId','runAttempt')){
    if($prior.runContext.$name -cne $runContext.$name){throw 'Staged run/attempt differs'}
}
if($prior.runContext.runAttempt -isnot [long] -and $prior.runContext.runAttempt -isnot [int]){throw 'Staged attempt is not an integer'}
& python (Join-Path $PSScriptRoot 'source_closure.py') verify --native 'build-evidence/native-inputs.json' --output 'build-evidence/source-closure.json' --source-commit $commit
if($LASTEXITCODE -ne 0){throw 'Current native/source/notice comparison is incomplete'}
$release=Join-Path $root 'stage';$native=Join-Path $root 'build-evidence/native-inputs.json'
$sdk=Join-Path ${env:ProgramFiles(x86)} 'Windows Kits/10/bin/10.0.26100.0/x64'
$makeappx=Join-Path $sdk 'makeappx.exe';$signtool=Join-Path $sdk 'signtool.exe'
foreach($tool in @($makeappx,$signtool)){if(-not (Test-Path -LiteralPath $tool -PathType Leaf)){throw "Missing exact SDK x64 tool: $tool"}}
$output=Join-Path $root 'build-evidence/msix'
if(Test-Path -LiteralPath $output){throw 'MSIX evidence already exists; preserving earlier run'}
[void][IO.Directory]::CreateDirectory($output)
$result=[ordered]@{schemaVersion=1;sourceCommit=$commit;runContext=$runContext;runId=$env:GITHUB_RUN_ID;runAttempt=$env:GITHUB_RUN_ATTEMPT;
    qualificationInstalled=$false;storeInstalled=$false;sourceLicenseClosure=$false;publicRelease=$false;error=$null}
try {
    foreach($mode in @('qualification','store')) {
        $current=Join-Path $output $mode;[void][IO.Directory]::CreateDirectory($current)
        $packageDirectory=Join-Path $current 'package'
        & python (Join-Path $PSScriptRoot 'build_package.py') build --release $release --native-input $native --source-commit $commit `
            --makeappx $makeappx --output $packageDirectory --identity-mode $mode
        if($LASTEXITCODE -ne 0){throw "Exact $mode MSIX build failed"}
        $filename=if($mode -ceq 'store'){'WaveWeft_1.0.1.0_x64.msix'}else{'WaveWeft.Qualification_1.0.1.0_x64.msix'}
        & (Join-Path $PSScriptRoot 'qualify-install.ps1') -Package (Join-Path $packageDirectory $filename) `
            -PackageRecord (Join-Path $packageDirectory 'package-record.json') -Release $release -NativeInput $native `
            -SignTool $signtool -Output (Join-Path $current 'install') -IdentityMode $mode
        $receipt=Get-Content (Join-Path $current 'install/installation-result.json') -Raw | ConvertFrom-Json
        if($receipt.identityMode -cne $mode -or $receipt.sourceCommit -cne $commit -or $receipt.installation_qualification_passed -isnot [bool] -or $receipt.installation_qualification_passed -ne $true){throw 'Installed receipt mode/source/completion differs'}
        $result[$mode+'Installed']=$true
    }
} catch {$result.error=$_.Exception.Message;throw}
finally {$result | ConvertTo-Json -Depth 20 | Set-Content (Join-Path $output 'qualification-result.json')}
Write-Output 'PASS: two separate installed consumer lifecycles. Independent unsigned Store export remains a separate final gate.'
