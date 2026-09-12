# SPDX-License-Identifier: GPL-3.0-only
$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
Add-Type -Path (Join-Path $PSScriptRoot 'AccessibilityGraphCapture.cs')
function Require($condition,$label){if(-not $condition){throw $label}}
function Reject([scriptblock]$action){$failed=$false;try{& $action}catch{$failed=$true};Require $failed 'Unsafe graph capture preparation was accepted'}
$temporaryBase=if($IsMacOS){'/private/tmp'}else{[IO.Path]::GetTempPath()}
$base=Join-Path $temporaryBase ('waveweft-graph-'+[guid]::NewGuid().ToString('N'))
try {
    Require ($null -eq [WaveQuayQualification.AccessibilityGraphCapture]::Prepare($false,'missing','bad','store')) 'Dormant preparation touched inputs'
    $root=Join-Path $base 'private-environment';$temp=Join-Path $root 'Temp'
    [void][IO.Directory]::CreateDirectory($temp)
    # Canonicalize the macOS /var temporary-directory alias for the real path test.
    if(-not $IsWindows){$root=(Resolve-Path -LiteralPath $root).ProviderPath}
    $token=[guid]::NewGuid().ToString();$marker=Join-Path $root '.waveweft-consumer-owner'
    [IO.File]::WriteAllText($marker,$token,[Text.UTF8Encoding]::new($false))
    $target=[WaveQuayQualification.AccessibilityGraphCapture]::Prepare($true,$root,$token,[System.Management.Automation.Language.NullString]::Value)
    Require ($target -ceq (Join-Path $root 'Temp/accessibility-graph.jsonl')) 'Different output target'
    Require (-not (Test-Path -LiteralPath $target)) 'Preparation wrote product output before original process'
    foreach($mode in @('qualification','store')){Reject {[WaveQuayQualification.AccessibilityGraphCapture]::Prepare($true,$root,$token,$mode)}}
    Reject {[WaveQuayQualification.AccessibilityGraphCapture]::Prepare($true,$root,'foreign',[System.Management.Automation.Language.NullString]::Value)}
    [IO.File]::WriteAllText($marker,[guid]::NewGuid().ToString())
    Reject {[WaveQuayQualification.AccessibilityGraphCapture]::Prepare($true,$root,$token,[System.Management.Automation.Language.NullString]::Value)}
    [IO.File]::WriteAllText($marker,$token)
    [IO.File]::WriteAllText($target,'original output')
    Reject {[WaveQuayQualification.AccessibilityGraphCapture]::Prepare($true,$root,$token,[System.Management.Automation.Language.NullString]::Value)}
    Require ([IO.File]::ReadAllText($target) -ceq 'original output') 'Existing graph output changed'
    [IO.File]::Delete($target);[void][IO.Directory]::CreateDirectory($target)
    Reject {[WaveQuayQualification.AccessibilityGraphCapture]::Prepare($true,$root,$token,[System.Management.Automation.Language.NullString]::Value)}
    [IO.Directory]::Delete($target);[IO.File]::Delete($marker)
    Reject {[WaveQuayQualification.AccessibilityGraphCapture]::Prepare($true,$root,$token,[System.Management.Automation.Language.NullString]::Value)}
    $tokens=$null;$parseErrors=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot '../invoke-windows-gui.ps1'),[ref]$tokens,[ref]$parseErrors)
    Require ($parseErrors.Count -eq 0) 'Production observer syntax'
    $clauses=@($ast.FindAll({param($node) $node -is [Management.Automation.Language.IfStatementAst] -and
        $node.Extent.Text -match '^if \(\$CaptureAccessibilityGraph\)' -and $node.Extent.Text -match 'collect_accessibility_graph.py'},$true))
    Require ($clauses.Count -eq 1) 'Exact production collection boundary missing'
    $primaryError=[InvalidOperationException]::new('Original UIA E_FAIL');$originalError=$primaryError
    $CaptureAccessibilityGraph=$true;$EvidenceDirectory=$base
    function python {if($script:failGraphCommand){throw 'Diagnostic command failure'};$global:LASTEXITCODE=1}
    foreach($failure in @($false,$true)) {
        $script:failGraphCommand=$failure
        & ([scriptblock]::Create($clauses[0].Extent.Text)) 3>$null
        Require ([object]::ReferenceEquals($primaryError,$originalError)) 'Graph failure replaced original UIA error'
    }
    $ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot '../qualify-windows.ps1'),[ref]$tokens,[ref]$parseErrors)
    Require ($parseErrors.Count -eq 0) 'Production qualification syntax'
    $function=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq 'Invoke-WaveProvenanceObservation'},$true)
    Require ($null -ne $function) 'Exact provenance boundary missing'
    . ([scriptblock]::Create($function.Extent.Text))
    foreach($diagnostic in @($false,$true)) {
        $result=@{diagnosticProvenanceErrors=@();windows_main_window_verified=$false}
        $original=[InvalidOperationException]::new('Original provenance failure')
        if($diagnostic) {
            Invoke-WaveProvenanceObservation -Action {throw $original} -Result $result -Diagnostic $true -Step 'native-source-inputs' 3>$null
            Require ($result.diagnosticProvenanceErrors.Count -eq 1 -and $result.diagnosticProvenanceErrors[0].exception.Contains('Original provenance failure')) 'Diagnostic provenance failure not preserved'
            Require (-not $result.windows_main_window_verified) 'Diagnostic provenance handling claimed acceptance'
        } else {
            Reject {Invoke-WaveProvenanceObservation -Action {throw $original} -Result $result -Diagnostic $false -Step 'native-source-inputs'}
            Require ($result.diagnosticProvenanceErrors.Count -eq 0) 'Normal fail-immediate behavior changed'
        }
    }
    $result=@{diagnosticProvenanceErrors=@()}
    Invoke-WaveProvenanceObservation -Action {throw ('x'*9000)} -Result $result -Diagnostic $true -Step 'native-source-inputs' 3>$null
    Require ($result.diagnosticProvenanceErrors[0].exception.Length -eq 8192 -and $result.diagnosticProvenanceErrors[0].truncated) 'Provenance exception bound differs'
    Write-Output 'PASS: actual graph preparation/ownership refusals and production collection boundary preserves primary error on both nonzero and thrown diagnostic failures.'
} finally {if(Test-Path -LiteralPath $base){Remove-Item -LiteralPath $base -Recurse -Force}}
