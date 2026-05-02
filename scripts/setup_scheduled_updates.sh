#!/usr/bin/env bash
# setup_scheduled_updates.sh
# ----------------------------------------------------------------------------
# Pokemon Champions skill の定期更新 launchd ジョブを冪等に登録する。
#
# 登録対象:
#   1. com.fideguch.pokechamp-fetch-usage  (champs/pokechamdb usage, 6h cycle)
#   2. com.fideguch.pokechamp-fetch-yt     (KYOUPOKE/クロコ/ポケソル, daily 06:00)
#   3. com.fideguch.pokechamp-fetch-niche  (niche 妨害技 11 種, daily 05:00)
#
# 実行は冪等。既に load 済みでも再 load される (-w で plist の Disabled キーを上書き)。
# このスクリプトは SessionStart hook (pokechamp-ensure-schedule.sh) からも呼ばれる。
# ----------------------------------------------------------------------------
set -euo pipefail

LA_DIR="$HOME/Library/LaunchAgents"
LOG_DIR="$HOME/.claude/logs"
mkdir -p "$LOG_DIR"

JOBS=(
  "com.fideguch.pokechamp-fetch-usage"
  "com.fideguch.pokechamp-fetch-yt"
  "com.fideguch.pokechamp-fetch-niche"
)

TS() { date '+%Y-%m-%dT%H:%M:%S%z'; }
GUI_DOMAIN="gui/$(id -u)"

echo "[$(TS)] === pokechamp scheduled updates setup ==="

# Pre-flight: plist が全部ある？
missing=0
for label in "${JOBS[@]}"; do
  plist="$LA_DIR/${label}.plist"
  if [[ ! -f "$plist" ]]; then
    echo "[$(TS)] [ERROR] missing plist: $plist"
    missing=$((missing + 1))
  fi
done
if [[ $missing -gt 0 ]]; then
  echo "[$(TS)] [ERROR] $missing plist file(s) missing — copy them to $LA_DIR first"
  exit 1
fi

# launchctl load -w (冪等: 既 load 済みなら error が出るが続行)
for label in "${JOBS[@]}"; do
  plist="$LA_DIR/${label}.plist"
  if launchctl print "$GUI_DOMAIN/$label" >/dev/null 2>&1; then
    echo "[$(TS)] already-loaded: $label (re-load to pick up plist edits)"
    launchctl bootout "$GUI_DOMAIN/$label" 2>/dev/null || true
  fi
  if launchctl bootstrap "$GUI_DOMAIN" "$plist" 2>/dev/null; then
    echo "[$(TS)] bootstrap OK: $label"
  else
    # bootstrap が失敗したら旧 API へフォールバック
    if launchctl load -w "$plist" 2>/dev/null; then
      echo "[$(TS)] load (legacy) OK: $label"
    else
      echo "[$(TS)] [WARN] failed to load $label — check $LOG_DIR/${label}.launchd.err.log"
    fi
  fi
done

# 検証: launchctl list で全部見えるか
echo "[$(TS)] --- verification ---"
all_present=1
for label in "${JOBS[@]}"; do
  if launchctl list "$label" >/dev/null 2>&1; then
    echo "[$(TS)] ✓ registered: $label"
  else
    echo "[$(TS)] ✗ NOT registered: $label"
    all_present=0
  fi
done

if [[ $all_present -eq 1 ]]; then
  echo "[$(TS)] === ALL JOBS REGISTERED ==="
  exit 0
else
  echo "[$(TS)] === PARTIAL FAILURE — see logs ==="
  exit 2
fi
