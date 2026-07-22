# Tight pull: document typography clues only (no Qt Controls QML flood).
#
#   $env:RM_HOST = '10.209.3.131'
#   $env:RM_PASS = '…'
#   .\scripts\pull_remarkable_typography_tight.ps1
#   .\scripts\pull_remarkable_typography_tight.ps1 -Password '…' -OutDir .\device_typo_tight
#
# Needs PuTTY plink/pscp when using a password.
#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Password = $env:RM_PASS,
    [string]$OutDir = $env:RM_OUT
)
$ErrorActionPreference = 'Stop'

$HostName = if ($env:RM_HOST) { $env:RM_HOST } else { '10.11.99.1' }
$User     = if ($env:RM_USER) { $env:RM_USER } else { 'root' }
$OutRoot  = if ($OutDir) { $OutDir } else { 'tests/expected/device_typography_tight' }
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
        $OutRoot = Join-Path $ScriptDir 'device_typography_tight'
    }
}

$Meta = Join-Path $OutRoot 'meta'
$Files = Join-Path $OutRoot 'files'
New-Item -ItemType Directory -Force -Path $Meta, $Files | Out-Null

Write-Host "-> $Target  out=$OutRoot  auth=$(if ($UsePass) { 'RM_PASS/plink' } else { 'ssh/key' })"

Invoke-RmSsh 'uname -a; head -n 5 /etc/os-release 2>/dev/null' |
    Tee-Object -FilePath (Join-Path $Meta 'device.txt') | Out-Host

# 1) Known webui CSS
try {
    Invoke-RmScp -Source "${Target}:/usr/share/remarkable/webui/assets/index.css" `
        -Destination (Join-Path $Files 'webui-index.css')
    Write-Host '  got webui-index.css'
} catch {
    Write-Warning "webui css: $_"
}

# 2) Ark / token / typography files (exclude Qt qml noise)
$findTok = @'
find /usr /home/root /opt /var -type f \( \
  -iname "*ark*" -o -iname "*token*" -o -iname "*typography*" \
  -o -iname "*paragraph*" -o -iname "*textstyle*" -o -iname "*stylesheet*" \
\) ! -path "*/QtQuick/*" ! -path "*/qml/Qt*" 2>/dev/null | head -n 200; true
'@
$tokPaths = Invoke-RmSsh $findTok
$tokPaths | Out-File -Encoding utf8 (Join-Path $Meta 'token-paths.txt')
$paths = @($tokPaths -split "`n" | ForEach-Object { $_.Trim() } | Where-Object {
    $_ -and ($_ -notmatch '/QtQuick/') -and ($_ -notmatch '/qml/Qt')
})
Write-Host ("token/typography candidates: {0}" -f $paths.Count)

$n = 0
foreach ($remote in $paths) {
    $n++
    $safe = ($remote -replace '^/', '' -replace '/', '_')
    if ($safe.Length -gt 160) { $safe = $safe.Substring($safe.Length - 160) }
    try {
        Invoke-RmScp -Source "${Target}:$remote" -Destination (Join-Path $Files $safe)
        Write-Host "  [$n] $remote"
    } catch {
        Write-Warning "skip $remote : $_"
    }
}

# 3) Doc-style size strings (tight filter)
$sizeStrings = @'
strings /usr/bin/xochitl 2>/dev/null | egrep -i \
  "TitleStyle|SubheadingStyle|Subheading2|BodyStyle|ParagraphStyle|font-size:[0-9]|[0-9]+pt;|[0-9]+pt |fontSize.?=.?[0-9]|pointSize.?=.?[0-9]|loaded CSS|EB ?Garamond|Noto Sans" \
  | sort -u | head -n 400; true
'@
Invoke-RmSsh $sizeStrings |
    Out-File -Encoding utf8 (Join-Path $Meta 'xochitl-doc-size-strings.txt')

# 4) Context windows around TitleStyle / Subheading (hex dump-ish via strings -n)
$ctx = @'
strings -n 8 /usr/bin/xochitl 2>/dev/null | egrep -n -i \
  "TitleStyle|SubheadingStyle|Subheading2Style|Body Text|Title Large|font-size:" \
  | head -n 200; true
'@
Invoke-RmSsh $ctx |
    Out-File -Encoding utf8 (Join-Path $Meta 'xochitl-style-context.txt')

# 5) Qt resource list embedded in binary (rcc paths often look like :/…)
$rcc = @'
strings /usr/bin/xochitl 2>/dev/null | egrep "^:/|^qrc:|\.css$|\.qml$" \
  | egrep -i "font|text|style|title|body|heading|paragraph|typography|token|ark" \
  | sort -u | head -n 300; true
'@
Invoke-RmSsh $rcc |
    Out-File -Encoding utf8 (Join-Path $Meta 'xochitl-qrc-paths.txt')

# 6) Grep webui css for font-size if present
$cssLocal = Join-Path $Files 'webui-index.css'
if (Test-Path $cssLocal) {
    Select-String -Path $cssLocal -Pattern 'font-size|Title|Subheading|heading|body' -AllMatches |
        ForEach-Object { $_.Line } |
        Select-Object -First 80 |
        Out-File -Encoding utf8 (Join-Path $Meta 'webui-css-font-hits.txt')
}

Write-Host "done -> $OutRoot"
Get-ChildItem $Meta | Select-Object Name, Length
Get-ChildItem $Files -ErrorAction SilentlyContinue | Select-Object Name, Length
Write-Host "Zip and share: $OutRoot"
