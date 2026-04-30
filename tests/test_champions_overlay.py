#!/usr/bin/env python3
"""
Champions overlay tests.

Validates the 3-layer SSOT contract:
- Showdown raw (lib.lookup.get_*_raw) returns vanilla Showdown values
- Champions overlay (lib.champions_overlay.get_*_overlayed) applies Champions diffs
- Implementation flags (lib.champions_overlay.is_implemented) gate construction

Note on lookup design choice:
The plan originally proposed making `get_move` (and friends) overlay-applied
by default. We kept `get_move` as raw + added explicit `get_move_raw` aliases
to protect the damage calc input path. Damage calc MUST always read raw
Showdown semantics; overlay values would silently corrupt formulas.
Tests cover both code paths and the design invariant.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.lookup import get_move, get_move_raw, get_item, get_item_raw
from lib.champions_overlay import (
    apply_move_overrides,
    get_move_overlayed,
    get_item_overlayed,
    is_implemented,
    get_implementation_note,
    load_overrides,
    load_implementation,
)


class TestMoveOverlay(unittest.TestCase):
    """Move-level Champions overrides."""

    def test_moonblast_champions_chance_10(self):
        """Moonblast SpA-1 chance should be 10% under Champions."""
        m = get_move_overlayed("moonblast")
        self.assertIsNotNone(m, "moonblast missing from moves.json")
        # Showdown stores it under 'secondary' (singular) for this move
        sec = m.get("secondary") or (m.get("secondaries") or [{}])[0]
        self.assertEqual(sec.get("chance"), 10,
                         f"expected Champions chance=10, got {sec.get('chance')}")

    def test_moonblast_raw_chance_30(self):
        """Showdown raw moonblast chance is 30%."""
        m = get_move_raw("moonblast")
        sec = m.get("secondary") or (m.get("secondaries") or [{}])[0]
        self.assertEqual(sec.get("chance"), 30,
                         f"expected Showdown raw chance=30, got {sec.get('chance')}")

    def test_ironhead_champions_chance_20(self):
        """Iron Head flinch chance: Champions 20% vs Showdown 30%."""
        overlay = get_move_overlayed("ironhead").get("secondary", {})
        raw = get_move_raw("ironhead").get("secondary", {})
        self.assertEqual(overlay.get("chance"), 20)
        self.assertEqual(raw.get("chance"), 30)

    def test_freezedry_secondary_removed(self):
        """Champions removes the freeze status on Freeze-Dry."""
        overlay = get_move_overlayed("freezedry")
        # Champions: secondary was removed
        self.assertIsNone(overlay.get("secondary"))
        self.assertIsNone(overlay.get("secondaries"))
        # Raw still has the freeze chance
        raw = get_move_raw("freezedry")
        raw_sec = raw.get("secondary") or (raw.get("secondaries") or [{}])[0]
        self.assertEqual(raw_sec.get("status"), "frz")

    def test_unmodified_move_unchanged(self):
        """Moves without overrides return identical raw + overlay values."""
        raw_bp = get_move_raw("thunderbolt").get("basePower")
        ov_bp = get_move_overlayed("thunderbolt").get("basePower")
        self.assertEqual(raw_bp, ov_bp)
        self.assertEqual(raw_bp, 90)  # canonical Showdown value


class TestConditionOverrides(unittest.TestCase):
    """Status condition overrides (par/frz/slp) live in load_overrides()."""

    def test_par_full_chance_125(self):
        """Champions paralysis full-stop chance = 12.5% (vs Showdown 25%)."""
        overrides = load_overrides()
        par = overrides.get("conditions", {}).get("par", {})
        self.assertEqual(par.get("fullParalysisChance"), 0.125)
        self.assertEqual(par.get("_was"), 0.25)

    def test_frz_thaw_3turn(self):
        """Champions auto-thaws after 3 turns (vs Showdown 20%/T)."""
        overrides = load_overrides()
        frz = overrides.get("conditions", {}).get("frz", {})
        self.assertEqual(frz.get("thawByTurn"), 3)


class TestImplementationFlags(unittest.TestCase):
    """is_implemented + get_implementation_note for Champions feature gates."""

    def test_rockyhelmet_not_implemented(self):
        """ゴツゴツメット is not in Champions; must NOT propose."""
        self.assertFalse(is_implemented("items", "rockyhelmet"))
        note = get_implementation_note("items", "rockyhelmet")
        self.assertIsNotNone(note)
        self.assertIn("未実装", note)

    def test_focussash_implemented(self):
        """きあいのタスキ is implemented."""
        self.assertTrue(is_implemented("items", "focussash"))

    def test_choiceband_not_implemented(self):
        """こだわりハチマキ is not in Champions."""
        self.assertFalse(is_implemented("items", "choiceband"))

    def test_unknown_id_defaults_true(self):
        """Unknown IDs default to True (no false-negative blocking)."""
        self.assertTrue(is_implemented("items", "nonexistent_xyz_item_99"))

    def test_gmax_not_implemented(self):
        """Gigantamax forms are not in Champions."""
        impl = load_implementation()
        # Sample one gmax entry
        gmax_entries = [k for k in impl["pokemon"] if k.endswith("gmax")]
        self.assertGreaterEqual(len(gmax_entries), 30,
                                f"expected >=30 gmax entries, got {len(gmax_entries)}")
        for k in gmax_entries[:3]:
            self.assertFalse(is_implemented("pokemon", k),
                             f"{k} should be implemented=False")


class TestSchemaKindRegion(unittest.TestCase):
    """Schema 1.1.0: kind/region fields enable category-based queries."""

    def test_all_pokemon_have_kind(self):
        impl = load_implementation()
        valid_kinds = ("gmax", "regional", "paradox", "treasures_of_ruin",
                       "legendary", "mythical")
        for k, v in impl["pokemon"].items():
            self.assertIn("kind", v, f"{k} missing 'kind' field")
            self.assertIn(v["kind"], valid_kinds,
                          f"{k}.kind = {v['kind']!r}, expected one of {valid_kinds}")

    def test_all_gmax_kind_consistent(self):
        impl = load_implementation()
        gmax_keys = [k for k in impl["pokemon"] if k.endswith("gmax")]
        for k in gmax_keys:
            self.assertEqual(impl["pokemon"][k]["kind"], "gmax",
                             f"{k} should have kind='gmax'")
            self.assertIsNone(impl["pokemon"][k]["region"],
                              f"{k} gmax should have region=None")

    def test_regional_region_detected(self):
        impl = load_implementation()
        regions_seen = set()
        for k, v in impl["pokemon"].items():
            if v["kind"] == "regional":
                self.assertIn(v["region"], ("alola", "galar", "hisui", "paldea"),
                              f"{k}.region = {v['region']!r}")
                self.assertTrue(k.endswith(v["region"]),
                                f"{k} should end with {v['region']!r}")
                regions_seen.add(v["region"])
        # At least 3 of 4 regions present
        self.assertGreaterEqual(len(regions_seen), 3,
                                f"only saw regions {regions_seen}")

    def test_megastone_kind(self):
        impl = load_implementation()
        for k, v in impl["megastones"].items():
            self.assertEqual(v.get("kind"), "megastone", f"{k} missing kind=megastone")

    def test_items_moves_kind(self):
        impl = load_implementation()
        for k, v in impl["items"].items():
            self.assertEqual(v.get("kind"), "item", f"{k} missing kind=item")
        for k, v in impl["moves"].items():
            self.assertEqual(v.get("kind"), "move", f"{k} missing kind=move")


class TestTbdGate(unittest.TestCase):
    """v0.3.2: Paradox/Treasures-of-Ruin/Legendary must return 'TBD' (not True).

    Root cause of previous bug: bool('TBD') == True, so unregistered or
    poorly-registered entries silently passed HG-1 check. Fix: 3-value return
    (True / False / 'TBD') + requires_tbd_warning() helper.
    """

    def test_chienpao_tbd(self):
        from lib.champions_overlay import is_implemented, requires_tbd_warning
        self.assertEqual(is_implemented("pokemon", "chienpao"), "TBD")
        self.assertTrue(requires_tbd_warning("pokemon", "chienpao"))

    def test_paradox_tbd(self):
        from lib.champions_overlay import is_implemented
        for pid in ("fluttermane", "ironvaliant", "roaringmoon", "ironbundle"):
            self.assertEqual(is_implemented("pokemon", pid), "TBD",
                             f"{pid} should be TBD (paradox)")

    def test_legendary_tbd(self):
        from lib.champions_overlay import is_implemented
        for pid in ("koraidon", "miraidon", "calyrexshadow", "zaciancrowned"):
            self.assertEqual(is_implemented("pokemon", pid), "TBD",
                             f"{pid} should be TBD (legendary out-of-scope)")

    def test_semi_legendary_tbd(self):
        from lib.champions_overlay import is_implemented
        for pid in ("urshifu", "urshifurapidstrike", "marshadow", "magearna"):
            self.assertEqual(is_implemented("pokemon", pid), "TBD",
                             f"{pid} should be TBD (semi-legendary)")

    def test_normal_pokemon_default_true(self):
        """Regression guard: 通常 SV ポケは引き続き True を返す (アラート過多防止)."""
        from lib.champions_overlay import is_implemented, requires_tbd_warning
        for pid in ("garchomp", "mawile", "tyranitar", "dragapult"):
            self.assertIs(is_implemented("pokemon", pid), True,
                          f"{pid} should remain default True")
            self.assertFalse(requires_tbd_warning("pokemon", pid))

    def test_gmax_still_false(self):
        """Regression guard: gmax は False のまま (TBD 化していないこと)."""
        from lib.champions_overlay import is_implemented
        self.assertIs(is_implemented("pokemon", "venusaurgmax"), False)

    def test_tbd_status_truthy_warning(self):
        """Document the trap: bool('TBD') is True. Use `is True` for strict OK."""
        from lib.champions_overlay import is_implemented
        status = is_implemented("pokemon", "chienpao")
        self.assertTrue(bool(status), "naive `if status:` check would PASS — known trap")
        self.assertIsNot(status, True, "but `is True` correctly distinguishes")


class TestLookupDesignInvariant(unittest.TestCase):
    """get_move (default) returns RAW to protect damage calc input."""

    def test_get_move_returns_raw(self):
        """get_move (without _raw) returns Showdown raw, not overlay.

        This is a load-bearing design choice: damage calc passes lookup
        results directly into the @smogon/calc engine. Overlay values
        would silently corrupt formulas.
        """
        default = get_move("moonblast")
        raw = get_move_raw("moonblast")
        self.assertEqual(default, raw,
                         "get_move() must equal get_move_raw() — overlay leaking would break calc")

    def test_get_item_returns_raw(self):
        default = get_item("focussash")
        raw = get_item_raw("focussash")
        self.assertEqual(default, raw)


if __name__ == "__main__":
    unittest.main(verbosity=2)
