#!/usr/bin/env bash
# Pull reMarkable fonts + fontconfig (+ optional xochitl size hints) over SSH.
#
# Run from a machine that can reach the tablet (USB 10.11.99.1 or Wi‑Fi IP):
#   ./scripts/pull_remarkable_fonts.sh
#   RM_HOST=192.168.1.50 RM_PASS=… ./scripts/pull_remarkable_fonts.sh
#
# Needs: ssh, scp; sshpass if using RM_PASS. Enable SSH in tablet Settings.
set -euo pipefail

HOST="${RM_HOST:-10.11.99.1}"
USER="${RM_USER:-root}"
OUT="${RM_OUT:-tests/expected/device_fonts}"
SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o ConnectTimeout=8)

ssh_cmd() {
  if [[ -n "${RM_PASS:-}" ]]; then
    command -v sshpass >/dev/null || { echo "need sshpass for RM_PASS" >&2; exit 1; }
    sshpass -p "$RM_PASS" ssh "${SSH_OPTS[@]}" "$USER@$HOST" "$@"
  else
    ssh "${SSH_OPTS[@]}" "$USER@$HOST" "$@"
  fi
}

scp_cmd() {
  if [[ -n "${RM_PASS:-}" ]]; then
    sshpass -p "$RM_PASS" scp "${SSH_OPTS[@]}" "$@"
  else
    scp "${SSH_OPTS[@]}" "$@"
  fi
}

mkdir -p "$OUT"/{fonts,fontconfig,meta}
echo "→ $USER@$HOST  out=$OUT"

ssh_cmd 'uname -a; cat /etc/os-release 2>/dev/null | head -5; ls /usr/bin/xochitl 2>/dev/null; which fc-list fc-match 2>/dev/null' \
  | tee "$OUT/meta/device.txt"

# Font inventory (what xochitl actually resolves)
ssh_cmd 'fc-list : family file | sort' >"$OUT/meta/fc-list.txt" || true
ssh_cmd 'for f in "EB Garamond" "Noto Sans" "Noto Serif" "Noto Sans Mono" serif sans-serif; do
  echo "=== $f ==="
  fc-match -v "$f" 2>/dev/null | egrep "family:|file:|style:|slant:|weight:|size:" || fc-match "$f"
done' >"$OUT/meta/fc-match.txt" || true

# fontconfig
ssh_cmd 'ls -la /etc/fonts /usr/share/fontconfig 2>/dev/null; find /etc/fonts /usr/share/fontconfig -type f 2>/dev/null | head -200' \
  >"$OUT/meta/fontconfig-index.txt" || true
mkdir -p "$OUT/fontconfig"
scp_cmd -r "$USER@$HOST:/etc/fonts/." "$OUT/fontconfig/etc-fonts/" 2>/dev/null || true

# Font files (common locations on remarkable OS)
ssh_cmd 'find /usr/share/fonts /home/root/.local/share/fonts /usr/lib/fonts -type f \( -name "*.ttf" -o -name "*.otf" -o -name "*.ttc" \) 2>/dev/null' \
  >"$OUT/meta/font-files.txt" || true

while IFS= read -r remote; do
  [[ -z "$remote" ]] && continue
  base=$(basename "$remote")
  dir=$(dirname "$remote" | tr '/' '_')
  mkdir -p "$OUT/fonts/$dir"
  scp_cmd "$USER@$HOST:$remote" "$OUT/fonts/$dir/$base" 2>/dev/null || true
done <"$OUT/meta/font-files.txt"

# xochitl strings that look like style / pt / font size tables
ssh_cmd 'strings /usr/bin/xochitl 2>/dev/null | egrep -i "garamond|noto|heading|font.?size|FontSize|pointSize|textStyle|ParagraphStyle|EBGaramond" | sort -u | head -400' \
  >"$OUT/meta/xochitl-font-strings.txt" || true

# Package list (what else ships with text stack)
ssh_cmd 'opkg list-installed 2>/dev/null | egrep -i "font|freetype|harfbuzz|qt" | head -80' \
  >"$OUT/meta/opkg-fonts-qt.txt" || true

echo "done → $OUT"
du -sh "$OUT" "$OUT/fonts" 2>/dev/null
ls "$OUT/meta"
