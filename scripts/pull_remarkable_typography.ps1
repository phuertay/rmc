# Pull reMarkable xochitl typography hints (CSS/QML paths + size strings).
#
#   $env:RM_HOST = '10.209.3.131'
#   $env:RM_PASS = '…'
#   .\scripts\pull_remarkable_typography.ps1
#   .\scripts\pull_remarkable_typography.ps1 -Password '…' -OutDir .\device_typo
#
# Needs PuTTY plink/pscp when using a password (same as pull_remarkable_fonts.ps1).
#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Password = $env:RM_PASS,
    [string]$OutDir = $env:RM_OUT
)
$ErrorActionPreference = 'Stop'

$HostName = if ($env:RM_HOST) { $env:RM_HOST } else { '10.11.99.1' }
$User     = if ($env:RM_USER) { $env:RM_USER } else { 'root' }
$OutRoot  = if ($OutDir) { $OutDir } else { 'tests/expected/device_typography' }
$Target   = "${User}@${HostName}"
$SshOpts  = @('-o', 'StrictHostKeyChecking=accept-new', '-o', 'ConnectTimeout=8')
$UsePass  = -not [string]::IsNullOrEmpty($Password)

function Test-Cmd($Name) {
    [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

if ($UsePass) {
    if (-not ((Test-Cmd 'plink') -and (Test-Cmd 'pscp'))) {
        throw "RM_PASS needs PuTTY plink.exe + pscp.exe on PATH (or omit password and use SSH key / prompt)."
    }
}

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
        $OutRoot = Join-Path $ScriptDir 'device_typography'
    }
}

$Meta = Join-Path $OutRoot 'meta'
$Res  = Join-Path $OutRoot 'resources'
New-Item -ItemType Directory -Force -Path $Meta, $Res | Out-Null

Write-Host "-> $Target  out=$OutRoot  auth=$(if ($UsePass) { 'RM_PASS/plink' } else { 'ssh key or prompt' })"

Invoke-RmSsh -Strict 'uname -a; head -n 5 /etc/os-release 2>/dev/null' |
    Tee-Object -FilePath (Join-Path $Meta 'device.txt') | Out-Host

# Paths that may hold Title/Subheading/Body CSS or QML
$findRes = @'
find /usr /home/root /opt /var -type f \( \
  -iname "*.css" -o -iname "*.qml" -o -iname "*.qss" -o -iname "*typography*" \
  -o -iname "*paragraph*" -o -iname "*textstyle*" -o -iname "*stylesheet*" \
\) 2>/dev/null | head -n 300; true
'@
$pathsText = Invoke-RmSsh $findRes
$pathsText | Out-File -Encoding utf8 (Join-Path $Meta 'resource-paths.txt')
$paths = @($pathsText -split "`n" | ForEach-Object { $_.Trim() } | Where-Object {
    $_ -and ($_ -match '\.(css|qml|qss)$' -or $_ -match 'typography|paragraph|textstyle|stylesheet')
})
Write-Host ("resource candidates: {0}" -f $paths.Count)

$i = 0
foreach ($remote in $paths) {
    $i++
    $safe = ($remote -replace '^/', '' -replace '/', '_')
    if ($safe.Length -gt 180) { $safe = $safe.Substring($safe.Length - 180) }
    $dest = Join-Path $Res $safe
    try {
        Invoke-RmScp -Source "${Target}:$remote" -Destination $dest
        Write-Host "  [$i] $remote"
    } catch {
        Write-Warning "skip $remote : $_"
    }
}

# Size / style strings from xochitl (BusyBox-safe)
$sizeStrings = @'
strings /usr/bin/xochitl 2>/dev/null | egrep -i \
  "font-size:|[0-9]+pt|[0-9]+px|Title|Subheading|Heading|Body|fontSize|pointSize|lineHeight|ParagraphStyle|typography|EB ?Garamond|Noto Sans" \
  | sort -u | head -n 500; true
'@
Invoke-RmSsh $sizeStrings |
    Out-File -Encoding utf8 (Join-Path $Meta 'xochitl-size-strings.txt')

# QML/JS snippets that mention fontSize near Title/Subheading
$qmlHints = @'
strings /usr/bin/xochitl 2>/dev/null | egrep -i \
  "Title|Subheading|subheading|fontSize|pixelSize|pointSize|lineHeight" \
  | sort -u | head -n 300; true
'@
Invoke-RmSsh $qmlHints |
    Out-File -Encoding utf8 (Join-Path $Meta 'xochitl-qml-hints.txt')

# Any JSON/XML under xochitl data that mentions font
$dataFind = @'
find /home/root/.local/share/remarkable /usr/share/remarkable /etc/remarkable \
  -type f \( -iname "*.json" -o -iname "*.xml" -o -iname "*.css" -o -iname "*.qml" \) 2>/dev/null \
  | head -n 200; true
'@
Invoke-RmSsh $dataFind |
    Out-File -Encoding utf8 (Join-Path $Meta 'remarkable-data-paths.txt')

Write-Host "done -> $OutRoot"
Get-ChildItem $Meta | Select-Object Name, Length
Write-Host "Zip this folder and share: $OutRoot"
