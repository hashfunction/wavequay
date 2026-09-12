# SPDX-License-Identifier: GPL-3.0-only
# Intentionally hosted by Windows PowerShell 5.1 / .NET Framework, not runner Qt.
param(
    [string]$Stage,
    [Parameter(Mandatory=$true)][string]$EvidenceDirectory,
    [string]$SourceCommit,
    [string]$ExpectedMainWindowTitle,
    [switch]$SelfTest
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:OS -ne 'Windows_NT' -or $env:CI -ne 'true' -or -not [Environment]::Is64BitProcess) {
    throw 'Requires a disposable x64 Windows CI desktop.'
}
New-Item -ItemType Directory -Force $EvidenceDirectory | Out-Null
try {
    Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes,WindowsBase,System.Windows.Forms,System.Drawing,System.Web.Extensions
    $references = @('System.dll','System.Core.dll','System.Drawing.dll','System.Windows.Forms.dll','System.Web.Extensions.dll',
        [System.Windows.Automation.AutomationElement].Assembly.Location,
        [System.Windows.Automation.ControlType].Assembly.Location,
        [System.Windows.Rect].Assembly.Location)
    Add-Type -Path @((Join-Path $PSScriptRoot 'GuiProbe.cs'),(Join-Path $PSScriptRoot 'OnboardingInput.cs')) -ReferencedAssemblies $references
    if ($SelfTest) {
        [WaveQuayQualification.GuiProbe]::SelfTest() | Set-Content -Encoding UTF8 (Join-Path $EvidenceDirectory 'gui-helper-self-test.json')
        Write-Output 'PASS: real Windows job cleanup and UIA interop fixture. This is not WaveWeft GUI qualification.'
        exit 0
    }
    if (-not $Stage -or -not $ExpectedMainWindowTitle -or $SourceCommit -notmatch '^[0-9a-f]{40}$') { throw 'Expected an exact stage and source commit.' }
    exit ([WaveQuayQualification.GuiProbe]::Run($Stage, $EvidenceDirectory, $SourceCommit, $ExpectedMainWindowTitle))
} catch {
    $_ | Out-String | Set-Content -Encoding UTF8 (Join-Path $EvidenceDirectory 'helper-error.log')
    Write-Error $_
    exit 1
}
