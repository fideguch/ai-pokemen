#!/usr/bin/env python3
"""
Build data/champions_implementation.json from a static source-of-truth dictionary.

This file is the SSOT for "what is implemented in Pokemon Champions vs not".
Categories:
- items: 持ち物 (実装済 / 未実装)
- moves: 技 (Champions 追加 / 削除技)
- pokemon: 各個体 (gmax は全 34 体未実装、リージョンフォームは全 55 体 TBD)
- megastones: メガストーン (Champions 公式アナウンス要確認)

Re-run on Champions patch updates:
    python3 scripts/build_champions_implementation.py

Source: references/implementation_status.md + references/champions_overrides_sources.md
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "champions_implementation.json"
POKEDEX = ROOT / "data" / "pokedex.json"
ITEMS = ROOT / "data" / "items.json"


# -----------------------------------------------------------------------------
# Static implementation status
# -----------------------------------------------------------------------------

# 持ち物: True=実装、False=未実装、TBD=確認待ち
ITEMS_STATIC: dict[str, dict] = {
    # 未実装 (構築提案禁止)
    "rockyhelmet":      {"implemented": False, "jp_name": "ゴツゴツメット", "_note": "Champions 未実装 (公式DB未確認)"},
    "choiceband":       {"implemented": False, "jp_name": "こだわりハチマキ", "_note": "Champions 未実装"},
    "choicespecs":      {"implemented": False, "jp_name": "こだわりメガネ",   "_note": "Champions 未実装"},
    "choicescarf":      {"implemented": True,  "jp_name": "こだわりスカーフ"},
    "lifeorb":          {"implemented": False, "jp_name": "いのちのたま",     "_note": "Champions 未実装"},
    "assaultvest":      {"implemented": False, "jp_name": "とつげきチョッキ", "_note": "Champions 未実装"},
    "heavydutyboots":   {"implemented": False, "jp_name": "あつぞこブーツ",   "_note": "Champions 未実装"},
    "weaknesspolicy":   {"implemented": False, "jp_name": "じゃくてんほけん", "_note": "Champions 未実装"},
    "redcard":          {"implemented": False, "jp_name": "レッドカード",     "_note": "Champions 未実装"},
    "custapberry":      {"implemented": False, "jp_name": "イバンのみ",       "_note": "Champions 未実装"},
    "ejectbutton":      {"implemented": False, "jp_name": "だっしゅつボタン", "_note": "Champions 未実装"},
    "ejectpack":        {"implemented": False, "jp_name": "だっしゅつパック", "_note": "Champions 未実装"},

    # 実装済
    "focussash":        {"implemented": True,  "jp_name": "きあいのタスキ"},
    "leftovers":        {"implemented": True,  "jp_name": "たべのこし"},
    "sitrusberry":      {"implemented": True,  "jp_name": "オボンのみ"},
    "lumberry":         {"implemented": True,  "jp_name": "ラムのみ"},
    "blacksludge":      {"implemented": True,  "jp_name": "くろいヘドロ"},
    "rockyhelmet_TBD":  {"implemented": "TBD", "jp_name": "(参考: 半減きのみ系は別途登録)"},
}

# 技: 実装済 (Champions 追加)
MOVES_STATIC: dict[str, dict] = {
    "poltergeist":  {"implemented": True, "jp_name": "ポルターガイスト"},
    "powerwhip":    {"implemented": True, "jp_name": "パワーウィップ"},
    "scaleshot":    {"implemented": True, "jp_name": "うろこのいし"},
    "flipturn":     {"implemented": True, "jp_name": "フリップターン"},
    "mysticalfire": {"implemented": True, "jp_name": "マジカルフレイム"},
    "superpower":   {"implemented": True, "jp_name": "ばかぢから"},
    "roost":        {"implemented": True, "jp_name": "はねやすめ"},
}

# Megastone known-implemented set (Champions has Mega Evolution per official trailer)
# 公式アナウンス済 = True、未確認 = TBD
MEGASTONES_KNOWN_IMPLEMENTED: set[str] = {
    "charizarditex", "charizarditey",
    "gengarite",
    "garchompite",
    "tyranitarite",
    "scizorite",
    "lucarionite",
    "salamencite",
    "metagrossite",
    "blastoisinite",
    "venusaurite",
    "alakazite",
    "kangaskhanite",
    "mewtwonitex", "mewtwonitey",
    "blazikenite",
    "gardevoirite",
    "absolite",
    "manectite",
    "houndoominite",
    "aerodactylite",
    "ampharosite",
    "banettite",
    "lopunnite",
    "mawilite",
    "medichamite",
    "pinsirite",
    "sablenite",
    "sceptilite",
    "swampertite",
    "aggronite",
    "audinite",
    "beedrillite",
    "cameruptite",
    "diancite",
    "galladite",
    "glalitite",
    "heracronite",
    "latiasite", "latiosite",
    "pidgeotite",
    "sharpedonite",
    "slowbronite",
    "steelixite",
}


# -----------------------------------------------------------------------------
# Dynamic generators (read from data/*.json)
# -----------------------------------------------------------------------------

def _load_pokedex() -> dict:
    return json.loads(POKEDEX.read_text(encoding="utf-8"))


def _load_items() -> dict:
    return json.loads(ITEMS.read_text(encoding="utf-8"))


def gen_gmax_entries() -> dict[str, dict]:
    """All gmax entries → implemented=False (not in Champions)."""
    pdex = _load_pokedex()
    out = {}
    for k, v in pdex.items():
        if k.endswith("gmax"):
            out[k] = {
                "implemented": False,
                "reason": "キョダイマックスは Champions に存在しない (SWSH 特有、Champions ベースは SV)",
            }
    return out


def gen_regional_form_entries() -> dict[str, dict]:
    """Alola/Galar/Hisui/Paldea forms → implemented=TBD (公式確認待ち)."""
    pdex = _load_pokedex()
    out = {}
    for k in pdex.keys():
        if k.endswith(("alola", "galar", "hisui", "paldea")):
            out[k] = {
                "implemented": "TBD",
                "reason": "リージョンフォームの実装は Champions 公式アナウンス要確認",
            }
    return out


def gen_megastone_entries() -> dict[str, dict]:
    """All megastones → True if in known set, else TBD."""
    items = _load_items()
    out = {}
    for k, v in items.items():
        if v.get("megaStone") is None:
            continue
        jp = v.get("name", k)
        if k in MEGASTONES_KNOWN_IMPLEMENTED:
            out[k] = {"implemented": True, "jp_name": jp}
        else:
            out[k] = {
                "implemented": "TBD",
                "jp_name": jp,
                "reason": "Champions 公式アナウンス要確認",
            }
    return out


# -----------------------------------------------------------------------------
# Build
# -----------------------------------------------------------------------------

def build() -> dict:
    pokemon_entries: dict[str, dict] = {}
    pokemon_entries.update(gen_gmax_entries())
    pokemon_entries.update(gen_regional_form_entries())

    return {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": ITEMS_STATIC,
        "moves": MOVES_STATIC,
        "pokemon": pokemon_entries,
        "megastones": gen_megastone_entries(),
    }


def main() -> None:
    payload = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT}")
    print(f"  schema_version: {payload['schema_version']}")
    print(f"  items:          {len(payload['items'])}")
    print(f"  moves:          {len(payload['moves'])}")
    print(f"  pokemon (total):  {len(payload['pokemon'])}")
    gmax_count = sum(1 for k in payload['pokemon'] if k.endswith('gmax'))
    print(f"    - gmax:       {gmax_count}")
    form_count = len(payload['pokemon']) - gmax_count
    print(f"    - regional:   {form_count}")
    print(f"  megastones:     {len(payload['megastones'])}")
    impl_megas = sum(1 for v in payload['megastones'].values() if v.get('implemented') is True)
    print(f"    - confirmed:  {impl_megas}")


if __name__ == "__main__":
    main()
