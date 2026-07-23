# Download font-pull scripts from GitHub and run them.
# Writes %USERPROFILE%\tmp\device_fonts\install_me\ with installable .ttf files.
#
# Expects $env:RM_PASS already set (tablet SSH). Needs PuTTY plink+pscp on PATH.
#
#   irm https://raw.githubusercontent.com/phuertay/rmc/cursor/ink-align-nudge-78e2/scripts/pull_remarkable_fonts_bootstrap.ps1 | iex
#
# Optional: $env:RM_HOST, $env:RM_OUT, $env:RM_BRANCH, $env:RM_XOCHITL
#Requires -Version 5.1
$ErrorActionPreference = 'Stop'

$LocalBinary = if ($env:RM_XOCHITL) { $env:RM_XOCHITL } else { '' }
if ([string]::IsNullOrWhiteSpace($LocalBinary) -and [string]::IsNullOrWhiteSpace($env:RM_PASS)) {
    throw @"
RM_PASS not set. Set it in this session first, then re-run (do not paste the password into the command):

  `$env:RM_PASS = '…'   # once per shell
  irm https://raw.githubusercontent.com/phuertay/rmc/cursor/ink-align-nudge-78e2/scripts/pull_remarkable_fonts_bootstrap.ps1 | iex

Or carve only: `$env:RM_XOCHITL = 'C:\path\to\xochitl'
"@
}
if (-not [string]::IsNullOrWhiteSpace($env:RM_PASS)) {
    Write-Host ("RM_PASS set (len={0})" -f $env:RM_PASS.Length)
}

$Branch = if ($env:RM_BRANCH) { $env:RM_BRANCH } else { 'cursor/ink-align-nudge-78e2' }
$Base = "https://raw.githubusercontent.com/phuertay/rmc/$Branch/scripts"
$OutDir = if ($env:RM_OUT) { $env:RM_OUT } else { Join-Path $env:USERPROFILE 'tmp\device_fonts' }
$Work = Join-Path $env:TEMP ("rm_fonts_pull_" + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Force -Path $Work, $OutDir | Out-Null

Write-Host "branch=$Branch  work=$Work  out=$OutDir"
foreach ($name in @('pull_remarkable_fonts.ps1', 'carve_remarkable_fonts.py', 'woff2_to_ttf.py')) {
    $url = "$Base/$name"
    $dest = Join-Path $Work $name
    Write-Host "get $url"
    Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
}

$pull = Join-Path $Work 'pull_remarkable_fonts.ps1'
if ($LocalBinary) {
    & $pull -OutDir $OutDir -LocalBinary $LocalBinary
} else {
    & $pull -OutDir $OutDir
}
$install = Join-Path $OutDir 'install_me'
if ((Test-Path -LiteralPath $install) -and @(Get-ChildItem $install -Filter *.ttf -EA SilentlyContinue).Count -gt 0) {
    Write-Host "OK fonts -> $install"
    explorer.exe $install
} else {
    Write-Warning "no valid TTFs in $install — check carve/convert logs above"
}
