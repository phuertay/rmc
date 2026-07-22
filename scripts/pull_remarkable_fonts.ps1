# Pull reMarkable fonts + fontconfig (+ optional xochitl size hints) over SSH.
#
# Run from a PC that can reach the tablet (USB 10.11.99.1 or Wi-Fi IP):
#   .\scripts\pull_remarkable_fonts.ps1
#   $env:RM_HOST='192.168.1.50'; $env:RM_PASS='…'; .\scripts\pull_remarkable_fonts.ps1
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
    [string]$Password = $env:RM_PASS,
    [string]$OutDir = $env:RM_OUT
)
$ErrorActionPreference = 'Stop'

$HostName = if ($env:RM_HOST) { $env:RM_HOST } else { '10.11.99.1' }
$User     = if ($env:RM_USER) { $env:RM_USER } else { 'root' }
$OutRoot  = if ($OutDir) { $OutDir } else { 'tests/expected/device_fonts' }
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

# Soft: return stdout even when remote exit != 0 (BusyBox find often exits 1).
function Invoke-RmSsh {
    param(
        [Parameter(Mandatory)][string]$RemoteCommand,
        [switch]$Strict
    )
    if ($UsePass) {
        $out = & plink -batch -ssh $Target -pw $Password $RemoteCommand 2>&1
        $code = $LASTEXITCODE
        if ($code -ne 0) {
            $null = cmd /c "echo y| plink -ssh $Target -pw `"$Password`" exit" 2>&1
            $out = & plink -batch -ssh $Target -pw $Password $RemoteCommand 2>&1
            $code = $LASTEXITCODE
        }
        # plink wraps remote stderr into the stream; keep text lines
        $text = @($out | ForEach-Object { "$_" }) -join "`n"
        if ($Strict -and $code -ne 0) {
            throw "plink failed ($code): $RemoteCommand`n$text"
        }
        return $text
    } else {
        $out = & ssh @SshOpts $Target $RemoteCommand 2>&1
        $code = $LASTEXITCODE
        $text = @($out | ForEach-Object { "$_" }) -join "`n"
        if ($Strict -and $code -ne 0) {
            throw "ssh failed ($code): $RemoteCommand`n$text"
        }
        return $text
    }
}

function Invoke-RmScp {
    param(
        [Parameter(Mandatory)][string]$Source,
        [Parameter(Mandatory)][string]$Destination,
        [switch]$Recurse
    )
    if ($UsePass) {
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

# Resolve OUT: -OutDir / RM_OUT, else next to script if not in a repo, else repo-relative
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
if (-not [System.IO.Path]::IsPathRooted($OutRoot)) {
    if ((Split-Path -Leaf $ScriptDir) -eq 'scripts' -and (Test-Path (Join-Path $RepoRoot '.git'))) {
        $OutRoot = Join-Path $RepoRoot $OutRoot
    } else {
        $OutRoot = Join-Path $ScriptDir 'device_fonts'
    }
}

$Meta = Join-Path $OutRoot 'meta'
$Fonts = Join-Path $OutRoot 'fonts'
$FcOut = Join-Path $OutRoot 'fontconfig\etc-fonts'
New-Item -ItemType Directory -Force -Path $Meta, $Fonts, $FcOut | Out-Null

Write-Host "-> $Target  out=$OutRoot  auth=$(if ($UsePass) { 'RM_PASS/plink' } else { 'ssh key or prompt' })"

# Device identity (BusyBox: head -n, not head -5)
Invoke-RmSsh -Strict 'uname -a; head -n 5 /etc/os-release 2>/dev/null; ls /usr/bin/xochitl 2>/dev/null; which fc-list fc-match 2>/dev/null' |
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

# fontconfig index + copy (no trailing "/." — pscp rejects '.' / '..' path segments)
Invoke-RmSsh 'ls -la /etc/fonts /usr/share/fontconfig 2>/dev/null; find /etc/fonts /usr/share/fontconfig -type f 2>/dev/null | head -n 200' |
    Out-File -Encoding utf8 (Join-Path $Meta 'fontconfig-index.txt')
try {
    Invoke-RmScp -Recurse -Source "${Target}:/etc/fonts" -Destination $FcOut
} catch {
    Write-Warning "scp /etc/fonts failed: $_"
}

# Font file list + download each
# Quote find expr for plink; tolerate exit 1 when some roots are missing.
$findFonts = 'find /usr/share/fonts /home/root/.local/share/fonts /usr/lib/fonts -type f \( -name "*.ttf" -o -name "*.otf" -o -name "*.ttc" \) 2>/dev/null; true'
$fontListPath = Join-Path $Meta 'font-files.txt'
$fontList = Invoke-RmSsh $findFonts
$fontList | Out-File -Encoding utf8 $fontListPath

$paths = @($fontList -split "`n" | ForEach-Object { $_.Trim() } | Where-Object {
    $_ -and ($_ -match '\.(ttf|otf|ttc)$')
})
Write-Host ("found {0} font files" -f $paths.Count)

foreach ($remote in $paths) {
    $base = Split-Path -Leaf $remote
    $dirKey = ((Split-Path -Parent $remote) -replace '/', '_')
    $destDir = Join-Path $Fonts $dirKey
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null
    try {
        Invoke-RmScp -Source "${Target}:$remote" -Destination (Join-Path $destDir $base)
        Write-Host "  got $base"
    } catch {
        Write-Warning "skip $remote : $_"
    }
}

# xochitl font-related strings (BusyBox: head -n)
Invoke-RmSsh 'strings /usr/bin/xochitl 2>/dev/null | egrep -i "garamond|noto|heading|font.?size|FontSize|pointSize|textStyle|ParagraphStyle|EBGaramond" | sort -u | head -n 400; true' |
    Out-File -Encoding utf8 (Join-Path $Meta 'xochitl-font-strings.txt')

# packages
Invoke-RmSsh 'opkg list-installed 2>/dev/null | egrep -i "font|freetype|harfbuzz|qt" | head -n 80; true' |
    Out-File -Encoding utf8 (Join-Path $Meta 'opkg-fonts-qt.txt')

Write-Host "done -> $OutRoot"
Get-ChildItem $Meta | Select-Object Name, Length
if (Test-Path $Fonts) {
    $bytes = (Get-ChildItem -Recurse -File $Fonts -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum).Sum
    Write-Host ("fonts ~{0:N1} MB" -f ($bytes / 1MB))
}
