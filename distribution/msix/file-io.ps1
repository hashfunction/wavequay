# Copyright 2026 Trieflow LLC. MIT licensed; see PIPELINE-MIT.txt.
# Exact shared file/JSON helpers extracted from the reviewed installed collector.
# Retained original attribution: RETICLEQUAY-MIT.txt.
function Assert-WaveWeftNoRedirect([string]$Path) {
    $item=Get-Item -LiteralPath $Path -Force
    while($item){if($item.Attributes -band [IO.FileAttributes]::ReparsePoint){throw "Redirected path: $($item.FullName)"};$item=if($item -is [IO.DirectoryInfo]){$item.Parent}else{$item.Directory}}
}
function Get-WaveWeftFile([string]$Path) {
    Assert-WaveWeftNoRedirect $Path;$item=Get-Item -LiteralPath $Path -Force
    if($item.PSIsContainer){throw 'Expected regular file'}
    return [ordered]@{bytes=$item.Length;sha256=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
function Assert-WaveWeftFile([string]$Path,$Expected) {
    $actual=Get-WaveWeftFile $Path
    if($actual.bytes -ne $Expected.bytes -or $actual.sha256 -cne $Expected.sha256){throw "File changed: $Path"}
}
function Write-WaveWeftJson([string]$Path,$Value) {
    $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($Value | ConvertTo-Json -Depth 100))
    $stream=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
}
