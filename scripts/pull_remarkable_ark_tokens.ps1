# Pull xochitl binary + carve Ark typography tokens (qrc:/ark-imports/tokens).
#
#   $env:RM_HOST = '10.209.3.131'
#   $env:RM_PASS = '…'
#   .\scripts\pull_remarkable_ark_tokens.ps1
#   .\scripts\pull_remarkable_ark_tokens.ps1 -Password '…' -OutDir .\ark_tokens
#
# Needs: PuTTY plink/pscp (if password), Python 3 on PATH for local carve.
#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Password = $env:RM_PASS,
    [string]$OutDir = $env:RM_OUT,
    [switch]$SkipBinary   # only remote strings; skip multi‑MB scp of xochitl
)
$ErrorActionPreference = 'Stop'

$HostName = if ($env:RM_HOST) { $env:RM_HOST } else { '10.11.99.1' }
$User     = if ($env:RM_USER) { $env:RM_USER } else { 'root' }
$OutRoot  = if ($OutDir) { $OutDir } else { 'tests/expected/ark_tokens' }
$Target   = "${User}@${HostName}"
$SshOpts  = @('-o', 'StrictHostKeyChecking=accept-new', '-o', 'ConnectTimeout=8')
$UsePass  = -not [string]::IsNullOrEmpty($Password)

function Test-Cmd($Name) {
    [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

if ($UsePass) {
    if (-not ((Test-Cmd 'plink') -and (Test-Cmd 'pscp'))) {
        throw "RM_PASS needs PuTTY plink.exe + pscp.exe on PATH."
    }
}

function Invoke-RmSsh {
    param([Parameter(Mandatory)][string]$RemoteCommand)
    if ($UsePass) {
        $out = & plink -batch -ssh $Target -pw $Password $RemoteCommand 2>&1
        if ($LASTEXITCODE -ne 0) {
            $null = cmd /c "echo y| plink -ssh $Target -pw `"$Password`" exit" 2>&1
            $out = & plink -batch -ssh $Target -pw $Password $RemoteCommand 2>&1
        }
        return (@($out | ForEach-Object { "$_" }) -join "`n")
    } else {
        $out = & ssh @SshOpts $Target $RemoteCommand 2>&1
        return (@($out | ForEach-Object { "$_" }) -join "`n")
    }
}

function Invoke-RmScp {
    param(
        [Parameter(Mandatory)][string]$Source,
        [Parameter(Mandatory)][string]$Destination
    )
    if ($UsePass) {
        & pscp -batch -pw $Password $Source $Destination
        if ($LASTEXITCODE -ne 0) { throw "pscp failed ($LASTEXITCODE): $Source" }
    } else {
        & scp @SshOpts $Source $Destination
        if ($LASTEXITCODE -ne 0) { throw "scp failed ($LASTEXITCODE): $Source" }
    }
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
if (-not [System.IO.Path]::IsPathRooted($OutRoot)) {
    if ((Split-Path -Leaf $ScriptDir) -eq 'scripts' -and (Test-Path (Join-Path $RepoRoot '.git'))) {
        $OutRoot = Join-Path $RepoRoot $OutRoot
    } else {
        $OutRoot = Join-Path $ScriptDir 'ark_tokens'
    }
}

$Meta = Join-Path $OutRoot 'meta'
$Bin  = Join-Path $OutRoot 'bin'
$Ext  = Join-Path $OutRoot 'extracted'
New-Item -ItemType Directory -Force -Path $Meta, $Bin, $Ext | Out-Null

Write-Host "-> $Target  out=$OutRoot  auth=$(if ($UsePass) { 'RM_PASS/plink' } else { 'ssh/key' })"

Invoke-RmSsh 'uname -a; ls -la /usr/bin/xochitl; ls -la /usr/share/remarkable/xochitl 2>/dev/null | head -n 40' |
    Tee-Object -FilePath (Join-Path $Meta 'device.txt') | Out-Host

# --- Remote: rich strings around Ark tokens / typography JSON ---
$remoteExtract = @'
# JSON-ish blobs and token keys from xochitl (BusyBox-safe)
strings -n 6 /usr/bin/xochitl 2>/dev/null | egrep -i \
  '"fontSize"|fontSize|"lineHeight"|lineHeight|"fontFamily"|title\.md|body\.md|title\.lg|Subheading|TitleStyle|ark-imports|/tokens' \
  | sort -u | head -n 800
true
'@
Invoke-RmSsh $remoteExtract |
    Out-File -Encoding utf8 (Join-Path $Meta 'xochitl-token-strings.txt')

# Wider context: lines that look like JSON objects with typography
$remoteJson = @'
strings -n 20 /usr/bin/xochitl 2>/dev/null | egrep '\{.*"fontSize".*\}|\{.*"lineHeight".*\}|"typography"\s*:\s*\{' \
  | head -n 200
true
'@
Invoke-RmSsh $remoteJson |
    Out-File -Encoding utf8 (Join-Path $Meta 'xochitl-jsonish.txt')

# List qrc paths again (narrow)
Invoke-RmSsh 'strings /usr/bin/xochitl 2>/dev/null | egrep "^qrc:/ark" | sort -u | head -n 200; true' |
    Out-File -Encoding utf8 (Join-Path $Meta 'qrc-ark-paths.txt')

# Any loose files under remarkable related to ark/tokens
$findArk = @'
find /usr/share/remarkable /usr/lib /opt -type f \( \
  -iname "*ark*" -o -iname "*token*" -o -path "*ark-imports*" \
\) 2>/dev/null | egrep -i "ark|token|typography|font" | egrep -v "marker|firmware|systemd" | head -n 100
true
'@
Invoke-RmSsh $findArk |
    Out-File -Encoding utf8 (Join-Path $Meta 'ark-file-paths.txt')

# --- Optional: copy xochitl for local carve ---
if (-not $SkipBinary) {
    $sizeLine = Invoke-RmSsh 'ls -l /usr/bin/xochitl | awk "{print \$5}"'
    Write-Host "xochitl size bytes: $sizeLine"
    $destXo = Join-Path $Bin 'xochitl'
    Write-Host "scp /usr/bin/xochitl -> $destXo (may take a while)..."
    try {
        Invoke-RmScp -Source "${Target}:/usr/bin/xochitl" -Destination $destXo
        Write-Host "  got xochitl"
    } catch {
        Write-Warning "scp xochitl failed: $_"
    }
}

# --- Local Python carve (works on copied binary or skips) ---
$carvePy = Join-Path $ScriptDir 'carve_ark_tokens.py'
if (-not (Test-Path $carvePy)) {
    # when script was downloaded alone, expect carve next to it
    $carvePy = Join-Path $ScriptDir 'carve_ark_tokens.py'
}
$xoLocal = Join-Path $Bin 'xochitl'
if ((Test-Path $xoLocal) -and (Test-Cmd 'python')) {
    Write-Host "carving with python..."
    & python $carvePy --binary $xoLocal --out $Ext 2>&1 | Tee-Object -FilePath (Join-Path $Meta 'carve-log.txt')
} elseif ((Test-Path $xoLocal) -and (Test-Cmd 'python3')) {
    & python3 $carvePy --binary $xoLocal --out $Ext 2>&1 | Tee-Object -FilePath (Join-Path $Meta 'carve-log.txt')
} else {
    Write-Host "skip local carve (need xochitl binary + python). Remote string dumps are in meta/."
}

Write-Host "done -> $OutRoot"
Get-ChildItem $Meta | Select-Object Name, Length
if (Test-Path $Ext) { Get-ChildItem $Ext -Recurse -File | Select-Object FullName, Length | Format-Table -AutoSize }

# Upload tip: NEVER zip bin/xochitl (tens of MB). Share only small text dumps.
$zipHint = Join-Path $OutRoot 'UPLOAD_THESE.txt'
@(
    'Upload ONLY these folders (text, small):'
    "  $Meta"
    "  $Ext   (only if python carve ran)"
    ''
    'Do NOT upload:'
    "  $Bin   (xochitl binary — too big; keep local)"
    ''
    'If carve skipped, meta/ alone is enough for cloud agent.'
    'Re-run with -SkipBinary to skip scp of xochitl next time.'
) | Set-Content -Encoding utf8 $zipHint
Write-Host ""
Write-Host "SHARE: zip meta\ (+ extracted\ if present). SKIP bin\."
Write-Host "hint file: $zipHint"
