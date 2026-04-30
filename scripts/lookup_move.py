#!/usr/bin/env python3
"""
技データ lookup CLI (SSOT: data/moves.json)

使用例:
  python3 scripts/lookup_move.py ポルターガイスト
  python3 scripts/lookup_move.py poltergeist
  python3 scripts/lookup_move.py "がんせきふうじ" "こごえるかぜ" "シャドーボール"

設計:
- moves.json (Showdown commit pinned in VERSION.json) を SSOT として参照
- 構築ファイル等で技データを「コピー」せず、これを呼び出して都度 lookup
- ダメ計バイナリ (bin/pokechamp-calc) と同じ原則 = データ二重管理を排除
"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.lookup import resolve_move, get_jp_name
from lib.champions_overlay import (
    get_move_overlayed,
    is_implemented,
    get_implementation_note,
)


def format_secondary(s: dict) -> str:
    if not s:
        return ""
    out = []
    ch = s.get("chance", "?")
    if "boosts" in s:
        for stat, v in s["boosts"].items():
            out.append(f"{stat}{v:+} {ch}%")
    if "status" in s:
        out.append(f"状態:{s['status']} {ch}%")
    if "volatileStatus" in s:
        out.append(f"vol:{s['volatileStatus']} {ch}%")
    return " / ".join(out)


def _format_was_note(meta: dict) -> str:
    """Build a 'Showdown 標準: X' suffix from _champions_meta, or empty string."""
    if not meta:
        return ""
    parts = []
    if "_was_chance" in meta:
        parts.append(f"Showdown 標準: {meta['_was_chance']}%")
    if "_was" in meta:
        parts.append(f"Showdown 標準: {meta['_was']}")
    if "_was_boosts" in meta:
        parts.append(f"Showdown 標準 boosts: {meta['_was_boosts']}")
    if "_note" in meta:
        parts.append(meta["_note"])
    if "_source" in meta:
        parts.append(f"出典: {meta['_source']}")
    return " (" + " / ".join(parts) + ")" if parts else ""


def display(query: str) -> None:
    r = resolve_move(query)
    mid = r.get("id")
    if not mid or r.get("match_type") == "none":
        cands = r.get("candidates", [])
        print(f"X '{query}' not found. 候補: {cands[:5] if cands else 'なし'}")
        return
    # Use overlay-applied move data (Champions-aware)
    m = get_move_overlayed(mid)
    if not m:
        print(f"X '{query}' resolved to '{mid}' but moves.json lookup failed")
        return
    meta = m.get("_champions_meta")
    champ_marker = " [Champions 仕様適用]" if meta else ""
    jp = get_jp_name("moves", mid) or "?"
    print(f"\n>> {jp} ({m.get('name', '?')}, id: {mid}) [match: {r.get('match_type')}]{champ_marker}")
    # Implementation status warning
    if not is_implemented("moves", mid):
        note = get_implementation_note("moves", mid) or ""
        print(f"  !!! Champions 未実装: {note}")
    print(f"  威力       : {m.get('basePower', 0) or '-'}")
    acc = m.get("accuracy", True)
    print(f"  命中       : {'無条件 (必中)' if acc is True else f'{acc}%'}")
    print(f"  分類       : {m.get('category', '-')}")
    print(f"  タイプ     : {m.get('type', '-')}")
    print(f"  PP         : {m.get('pp', '-')}")
    pri = m.get("priority", 0)
    if pri != 0:
        print(f"  優先度     : {pri:+}")
    print(f"  対象       : {m.get('target', '-')}")

    # 追加効果
    effects = []
    if "secondary" in m and m["secondary"]:
        effects.append(format_secondary(m["secondary"]))
    if "secondaries" in m and m["secondaries"]:
        for s in m["secondaries"]:
            effects.append(format_secondary(s))
    if "self" in m and m["self"]:
        sd = m["self"].get("boosts", {})
        for stat, v in sd.items():
            effects.append(f"自{stat}{v:+}")
        if "volatileStatus" in m["self"]:
            effects.append(f"自 vol:{m['self']['volatileStatus']}")
    if "volatileStatus" in m:
        effects.append(f"vol:{m['volatileStatus']}")
    if "status" in m:
        effects.append(f"status:{m['status']}")
    if "sideCondition" in m:
        effects.append(f"設置:{m['sideCondition']}")
    if "forceSwitch" in m:
        effects.append("強制交代")
    if "drain" in m:
        d = m["drain"]
        effects.append(f"吸収 {d[0]}/{d[1]}")
    if "recoil" in m:
        r2 = m["recoil"]
        effects.append(f"反動 {r2[0]}/{r2[1]}")
    if effects:
        print(f"  追加効果   : {' / '.join(filter(None, effects))}")
    desc = m.get("shortDesc", "") or m.get("desc", "")
    if desc:
        print(f"  説明       : {desc[:120]}")
    if meta:
        print(f"  Champions差分 : {_format_was_note(meta).strip(' ()')}")


def main():
    if len(sys.argv) < 2:
        print("使用法: python3 scripts/lookup_move.py <技名> [技名2 ...]")
        print("例    : python3 scripts/lookup_move.py ポルターガイスト しんそく")
        sys.exit(1)
    for q in sys.argv[1:]:
        display(q)


if __name__ == "__main__":
    main()
