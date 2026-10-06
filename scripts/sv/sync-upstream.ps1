<#
.SYNOPSIS
  Track upstream Meetily: fast-forward main, report what changed, optionally rebase custom.
.DESCRIPTION
  Default is report-only apart from fast-forwarding the pristine mirror branch 'main'.
  Use -Rebase to rebase 'custom' onto 'main'. Never pushes.
#>
[CmdletBinding()]
param([switch]$Rebase)

$ErrorActionPreference = 'Stop'
Set-Location (git rev-parse --show-toplevel)

if (git status --porcelain) { throw 'Working tree is dirty - commit or stash first.' }
$start = git branch --show-current

git fetch upstream --tags --prune
git fetch origin --prune

# Files we changed relative to upstream (what could conflict)
$ourFiles = @(git diff --name-only main...custom)

git checkout main | Out-Null
$before = git rev-parse HEAD
git merge --ff-only upstream/main
$after = git rev-parse HEAD

if ($before -eq $after) {
    Write-Host 'main already up to date with upstream.' -ForegroundColor Green
} else {
    Write-Host "`nNew upstream commits ($($before.Substring(0,7))..$($after.Substring(0,7))):" -ForegroundColor Cyan
    git log --oneline "$before..$after"
    $theirFiles = @(git diff --name-only $before $after)
    $overlap = $ourFiles | Where-Object { $theirFiles -contains $_ }
    if ($overlap) {
        Write-Host "`nUpstream touched files we also changed (expect conflicts):" -ForegroundColor Yellow
        $overlap
    } else {
        Write-Host "`nNo overlap with files changed on 'custom'." -ForegroundColor Green
    }
    if ($theirFiles -contains 'backend/whisper.cpp') {
        Write-Host 'whisper.cpp submodule pointer changed - review it.' -ForegroundColor Yellow
    }
}

$latest = git describe --tags --abbrev=0 upstream/main 2>$null
if ($latest) { Write-Host "Latest upstream tag: $latest" }

if ($Rebase) {
    git checkout custom | Out-Null
    git rebase main
    Write-Host "custom rebased onto main. Push with: git push --force-with-lease origin custom" -ForegroundColor Cyan
} elseif ($start -and $start -ne 'main') {
    git checkout $start | Out-Null
}
