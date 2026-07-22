# Pull reMarkable fonts + fontconfig (+ optional xochitl size hints) over SSH.
#
# Run from a PC that can reach the tablet (USB 10.11.99.1 or Wi-Fi IP):
#   .\scripts\pull_remarkable_fonts.ps1
#   $env:RM_HOST='192.168.1.50'; $env:RM_PASS='your-ssh-password'; .\scripts\pull_remarkable_fonts.ps1
#
# Password (pick one):
#   $env:RM_PASS = '...'          # non-interactive (needs PuTTY plink/pscp on PATH)
#   -Password '...'               # same, as parameter
#   (omit)                        # OpenSSH prompts interactively, or use an SSH key
#
# Needs: OpenSSH (ssh/scp) and/or PuTTY (plink/pscp) when RM_PASS is set.
# Enable SSH in tablet Settings.
#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Password = $env:RM_PASS
)
$ErrorActionPreference = 'Stop'

$HostName = if ($env:RM_HOST) { $env:RM_HOST } else { '10.11.99.1' }
$User     = if ($env:RM_USER) { $env:RM_USER } else { 'root' }
$OutRoot  = if ($env:RM_OUT)  { $env:RM_OUT }  else { 'tests/expected/device_fonts' }
$Target   = "${User}@${HostName}"
$SshOpts  = @('-o', 'StrictHostKeyChecking=accept-new', '-o', 'ConnectTimeout=8')
$UsePass  = -not [string]::IsNullOrEmpty($Password)

function Test-Cmd($Name) {
    [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

if ($UsePass) {
    if (-not ((Test-Cmd 'plink') -and (Test-Cmd 'pscp'))) {
        throw @"
RM_PASS / -Password needs PuTTY tools on PATH (plink.exe + pscp.exe).
Install PuTTY, or omit the password and type it when OpenSSH prompts,
or set up an SSH key (recommended).
"@
    }
}

function Invoke-RmSsh {
    param([Parameter(Mandatory)][string]$RemoteCommand)
    if ($UsePass) {
        # -batch: no interactive prompts; accept host key via echo y once if needed
        $out = & plink -batch -ssh $Target -pw $Password $RemoteCommand 2>&1
        if ($LASTEXITCODE -ne 0) {
            # first connect: accept host key then retry
            $null = cmd /c "echo y| plink -ssh $Target -pw `"$Password`" exit" 2>&1
            $out = & plink -batch -ssh $Target -pw $Password $RemoteCommand 2>&1
        }
        if ($LASTEXITCODE -ne 0) {
            throw "plink failed ($LASTEXITCODE): $RemoteCommand`n$out"
        }
        $out
    } else {
        & ssh @SshOpts $Target $RemoteCommand
        if ($LASTEXITCODE -ne 0) {
            throw "ssh failed ($LASTEXITCODE): $RemoteCommand"
        }
    }
}

function Invoke-RmScp {
    param(
        [Parameter(Mandatory)][string]$Source,
        [Parameter(Mandatory)][string]$Destination,
        [switch]$Recurse
    )
    if ($UsePass) {
        # pscp remote syntax: user@host:path
        $pscpArgs = @('-batch', '-pw', $Password)
        if ($Recurse) { $pscpArgs += '-r' }
        $pscpArgs += @($Source, $Destination)
        & pscp @pscpArgs
        if ($LASTEXITCODE -ne 0) {
            throw "pscp failed ($LASTEXITCODE): $Source -> $Destination"
        }
    } else {
        $scpArgs = @() + $SshOpts
        if ($Recurse) { $scpArgs += '-r' }
        $scpArgs += @($Source, $Destination)
        & scp @scpArgs
        if ($LASTEXITCODE -ne 0) {
            throw "scp failed ($LASTEXITCODE): $Source -> $Destination"
        }
    }
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

Write-Host "-> $Target  out=$OutRoot  auth=$(if ($UsePass) { 'RM_PASS/plink' } else { 'ssh key or prompt' })"

# Device identity
Invoke-RmSsh 'uname -a; cat /etc/os-release 2>/dev/null | head -5; ls /usr/bin/xochitl 2>/dev/null; which fc-list fc-match 2>/dev/null' |
    Tee-Object -FilePath (Join-Path $Meta 'device.txt') | Out-Host

# Font inventory
Invoke-RmSsh 'fc-list : family file | sort' |
    Out-File -Encoding utf8 (Join-Path $Meta 'fc-list.txt')

$fcMatchRemote = @'
for f in "EB Garamond" "Noto Sans" "Noto Serif" "Noto Sans Mono" serif sans-serif; do
  echo "=== $f ==="
  fc-match -v "$f" 2>/dev/null | egrep "family:|file:|style:|slant:|weight:|size:" || fc-match "$f"
done
'@
Invoke-RmSsh $fcMatchRemote |
    Out-File -Encoding utf8 (Join-Path $Meta 'fc-match.txt')

# fontconfig index + copy
Invoke-RmSsh 'ls -la /etc/fonts /usr/share/fontconfig 2>/dev/null; find /etc/fonts /usr/share/fontconfig -type f 2>/dev/null | head -200' |
    Out-File -Encoding utf8 (Join-Path $Meta 'fontconfig-index.txt')
try {
    Invoke-RmScp -Recurse -Source "${Target}:/etc/fonts/." -Destination $FcOut
} catch {
    Write-Warning "scp /etc/fonts failed: $_"
}

# Font file list + download each
$fontListPath = Join-Path $Meta 'font-files.txt'
Invoke-RmSsh 'find /usr/share/fonts /home/root/.local/share/fonts /usr/lib/fonts -type f \( -name "*.ttf" -o -name "*.otf" -o -name "*.ttc" \) 2>/dev/null' |
    Out-File -Encoding utf8 $fontListPath

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
Invoke-RmSsh 'strings /usr/bin/xochitl 2>/dev/null | egrep -i "garamond|noto|heading|font.?size|FontSize|pointSize|textStyle|ParagraphStyle|EBGaramond" | sort -u | head -400' |
    Out-File -Encoding utf8 (Join-Path $Meta 'xochitl-font-strings.txt')

# packages
Invoke-RmSsh 'opkg list-installed 2>/dev/null | egrep -i "font|freetype|harfbuzz|qt" | head -80' |
    Out-File -Encoding utf8 (Join-Path $Meta 'opkg-fonts-qt.txt')

Write-Host "done -> $OutRoot"
Get-ChildItem $Meta | Select-Object Name, Length
if (Test-Path $Fonts) {
    $bytes = (Get-ChildItem -Recurse -File $Fonts -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum).Sum
    Write-Host ("fonts ~{0:N1} MB" -f ($bytes / 1MB))
}
