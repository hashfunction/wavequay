# Copyright 2026 Trieflow LLC. MIT licensed; see PIPELINE-MIT.txt.
# Owned installation structure derives from the reviewed Scriblark/ReticleQuay
# qualification helpers; RETICLEQUAY-MIT.txt retains the original terms.
[CmdletBinding()]
param([string]$Package,[string]$PackageRecord,[string]$Release,[string]$NativeInput,
      [string]$SignTool,[string]$Output,[ValidateSet('qualification','store')][string]$IdentityMode='qualification',
      [switch]$LibraryOnly)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'file-io.ps1')

function Invoke-WaveWeftInstallCore([Collections.IDictionary]$Operations) {
    $normal=@('Preflight','SignCopy','Install','Consumer','Uninstall')
    $cleanup=@('RemoveOwnedPackage','RemoveCertificateTrust','RemoveCertificate','RemoveTemporary')
    foreach($name in $normal+$cleanup){if(-not $Operations.Contains($name) -or $Operations[$name] -isnot [scriptblock]){throw "Missing install operation: $name"}}
    $primary=$null;$errors=[Collections.Generic.List[string]]::new()
    try {foreach($name in $normal){& $Operations[$name] | Out-Host}}
    catch {$primary=$_.Exception.Message}
    finally {foreach($name in $cleanup){try{& $Operations[$name] | Out-Host}catch{$errors.Add("${name}: $($_.Exception.ToString())")}}}
    return [pscustomobject]@{passed=(-not $primary -and $errors.Count -eq 0);primary_error=$primary;cleanup_errors=@($errors)}
}
function Get-WaveWeftInstallIdentity([ValidateSet('qualification','store')][string]$Mode='qualification') {
    $value=[ordered]@{packageName='Trieflow.WaveQuay.Qualification';publisher='CN=WaveQuay-CI-Qualification';version='1.0.1.0';architecture='x64';applicationId='WaveQuay';executable='bin/WaveWeft.exe';deviceFamily='Windows.Desktop';minVersion='10.0.19041.0';maxVersionTested='10.0.26100.0';capability='runFullTrust'}
    if($Mode -ceq 'store'){$value.packageName='1659hashfunction.WaveQuay';$value.publisher='CN=B6A2631A-FD32-45CC-AE12-82466975F528';$value.familyName='1659hashfunction.WaveQuay_r3hxytd7jt6c4'}
    return $value
}
function Assert-WaveWeftRegistration($Candidate,$Identity,[string]$Family,[bool]$AddCompleted,[array]$Before) {
    if(-not $AddCompleted -or $Before.Count -ne 0){throw 'Registration cannot be owned without successful Add and empty preflight'}
    $publisherId=$Family.Substring($Identity.packageName.Length+1)
    $full=$Identity.packageName+'_1.0.1.0_x64__'+$publisherId
    if([string]$Candidate.Name -cne $Identity.packageName -or [string]$Candidate.Publisher -cne $Identity.publisher -or
       [string]$Candidate.Version -cne '1.0.1.0' -or [string]$Candidate.Architecture -cne 'X64' -or
       [string]$Candidate.PackageFullName -cne $full -or [string]$Candidate.PackageFamilyName -cne $Family){throw 'Installed registration differs from exact selected identity'}
}
function Invoke-WaveWeftNative([string]$Program,[string[]]$Arguments) {& $Program @Arguments;if($LASTEXITCODE -ne 0){throw "$Program exited $LASTEXITCODE"}}

function Invoke-WaveWeftInstall {
    $root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
    $identity=Get-WaveWeftInstallIdentity $IdentityMode
    $state=[ordered]@{output=$null;record=$null;temporary=$null;token=$null;signedCopy=$null;publicCertificate=$null;
        certificate=$null;trustAttempted=$false;installed=$null;installedByUs=$false;addCompleted=$false;
        family=$null;dataRoot=$null;dataAbsent=$false;before=@();residual=@();unsigned=$null;signed=$null;
        signTool=$null;gui=$null;flow=$null;validation=$null;cleanClose=$false;uninstalled=$false;
        profileGone=$false;trustGone=$false;certificateGone=$false;temporaryGone=$false;unsignedUnchanged=$false;runContext=$null}
    $ops=[ordered]@{}
    $ops.Preflight={
        if(-not $IsWindows -or $env:CI -cne 'true' -or $env:GITHUB_SHA -cnotmatch '^[0-9a-f]{40}$'){throw 'Requires exact-source disposable Windows CI'}
        $runText=Invoke-WaveWeftNative python @((Join-Path $PSScriptRoot 'run_context.py'),'--source-commit',$env:GITHUB_SHA)
        $state.runContext=$runText | ConvertFrom-Json
        foreach($path in @($Package,$PackageRecord,$Release,$NativeInput,$SignTool,$Output)){if(-not $path){throw 'All exact package/runtime/tool/output paths are required'}}
        if(Test-Path -LiteralPath $Output){throw 'Installation evidence output already exists'}
        Assert-WaveWeftNoRedirect ([IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($Output)))
        [void][IO.Directory]::CreateDirectory($Output);$state.output=[IO.Path]::GetFullPath($Output)
        $state.record=Get-Content -LiteralPath $PackageRecord -Raw | ConvertFrom-Json
        Invoke-WaveWeftNative python @((Join-Path $PSScriptRoot 'build_package.py'),'verify','--package',$Package,'--record',$PackageRecord,
            '--release',$Release,'--native-input',$NativeInput,'--source-commit',$env:GITHUB_SHA,'--identity-mode',$IdentityMode)
        if($state.record.identityMode -cne $IdentityMode -or $state.record.sourceCommit -cne $env:GITHUB_SHA -or
            $state.record.qualificationIdentityOnly -isnot [bool] -or $state.record.qualificationIdentityOnly -ne ($IdentityMode -ceq 'qualification') -or
            $state.record.storeIdentityUsed -isnot [bool] -or $state.record.storeIdentityUsed -ne ($IdentityMode -ceq 'store')){throw 'Wrong package mode/source flags'}
        if(@($state.record.identity.PSObject.Properties).Count -ne $identity.Count){throw 'Unexpected identity fields'}
        foreach($name in $identity.Keys){if($state.record.identity.$name -cne $identity[$name]){throw "Package selected identity differs: $name"}}
        foreach($name in @('signed','publicRelease','licenseClearanceClaimed','installationQualificationPassed')){
            if($state.record.$name -isnot [bool] -or $state.record.$name -ne $false){throw "Premature package claim: $name"}}
        $state.unsigned=Get-WaveWeftFile $Package
        $tool=(Resolve-Path -LiteralPath $SignTool).Path
        if([IO.Path]::GetFileName($tool) -ine 'signtool.exe' -or
            [IO.Path]::GetDirectoryName($tool) -ine [IO.Path]::GetDirectoryName($state.record.makeAppx.path) -or
            $state.record.makeAppx.sdkVersion -cne '10.0.26100.0'){throw 'SignTool must be the exact qualified SDK x64 sibling'}
        Assert-WaveWeftFile $state.record.makeAppx.path $state.record.makeAppx
        $state.signTool=[ordered]@{path=$tool;file=(Get-WaveWeftFile $tool)}
        if(-not ('WaveQuayQualification.PackageActivation' -as [type])){Add-Type -Path (Join-Path $PSScriptRoot '../windows-gui/PackageActivation.cs')}
        $state.family=[WaveQuayQualification.PackageActivation]::FamilyForMode($IdentityMode)
        $state.before=@(Get-AppxPackage -Name $identity.packageName | ForEach-Object {[string]$_.PackageFullName})
        if($state.before.Count){throw 'Existing same-name registration will not be replaced or removed'}
        $state.dataRoot=Join-Path ([Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData)) ('Packages/'+$state.family)
        if(Test-Path -LiteralPath $state.dataRoot){throw 'Existing package user data will not be adopted'}
        $state.dataAbsent=$true
    }.GetNewClosure()
    $ops.SignCopy={
        $state.token=[guid]::NewGuid().ToString()
        $state.temporary=Join-Path $env:RUNNER_TEMP ('waveweft-install-'+[guid]::NewGuid().ToString('N'))
        Assert-WaveWeftNoRedirect $env:RUNNER_TEMP
        New-Item -ItemType Directory -Path $state.temporary | Out-Null
        [IO.File]::WriteAllText((Join-Path $state.temporary '.owner'),$state.token,[Text.UTF8Encoding]::new($false))
        $state.signedCopy=Join-Path $state.temporary 'temporary-signed.msix'
        [IO.File]::Copy($Package,$state.signedCopy,$false)
        $state.publicCertificate=Join-Path $state.temporary 'public.cer'
        $state.certificate=New-SelfSignedCertificate -Type Custom -KeyUsage DigitalSignature -KeyExportPolicy NonExportable -KeySpec Signature `
            -CertStoreLocation 'Cert:\CurrentUser\My' -TextExtension @('2.5.29.37={text}1.3.6.1.5.5.7.3.3','2.5.29.19={text}') `
            -Subject $identity.publisher -FriendlyName 'WaveWeft ephemeral installed qualification' -NotAfter (Get-Date).AddHours(12)
        Export-Certificate -Cert $state.certificate -FilePath $state.publicCertificate | Out-Null
        $trust='Cert:\LocalMachine\TrustedPeople\'+$state.certificate.Thumbprint
        if(Test-Path -LiteralPath $trust){throw 'Generated certificate unexpectedly exists in trust store'}
        $state.trustAttempted=$true
        $imported=Import-Certificate -FilePath $state.publicCertificate -CertStoreLocation 'Cert:\LocalMachine\TrustedPeople'
        if($imported.Thumbprint -cne $state.certificate.Thumbprint){throw 'Imported certificate identity differs'}
        foreach($arguments in @(@('sign','/fd','SHA256','/sha1',$state.certificate.Thumbprint,'/s','My',$state.signedCopy),@('verify','/pa','/all','/v',$state.signedCopy))){
            Assert-WaveWeftFile $state.signTool.path $state.signTool.file
            Invoke-WaveWeftNative $state.signTool.path $arguments
        }
        Assert-WaveWeftFile $state.signTool.path $state.signTool.file
        $signature=Get-AuthenticodeSignature -LiteralPath $state.signedCopy
        if([string]$signature.Status -cne 'Valid' -or $signature.SignerCertificate.Thumbprint -cne $state.certificate.Thumbprint){throw 'Temporary signature differs from owned certificate'}
        Assert-WaveWeftFile $Package $state.unsigned
        $state.signed=Get-WaveWeftFile $state.signedCopy
    }.GetNewClosure()
    $ops.Install={
        Assert-WaveWeftFile $state.signedCopy $state.signed
        Add-AppxPackage -Path $state.signedCopy
        $state.addCompleted=$true
        $matches=@(Get-AppxPackage -Name $identity.packageName)
        if($matches.Count -ne 1){throw 'Expected one exact installed package registration'}
        Assert-WaveWeftRegistration $matches[0] $identity $state.family $state.addCompleted $state.before
        $state.installed=$matches[0];$state.installedByUs=$true
        Invoke-WaveWeftNative python @((Join-Path $PSScriptRoot 'build_package.py'),'installed','--package',$Package,'--record',$PackageRecord,
            '--release',$Release,'--native-input',$NativeInput,'--source-commit',$env:GITHUB_SHA,'--identity-mode',$IdentityMode,
            '--installed-root',[string]$state.installed.InstallLocation)
        [void][IO.Directory]::CreateDirectory($state.dataRoot);Assert-WaveWeftNoRedirect $state.dataRoot
        $stream=[IO.File]::Open((Join-Path $state.dataRoot '.waveweft-msix-owner'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        try{$bytes=[Text.UTF8Encoding]::new($false).GetBytes($state.token);$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
        $gui=Join-Path $state.output 'gui';[void][IO.Directory]::CreateDirectory($gui)
        Write-WaveWeftJson (Join-Path $gui 'installed-profile-claim.json') ([ordered]@{schemaVersion=1;sourceCommit=$env:GITHUB_SHA;
            identityMode=$IdentityMode;packageFamilyName=$state.family;packageFullName=[string]$state.installed.PackageFullName;
            dataRoot=$state.dataRoot;preinstallDataRootAbsent=$state.dataAbsent;token=$state.token})
        Write-WaveWeftJson (Join-Path $state.output 'installation-start.json') ([ordered]@{sourceCommit=$env:GITHUB_SHA;runContext=$state.runContext;identityMode=$IdentityMode;
            package_full_name=[string]$state.installed.PackageFullName;package_family_name=$state.family;install_location=[string]$state.installed.InstallLocation;
            preflight_package_full_names=@($state.before);add_completed=$state.addCompleted;installed_by_us=$state.installedByUs;
            package_data_root=$state.dataRoot;preinstall_data_root_absent=$state.dataAbsent})
    }.GetNewClosure()
    $ops.Consumer={
        $gui=Join-Path $state.output 'gui'
        & (Join-Path $PSScriptRoot '../invoke-windows-gui.ps1') -Stage ([string]$state.installed.InstallLocation) -EvidenceDirectory $gui `
            -SourceCommit $env:GITHUB_SHA -IdentityMode $IdentityMode -PackageFullName ([string]$state.installed.PackageFullName) -PackageFamilyName $state.family
        Invoke-WaveWeftNative python @((Join-Path $PSScriptRoot '../verify_gui_evidence.py'),'--report',(Join-Path $gui 'gui-observations.json'),
            '--inventory',(Join-Path $root 'build-evidence/stage-inventory.json'),'--source-commit',$env:GITHUB_SHA,
            '--installed-record',(Join-Path $state.output 'installation-start.json'))
        # Preserve JSON strings/timestamps exactly; deserialize snapshots only
        # for checks. The final receipt stores paths/hashes, not lossy nested JSON.
        $state.gui=Get-Content (Join-Path $gui 'gui-observations.json') -Raw | ConvertFrom-Json
        $state.flow=Get-Content (Join-Path $gui 'consumer-workflow.json') -Raw | ConvertFrom-Json
        $state.validation=Get-Content (Join-Path $gui 'consumer-validation.json') -Raw | ConvertFrom-Json
        if($state.validation.sourceCommit -cne $env:GITHUB_SHA -or $state.validation.verified -ne $true -or
            $state.validation.cleanup -ne $true -or $state.validation.errors.Count -ne 0 -or
            $state.validation.packageProfileCleanupDelegatedToUninstall -ne $true -or
            $state.flow.completed -ne $true -or $state.flow.normalCloseExitCode -ne 0 -or $state.gui.consumerClosedNormally -ne $true){throw 'Actual installed consumer/oracle/normal close is incomplete'}
        $state.cleanClose=$true
        Invoke-WaveWeftNative python @((Join-Path $PSScriptRoot 'build_package.py'),'installed','--package',$Package,'--record',$PackageRecord,
            '--release',$Release,'--native-input',$NativeInput,'--source-commit',$env:GITHUB_SHA,'--identity-mode',$IdentityMode,
            '--installed-root',[string]$state.installed.InstallLocation)
    }.GetNewClosure()
    $ops.Uninstall={
        if(-not $state.installedByUs -or -not $state.cleanClose){throw 'Normal close and exact installed ownership required'}
        Remove-AppxPackage -Package ([string]$state.installed.PackageFullName)
        if(@(Get-AppxPackage -Name $identity.packageName).Count){throw 'Registration remains after uninstall'}
        $state.uninstalled=$true
        $state.profileGone=-not (Test-Path -LiteralPath $state.dataRoot)
        if(-not $state.profileGone){throw 'Package data root remains after owned uninstall; retained for diagnosis'}
    }.GetNewClosure()
    $ops.RemoveOwnedPackage={
        if(-not $state.family){return}
        $remaining=@(Get-AppxPackage -Name $identity.packageName)
        if($state.installedByUs){
            $owned=@($remaining | Where-Object {[string]$_.PackageFullName -ceq [string]$state.installed.PackageFullName})
            if($owned.Count -eq 1){Remove-AppxPackage -Package ([string]$state.installed.PackageFullName)}
        }
        $state.residual=@(Get-AppxPackage -Name $identity.packageName | ForEach-Object {[string]$_.PackageFullName})
        if($state.residual.Count){throw 'Unowned or unresolved registration preserved'}
        if($state.installedByUs -and (Test-Path -LiteralPath $state.dataRoot)){throw 'Owned package data remains; no manual recursive deletion'}
    }.GetNewClosure()
    $ops.RemoveCertificateTrust={
        if(-not $state.certificate){$state.trustGone=$true;return}
        $path='Cert:\LocalMachine\TrustedPeople\'+$state.certificate.Thumbprint
        if($state.trustAttempted -and (Test-Path -LiteralPath $path)){
            $actual=Get-Item -LiteralPath $path
            if([Convert]::ToBase64String($actual.RawData) -cne [Convert]::ToBase64String($state.certificate.RawData)){throw 'Trusted certificate changed; preserved'}
            Remove-Item -LiteralPath $path
        }
        $state.trustGone=-not (Test-Path -LiteralPath $path)
        if(-not $state.trustGone){throw 'Certificate trust remains'}
    }.GetNewClosure()
    $ops.RemoveCertificate={
        if(-not $state.certificate){$state.certificateGone=$true;return}
        $path='Cert:\CurrentUser\My\'+$state.certificate.Thumbprint
        if(Test-Path -LiteralPath $path){
            $actual=Get-Item -LiteralPath $path
            if([Convert]::ToBase64String($actual.RawData) -cne [Convert]::ToBase64String($state.certificate.RawData)){throw 'Personal certificate changed; preserved'}
            Remove-Item -LiteralPath $path -DeleteKey
        }
        $state.certificateGone=-not (Test-Path -LiteralPath $path)
        if(-not $state.certificateGone){throw 'Personal certificate remains'}
    }.GetNewClosure()
    $ops.RemoveTemporary={
        if($state.unsigned){Assert-WaveWeftFile $Package $state.unsigned;$state.unsignedUnchanged=$true}
        if(-not $state.temporary){$state.temporaryGone=$true;return}
        Assert-WaveWeftNoRedirect $state.temporary
        if([IO.File]::ReadAllText((Join-Path $state.temporary '.owner')) -cne $state.token){throw 'Temporary directory owner changed'}
        foreach($item in Get-ChildItem -LiteralPath $state.temporary -Force){
            if($item.PSIsContainer -or $item.Name -cnotin @('.owner','temporary-signed.msix','public.cer')){throw 'Unknown temporary signing file; preserved'}
            Assert-WaveWeftNoRedirect $item.FullName
        }
        Remove-Item -LiteralPath $state.temporary -Recurse -Force
        $state.temporaryGone=-not (Test-Path -LiteralPath $state.temporary)
        if(-not $state.temporaryGone){throw 'Temporary signing files remain'}
    }.GetNewClosure()
    $core=Invoke-WaveWeftInstallCore $ops
    if($state.output){
        $evidence=[ordered]@{}
        foreach($name in @('gui-observations.json','consumer-workflow.json','consumer-validation.json','consumer-fixture-claim.json','installed-profile-claim.json','display-preparation.json','watchdog.json')){
            $path=Join-Path $state.output ('gui/'+$name);if(Test-Path -LiteralPath $path){$evidence['gui/'+$name]=Get-WaveWeftFile $path}
        }
        $start=Join-Path $state.output 'installation-start.json'
        if(Test-Path -LiteralPath $start){$evidence['installation-start.json']=Get-WaveWeftFile $start}
        $result=[ordered]@{schemaVersion=1;sourceCommit=$env:GITHUB_SHA;runId=$env:GITHUB_RUN_ID;runAttempt=$env:GITHUB_RUN_ATTEMPT;runContext=$state.runContext;
            identityMode=$IdentityMode;identity=$identity;installation_qualification_passed=[bool]$core.passed;primary_error=$core.primary_error;cleanup_errors=@($core.cleanup_errors);
            add_completed=$state.addCompleted;installed_by_us=$state.installedByUs;preflight_package_full_names=@($state.before);residual_package_full_names=@($state.residual);
            package_full_name=if($state.installed){[string]$state.installed.PackageFullName}else{$null};package_family_name=$state.family;
            install_location=if($state.installed){[string]$state.installed.InstallLocation}else{$null};package_data_root=$state.dataRoot;preinstall_data_root_absent=$state.dataAbsent;
            normal_close=$state.cleanClose;uninstall_verified=$state.uninstalled;package_profile_removed=$state.profileGone;certificate_trust_removed=$state.trustGone;
            personal_certificate_removed=$state.certificateGone;temporary_signing_files_removed=$state.temporaryGone;unsigned_package=$state.unsigned;unsigned_package_unchanged=$state.unsignedUnchanged;signed_copy=$state.signed;
            process_id=if($state.gui){$state.gui.processId}else{$null};evidence=$evidence;publicRelease=$false;licenseClearanceClaimed=$false}
        Write-WaveWeftJson (Join-Path $state.output 'installation-result.json') $result
    }
    if(-not $core.passed){throw "Installed WaveWeft workflow failed: $($core.primary_error); $($core.cleanup_errors -join '; ')"}
    Write-Output 'PASS: exact installed activation, complete consumer/oracle/normal close, uninstall and owned cleanup. Public/source release gates remain separate.'
}
if(-not $LibraryOnly){Invoke-WaveWeftInstall}
