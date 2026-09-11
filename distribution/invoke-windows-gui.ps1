# SPDX-License-Identifier: GPL-3.0-only
param(
    [string]$Stage = (Join-Path (Split-Path $PSScriptRoot -Parent) 'stage'),
    [string]$EvidenceDirectory = (Join-Path (Split-Path $PSScriptRoot -Parent) 'build-evidence/gui'),
    [string]$SourceCommit,
    [switch]$SelfTest
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $IsWindows -or $env:CI -ne 'true') { throw 'Requires a disposable Windows CI runner.' }
$EvidenceDirectory = [IO.Path]::GetFullPath($EvidenceDirectory)
New-Item -ItemType Directory -Force $EvidenceDirectory | Out-Null
$hostExecutable = Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe'
$start = [Diagnostics.ProcessStartInfo]::new($hostExecutable)
$start.UseShellExecute = $false
$start.RedirectStandardOutput = $true
$start.RedirectStandardError = $true
foreach ($argument in @('-NoProfile','-NonInteractive','-STA','-ExecutionPolicy','Bypass','-File',
    (Join-Path $PSScriptRoot 'windows-gui/observe.ps1'),'-EvidenceDirectory',$EvidenceDirectory)) {
    $start.ArgumentList.Add($argument)
}
if ($SelfTest) {
    $start.ArgumentList.Add('-SelfTest')
} else {
    # Same checked source contract consumed independently by the verifier.
    $expectedTitle = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'windows-gui/expected-main-window-title.txt')).TrimEnd([char[]]"`r`n")
    if ([string]::IsNullOrWhiteSpace($expectedTitle) -or $expectedTitle -match '[\r\n]') { throw 'Invalid configured main-window title.' }
    foreach ($argument in @('-Stage',[IO.Path]::GetFullPath($Stage),'-SourceCommit',$SourceCommit,
        '-ExpectedMainWindowTitle',$expectedTitle)) { $start.ArgumentList.Add($argument) }
}
$child = [Diagnostics.Process]::new()
$child.StartInfo = $start
$clock = [Diagnostics.Stopwatch]::StartNew()
$timedOut = $false
$started = $false
$stdout = $null
$stderr = $null
try {
    if (-not $child.Start()) { throw 'Could not start Windows UIA observer.' }
    $started = $true
    $stdout = $child.StandardOutput.ReadToEndAsync()
    $stderr = $child.StandardError.ReadToEndAsync()
    while (-not $child.WaitForExit(1000)) {
        if ($clock.Elapsed.TotalSeconds -ge 180) {
            $timedOut = $true
            # The helper owns a KILL_ON_JOB_CLOSE job for WaveQuay. Also terminate
            # the exact helper process tree, including an assignment-failure race.
            $child.Kill($true)
            $child.WaitForExit()
            throw 'GUI observer exceeded 180 seconds; owned helper/process tree stopped.'
        }
    }
    if ($child.ExitCode -ne 0) { throw "GUI observer exited $($child.ExitCode); inspect retained evidence." }
} finally {
    if ($started) {
        if (-not $child.HasExited) { $child.Kill($true); $child.WaitForExit() }
        if ($null -ne $stdout) { $stdout.GetAwaiter().GetResult() | Set-Content (Join-Path $EvidenceDirectory 'helper-stdout.log') }
        if ($null -ne $stderr) { $stderr.GetAwaiter().GetResult() | Set-Content (Join-Path $EvidenceDirectory 'helper-stderr.log') }
        @{ helper_pid=$child.Id; helper_executable=$hostExecutable; timed_out=$timedOut; elapsed_seconds=$clock.Elapsed.TotalSeconds; exit_code=$child.ExitCode } |
            ConvertTo-Json | Set-Content (Join-Path $EvidenceDirectory 'watchdog.json')
    }
    $child.Dispose()
}
