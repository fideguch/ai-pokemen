"""Phase 4 unit tests. Run with: python3 -m unittest tests.test_lib -v
   Or:                          python3 tests/test_lib.py
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import lookup, intent_router, visualizer, persona, session_state  # noqa: E402


class TestLookup(unittest.TestCase):
    def test_resolve_pokemon_jp_exact(self):
        r = lookup.resolve_pokemon("ガブリアス")
        self.assertEqual(r["match_type"], "jp_exact")
        self.assertEqual(r["id"], "garchomp")

    def test_resolve_pokemon_en_exact(self):
        r = lookup.resolve_pokemon("Garchomp")
        self.assertEqual(r["match_type"], "exact")
        self.assertEqual(r["id"], "garchomp")

    def test_resolve_pokemon_partial(self):
        r = lookup.resolve_pokemon("ガブリ")  # partial JP
        self.assertIn(r["match_type"], ("partial", "ambiguous"))
        self.assertIn("garchomp", r["candidates"])

    def test_resolve_pokemon_none(self):
        r = lookup.resolve_pokemon("ZZZZ_NOT_A_POKEMON")
        self.assertEqual(r["match_type"], "none")
        self.assertIsNone(r["id"])

    def test_resolve_move_jp(self):
        r = lookup.resolve_move("じしん")
        self.assertEqual(r["match_type"], "jp_exact")
        self.assertEqual(r["id"], "earthquake")

    def test_resolve_item_jp(self):
        r = lookup.resolve_item("こだわりハチマキ")
        self.assertEqual(r["id"], "choiceband")

    def test_resolve_ability_jp(self):
        r = lookup.resolve_ability("さめはだ")
        self.assertEqual(r["id"], "roughskin")

    def test_pokedex_entry_has_stats(self):
        e = lookup.get_pokedex_entry("garchomp")
        self.assertIsNotNone(e)
        self.assertIn("baseStats", e)
        self.assertIn("hp", e["baseStats"])

    def test_jp_name_reverse(self):
        self.assertEqual(lookup.get_jp_name("pokemon", "garchomp"), "ガブリアス")
        self.assertEqual(lookup.get_jp_name("moves", "earthquake"), "じしん")

    def test_resolve_empty_input(self):
        r = lookup.resolve_pokemon("")
        self.assertEqual(r["match_type"], "none")


class TestIntentRouter(unittest.TestCase):
    def test_t1_damage_calc_keyword(self):
        r = intent_router.classify("鉢巻ガブのEQでミミの確定数は?")
        self.assertEqual(r.tier, "T1")
        self.assertGreater(r.confidence, 0.5)

    def test_t1_numeric(self):
        r = intent_router.classify("HP252振りで耐えるか")
        self.assertEqual(r.tier, "T1")

    def test_t2_team_advice(self):
        r = intent_router.classify("受けループの構築教えて")
        self.assertEqual(r.tier, "T2")

    def test_t3_meta_query(self):
        r = intent_router.classify("今シーズンの環境メタは?")
        self.assertEqual(r.tier, "T3")

    def test_mixed_t3_plus_t1(self):
        r = intent_router.classify("今期トップのガブの確定数は")
        self.assertEqual(r.tier, "MIXED")

    def test_default_t2(self):
        r = intent_router.classify("どうしよう")
        self.assertEqual(r.tier, "T2")
        self.assertLess(r.confidence, 0.6)

    def test_empty_input(self):
        r = intent_router.classify("")
        self.assertEqual(r.tier, "T2")
        self.assertEqual(r.confidence, 0.0)


class TestVisualizer(unittest.TestCase):
    def test_damage_table_basic(self):
        out = visualizer.render_damage_table(
            {"percent_min": 117, "percent_max": 138, "damage": [295, 348],
             "defender_max_hp": 252,
             "ko_chance": {"text": "guaranteed OHKO"}, "desc": "rolled"},
            "Garchomp", "Mimikyu", attacker_jp="ガブリアス", defender_jp="ミミッキュ",
        )
        self.assertIn("ガブリアス", out)
        self.assertIn("ミミッキュ", out)
        self.assertIn("117", out)  # 117.0% formatted
        self.assertIn("138", out)
        self.assertIn("guaranteed OHKO", out)
        self.assertIn("💀", out)  # OHKO marker

    def test_damage_table_hp_gauge(self):
        out = visualizer.render_damage_table(
            {"percent_min": 50, "percent_max": 60, "damage": [100, 120],
             "defender_max_hp": 200, "ko_chance": {}, "desc": ""},
            "A", "B",
        )
        self.assertIn("█", out)  # HP filled
        self.assertIn("░", out)  # HP empty (damaged area)
        self.assertIn("HP前", out)
        self.assertIn("HP後", out)

    def test_hp_gauge_color_zones(self):
        # >50%: green
        self.assertIn("🟢", visualizer.render_hp_gauge(75))
        # 20-50%: yellow
        self.assertIn("🟡", visualizer.render_hp_gauge(35))
        # <20%: red
        self.assertIn("🔴", visualizer.render_hp_gauge(10))
        # 0%: red
        self.assertIn("🔴", visualizer.render_hp_gauge(0))

    def test_pokemon_card_garchomp(self):
        """Pokemon card with type JP names + move JP/EN resolution."""
        card = visualizer.render_pokemon_card("garchomp", {
            "slot": 1,
            "item": "きあいのタスキ", "ability": "さめはだ", "nature": "ようき",
            "evs": "AS252+B4",
            "moves": ["じしん", "げきりん"],
            "role": "ステロ撒き要員",
        })
        self.assertIn("ガブリアス", card)
        self.assertIn("Garchomp", card)
        self.assertIn("ドラゴン", card)  # Type JP
        self.assertIn("じめん", card)
        self.assertIn("100", card)  # Earthquake basePower (JP resolve OK)
        self.assertIn("ようき", card)
        self.assertIn("S↑/C↓", card)  # Nature hint
        self.assertIn("ステロ撒き", card)

    def test_sprite_tool_fail_soft(self):
        """Sprite tool detection should never raise; return empty if absent."""
        result = visualizer.render_pokemon_sprite("garchomp")
        self.assertIsInstance(result, str)  # empty or sprite text

    def test_showdown_export_format(self):
        """Pokemon Showdown text export format compliance."""
        out = visualizer.export_showdown_format([
            {"pokemon_id": "garchomp", "item": "Focus Sash", "ability": "Rough Skin",
             "nature": "Jolly", "evs": {"atk": 252, "spe": 252, "def": 4},
             "moves": ["じしん", "げきりん"]},
        ])
        self.assertIn("Garchomp @ Focus Sash", out)
        self.assertIn("Ability: Rough Skin", out)
        self.assertIn("EVs: 252 Atk / 4 Def / 252 Spe", out)
        self.assertIn("Jolly Nature", out)
        self.assertIn("- Earthquake", out)  # JP → EN resolved
        self.assertIn("- Outrage", out)

    def test_type_matchup_ground(self):
        # Ground pokemon -> water 2x, electric 0x, ice 2x, etc.
        # Showdown typechart keys are PascalCase (Electric, Ground), but values are lowercased.
        chart = lookup.get_typechart()
        # Use proper-case as required by Showdown typechart keys
        out = visualizer.render_type_matchup(["Ground"], chart)
        self.assertIn("タイプ相性", out)
        # Electric is rendered as-is from typechart keys ("electric" if lowercased)
        self.assertTrue("Electric" in out or "electric" in out)

    def test_role_matrix(self):
        out = visualizer.render_role_matrix(
            ["A", "B"], ["X", "Y"], lambda s, o: f"{s}vs{o}",
        )
        self.assertIn("AvsX", out)
        self.assertIn("BvsY", out)

    def test_cycle_flow(self):
        out = visualizer.render_cycle_flow(["A", "B", "C"])
        self.assertIn("A → B → C", out)


class TestPersona(unittest.TestCase):
    def test_glossary_size_at_least_30(self):
        # PQG修正5: 30語以上 mandatory
        self.assertGreaterEqual(persona.glossary_size(), 30)

    def test_haijin_to_standard(self):
        out = persona.haijin_to_standard("珠ガブのEQ")
        self.assertIn("いのちのたま", out)

    def test_expand_glossary_appends_terms(self):
        out = persona.expand_glossary("HBドオーに鉢巻ガブのEQ")
        self.assertIn("用語", out)
        self.assertIn("こだわりハチマキ", out)

    def test_expand_glossary_no_terms(self):
        out = persona.expand_glossary("普通の文章です")
        self.assertEqual(out, "普通の文章です")


class TestSessionState(unittest.TestCase):
    def test_load_creates_default(self):
        s = session_state.load()
        self.assertIn("version", s)
        self.assertEqual(s["version"], 1)
        self.assertEqual(s["team"], [])

    def test_track_team_immutable(self):
        s = session_state.load()
        original_team = s["team"]
        new = session_state.track_team(s, [{"id": "garchomp"}])
        self.assertEqual(s["team"], original_team)  # original unchanged
        self.assertEqual(new["team"], [{"id": "garchomp"}])

    def test_track_last_calc(self):
        s = session_state._empty_state()
        new = session_state.track_last_calc(s, {"min": 50, "max": 60})
        self.assertEqual(new["last_calc"]["max"], 60)

    def test_focus_pokemon_priority(self):
        s = session_state._empty_state()
        s["last_topic"] = "garchomp"
        s["team"] = [{"id": "mimikyu"}]
        self.assertEqual(session_state.get_focus_pokemon(s), "garchomp")

        s["last_topic"] = None
        self.assertEqual(session_state.get_focus_pokemon(s), "mimikyu")

    def test_save_and_reload(self):
        s = session_state._empty_state()
        s["team"] = [{"id": "test_save_garchomp"}]
        session_state.save(s)
        reloaded = session_state.load()
        self.assertEqual(reloaded["team"][0]["id"], "test_save_garchomp")
        # Cleanup
        session_state.reset()


class TestVisualizerV051(unittest.TestCase):
    """v0.5.1 UI overhaul (P1-P7). Append-only — does NOT modify TestVisualizer."""

    # P1: render_type_weakness_chart -------------------------------------------
    def test_weakness_chart_garchomp_dragon_ground(self):
        out = visualizer.render_type_weakness_chart(["Dragon", "Ground"])
        # 4x: Ice (Dragon 2x × Ground 2x = 4x)
        self.assertIn("弱点 4倍", out)
        self.assertIn("こおり", out)
        # 2x: Dragon (Dragon 2x × Ground 1x), Fairy (Dragon 2x × Ground 1x)
        self.assertIn("弱点 2倍", out)
        self.assertIn("ドラゴン", out)
        self.assertIn("フェアリー", out)
        # 0x: Electric (Ground immune)
        self.assertIn("無効", out)
        self.assertIn("でんき", out)
        # ½: Fire (Dragon ½), Poison (Ground ½), Rock (Ground ½)
        self.assertIn("耐性 ½", out)

    def test_weakness_chart_filters_status_keys(self):
        """damageTaken contains brn/par/sandstorm/etc — must not appear."""
        out = visualizer.render_type_weakness_chart(["Normal"])
        for stray in ("brn", "par", "frz", "tox", "powder", "prankster",
                      "sandstorm", "trapped", "Stellar"):
            self.assertNotIn(stray, out)

    def test_weakness_chart_single_type(self):
        out = visualizer.render_type_weakness_chart(["Steel"])
        # Steel resists many, immune to Poison
        self.assertIn("無効", out)
        self.assertIn("どく", out)

    def test_weakness_chart_empty_types(self):
        out = visualizer.render_type_weakness_chart([])
        # No types → all attacks hit at 1x (no weak/resist/immune)
        self.assertIn("等倍", out)

    # P2: show_weakness kwarg --------------------------------------------------
    def test_show_weakness_kwarg_default_off(self):
        card = visualizer.render_pokemon_card("garchomp", {"item": "タスキ"})
        self.assertNotIn("弱点/耐性:", card)

    def test_show_weakness_kwarg_on(self):
        card = visualizer.render_pokemon_card(
            "garchomp", {"item": "タスキ"}, show_weakness=True,
        )
        self.assertIn("弱点/耐性:", card)
        self.assertIn("こおり", card)  # 4x

    # P3: render_environmental_damage ------------------------------------------
    def test_env_damage_stealth_rock_only(self):
        out = visualizer.render_environmental_damage(100.0, stealth_rock=True)
        # 12.5% off → 87.5%
        self.assertIn("ステロ", out)
        self.assertIn("最終 HP: 87.5%", out)

    def test_env_damage_stealth_rock_4x(self):
        out = visualizer.render_environmental_damage(
            100.0, stealth_rock=True, stealth_rock_multiplier=4.0,
        )
        # 50% off → 50%
        self.assertIn("最終 HP: 50.0%", out)

    def test_env_damage_sandstorm_3turns(self):
        out = visualizer.render_environmental_damage(
            100.0, sandstorm=True, turns=3,
        )
        # 6.25% × 3 = 18.75% off → 81.25%
        self.assertIn("最終 HP: 81.2%", out)

    def test_env_damage_sandstorm_immune(self):
        """Rock/Steel/Ground types skip sandstorm chip."""
        out = visualizer.render_environmental_damage(
            100.0, sandstorm=True, sandstorm_immune=True, turns=5,
        )
        self.assertIn("最終 HP: 100.0%", out)

    def test_env_damage_combined_sr_plus_sand(self):
        out = visualizer.render_environmental_damage(
            100.0, stealth_rock=True, stealth_rock_multiplier=2.0,
            sandstorm=True, turns=2,
        )
        # SR 25% off → 75%, then sand 6.25%×2 = 12.5% → 62.5%
        self.assertIn("最終 HP: 62.5%", out)

    def test_env_damage_clamped_to_zero(self):
        out = visualizer.render_environmental_damage(
            10.0, stealth_rock=True, stealth_rock_multiplier=4.0,
        )
        # 10 - 50 → clamp to 0
        self.assertIn("最終 HP: 0.0%", out)

    def test_env_damage_pure_python_no_calc_call(self):
        """Smoke test: function returns instantly, no subprocess invoked.
        Enforces 'pure-Python calculation, no calc binary' contract."""
        import time
        t0 = time.perf_counter()
        for _ in range(100):
            visualizer.render_environmental_damage(
                100.0, stealth_rock=True, sandstorm=True, turns=10,
            )
        dt_ms = (time.perf_counter() - t0) * 1000
        # Should be well under 100ms even with 100 iterations.
        self.assertLess(dt_ms, 500.0,
                        f"env_damage too slow: {dt_ms:.1f}ms for 100 calls")

    # P4: render_stats_radar ---------------------------------------------------
    def test_stats_radar_basic(self):
        out = visualizer.render_stats_radar(
            {"hp": 108, "atk": 130, "def": 95, "spa": 80, "spd": 85, "spe": 102},
        )
        self.assertIn("種族値レーダー", out)
        self.assertIn("HP", out)
        self.assertIn("Atk", out)
        self.assertIn("108", out)
        self.assertIn("130", out)
        # 5-stage dot scale present
        self.assertIn("●", out)

    def test_stats_radar_empty(self):
        out = visualizer.render_stats_radar({})
        # Should not crash, all values default to 0
        self.assertIn("種族値レーダー", out)
        self.assertIn("○○○○○", out)

    def test_show_radar_kwarg_on(self):
        card = visualizer.render_pokemon_card(
            "garchomp", {"item": "タスキ"}, show_radar=True,
        )
        self.assertIn("種族値レーダー", card)

    # P5: render_pokemon_card_compact -----------------------------------------
    def test_compact_falls_back_when_no_sprite(self):
        """No sprite text → vertical render_pokemon_card returned (non-empty)."""
        out = visualizer.render_pokemon_card_compact(
            "garchomp", {"item": "タスキ", "ability": "さめはだ"},
            sprite_text="",
        )
        self.assertIn("ガブリアス", out)
        self.assertIn("Garchomp", out)
        # Vertical fallback uses the standard separator.
        self.assertIn("═", out)

    def test_compact_with_synthetic_sprite(self):
        sprite = "###\n# #\n###"
        out = visualizer.render_pokemon_card_compact(
            "garchomp", {"item": "タスキ", "ability": "さめはだ"},
            sprite_text=sprite,
        )
        # Sprite line on left, card content on right
        self.assertIn("###", out)
        self.assertIn("ガブリアス", out)
        # Two columns separated by 2-space gap
        self.assertIn("  ", out)

    def test_compact_ansi_width_measurement(self):
        """ANSI escapes must be stripped for width but preserved in display
        (PQG condition #4)."""
        # Sprite with ANSI red color: \x1b[31mABC\x1b[0m → visible width 3
        ansi_sprite = "\x1b[31mABC\x1b[0m\nXYZ"
        out = visualizer.render_pokemon_card_compact(
            "garchomp", {"item": "タスキ"},
            sprite_text=ansi_sprite,
        )
        # ANSI bytes preserved in output
        self.assertIn("\x1b[31m", out)
        # Visible width helper itself
        self.assertEqual(visualizer._visible_width("\x1b[31mABC\x1b[0m"), 3)
        self.assertEqual(visualizer._visible_width("XYZ"), 3)

    # P7: size kwarg on render_pokemon_sprite ----------------------------------
    def test_sprite_size_default_medium(self):
        """Default size kwarg should be 'medium'; function still fail-soft."""
        out = visualizer.render_pokemon_sprite("garchomp")
        self.assertIsInstance(out, str)

    def test_sprite_size_unknown_falls_back(self):
        """Invalid size value should not raise; falls back to 'medium'."""
        out = visualizer.render_pokemon_sprite("garchomp", size="huge_invalid")
        self.assertIsInstance(out, str)

    def test_sprite_size_all_valid_values(self):
        for sz in ("small", "medium", "large"):
            out = visualizer.render_pokemon_sprite("garchomp", size=sz)
            self.assertIsInstance(out, str)


class TestShowPartyCLI(unittest.TestCase):
    """P6: scripts/show_party.py — table parser + path-traversal validator."""

    def setUp(self):
        # Lazy import to avoid evaluating argparse on module load.
        sys.path.insert(0, str(ROOT / "scripts"))
        import importlib
        import show_party
        importlib.reload(show_party)
        self.show_party = show_party

    def test_validate_build_id_rejects_traversal(self):
        with self.assertRaises(SystemExit) as cm:
            self.show_party.validate_build_id("../../etc/passwd")
        self.assertEqual(cm.exception.code, 2)

    def test_validate_build_id_rejects_empty(self):
        with self.assertRaises(SystemExit) as cm:
            self.show_party.validate_build_id("")
        self.assertEqual(cm.exception.code, 2)

    def test_validate_build_id_rejects_special_chars(self):
        for bad in ("foo bar", "foo;rm", "foo/bar", "foo$bar"):
            with self.assertRaises(SystemExit) as cm:
                self.show_party.validate_build_id(bad)
            self.assertEqual(cm.exception.code, 2, f"failed to reject: {bad!r}")

    def test_validate_build_id_accepts_real_build(self):
        p = self.show_party.validate_build_id("A.3-Final-v7.8")
        self.assertTrue(p.exists())
        self.assertTrue(str(p).endswith("A.3-Final-v7.8.md"))

    def test_parse_party_table_finds_6_members(self):
        build_md = (ROOT / "builds" / "A.3-Final-v7.8.md").read_text(encoding="utf-8")
        party = self.show_party.parse_party_table(build_md)
        self.assertEqual(len(party), 6)
        # Each entry has the required keys
        required = {"slot", "pokemon_id", "jp_name", "item", "ability",
                    "nature", "evs", "moves"}
        for member in party:
            self.assertTrue(required.issubset(member.keys()))

    def test_parse_party_resolves_mega_prefix(self):
        build_md = (ROOT / "builds" / "A.3-Final-v7.8.md").read_text(encoding="utf-8")
        party = self.show_party.parse_party_table(build_md)
        ids = [m["pokemon_id"] for m in party]
        # メガカイリュー → dragonite, メガゲンガー → gengar
        self.assertIn("dragonite", ids)
        self.assertIn("gengar", ids)
        # Other slots resolve normally
        self.assertIn("garchomp", ids)
        self.assertIn("hippowdon", ids)


if __name__ == "__main__":
    unittest.main(verbosity=2)
