# Pull reMarkable fonts + fontconfig (+ optional xochitl size hints) over SSH.
#
# Run from a PC that can reach the tablet (USB 10.11.99.1 or Wi-Fi IP):
#   .\scripts\pull_remarkable_fonts.ps1
#   $env:RM_HOST='192.168.1.50'; .\scripts\pull_remarkable_fonts.ps1
#
# Needs: OpenSSH client (ssh, scp) — Windows Optional Feature, or Git for Windows.
# Auth: SSH key (preferred), or type password when prompted.
# Enable SSH in tablet Settings.
#Requires -Version 5.1
$ErrorActionPreference = 'Stop'

$HostName = if ($env:RM_HOST) { $env:RM_HOST } else { '10.11.99.1' }
$User     = if ($env:RM_USER) { $env:RM_USER } else { 'root' }
$OutRoot  = if ($env:RM_OUT)  { $env:RM_OUT }  else { 'tests/expected/device_fonts' }
$Target   = "${User}@${HostName}"
$SshOpts  = @('-o', 'StrictHostKeyChecking=accept-new', '-o', 'ConnectTimeout=8')

function Invoke-RmSsh {
    param([Parameter(Mandatory)][string]$RemoteCommand)
    & ssh @SshOpts $Target $RemoteCommand
    if ($LASTEXITCODE -ne 0) {
        throw "ssh failed ($LASTEXITCODE): $RemoteCommand"
    }
}

function Invoke-RmScp {
    param(
        [Parameter(Mandatory)][string]$Source,
        [Parameter(Mandatory)][string]$Destination,
        [switch]$Recurse
    )
    $scpArgs = @() + $SshOpts
    if ($Recurse) { $scpArgs += '-r' }
    $scpArgs += @($Source, $Destination)
    & scp @scpArgs
}

# Resolve OUT relative to repo root if script lives in scripts/
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not [System.IO.Path]::IsPathRooted($OutRoot)) {
    $OutRoot = Join-Path $RepoRoot $OutRoot
}

$Meta = Join-Path $OutRoot 'meta'
$Fonts = Join-Path $OutRoot 'fonts'
$FcOut = Join-Path $OutRoot 'fontconfig\etc-fonts'
New-Item -ItemType Directory -Force -Path $Meta, $Fonts, $FcOut | Out-Null

Write-Host "-> $Target  out=$OutRoot"

# Device identity
$deviceCmd = 'uname -a; cat /etc/os-release 2>/dev/null | head -5; ls /usr/bin/xochitl 2>/dev/null; which fc-list fc-match 2>/dev/null'
Invoke-RmSsh $deviceCmd | Tee-Object -FilePath (Join-Path $Meta 'device.txt')

# Font inventory
& ssh @SshOpts $Target 'fc-list : family file | sort' |
    Out-File -Encoding utf8 (Join-Path $Meta 'fc-list.txt')

$fcMatchRemote = @'
for f in "EB Garamond" "Noto Sans" "Noto Serif" "Noto Sans Mono" serif sans-serif; do
  echo "=== $f ==="
  fc-match -v "$f" 2>/dev/null | egrep "family:|file:|style:|slant:|weight:|size:" || fc-match "$f"
done
'@
& ssh @SshOpts $Target $fcMatchRemote |
    Out-File -Encoding utf8 (Join-Path $Meta 'fc-match.txt')

# fontconfig index + copy
$fcIndex = 'ls -la /etc/fonts /usr/share/fontconfig 2>/dev/null; find /etc/fonts /usr/share/fontconfig -type f 2>/dev/null | head -200'
& ssh @SshOpts $Target $fcIndex |
    Out-File -Encoding utf8 (Join-Path $Meta 'fontconfig-index.txt')
try {
    Invoke-RmScp -Recurse -Source "${Target}:/etc/fonts/." -Destination $FcOut
} catch {
    Write-Warning "scp /etc/fonts failed: $_"
}

# Font file list + download each
$findFonts = 'find /usr/share/fonts /home/root/.local/share/fonts /usr/lib/fonts -type f \( -name "*.ttf" -o -name "*.otf" -o -name "*.ttc" \) 2>/dev/null'
$fontListPath = Join-Path $Meta 'font-files.txt'
& ssh @SshOpts $Target $findFonts | Out-File -Encoding utf8 $fontListPath

Get-Content $fontListPath | ForEach-Object {
    $remote = $_.Trim()
    if (-not $remote) { return }
    $base = Split-Path -Leaf $remote
    $dirKey = ((Split-Path -Parent $remote) -replace '/', '_')
    $destDir = Join-Path $Fonts $dirKey
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null
    try {
        Invoke-RmScp -Source "${Target}:$remote" -Destination (Join-Path $destDir $base)
    } catch {
        Write-Warning "skip $remote : $_"
    }
}

# xochitl font-related strings
$xoStrings = 'strings /usr/bin/xochitl 2>/dev/null | egrep -i "garamond|noto|heading|font.?size|FontSize|pointSize|textStyle|ParagraphStyle|EBGaramond" | sort -u | head -400'
& ssh @SshOpts $Target $xoStrings |
    Out-File -Encoding utf8 (Join-Path $Meta 'xochitl-font-strings.txt')

# packages
$opkg = 'opkg list-installed 2>/dev/null | egrep -i "font|freetype|harfbuzz|qt" | head -80'
& ssh @SshOpts $Target $opkg |
    Out-File -Encoding utf8 (Join-Path $Meta 'opkg-fonts-qt.txt')

Write-Host "done -> $OutRoot"
Get-ChildItem $Meta | Select-Object Name, Length
if (Test-Path $Fonts) {
    $bytes = (Get-ChildItem -Recurse -File $Fonts -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum).Sum
    Write-Host ("fonts ~{0:N1} MB" -f ($bytes / 1MB))
}
