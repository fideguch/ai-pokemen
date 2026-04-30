#!/usr/bin/env python3
"""
Build data/champions_overrides.json from a static source-of-truth dictionary.

This script regenerates the overrides JSON from in-script data so the file is
reproducible and reviewable in git diff. To update overrides:
1. Edit OVERRIDES dict below.
2. Run: python3 scripts/build_champions_overrides.py
3. Commit data/champions_overrides.json with the script change.

Source references: references/champions_overrides_sources.md
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "champions_overrides.json"

# -----------------------------------------------------------------------------
# Source-of-truth overrides dict
# -----------------------------------------------------------------------------
OVERRIDES: dict = {
    "schema_version": "1.0.0",
    "source_refs": ["references/champions_overrides_sources.md"],

    # Move base / secondary effects nerf
    "moves": {
        "moonblast": {
            "secondary": {"chance": 10, "boosts": {"spa": -1}},
            "_was_chance": 30,
            "_source": "game8",
        },
        "ironhead": {
            "secondary": {"chance": 20, "volatileStatus": "flinch"},
            "_was_chance": 30,
            "_source": "altema",
        },
        "fakeout": {
            "secondary": {"chance": 30, "volatileStatus": "flinch"},
            "_was_chance": 100,
            "_note": "ねこだまし ひるみ確率を 100%→30% にナーフ",
            "_source": "gamepedia",
        },
        "shadowball": {
            "secondary": {"chance": 10, "boosts": {"spd": -1}},
            "_was_chance": 20,
            "_source": "game8",
        },
        "freezedry": {
            "_secondary_removed": True,
            "_was": {"chance": 10, "status": "frz"},
            "_note": "凍結追加効果を削除",
            "_source": "gamepedia",
        },
        "leechseed": {
            "_drain_per_turn": "1/16",
            "_was": "1/8",
            "_source": "altema",
        },
        "saltcure": {
            "_dmg_per_turn": "1/16",
            "_was": "1/8",
            "_note": "水/鋼相手は 1/8 維持",
            "_source": "game8",
        },
        "toxicspikes": {
            "_dmg_per_turn": "1/16",
            "_was": "1/8",
            "_source": "gamepedia",
        },
    },

    # Ability overrides (text-only notes for now; runtime effect handled in calc)
    "abilities": {
        "ironfist": {
            "_note": "ふかしのこぶし: 守る貫通時に 1/4 ダメ追加 (Champions 仕様)",
            "_source": "note",
        },
    },

    # Item overrides (none currently; all changes captured in implementation flag)
    "items": {},

    # Status condition overrides
    "conditions": {
        "par": {
            "fullParalysisChance": 0.125,
            "_was": 0.25,
            "_source": "game8/altema",
        },
        "frz": {
            "thawByTurn": 3,
            "_was": "permanent (20%/T 解除)",
            "_source": "game8",
        },
        "slp": {
            "guaranteedWakeByTurn": 3,
            "_was": "1-3 turns (random)",
            "_source": "gamepedia",
        },
    },

    # Per-pokemon move list adjustments
    "removed_moves_per_pokemon": {
        "kommoo": ["bodypress"],
        "gengar": ["encore"],
        "dragonite": ["encore"],
        "kangaskhan": ["powerupperch"],
        "incineroar": ["knockoff", "uturn"],
        "gliscor": ["taunt"],
    },
    "added_moves_per_pokemon": {
        "aegislash": ["poltergeist"],
        "gyarados": ["powerwhip"],
        "charizard": ["scaleshot"],
        "greninja": ["flipturn"],
        "sylveon": ["mysticalfire"],
        "tyranitar": ["superpower"],
        "scizor": ["roost"],
    },

    # Move buffs (basePower / accuracy / boosts)
    "buffs_moves": {
        "gforce": {"basePower": 90, "_was": 80, "_source": "note"},
        "tropicalkick": {"basePower": 85, "_was": 70, "_source": "note"},
        "iceberg": {"basePower": 120, "_was": 100, "_source": "note"},
        "wakeupslap": {"basePower": 100, "_was": 70, "_source": "gamepedia"},
        "crabhammer": {"accuracy": 95, "_was": 90, "_source": "game8"},
        "toxicthread": {
            "boosts": {"spe": -2},
            "_was_boosts": {"spe": -1},
            "_source": "altema",
        },
    },
}


def build() -> dict:
    """Return the overrides dict with generated_at timestamp."""
    out = dict(OVERRIDES)  # shallow copy
    out["generated_at"] = datetime.now(timezone.utc).isoformat()
    return out


def main() -> None:
    payload = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT}")
    print(f"  schema_version: {payload['schema_version']}")
    print(f"  generated_at:   {payload['generated_at']}")
    print(f"  moves:          {len(payload['moves'])}")
    print(f"  buffs_moves:    {len(payload['buffs_moves'])}")
    print(f"  conditions:     {len(payload['conditions'])}")
    print(f"  removed_moves_per_pokemon: {len(payload['removed_moves_per_pokemon'])}")
    print(f"  added_moves_per_pokemon:   {len(payload['added_moves_per_pokemon'])}")


if __name__ == "__main__":
    main()
