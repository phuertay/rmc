# Download font-pull scripts from GitHub and run them (writes remarkable_onenote_fonts.zip).
#
#   $env:RM_PASS = '…'   # tablet SSH password; needs PuTTY plink+pscp on PATH
#   irm https://raw.githubusercontent.com/phuertay/rmc/cursor/ink-align-nudge-78e2/scripts/pull_remarkable_fonts_bootstrap.ps1 | iex
#
# Optional:
#   $env:RM_HOST = '10.11.99.1'
#   $env:RM_OUT  = "$env:USERPROFILE\tmp\device_fonts"
#   $env:RM_BRANCH = 'cursor/ink-align-nudge-78e2'   # or main later
#Requires -Version 5.1
$ErrorActionPreference = 'Stop'

$Branch = if ($env:RM_BRANCH) { $env:RM_BRANCH } else { 'cursor/ink-align-nudge-78e2' }
$Base = "https://raw.githubusercontent.com/phuertay/rmc/$Branch/scripts"
$OutDir = if ($env:RM_OUT) { $env:RM_OUT } else { Join-Path $env:USERPROFILE 'tmp\device_fonts' }
$Work = Join-Path $env:TEMP ("rm_fonts_pull_" + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Force -Path $Work, $OutDir | Out-Null

Write-Host "branch=$Branch  work=$Work  out=$OutDir"
foreach ($name in @('pull_remarkable_fonts.ps1', 'carve_remarkable_fonts.py')) {
    $url = "$Base/$name"
    $dest = Join-Path $Work $name
    Write-Host "get $url"
    Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
}

$pull = Join-Path $Work 'pull_remarkable_fonts.ps1'
& $pull -OutDir $OutDir
$zip = Join-Path $OutDir 'remarkable_onenote_fonts.zip'
if (Test-Path -LiteralPath $zip) {
    Write-Host "OK zip -> $zip"
    explorer.exe /select,"$zip"
} else {
    Write-Warning "zip missing — carve found no reMarkableSerifSmall/Sans under $OutDir\fonts"
    Write-Host "If you already have xochitl: `$env:RM_OUT='$OutDir'; & '$pull' -LocalBinary C:\path\to\xochitl -OutDir '$OutDir'"
}
