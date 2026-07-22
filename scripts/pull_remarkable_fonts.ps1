# Pull reMarkable fonts + fontconfig (+ optional xochitl size hints) over SSH.
#
# Run from a PC that can reach the tablet (USB 10.11.99.1 or Wi-Fi IP):
#   .\scripts\pull_remarkable_fonts.ps1
#   $env:RM_HOST='192.168.1.50'; $env:RM_PASS='…'; .\scripts\pull_remarkable_fonts.ps1
# Output zip: <OutDir>\remarkable_onenote_fonts.zip  (Serif Small + Sans only)
#
# Already have xochitl (fonts often live only in RCC, not /usr/share/fonts):
#   .\scripts\pull_remarkable_fonts.ps1 -LocalBinary C:\path\to\xochitl
#
# Install pulled TTFs on Windows (right-click → Install for all users), then
# OneNote will honor CSS font-family "reMarkable Serif Small" / "reMarkable Sans".
# Script writes remarkable_onenote_fonts.zip (needed faces only). Do NOT commit it.
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
    [string]$OutDir = $env:RM_OUT,
    [string]$LocalBinary = ''  # carve TTFs from this xochitl; skip SSH if set alone
)
$ErrorActionPreference = 'Stop'
$ScriptRev = '2026-07-22-fonts-zip-v2'

$HostName = if ($env:RM_HOST) { $env:RM_HOST } else { '10.11.99.1' }
$User     = if ($env:RM_USER) { $env:RM_USER } else { 'root' }
$OutRoot  = if ($OutDir) { $OutDir } else { 'tests/expected/device_fonts' }
$Target   = "${User}@${HostName}"
$SshOpts  = @('-o', 'StrictHostKeyChecking=accept-new', '-o', 'ConnectTimeout=8')
$UsePass  = -not [string]::IsNullOrEmpty($Password)
$LocalOnly = -not [string]::IsNullOrEmpty($LocalBinary)

function Test-Cmd($Name) {
    [bool](Get-Command $Name -ErrorAction SilentlyContinue)
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

$CarvePy = Join-Path $ScriptDir 'carve_remarkable_fonts.py'

$Meta = Join-Path $OutRoot 'meta'
$Fonts = Join-Path $OutRoot 'fonts'
$Carved = Join-Path $Fonts 'carved_from_xochitl'
$Webui = Join-Path $Fonts 'webui'
$FcOut = Join-Path $OutRoot 'fontconfig\etc-fonts'
$Bin = Join-Path $OutRoot 'bin'
New-Item -ItemType Directory -Force -Path $Meta, $Fonts, $FcOut, $Bin | Out-Null

function Invoke-CarveXochitl {
    param([Parameter(Mandatory)][string]$BinaryPath)
    if (-not (Test-Path -LiteralPath $CarvePy)) {
        Write-Warning "missing $CarvePy"
        return
    }
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
    if (-not $py) {
        Write-Warning "python not on PATH; skip RCC font carve"
        return
    }
    New-Item -ItemType Directory -Force -Path $Carved | Out-Null
    Write-Host "carve reMarkable*.ttf from $BinaryPath ..."
    & $py.Source $CarvePy --binary $BinaryPath --out $Carved
}

if ($LocalOnly) {
    if (-not (Test-Path -LiteralPath $LocalBinary)) {
        throw "LocalBinary not found: $LocalBinary"
    }
    $xo = (Resolve-Path -LiteralPath $LocalBinary).Path
    Write-Host "-> local-only carve  binary=$xo  out=$OutRoot"
    "local-only $xo size=$((Get-Item -LiteralPath $xo).Length)" |
        Set-Content -Encoding utf8 (Join-Path $Meta 'device.txt')
    Invoke-CarveXochitl -BinaryPath $xo
} else {
    if ($UsePass) {
        if (-not ((Test-Cmd 'plink') -and (Test-Cmd 'pscp'))) {
            throw @"
RM_PASS / -Password needs PuTTY tools on PATH (plink.exe + pscp.exe).
Install PuTTY, or omit the password and type it when OpenSSH prompts,
or set up an SSH key (recommended).
"@
        }
    }

    Write-Host "-> $Target  out=$OutRoot  auth=$(if ($UsePass) { 'RM_PASS/plink' } else { 'ssh key or prompt' })"

    # Device identity (BusyBox: head -n, not head -5)
    Invoke-RmSsh -Strict 'uname -a; head -n 5 /etc/os-release 2>/dev/null; ls /usr/bin/xochitl 2>/dev/null; which fc-list fc-match 2>/dev/null' |
        Tee-Object -FilePath (Join-Path $Meta 'device.txt') | Out-Host

    # Font inventory
    Invoke-RmSsh 'fc-list : family file | sort' |
        Out-File -Encoding utf8 (Join-Path $Meta 'fc-list.txt')

    $fcMatchRemote = @'
for f in "reMarkable Serif Small" "reMarkable Sans" "EB Garamond" "Noto Sans" serif sans-serif; do
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

    # Font file list + download each (system dirs + anything named reMarkable*)
    $findFonts = @'
find /usr/share/fonts /home/root/.local/share/fonts /usr/lib/fonts /usr/share/remarkable \
  -type f \( -name "*.ttf" -o -name "*.otf" -o -name "*.ttc" -o -name "*.woff" -o -name "*.woff2" \) 2>/dev/null
find /usr/share/remarkable /usr/lib -iname "*remarkable*serif*" -o -iname "*remarkable*sans*" 2>/dev/null | head -n 50
true
'@
    $fontListPath = Join-Path $Meta 'font-files.txt'
    $fontList = Invoke-RmSsh $findFonts
    $fontList | Out-File -Encoding utf8 $fontListPath

    $paths = @($fontList -split "`n" | ForEach-Object { $_.Trim() } | Where-Object {
        $_ -and ($_ -match '\.(ttf|otf|ttc|woff2?)$')
    } | Select-Object -Unique)
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

    # WebUI faces (often only woff2 on disk; notebook TTFs may be RCC-only)
    New-Item -ItemType Directory -Force -Path $Webui | Out-Null
    foreach ($w in @(
        '/usr/share/remarkable/webui/reMarkableSans.woff2',
        '/usr/share/remarkable/webui/reMarkableSerif.woff2'
    )) {
        $base = Split-Path -Leaf $w
        try {
            Invoke-RmScp -Source "${Target}:$w" -Destination (Join-Path $Webui $base)
            Write-Host "  got webui/$base"
        } catch {
            Write-Warning "skip $w : $_"
        }
    }

    # xochitl font-related strings + carve TTFs from binary (exact notebook faces)
    Invoke-RmSsh 'strings /usr/bin/xochitl 2>/dev/null | egrep -i "reMarkable|garamond|noto|SerifSmall|font.?size|FontSize|ParagraphStyle" | sort -u | head -n 400; true' |
        Out-File -Encoding utf8 (Join-Path $Meta 'xochitl-font-strings.txt')

    Invoke-RmSsh 'opkg list-installed 2>/dev/null | egrep -i "font|freetype|harfbuzz|qt" | head -n 80; true' |
        Out-File -Encoding utf8 (Join-Path $Meta 'opkg-fonts-qt.txt')

    $xoLocal = Join-Path $Bin 'xochitl'
    if ($LocalBinary -and (Test-Path -LiteralPath $LocalBinary)) {
        Invoke-CarveXochitl -BinaryPath ((Resolve-Path -LiteralPath $LocalBinary).Path)
    } else {
        try {
            Write-Host "scp /usr/bin/xochitl -> $xoLocal (for RCC font carve; large)..."
            Invoke-RmScp -Source "${Target}:/usr/bin/xochitl" -Destination $xoLocal
            Invoke-CarveXochitl -BinaryPath $xoLocal
        } catch {
            Write-Warning "xochitl scp/carve failed: $_. Re-run with -LocalBinary if you already have xochitl."
        }
    }
}

Write-Host "done -> $OutRoot  rev=$ScriptRev"
Get-ChildItem $Meta -ErrorAction SilentlyContinue | Select-Object Name, Length
if (Test-Path $Fonts) {
    $bytes = (Get-ChildItem -Recurse -File $Fonts -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum).Sum
    Write-Host ("fonts ~{0:N1} MB" -f ($bytes / 1MB))
}

# --- Pick notebook faces only → remarkable_onenote_fonts.zip ---
# Needed for OneNote CSS: reMarkable Serif Small (L1/L2) + reMarkable Sans (L3+).
# (plain arrays only — Generic.List[object] blows up on some PS builds)
$ZipPath = Join-Path $OutRoot 'remarkable_onenote_fonts.zip'
$Stage = Join-Path $OutRoot 'share_fonts'
if (Test-Path -LiteralPath $Stage) { Remove-Item -LiteralPath $Stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Stage | Out-Null

$allFontFiles = @()
if (Test-Path -LiteralPath $Fonts) {
    $allFontFiles = @(Get-ChildItem -LiteralPath $Fonts -Recurse -File -ErrorAction SilentlyContinue)
}
$serifTtf = @($allFontFiles | Where-Object {
    $_.Name -like 'reMarkableSerifSmall*' -and ($_.Extension -eq '.ttf' -or $_.Extension -eq '.otf')
})
$sansTtf = @($allFontFiles | Where-Object {
    $_.Name -like 'reMarkableSans*' -and ($_.Extension -eq '.ttf' -or $_.Extension -eq '.otf')
})
$needed = @($serifTtf + $sansTtf)
if ($serifTtf.Count -eq 0) {
    $needed += @($allFontFiles | Where-Object { $_.Name -eq 'reMarkableSerif.woff2' })
}
if ($sansTtf.Count -eq 0) {
    $needed += @($allFontFiles | Where-Object { $_.Name -eq 'reMarkableSans.woff2' })
}
# de-dupe by name
$seen = @{}
$needed = @($needed | Where-Object {
    if (-not $_ -or $seen.ContainsKey($_.Name)) { return $false }
    $seen[$_.Name] = $true
    $true
})

if ($needed.Count -eq 0) {
    Write-Warning "no reMarkable Serif Small / Sans fonts found under $Fonts — zip skipped"
    Write-Host "names present:"
    $allFontFiles | Select-Object -First 40 Name | ForEach-Object { Write-Host ("  " + $_.Name) }
} else {
    $lines = @(
        "remarkable_onenote_fonts  rev=$ScriptRev"
        "Install on Windows: select *.ttf/*.otf → right-click → Install for all users."
        "OneNote CSS expects families: 'reMarkable Serif Small' and 'reMarkable Sans'."
        "Do not commit this zip to a public repo (proprietary)."
        ""
    )
    foreach ($f in $needed) {
        Copy-Item -LiteralPath $f.FullName -Destination (Join-Path $Stage $f.Name) -Force
        $lines += ("{0}  {1} bytes  from {2}" -f $f.Name, $f.Length, $f.FullName)
        Write-Host ("  pack {0}" -f $f.Name)
    }
    $lines -join "`n" | Set-Content -Encoding utf8 (Join-Path $Stage 'INSTALL.txt')
    if (Test-Path -LiteralPath $ZipPath) { Remove-Item -LiteralPath $ZipPath -Force }
    Compress-Archive -Path (Join-Path $Stage '*') -DestinationPath $ZipPath -Force
    Write-Host ("zip -> {0}  ({1} files, {2:N1} KB)" -f $ZipPath, $needed.Count, ((Get-Item $ZipPath).Length / 1KB))
}
