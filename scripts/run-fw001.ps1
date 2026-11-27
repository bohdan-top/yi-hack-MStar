[CmdletBinding()]
param(
    [string]$DataRoot = 'E:\FirmwareBuild',
    [ValidateRange(1,64)][int]$CpuLimit = 6,
    [ValidateRange(1,128)][int]$MemoryGB = 8,
    [ValidateRange(1,1000)][int]$MinimumFreeGB = 40,
    [string]$Distro = 'FirmwareBuild',
    [string]$Inputs,
    [string]$LockFile,
    [string]$OutputRoot,
    [string]$LinuxStageRoot = '/var/tmp/fw001',
    [string]$ApprovedLockSha256,
    [string]$ApprovedEntrypoint,
    [string]$OfficialReferenceArchive,
    [string]$ReferenceDirectory,
    [string]$PrimaryOutput,
    [string]$RepeatOutput,
    [switch]$ValidateOnly,
    [switch]$Clean,
    [switch]$PreflightOnly
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot '../ci/fw001/host-checks.ps1')
$timer = [Diagnostics.Stopwatch]::StartNew()
$repo = Split-Path -Parent $PSScriptRoot
# Do not write a diagnostic to an unvalidated destination.
$root = Assert-Fw001DataPath $DataRoot $DataRoot
$drive = [IO.Path]::GetPathRoot($root)
if ($drive -ieq [IO.Path]::GetPathRoot($env:SystemRoot)) { throw 'SYSTEM_DATA_DRIVE_REJECTED' }
if (-not (Test-Path -LiteralPath $drive)) { throw 'DATA_DRIVE_UNAVAILABLE' }
if ($root.TrimEnd('\') -ieq $drive.TrimEnd('\')) { throw 'DATA_ROOT_MUST_BE_A_DIRECTORY' }
if (-not $Inputs) { $Inputs = Join-Path $root 'inputs' }
if (-not $LockFile) { $LockFile = Join-Path $root 'lock.json' }
if (-not $OutputRoot) { $OutputRoot = Join-Path $root 'outputs' }
$reportDir = Assert-Fw001DataPath (Join-Path $root 'reports') $root
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
$runId = [Guid]::NewGuid().ToString('N')
$reportPath = Join-Path $reportDir ("fw001-host-$runId.json")
$privateLog = Join-Path $reportDir ("private-fw001-host-$runId.log")
$system = [IO.DriveInfo]::new([IO.Path]::GetPathRoot($env:SystemRoot))
$free = [IO.DriveInfo]::new($drive).AvailableFreeSpace
$systemBefore = $system.AvailableFreeSpace
$savedTemp = @{ TEMP = $env:TEMP; TMP = $env:TMP; TMPDIR = $env:TMPDIR }
$status = 'BLOCKED'
$stage = 'storage'
$failureCode = $null
$runnerCode = $null
$exitCode = 1
$swapPlacement = 'not checked'
function Convert-WslPath([string]$Path) {
    $converted = & wsl.exe --distribution $Distro --exec wslpath -a -u $Path 2>> $privateLog
    if ($LASTEXITCODE -ne 0 -or -not $converted) { throw 'WSL_PATH_TRANSLATION_FAILED' }
    return ($converted | Select-Object -Last 1).Trim()
}
try {
    $Inputs = Assert-Fw001DataPath $Inputs $root
    $LockFile = Assert-Fw001DataPath $LockFile $root
    $OutputRoot = Assert-Fw001DataPath $OutputRoot $root
    if ($free -lt $MinimumFreeGB * 1GB) { throw 'INSUFFICIENT_DATA_DISK_SPACE' }
    $tempRoot = Assert-Fw001DataPath (Join-Path $root 'temp') $root
    New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
    $env:TEMP = $tempRoot; $env:TMP = $tempRoot; $env:TMPDIR = $tempRoot
    $stage = 'WSL distribution'
    Write-Host '[FW-001] Checking dedicated WSL2 distribution placement.'
    $null = Get-Command wsl.exe -ErrorAction Stop
    $distros = @(Get-ChildItem 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss' -ErrorAction SilentlyContinue |
        ForEach-Object { Get-ItemProperty $_.PSPath } |
        Where-Object { $_.DistributionName -eq $Distro })
    if ($distros.Count -ne 1 -or $distros[0].Version -ne 2) { throw 'WSL_DISTRO_MISSING' }
    $base = Assert-Fw001DataPath (ConvertFrom-Fw001WslBasePath $distros[0].BasePath) $root
    $vhd = Assert-Fw001DataPath (Join-Path $base 'ext4.vhdx') $root
    if (-not (Test-Path -LiteralPath $vhd -PathType Leaf)) { throw 'WSL_DATA_VHD_MISSING' }
    $stage = 'WSL swap approval'
    $swapPlacement = Assert-Fw001SwapPlacement (Join-Path $env:USERPROFILE '.wslconfig') $root
    $stage = 'input approval'
    if ($ApprovedLockSha256 -cnotmatch '^[a-f0-9]{64}$' -or $ApprovedEntrypoint -cnotmatch '^[a-f0-9]{40}$') {
        throw 'INDEPENDENT_INPUT_APPROVAL_REQUIRED'
    }
    if (-not (Test-Path -LiteralPath $LockFile -PathType Leaf) -or -not (Test-Path -LiteralPath $Inputs -PathType Container)) {
        throw 'APPROVED_PRIVATE_INPUTS_MISSING'
    }
    if ((Get-FileHash -LiteralPath $LockFile -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ApprovedLockSha256) {
        throw 'INPUT_LOCK_DIGEST_MISMATCH'
    }
    $stage = 'Linux runner'
    Write-Host '[FW-001] Starting the verified Linux runner; diagnostics remain private.'
    if (-not $OfficialReferenceArchive) { $OfficialReferenceArchive = Join-Path $root 'candidates/official-y203c_0.5.8.tgz' }
    $OfficialReferenceArchive = Assert-Fw001DataPath $OfficialReferenceArchive $root
    $entry = Convert-WslPath (Join-Path $repo 'ci/fw001/run.py')
    $argsList = @('python3','-B',$entry,
        '--inputs',(Convert-WslPath $Inputs),'--lock',(Convert-WslPath $LockFile),
        '--output-root',(Convert-WslPath $OutputRoot),'--report-dir',(Convert-WslPath $reportDir),
        '--stage-root',$LinuxStageRoot,'--cpus',"$CpuLimit",'--memory-gib',"$MemoryGB",
        '--min-free-gib',"$MinimumFreeGB",'--approved-lock-sha256',$ApprovedLockSha256,
        '--approved-entrypoint',$ApprovedEntrypoint,'--reference-archive',(Convert-WslPath $OfficialReferenceArchive))
    if ($ValidateOnly) {
        if ($Clean -or $PreflightOnly) { throw 'INCOMPATIBLE_VALIDATION_FLAGS' }
        $PrimaryOutput = Assert-Fw001DataPath $PrimaryOutput $root
        $RepeatOutput = Assert-Fw001DataPath $RepeatOutput $root
        $ReferenceDirectory = Assert-Fw001DataPath $ReferenceDirectory $root
        $entry = Convert-WslPath (Join-Path $repo 'ci/fw001/artifact_validation.py')
        $validationReport = Join-Path $reportDir ("fw001-validation-$runId.json")
        $argsList = @('python3','-B',$entry,(Convert-WslPath $PrimaryOutput),
            '--repeat',(Convert-WslPath $RepeatOutput),'--reference',(Convert-WslPath $ReferenceDirectory),
            '--reference-archive',(Convert-WslPath $OfficialReferenceArchive),'--report',(Convert-WslPath $validationReport),
            '--lock',(Convert-WslPath $LockFile),'--approved-entrypoint',$ApprovedEntrypoint,
            '--approved-lock-sha256',$ApprovedLockSha256,'--cpus',"$CpuLimit",'--memory-gib',"$MemoryGB")
    }
    if ($Clean) { $argsList += '--clean' }
    if ($PreflightOnly) { $argsList += '--preflight-only' }
    & wsl.exe --distribution $Distro --exec @argsList 2>&1 | ForEach-Object {
        $line = $_.ToString()
        Add-Content -LiteralPath $privateLog -Value $line -Encoding utf8
        $progress = Get-Fw001PublicProgress $line
        if ($progress) { Write-Host $progress }
    }
    $runnerCode = $LASTEXITCODE
    if ($runnerCode -ne 0) { throw 'LINUX_RUNNER_BLOCKED' }
    $status = if ($PreflightOnly) { 'PREFLIGHT PASS; full build NOT RUN' } elseif ($ValidateOnly) { 'ARTIFACT VALIDATION PASS' } else { 'BUILD AND VALIDATION PASS' }
    $exitCode = 0
} catch {
    # Arbitrary exception text can contain private paths, URLs or input data.
    $_ | Out-String | Add-Content -LiteralPath $privateLog -Encoding utf8
    $message = $_.Exception.Message
    $failureCode = if ($message -cmatch '^[A-Z][A-Z0-9_]+$') { $message } else { 'HOST_PREREQUISITE_ERROR' }
    Write-Warning ("FW-001 blocked at $stage ($failureCode). Inspect private diagnostics and docs/fw-001-local-build.md.")
} finally {
    foreach ($name in $savedTemp.Keys) { [Environment]::SetEnvironmentVariable($name, $savedTemp[$name], 'Process') }
    [ordered]@{
        schema = 1; status = $status; stage = $stage; failure_code = $failureCode
        runner_exit_code = $runnerCode; requested_cpu = $CpuLimit; requested_ram_gib = $MemoryGB
        elapsed_seconds = [math]::Round($timer.Elapsed.TotalSeconds,3)
        data_free_before_bytes = $free; data_free_after_bytes = [IO.DriveInfo]::new($drive).AvailableFreeSpace
        system_free_before_bytes = $systemBefore; system_free_after_bytes = $system.AvailableFreeSpace
        storage_scope = 'whole Windows volumes; unrelated activity may affect values'
        swap_placement = $swapPlacement; temporary_files = 'selected data root'
        peak_cpu_ram = 'not measured by Windows wrapper'; release_approved = $false
    } | ConvertTo-Json | Set-Content -LiteralPath $reportPath -Encoding utf8
}
exit $exitCode
