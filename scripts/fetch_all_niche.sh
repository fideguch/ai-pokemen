#!/usr/bin/env bash
# fetch_all_niche.sh
# ----------------------------------------------------------------------------
# SKILL.md HG-niche-depth (2026-05-01) で要求された niche 妨害技 全件 fetch。
# fetch_niche_users.py の SEED 辞書から技名キーを取り出し、順次 fetch する。
# 各技は内部 24h TTL で gate 済み (cache/niche_users/YYYY-MM-DD/<move>.json)。
# launchd com.fideguch.pokechamp-fetch-niche から呼ばれる前提。
# ----------------------------------------------------------------------------
set -euo pipefail

ROOT="/Users/fumito_ideguchi/ai-pokemen"
PY="/Users/fumito_ideguchi/.pyenv/shims/python3"
TS() { date '+%Y-%m-%dT%H:%M:%S%z'; }

cd "$ROOT"

echo "[$(TS)] === fetch_all_niche start ==="

# SEED 辞書のキーを Python 経由で取り出す (SSOT を script に複製しない)
# macOS デフォルトの Bash 3.2 は mapfile 非対応 → while read で互換実装
MOVES=()
while IFS= read -r line; do
  [[ -n "$line" ]] && MOVES+=("$line")
done < <(
  "$PY" -c "
import sys
sys.path.insert(0, 'scripts')
import fetch_niche_users as f
for k in f.NICHE_USERS_SEED.keys():
    print(k)
"
)

if [[ ${#MOVES[@]} -eq 0 ]]; then
  echo "[$(TS)] [ERROR] SEED list empty — abort"
  exit 1
fi

echo "[$(TS)] target moves: ${#MOVES[@]} (${MOVES[*]})"

OK=0
FAIL=0
for mv in "${MOVES[@]}"; do
  # 各 move は failure isolation: 1 つコケても次に進む
  if "$PY" scripts/fetch_niche_users.py "$mv" >/dev/null 2>&1; then
    OK=$((OK + 1))
    echo "[$(TS)] OK   $mv"
  else
    FAIL=$((FAIL + 1))
    echo "[$(TS)] FAIL $mv"
  fi
  # 行儀よく 2s インターバル (champs.pokedb への負荷配慮)
  sleep 2
done

echo "[$(TS)] === fetch_all_niche done: OK=$OK FAIL=$FAIL / total=${#MOVES[@]} ==="
exit 0
