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
    [switch]$Clean,
    [switch]$PreflightOnly
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$started = Get-Date
$root = [IO.Path]::GetFullPath($DataRoot)
$drive = [IO.Path]::GetPathRoot($root)
$repo = Split-Path -Parent $PSScriptRoot
if ($drive -ieq [IO.Path]::GetPathRoot($env:SystemRoot)) { throw 'Choose a non-system data disk.' }
if (-not (Test-Path -LiteralPath $drive)) { throw 'Data drive is unavailable.' }
if (-not $Inputs) { $Inputs = Join-Path $root 'inputs' }
if (-not $LockFile) { $LockFile = Join-Path $root 'lock.json' }
if (-not $OutputRoot) { $OutputRoot = Join-Path $root 'outputs' }
function Assert-DataPath([string]$Path) {
    $full = [IO.Path]::GetFullPath($Path)
    if ([IO.Path]::GetPathRoot($full) -ine $drive) { throw 'All private Windows paths must use the selected data drive.' }
    $p = $full
    while ($p -and (Test-Path -LiteralPath $p)) {
        if ((Get-Item -LiteralPath $p -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse points in private paths are not supported.' }
        $parent = Split-Path -Parent $p
        if ($parent -eq $p) { break }
        $p = $parent
    }
    # Check existing ancestors even for a new leaf.
    $p = $full
    while ($p) {
        if ((Test-Path -LiteralPath $p) -and ((Get-Item -LiteralPath $p -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Reparse points in private paths are not supported.' }
        $parent = Split-Path -Parent $p
        if ($parent -eq $p) { break }
        $p = $parent
    }
    return $full
}
$root = Assert-DataPath $root
$Inputs = Assert-DataPath $Inputs
$LockFile = Assert-DataPath $LockFile
$OutputRoot = Assert-DataPath $OutputRoot
$reportDir = Join-Path $root 'reports'
$null = Assert-DataPath $reportDir
$free = [IO.DriveInfo]::new($drive).AvailableFreeSpace
$system = [IO.DriveInfo]::new([IO.Path]::GetPathRoot($env:SystemRoot))
$systemBefore = $system.AvailableFreeSpace
if ($free -lt $MinimumFreeGB * 1GB) { throw 'Insufficient free space on data drive.' }
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
$report = Join-Path $reportDir ("fw001-host-" + [Guid]::NewGuid().ToString('N') + '.json')
$status = 'BLOCKED'
$stage = 'Windows/WSL prerequisites'
$exitCode = 1
function Invoke-Wsl([string[]]$Arguments) {
    & wsl.exe --distribution $Distro --exec @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'WSL stage failed; inspect private diagnostics and sanitized reports.' }
}
function Convert-WslPath([string]$Path) {
    $converted = & wsl.exe --distribution $Distro --exec wslpath -a -u $Path
    if ($LASTEXITCODE -ne 0 -or -not $converted) { throw 'WSL path translation failed.' }
    return ($converted | Select-Object -Last 1).Trim()
}
try {
    Write-Host '[FW-001] Checking dedicated WSL2 distribution placement.'
    $null = Get-Command wsl.exe -ErrorAction Stop
    $distros = @(Get-ChildItem 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss' |
        ForEach-Object { Get-ItemProperty $_.PSPath } |
        Where-Object { $_.DistributionName -eq $Distro })
    if ($distros.Count -ne 1 -or $distros[0].Version -ne 2) { throw 'Provision the dedicated WSL2 distribution first; no automatic installation or relocation.' }
    $base = $distros[0].BasePath -replace '^\\\\\?\\',''
    $base = Assert-DataPath $base
    $vhd = Join-Path $base 'ext4.vhdx'
    $null = Assert-DataPath $vhd
    if (-not (Test-Path -LiteralPath $vhd -PathType Leaf)) { throw 'Dedicated WSL2 ext4.vhdx not found on data disk.' }
    $stage = 'Approval prerequisites'
    if ($ApprovedLockSha256 -cnotmatch '^[a-f0-9]{64}$' -or $ApprovedEntrypoint -cnotmatch '^[a-f0-9]{40}$') {
        throw 'Supply independently approved lock SHA-256 and reviewed entrypoint commit. See docs/fw-001-local-build.md.'
    }
    if (-not (Test-Path -LiteralPath $LockFile -PathType Leaf) -or -not (Test-Path -LiteralPath $Inputs -PathType Container)) {
        throw 'Approved private lock and inputs are required.'
    }
    $stage = 'Linux runner'
    $entry = Convert-WslPath (Join-Path $repo 'ci/fw001/run.py')
    $argsList = @('python3','-B',$entry,
        '--inputs',(Convert-WslPath $Inputs),'--lock',(Convert-WslPath $LockFile),
        '--output-root',(Convert-WslPath $OutputRoot),'--report-dir',(Convert-WslPath $reportDir),
        '--stage-root',$LinuxStageRoot,'--cpus',"$CpuLimit",'--memory-gib',"$MemoryGB",
        '--min-free-gib',"$MinimumFreeGB",'--approved-lock-sha256',$ApprovedLockSha256,
        '--approved-entrypoint',$ApprovedEntrypoint)
    if ($Clean) { $argsList += '--clean' }
    if ($PreflightOnly) { $argsList += '--preflight-only' }
    Invoke-Wsl $argsList
    $status = 'Runner completed; inspect Linux report for validation status'
    $exitCode = 0
} catch {
    Write-Warning ("FW-001 blocked at " + $stage + '. ' + $_.Exception.Message)
} finally {
    [ordered]@{
        status = $status; stage = $stage; requested_cpu = $CpuLimit; requested_ram_gib = $MemoryGB
        elapsed_seconds = [math]::Round(((Get-Date)-$started).TotalSeconds,2)
        data_free_before_bytes = $free; data_free_after_bytes = [IO.DriveInfo]::new($drive).AvailableFreeSpace
        system_free_before_bytes = $systemBefore; system_free_after_bytes = $system.AvailableFreeSpace
        storage_scope = 'whole Windows volumes; unrelated activity may affect values'
        peak_cpu_ram = 'not measured by Windows wrapper'; release_approved = $false
    } | ConvertTo-Json | Set-Content -LiteralPath $report -Encoding UTF8
}
exit $exitCode
