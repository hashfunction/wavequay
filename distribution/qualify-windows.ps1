$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not $IsWindows -or $env:CI -ne 'true') { throw 'Requires a disposable Windows CI runner.' }
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force build-evidence | Out-Null
function Invoke-Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program exited $LASTEXITCODE" }
}
$expectedPins = @{ muse='3c5512eb8ee1a863a6123e62bd75a6ab55045752'; muse_deps='b915e6703a2a9839b2a98d4ca2468a88e361929f'; '.ci-googletest'='063de7e9578f82b369302001269680b4b1553359' }
foreach ($path in $expectedPins.Keys) {
    if ((git -C $path rev-parse HEAD) -ne $expectedPins[$path]) { throw "Dependency pin differs: $path" }
}
$submodules = @(git submodule status --recursive)
if ($LASTEXITCODE -ne 0 -or @($submodules | Where-Object { -not $_.StartsWith(' ') }).Count) { throw 'Submodules are missing or changed.' }
$submodules | Set-Content build-evidence/submodules.txt
cmake --version | Set-Content build-evidence/cmake.txt
qmake -query | Set-Content build-evidence/qt.txt
$env:EXTDEPS_CACHE = Join-Path (Get-Location) '.ci-dependency-cache'
$sourceCommit = (git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $sourceCommit -notmatch '^[0-9a-f]{40}$') { throw 'Cannot identify exact source revision.' }
$result = @{ source_commit=$sourceCommit; built=$false; native_recipe_tests=$false; staged=$false;
    windows_main_window_verified=$false; audio_device_tests=$false; native_export_tests=$false;
    source_license_closure=$false; submitted=$false }
try {
    Invoke-Checked python @('-m','unittest','discover','-s','distribution/tests','-v')
    & ./distribution/invoke-windows-gui.ps1 -SelfTest -EvidenceDirectory (Join-Path (Get-Location) 'build-evidence/gui-helper')
    Invoke-Checked cmake @('-S','.ci-googletest','-B','build-gtest','-G','Ninja','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_STANDARD=17','-Dgtest_force_shared_crt=ON','-DBUILD_GMOCK=ON',"-DCMAKE_INSTALL_PREFIX=$(Get-Location)/.ci-gtest-install")
    Invoke-Checked cmake @('--build','build-gtest','--parallel','2')
    Invoke-Checked cmake @('--install','build-gtest')
    $env:CMAKE_PREFIX_PATH = "$(Get-Location)/.ci-gtest-install;$env:CMAKE_PREFIX_PATH"
    Invoke-Checked cmake @('-S','src/importexport/export/tests','-B','build-recipe-tests','-G','Ninja','-DCMAKE_BUILD_TYPE=Release')
    Copy-Item build-recipe-tests/wavequay-test-dependencies.json build-evidence/
    Invoke-Checked cmake @('--build','build-recipe-tests','--parallel','2')
    Invoke-Checked ctest @('--test-dir','build-recipe-tests','--timeout','60','--output-on-failure','--output-junit',"$(Get-Location)/build-evidence/recipe-tests.xml")
    $result.native_recipe_tests = $true
    Invoke-Checked cmake @('-C','buildscripts/ci/windows/wavequay-release.cmake','-S','.','-B','build','-G','Ninja','-DMUSE_ENABLE_UNIT_TESTS=OFF','-DAU_BUILD_EXPORT_TESTS=OFF',"-DCMAKE_INSTALL_PREFIX=$(Get-Location)/stage")
    Invoke-Checked cmake @('--build','build','--parallel','2')
    $result.built = $true
    Invoke-Checked cmake @('--install','build')
    $result.staged = $true
    Get-ChildItem stage -Recurse -File | ForEach-Object {
        @{ path=[IO.Path]::GetRelativePath((Join-Path (Get-Location) 'stage'), $_.FullName); bytes=$_.Length; sha256=(Get-FileHash $_.FullName -Algorithm SHA256).Hash }
    } | ConvertTo-Json -Depth 3 | Set-Content build-evidence/stage-inventory.json
    $result | ConvertTo-Json | Set-Content build-evidence/result.json
    & ./distribution/invoke-windows-gui.ps1 -SourceCommit $sourceCommit
    Invoke-Checked python @('distribution/verify_gui_evidence.py','--report','build-evidence/gui/gui-observations.json',
        '--inventory','build-evidence/stage-inventory.json','--source-commit',$sourceCommit)
    $result.windows_main_window_verified = $true
} finally {
    $result | ConvertTo-Json | Set-Content build-evidence/result.json
    Get-ChildItem .qt-archives,.ci-dependency-cache -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Extension -in @('.zip','.7z','.gz','.xz','.bz2','.zst','.tar') } | ForEach-Object {
        @{ path=[IO.Path]::GetRelativePath((Get-Location).Path, $_.FullName); bytes=$_.Length; sha256=(Get-FileHash $_.FullName -Algorithm SHA256).Hash }
    } | ConvertTo-Json -Depth 3 | Set-Content build-evidence/dependency-downloads.json
}
