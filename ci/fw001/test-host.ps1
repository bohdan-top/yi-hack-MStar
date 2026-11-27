[CmdletBinding()]
param([string]$TestRoot = 'E:\FirmwareBuild\temp')
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'host-checks.ps1')
$passed = 0
function Check([bool]$Condition, [string]$Name) {
    if (-not $Condition) { throw "FAILED: $Name" }
    $script:passed++
}
function Reject([scriptblock]$Action, [string]$Code) {
    $caught = $false
    try { & $Action | Out-Null } catch { $caught = $_.Exception.Message -ceq $Code }
    Check $caught $Code
}
$testParent = [IO.Path]::GetFullPath($TestRoot)
$testDir = Join-Path $testParent ('fw001-host-test-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testDir | Out-Null
try {
    Check ((ConvertFrom-Fw001WslBasePath '\\?\E:\FirmwareBuild\wsl') -ceq 'E:\FirmwareBuild\wsl') 'WSL extended path'
    Check ((ConvertFrom-Fw001WslBasePath 'E:\FirmwareBuild\wsl') -ceq 'E:\FirmwareBuild\wsl') 'WSL plain path'
    Check ((Assert-Fw001DataPath (Join-Path $testDir 'new leaf\input.json') $testDir) -ceq (Join-Path $testDir 'new leaf\input.json')) 'new leaf and spaces'
    Reject { Assert-Fw001DataPath ($testDir + '-sibling\input.json') $testDir } 'PATH_OUTSIDE_DATA_ROOT'
    Reject { Assert-Fw001DataPath (Join-Path $testDir '..\outside') $testDir } 'PATH_OUTSIDE_DATA_ROOT'
    Reject { Assert-Fw001DataPath 'relative\input' $testDir } 'PATH_NOT_LOCAL_ABSOLUTE'
    Reject { Assert-Fw001DataPath '\\server\share\input' $testDir } 'PATH_NOT_LOCAL_ABSOLUTE'
    Reject { Assert-Fw001DataPath '\\?\E:\input' $testDir } 'PATH_NOT_LOCAL_ABSOLUTE'
    $config = Join-Path $testDir '.wslconfig'
    Reject { Assert-Fw001SwapPlacement $config $testDir } 'WSL_SWAP_APPROVAL_REQUIRED'
    "[wsl2]`nswap=0" | Set-Content -LiteralPath $config
    Check ((Assert-Fw001SwapPlacement $config $testDir) -like 'disabled*') 'swap disabled'
    "[wsl2]`nswapFile=$($testDir.Replace('\', '\\'))\\swap.vhdx" | Set-Content -LiteralPath $config
    Check ((Assert-Fw001SwapPlacement $config $testDir) -like 'data-root*') 'swap on selected data root'
    "[other]`nswap=0" | Set-Content -LiteralPath $config
    Reject { Assert-Fw001SwapPlacement $config $testDir } 'WSL_SWAP_APPROVAL_REQUIRED'
    "[wsl2]`nswapFile=C:\\private\\swap.vhdx" | Set-Content -LiteralPath $config
    Reject { Assert-Fw001SwapPlacement $config $testDir } 'PATH_OUTSIDE_DATA_ROOT'
    "[wsl2]`nswap=0`nSwap=1GB" | Set-Content -LiteralPath $config
    Reject { Assert-Fw001SwapPlacement $config $testDir } 'WSL_CONFIG_DUPLICATE_KEY'
    $target = Join-Path $testDir 'target'
    $junction = Join-Path $testDir 'junction'
    New-Item -ItemType Directory -Path $target | Out-Null
    'retained' | Set-Content -LiteralPath (Join-Path $target 'sentinel')
    New-Item -ItemType Junction -Path $junction -Target $target | Out-Null
    try {
        Reject { Assert-Fw001DataPath (Join-Path $junction 'missing\leaf') $testDir } 'PATH_REPARSE_POINT'
    } finally {
        Remove-Item -LiteralPath $junction -Force
    }
    Check (Test-Path -LiteralPath (Join-Path $target 'sentinel')) 'junction target retained'
    Check ((Get-Fw001PublicProgress '[FW-001] primary offline build') -ceq '[FW-001] primary offline build') 'reviewed progress visible'
    Check ($null -eq (Get-Fw001PublicProgress '[FW-001] private-marker')) 'arbitrary progress hidden'
    Check ($null -eq (Get-Fw001PublicProgress "[FW-001] primary offline build`nprivate-marker")) 'multiline progress hidden'
    $runner = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../scripts/run-fw001.ps1'))
    $shell = Join-Path $PSHOME 'pwsh.exe'
    $result = & $shell -NoProfile -File $runner -DataRoot $testDir -Inputs 'C:\private-marker\inputs' 2>&1 | Out-String
    Check ($LASTEXITCODE -eq 1) 'outside input path exits nonzero'
    Check (-not $result.Contains('private-marker')) 'console diagnostics sanitized'
    $reports = @(Get-ChildItem -LiteralPath (Join-Path $testDir 'reports') -Filter 'fw001-host-*.json')
    Check ($reports.Count -eq 1) 'one sanitized failure report'
    $report = Get-Content -Raw -LiteralPath $reports[0].FullName | ConvertFrom-Json
    Check ($report.failure_code -ceq 'PATH_OUTSIDE_DATA_ROOT') 'failure report code'
    Check (-not (Get-Content -Raw -LiteralPath $reports[0].FullName).Contains('private-marker')) 'report sanitization'
    $missingDistro = 'FW001-Missing-' + [Guid]::NewGuid().ToString('N')
    $result = & $shell -NoProfile -File $runner -DataRoot $testDir -Distro $missingDistro -CpuLimit 6 -MemoryGB 8 2>&1 | Out-String
    Check ($LASTEXITCODE -eq 1) 'missing distro exits nonzero'
    $reports = @(Get-ChildItem -LiteralPath (Join-Path $testDir 'reports') -Filter 'fw001-host-*.json' | Sort-Object LastWriteTimeUtc)
    $report = Get-Content -Raw -LiteralPath $reports[-1].FullName | ConvertFrom-Json
    Check ($report.failure_code -ceq 'WSL_DISTRO_MISSING') 'missing distro fails before WSL startup'
    Check ($report.requested_cpu -eq 6 -and $report.requested_ram_gib -eq 8) 'requested limits recorded'
    Check ($report.elapsed_seconds -ge 0 -and $report.data_free_before_bytes -gt 0) 'measured host evidence'
    Write-Host "PASS: $passed host checks; task-owned test cleanup only."
} finally {
    # Validate the absolute target and reject a replaced test root before recursive deletion.
    $full = Assert-Fw001DataPath $testDir $testParent
    if ((Split-Path -Parent $full) -ine $testParent -or (Split-Path -Leaf $full) -notmatch '^fw001-host-test-[a-f0-9]{32}$') {
        throw 'UNSAFE_TEST_CLEANUP_TARGET'
    }
    Remove-Item -LiteralPath $full -Recurse -Force
}
