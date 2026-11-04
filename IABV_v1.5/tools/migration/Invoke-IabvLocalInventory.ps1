[CmdletBinding()]
param(
    [string[]]$ScanRoots = @(
        "C:\Python",
        "C:\Temp",
        (Join-Path $env:USERPROFILE "source\repos"),
        (Join-Path $env:USERPROFILE "Documents\GitHub")
    ),
    [string]$OutputRoot = (Join-Path $env:USERPROFILE "Desktop\IABV-Migration-Audit"),
    [switch]$RunFsck
)

# Read-only inventory. This script does NOT clone, fetch, push, clean, reset,
# delete, archive, copy repository files, inspect file contents, or read secrets.
# It writes only a JSON metadata report under OutputRoot.

$ErrorActionPreference = "Continue"

function Add-UniquePath {
    param(
        [System.Collections.Generic.List[string]]$List,
        [string]$Value
    )
    if (-not [string]::IsNullOrWhiteSpace($Value)) {
        $resolved = [System.IO.Path]::GetFullPath($Value)
        if (-not $List.Contains($resolved)) {
            $List.Add($resolved)
        }
    }
}

function Invoke-GitCapture {
    param(
        [string]$RepositoryPath,
        [string[]]$GitArguments
    )
    $output = @()
    $exitCode = -1
    try {
        $output = @(& git -C $RepositoryPath @GitArguments 2>&1 | ForEach-Object { $_.ToString() })
        $exitCode = $LASTEXITCODE
    }
    catch {
        $output = @($_.Exception.Message)
    }
    [PSCustomObject]@{
        Arguments = @($GitArguments)
        ExitCode  = $exitCode
        Output    = $output
    }
}

function Get-SafeRemoteInventory {
    param([string]$RepositoryPath)
    $namesResult = Invoke-GitCapture -RepositoryPath $RepositoryPath -GitArguments @("remote")
    $items = @()
    foreach ($name in $namesResult.Output) {
        if ([string]::IsNullOrWhiteSpace($name)) { continue }
        $urlResult = Invoke-GitCapture -RepositoryPath $RepositoryPath -GitArguments @("remote", "get-url", "$name")
        foreach ($rawUrl in $urlResult.Output) {
            # Redact URL user-info and query strings; never persist embedded tokens.
            $safeUrl = $rawUrl -replace "(?i)(https?://)[^/@]+@", '$1<redacted>@'
            $safeUrl = $safeUrl -replace "\?.*$", "?<redacted>"
            $items += [PSCustomObject]@{
                Name = $name
                Url = $safeUrl
                ReadExitCode = $urlResult.ExitCode
            }
        }
    }
    $items
}

function Find-GitRepositories {
    param([string[]]$Roots)
    $found = [System.Collections.Generic.List[string]]::new()
    $visited = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )

    foreach ($root in $Roots) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        $rootItem = Get-Item -LiteralPath $root -ErrorAction SilentlyContinue
        if (-not $rootItem -or -not $rootItem.PSIsContainer) { continue }

        $pending = [System.Collections.Generic.Stack[string]]::new()
        $pending.Push($rootItem.FullName)

        while ($pending.Count -gt 0) {
            $current = $pending.Pop()
            if (-not $visited.Add($current)) { continue }

            $gitMarker = Join-Path $current ".git"
            if (Test-Path -LiteralPath $gitMarker) {
                Add-UniquePath -List $found -Value $current
                # Stop descending into a repository; this avoids scanning .git/objects.
                continue
            }

            $children = @(Get-ChildItem -LiteralPath $current -Directory -Force -ErrorAction SilentlyContinue)
            foreach ($child in $children) {
                if (($child.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                    continue
                }
                $pending.Push($child.FullName)
            }
        }
    }
    @($found)
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git was not found on PATH. Install/enable Git for Windows, then rerun this read-only inventory."
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$reportDirectory = Join-Path $OutputRoot ("IABV-Migration-Audit-" + $stamp)
New-Item -ItemType Directory -Path $reportDirectory -Force | Out-Null

$repositories = Find-GitRepositories -Roots $ScanRoots
$repoReports = @()

foreach ($repositoryPath in $repositories) {
    $repoReports += [PSCustomObject]@{
        Path = $repositoryPath
        TopLevel = Invoke-GitCapture $repositoryPath @("rev-parse", "--show-toplevel")
        CommonGitDir = Invoke-GitCapture $repositoryPath @("rev-parse", "--git-common-dir")
        Head = Invoke-GitCapture $repositoryPath @("rev-parse", "HEAD")
        CurrentBranch = Invoke-GitCapture $repositoryPath @("branch", "--show-current")
        Status = Invoke-GitCapture $repositoryPath @("status", "--porcelain=v2", "--branch")
        LocalAndRemoteBranches = Invoke-GitCapture $repositoryPath @("branch", "-avv")
        Tags = Invoke-GitCapture $repositoryPath @("tag", "--list")
        Refs = Invoke-GitCapture $repositoryPath @(
            "for-each-ref", "--format=%(refname) %(objectname) %(objecttype)"
        )
        Reflogs = Invoke-GitCapture $repositoryPath @("reflog", "--all", "--date=iso")
        Remotes = Get-SafeRemoteInventory $repositoryPath
        Worktrees = Invoke-GitCapture $repositoryPath @("worktree", "list", "--porcelain")
        Stashes = Invoke-GitCapture $repositoryPath @("stash", "list")
        ObjectStore = Invoke-GitCapture $repositoryPath @("count-objects", "-vH")
        UntrackedPaths = Invoke-GitCapture $repositoryPath @("ls-files", "--others", "--exclude-standard")
        IgnoredPaths = Invoke-GitCapture $repositoryPath @("ls-files", "--others", "-i", "--exclude-standard")
        LfsFiles = Invoke-GitCapture $repositoryPath @("lfs", "ls-files", "--all")
        Submodules = Invoke-GitCapture $repositoryPath @("submodule", "status", "--recursive")
        Fsck = if ($RunFsck) {
            Invoke-GitCapture $repositoryPath @("fsck", "--full", "--no-reflogs", "--unreachable")
        } else {
            [PSCustomObject]@{
                Arguments = @("fsck", "--full", "--no-reflogs", "--unreachable")
                ExitCode = $null
                Output = @("NOT_RUN: rerun with -RunFsck after reviewing expected runtime.")
            }
        }
    }
}

$report = [PSCustomObject]@{
    TaskId = "IABV_REPOSITORY_MIGRATION_AND_RECOVERY_R1_20261104"
    GeneratedAtLocal = (Get-Date).ToString("o")
    GeneratedAtUtc = (Get-Date).ToUniversalTime().ToString("o")
    ComputerName = $env:COMPUTERNAME
    ScanRoots = $ScanRoots
    ExistingScanRoots = @($ScanRoots | Where-Object { Test-Path -LiteralPath $_ })
    RepositoryCount = $repositories.Count
    Repositories = $repoReports
    SafetyBoundary = @(
        "Read-only Git metadata inventory; no source file contents are read.",
        "Remote URL user-info and query strings are redacted in this report.",
        "No fetch, push, clone, bundle, LFS download, copy, delete, clean, reset, prune or upload is performed.",
        "Untracked/ignored paths and local refs may reveal sensitive filenames; keep this report private and sanitize before sharing.",
        "This is not a backup and does not prove LFS object availability or local database recoverability."
    )
}

$jsonPath = Join-Path $reportDirectory "local-git-inventory.json"
$report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$summaryPath = Join-Path $reportDirectory "README.txt"
@(
    "IABV local migration inventory",
    "Generated UTC: $($report.GeneratedAtUtc)",
    "Repositories discovered: $($report.RepositoryCount)",
    "Output: $jsonPath",
    "",
    "This report is a read-only inventory, not a backup.",
    "Do not upload raw reports without reviewing and sanitizing paths and remote names.",
    "No repository contents, credentials, cookies, database contents or secret values were read."
) | Set-Content -LiteralPath $summaryPath -Encoding UTF8

Write-Host "Inventory complete. Repositories found: $($report.RepositoryCount)"
Write-Host "Report: $jsonPath"
Write-Host "Summary: $summaryPath"
Write-Host "No repository was modified and no data was uploaded."
