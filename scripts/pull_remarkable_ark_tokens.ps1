# Pull xochitl binary + carve Ark typography tokens (qrc:/ark-imports/tokens).
#
#   $env:RM_HOST = '10.209.3.131'
#   $env:RM_PASS = '…'
#   .\scripts\pull_remarkable_ark_tokens.ps1
#   .\scripts\pull_remarkable_ark_tokens.ps1 -Password '…' -OutDir .\ark_tokens
#
# Already have xochitl locally (skip SSH):
#   .\scripts\pull_remarkable_ark_tokens.ps1 -LocalBinary C:\Users\phuer\tmp\ark_tokens\bin\xochitl -OutDir C:\Users\phuer\tmp\ark_tokens
#
# Writes share/ + ark_tokens_share.zip (meta + text RCC dumps only; never bin/).
# Upload ark_tokens_share.zip. LocalBinary skips SSH if xochitl already on disk.
#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Password = $env:RM_PASS,
    [string]$OutDir = $env:RM_OUT,
    [string]$LocalBinary = '',  # skip SSH; carve+RCC this file into OutDir
    [switch]$SkipBinary   # remote strings only; skip multi‑MB scp of xochitl
)
$ErrorActionPreference = 'Stop'

$HostName = if ($env:RM_HOST) { $env:RM_HOST } else { '10.11.99.1' }
$User     = if ($env:RM_USER) { $env:RM_USER } else { 'root' }
$OutRoot  = if ($OutDir) { $OutDir } else { 'tests/expected/ark_tokens' }
$Target   = "${User}@${HostName}"
$SshOpts  = @('-o', 'StrictHostKeyChecking=accept-new', '-o', 'ConnectTimeout=8')
$UsePass  = -not [string]::IsNullOrEmpty($Password)
$LocalOnly = -not [string]::IsNullOrEmpty($LocalBinary)

function Test-Cmd($Name) {
    [bool](Get-Command $Name -ErrorAction SilentlyContinue)
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

$xoLocal = Join-Path $Bin 'xochitl'

if ($LocalOnly) {
    if (-not (Test-Path -LiteralPath $LocalBinary)) {
        throw "LocalBinary not found: $LocalBinary"
    }
    Write-Host "-> local-only  binary=$LocalBinary  out=$OutRoot"
    $srcFull = [System.IO.Path]::GetFullPath($LocalBinary)
    $dstFull = [System.IO.Path]::GetFullPath($xoLocal)
    if ($srcFull -ne $dstFull) {
        Copy-Item -LiteralPath $LocalBinary -Destination $xoLocal -Force
    }
    "local-only $($LocalBinary) size=$((Get-Item -LiteralPath $xoLocal).Length)" |
        Set-Content -Encoding utf8 (Join-Path $Meta 'device.txt')
} else {
    if ($UsePass) {
        if (-not ((Test-Cmd 'plink') -and (Test-Cmd 'pscp'))) {
            throw "RM_PASS needs PuTTY plink.exe + pscp.exe on PATH."
        }
    }

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
        Write-Host "scp /usr/bin/xochitl -> $xoLocal (may take a while)..."
        try {
            Invoke-RmScp -Source "${Target}:/usr/bin/xochitl" -Destination $xoLocal
            Write-Host "  got xochitl"
        } catch {
            Write-Warning "scp xochitl failed: $_"
        }
    }
}

# --- Local Python carve + Qt RCC extract (need copied binary) ---
$carvePy = Join-Path $ScriptDir 'carve_ark_tokens.py'
$rccPy   = Join-Path $ScriptDir 'extract_qt_rcc.py'
$Py = $null
if (Test-Cmd 'python') { $Py = 'python' }
elseif (Test-Cmd 'python3') { $Py = 'python3' }

if ((Test-Path $xoLocal) -and $Py) {
    Write-Host "carving with $Py..."
    & $Py $carvePy --binary $xoLocal --out $Ext 2>&1 |
        Tee-Object -FilePath (Join-Path $Meta 'carve-log.txt')
    if (Test-Path $rccPy) {
        Write-Host "extracting Qt RCC (hard path)..."
        $RccOut = Join-Path $Ext 'rcc'
        & $Py $rccPy --binary $xoLocal --out $RccOut 2>&1 |
            Tee-Object -FilePath (Join-Path $Meta 'rcc-log.txt')
    } else {
        Write-Warning "missing extract_qt_rcc.py next to this script"
    }
} else {
    Write-Host "skip local carve/RCC (need xochitl binary + python). Remote string dumps are in meta/."
}

Write-Host "done -> $OutRoot"
Get-ChildItem $Meta -ErrorAction SilentlyContinue | Select-Object Name, Length
if (Test-Path (Join-Path $Ext 'rcc\SUMMARY.txt')) {
    Get-Content (Join-Path $Ext 'rcc\SUMMARY.txt') | Out-Host
}

# --- Build slim share/ (only what cloud agent needs) + zip ---
# Never include bin/xochitl. Skip images/fonts/binaries from RCC trees.
$Share = Join-Path $OutRoot 'share'
$ZipPath = Join-Path $OutRoot 'ark_tokens_share.zip'
if (Test-Path $Share) { Remove-Item -Recurse -Force $Share }
New-Item -ItemType Directory -Force -Path $Share | Out-Null

function Copy-ShareFile {
    param([string]$Src, [string]$RelDest)
    if (-not (Test-Path -LiteralPath $Src)) { return }
    $dest = Join-Path $Share $RelDest
    New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
    Copy-Item -LiteralPath $Src -Destination $dest -Force
}

# Always: remote/local meta logs
if (Test-Path $Meta) {
    Get-ChildItem $Meta -File | ForEach-Object {
        Copy-ShareFile $_.FullName ("meta\" + $_.Name)
    }
}

# Carve text dumps (top of extracted/)
foreach ($name in @(
    'token-strings.txt', 'fontsize-lines.txt', 'fontsize-numbers.txt',
    'qrc-ark-paths.txt', 'json_blobs_index.txt'
)) {
    Copy-ShareFile (Join-Path $Ext $name) ("extracted\" + $name)
}
Get-ChildItem $Ext -Filter 'json_blob_*.json' -File -ErrorAction SilentlyContinue | ForEach-Object {
    Copy-ShareFile $_.FullName ("extracted\" + $_.Name)
}

# RCC: summaries + text-like payloads only
$Rcc = Join-Path $Ext 'rcc'
if (Test-Path $Rcc) {
    foreach ($name in @('SUMMARY.txt', 'typography_hits.txt', 'name_sections.txt')) {
        Copy-ShareFile (Join-Path $Rcc $name) ("extracted\rcc\" + $name)
    }
    $textExt = @('.txt', '.json', '.qml', '.js', '.css', '.md', '.xml', '.html', '.qss', '.conf')
    Get-ChildItem $Rcc -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
        $rel = $_.FullName.Substring($Rcc.Length).TrimStart('\', '/')
        if ($_.Name -in @('SUMMARY.txt', 'typography_hits.txt', 'name_sections.txt')) { return }
        if ($_.Length -gt 512KB) { return }
        if ($textExt -notcontains $_.Extension.ToLowerInvariant() -and $_.Name -ne '_meta.txt') { return }
        # skip obvious junk
        if ($rel -match '(^|[/\\])(icons?|images?|img)([/\\]|$)') { return }
        Copy-ShareFile $_.FullName ("extracted\rcc\" + $rel)
    }
}

# Manifest
$files = @(Get-ChildItem $Share -Recurse -File)
@(
    "ark_tokens share bundle"
    "created=$(Get-Date -Format o)"
    "file_count=$($files.Count)"
    "total_bytes=$((($files | Measure-Object Length -Sum).Sum))"
    ""
    "UPLOAD this zip to the cloud agent. bin/xochitl is NOT included."
    ""
) + ($files | ForEach-Object { $_.FullName.Substring($Share.Length).TrimStart('\', '/') + "  $($_.Length)" }) |
    Set-Content -Encoding utf8 (Join-Path $Share 'MANIFEST.txt')

if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }
# Compress share/* so zip root has meta/, extracted/, MANIFEST.txt
Compress-Archive -Path (Join-Path $Share '*') -DestinationPath $ZipPath -Force

Write-Host ""
Write-Host "UPLOAD THIS ZIP: $ZipPath"
Write-Host "size: $((Get-Item $ZipPath).Length) bytes  files: $($files.Count)"
Write-Host "staging: $Share"
