# SPDX-License-Identifier: GPL-3.0-only
# Managed query/ownership seam fixtures, not Windows product UI evidence.
$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
Add-Type -Path @((Join-Path $PSScriptRoot 'ConsumerTextReadback.cs'),(Join-Path $PSScriptRoot 'ConsumerTextReadbackTests.cs'))
[WaveQuayQualificationTests.ConsumerTextReadbackTests]::Run()
