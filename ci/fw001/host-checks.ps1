# Shared, side-effect-free Windows path checks for the FW-001 host runner.
Set-StrictMode -Version Latest

function ConvertFrom-Fw001WslBasePath([string]$Path) {
    if ($Path.StartsWith('\\?\', [StringComparison]::Ordinal)) { return $Path.Substring(4) }
    return $Path
}

function Assert-Fw001DataPath([string]$Path, [string]$DataRoot) {
    # Relative, UNC and device paths can select another filesystem unexpectedly.
    if ($Path -notmatch '^[A-Za-z]:[\\/]' -or $DataRoot -notmatch '^[A-Za-z]:[\\/]') {
        throw 'PATH_NOT_LOCAL_ABSOLUTE'
    }
    $full = [IO.Path]::GetFullPath($Path)
    $root = [IO.Path]::GetFullPath($DataRoot).TrimEnd('\', '/')
    if ($full -ine $root -and -not $full.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'PATH_OUTSIDE_DATA_ROOT'
    }
    $ancestor = $full
    while ($ancestor) {
        if ((Test-Path -LiteralPath $ancestor) -and
            ((Get-Item -LiteralPath $ancestor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw 'PATH_REPARSE_POINT'
        }
        $parent = Split-Path -Parent $ancestor
        if ($parent -eq $ancestor) { break }
        $ancestor = $parent
    }
    return $full
}

function Assert-Fw001SwapPlacement([string]$ConfigPath, [string]$DataRoot) {
    # Read only. Applying a changed .wslconfig requires an explicitly approved VM restart.
    if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) { throw 'WSL_SWAP_APPROVAL_REQUIRED' }
    $section = ''
    $settings = @{}
    foreach ($line in Get-Content -LiteralPath $ConfigPath) {
        $line = $line.Trim()
        if (-not $line -or $line.StartsWith('#') -or $line.StartsWith(';')) { continue }
        if ($line -match '^\[([^\]]+)\]$') { $section = $Matches[1]; continue }
        if ($section -ieq 'wsl2' -and $line -match '^([^=]+)=(.*)$') {
            $key = $Matches[1].Trim()
            if ($settings.ContainsKey($key)) { throw 'WSL_CONFIG_DUPLICATE_KEY' }
            $settings[$key] = $Matches[2].Trim()
        }
    }
    if ($settings.ContainsKey('swap') -and $settings['swap'] -eq '0') { return 'disabled in configuration; effective VM state requires verification' }
    if (-not $settings.ContainsKey('swapFile')) { throw 'WSL_SWAP_APPROVAL_REQUIRED' }
    # WSL configuration uses doubled backslashes in Windows paths.
    $swapPath = $settings['swapFile'].Replace('\\', '\')
    $null = Assert-Fw001DataPath $swapPath $DataRoot
    return 'data-root swap configured; effective VM state requires verification'
}

function Get-Fw001PublicProgress([string]$Line) {
    # Only fixed messages authored by the reviewed runner may reach the console.
    $allowed = @('[FW-001] verify/cache inputs', '[FW-001] FW-008 private preflight',
        '[FW-001] primary offline build', '[FW-001] independent offline repeat build')
    if ($allowed -ccontains $Line) { return $Line }
}
