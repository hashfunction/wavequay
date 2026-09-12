# SPDX-License-Identifier: GPL-3.0-only
# Production observation boundary fixture; no synthetic UIA success claim.
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
Add-Type -Path @((Join-Path $PSScriptRoot 'ConsumerTreeRead.cs'),(Join-Path $PSScriptRoot 'ConsumerTreeReadTests.cs'))
[WaveQuayQualificationTests.ConsumerTreeReadTests]::Run()
