"""Champions overrides + implementation overlay layer.

This module provides Champions-aware lookups by merging:
- Showdown raw data (data/{moves,items,abilities}.json) — via lib.lookup.*_raw
- Champions overrides (data/champions_overrides.json) — Showdown-value diff
- Champions implementation flags (data/champions_implementation.json) — feature on/off

Design notes:
- The raw lib.lookup functions are unchanged (lru_cache on raw JSON).
- This overlay never mutates raw cached dicts; it returns deep copies with
  overrides merged.
- get_*_overlayed: returns Champions-applied value (use for user-facing output).
- get_*_raw (in lib.lookup): returns Showdown value (use for damage calc input).

Usage:
    from lib.champions_overlay import (
        get_move_overlayed, get_item_overlayed, get_ability_overlayed,
        is_implemented, get_implementation_note, load_overrides,
    )
"""
from __future__ import annotations

import copy
import functools
import json
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OVERRIDES_PATH = DATA_DIR / "champions_overrides.json"
IMPLEMENTATION_PATH = DATA_DIR / "champions_implementation.json"


# -----------------------------------------------------------------------------
# Loaders (cached)
# -----------------------------------------------------------------------------


@functools.lru_cache(maxsize=1)
def load_overrides() -> dict[str, Any]:
    """Load data/champions_overrides.json. Returns empty dict if missing."""
    if not OVERRIDES_PATH.exists():
        return {
            "schema_version": "0.0.0",
            "moves": {},
            "items": {},
            "abilities": {},
            "conditions": {},
            "buffs_moves": {},
            "removed_moves_per_pokemon": {},
            "added_moves_per_pokemon": {},
        }
    return json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=1)
def load_implementation() -> dict[str, Any]:
    """Load data/champions_implementation.json. Returns empty dict if missing."""
    if not IMPLEMENTATION_PATH.exists():
        return {
            "schema_version": "0.0.0",
            "items": {},
            "moves": {},
            "pokemon": {},
            "megastones": {},
        }
    return json.loads(IMPLEMENTATION_PATH.read_text(encoding="utf-8"))


# -----------------------------------------------------------------------------
# Deep merge helper
# -----------------------------------------------------------------------------


def _deep_merge(base: Any, override: Any) -> Any:
    """Recursively merge override into base.

    Rules:
    - If both are dict, merge keys (override wins on conflict).
    - Otherwise, override replaces base entirely.
    - Keys starting with "_" in override are metadata (carried through but do not
      themselves replace base content).
    """
    if isinstance(base, dict) and isinstance(override, dict):
        out = dict(base)  # shallow copy of base
        for k, v in override.items():
            if k in out:
                out[k] = _deep_merge(out[k], v)
            else:
                out[k] = copy.deepcopy(v)
        return out
    # Non-dict or type mismatch: override wins
    return copy.deepcopy(override)


# -----------------------------------------------------------------------------
# Per-category overlay appliers
# -----------------------------------------------------------------------------


def apply_move_overrides(mid: str, base: dict) -> dict:
    """Return base merged with overrides for move id `mid`.

    Handles:
    - moves[mid]: secondary/secondaries chance/effect changes
    - moves[mid]._secondary_removed: True -> drop secondary entirely
    - buffs_moves[mid]: basePower / accuracy / boosts overrides
    """
    if base is None:
        return None
    overrides = load_overrides()
    out = copy.deepcopy(base)

    # 1. Apply moves overrides
    move_ovr = overrides.get("moves", {}).get(mid)
    if move_ovr:
        # Special: full removal of secondary
        if move_ovr.get("_secondary_removed"):
            out.pop("secondary", None)
            out.pop("secondaries", None)
        # Merge non-meta keys
        for k, v in move_ovr.items():
            if k.startswith("_"):
                # Metadata: store in _champions_meta
                out.setdefault("_champions_meta", {})[k] = v
                continue
            if k in ("secondary", "secondaries"):
                out[k] = copy.deepcopy(v)
            else:
                out[k] = _deep_merge(out.get(k), v)

    # 2. Apply buffs_moves
    buff_ovr = overrides.get("buffs_moves", {}).get(mid)
    if buff_ovr:
        for k, v in buff_ovr.items():
            if k.startswith("_"):
                out.setdefault("_champions_meta", {})[k] = v
                continue
            out[k] = _deep_merge(out.get(k), v)

    return out


def apply_item_overrides(iid: str, base: dict) -> dict:
    if base is None:
        return None
    overrides = load_overrides()
    out = copy.deepcopy(base)
    item_ovr = overrides.get("items", {}).get(iid)
    if item_ovr:
        for k, v in item_ovr.items():
            if k.startswith("_"):
                out.setdefault("_champions_meta", {})[k] = v
            else:
                out[k] = _deep_merge(out.get(k), v)
    return out


def apply_ability_overrides(aid: str, base: dict) -> dict:
    if base is None:
        return None
    overrides = load_overrides()
    out = copy.deepcopy(base)
    abil_ovr = overrides.get("abilities", {}).get(aid)
    if abil_ovr:
        for k, v in abil_ovr.items():
            if k.startswith("_"):
                out.setdefault("_champions_meta", {})[k] = v
            else:
                out[k] = _deep_merge(out.get(k), v)
    return out


# -----------------------------------------------------------------------------
# High-level get_*_overlayed (raw lookup -> overlay)
# -----------------------------------------------------------------------------


def get_move_overlayed(mid: str) -> Optional[dict]:
    """Return the overlay-applied move dict, or None if mid not in moves.json."""
    # Lazy import to avoid circular import (lib.lookup imports nothing from us).
    from lib.lookup import get_move_raw

    base = get_move_raw(mid)
    if base is None:
        return None
    return apply_move_overrides(mid, base)


def get_item_overlayed(iid: str) -> Optional[dict]:
    from lib.lookup import get_item_raw

    base = get_item_raw(iid)
    if base is None:
        return None
    return apply_item_overrides(iid, base)


def get_ability_overlayed(aid: str) -> Optional[dict]:
    from lib.lookup import get_ability_raw

    base = get_ability_raw(aid)
    if base is None:
        return None
    return apply_ability_overrides(aid, base)


# -----------------------------------------------------------------------------
# Implementation flag accessors
# -----------------------------------------------------------------------------


def is_implemented(category: str, sid: str) -> bool:
    """Return True if Champions implements this entity, False otherwise.

    Default: True (assume implemented unless explicitly marked otherwise).
    Categories: "items" | "moves" | "pokemon" | "megastones"
    """
    impl = load_implementation()
    cat = impl.get(category, {})
    entry = cat.get(sid)
    if entry is None:
        # Unknown -> default True (no false negatives), but caller can use
        # get_implementation_note to detect missing entries.
        return True
    if isinstance(entry, dict):
        return bool(entry.get("implemented", True))
    return bool(entry)


def get_implementation_note(category: str, sid: str) -> Optional[str]:
    """Return a human-readable note about implementation status, or None."""
    impl = load_implementation()
    entry = impl.get(category, {}).get(sid)
    if not isinstance(entry, dict):
        return None
    parts = []
    if "_note" in entry:
        parts.append(entry["_note"])
    if "reason" in entry:
        parts.append(entry["reason"])
    if "jp_name" in entry:
        parts.append(f"JP: {entry['jp_name']}")
    return " / ".join(parts) if parts else None


# -----------------------------------------------------------------------------
# CLI entry (debug helper)
# -----------------------------------------------------------------------------


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: champions_overlay.py <category> <sid>")
        print("  category: move | item | ability | impl-item | impl-pokemon")
        sys.exit(2)
    cat, sid = sys.argv[1], sys.argv[2]
    fn = {
        "move": get_move_overlayed,
        "item": get_item_overlayed,
        "ability": get_ability_overlayed,
    }.get(cat)
    if fn:
        print(json.dumps(fn(sid), ensure_ascii=False, indent=2))
    elif cat == "impl-item":
        print(f"implemented: {is_implemented('items', sid)}")
        print(f"note: {get_implementation_note('items', sid)}")
    elif cat == "impl-pokemon":
        print(f"implemented: {is_implemented('pokemon', sid)}")
        print(f"note: {get_implementation_note('pokemon', sid)}")
    else:
        print(f"Unknown category: {cat}")
        sys.exit(2)
