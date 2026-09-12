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
if (-not $SelfTest) {
    & python (Join-Path $PSScriptRoot 'consumer_audio.py') prepare --evidence $EvidenceDirectory --source-commit $SourceCommit
    if ($LASTEXITCODE -ne 0) { throw 'Could not exclusively prepare original consumer audio fixture.' }
}
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
. (Join-Path $PSScriptRoot 'windows-gui/display-modes.ps1')
$observe = {
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
        # Original startup deadline remains 90s inside GuiProbe. The separate
        # consumer driver has a 420s budget; allow bounded diagnostics/cleanup.
        $observerBudget = if ($SelfTest) { 180 } else { 600 }
        if ($clock.Elapsed.TotalSeconds -ge $observerBudget) {
            $timedOut = $true
            # The helper owns a KILL_ON_JOB_CLOSE job for WaveWeft. Also terminate
            # the exact helper process tree, including an assignment-failure race.
            $child.Kill($true)
            $child.WaitForExit()
            throw "GUI observer exceeded $observerBudget seconds; owned helper/process tree stopped."
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
    if (-not $SelfTest) {
        # Muse's Windows logger uses OutputDebugString and app-local files,
        # including Qt messages. Capture only logs under verified fresh roots,
        # after the owned helper/process tree is stopped, even when it failed.
        & python (Join-Path $PSScriptRoot 'collect_application_logs.py') --report (Join-Path $EvidenceDirectory 'gui-observations.json')
        if ($LASTEXITCODE -ne 0) { Write-Warning 'Application log capture was incomplete; inspect application-logs.json.' }
        & python (Join-Path $PSScriptRoot 'consumer_audio.py') finalize --evidence $EvidenceDirectory --source-commit $SourceCommit
        if ($LASTEXITCODE -ne 0) { throw 'Consumer file/profile validation or owned cleanup failed; inspect consumer-validation.json.' }
    }
}

}
if ($SelfTest) { & $observe }
else {
    $displayFile=Join-Path $EvidenceDirectory 'display-preparation.json'
    if (Test-Path -LiteralPath $displayFile) { throw 'Display evidence already exists and will not be replaced.' }
    $display=@{displayOriginalMode=$null;displayDevice=$null;displayRestoreRequired=$false;displayEvidence=$null;displayRestoreError=$null}
    Invoke-GuiDisplayScope $display $observe {
        $json=@{schema_version=1;source_commit=$SourceCommit;display=$display.displayEvidence;restore_error=$display.displayRestoreError} | ConvertTo-Json -Depth 12
        $stream=[IO.File]::Open($displayFile,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        try {$bytes=[Text.UTF8Encoding]::new($false).GetBytes($json);$stream.Write($bytes,0,$bytes.Length)} finally {$stream.Dispose()}
    }
}
