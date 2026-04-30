"""Phase 4: Visualizers — Markdown tables + ASCII bars + matrices.

All renderers are pure functions returning markdown strings.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

# ANSI escape stripper for visible-width measurement (used by compact 2-col layout).
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _visible_width(s: str) -> int:
    """Return display width of `s` ignoring ANSI escape sequences.

    Used by render_pokemon_card_compact to align ANSI-colored sprite columns
    (PQG condition #4: ANSI-aware width measurement).
    """
    return len(ANSI_RE.sub("", s))


def render_hp_gauge(remain_pct: float, width: int = 20) -> str:
    """Render a Pokemon-battle-screen-like HP gauge.

    Bar fills from LEFT with remaining HP (█), missing portion shown as ░ on RIGHT.
    Mirrors the in-game HP behavior (full = left filled, damaged = right empties).

    Color hint via emoji:
      remain >50%  → 🟢
      20-50%       → 🟡
      <20%         → 🔴

    Args:
        remain_pct: HP remaining percentage (0-100). Damaged amount = 100 - remain_pct.
        width: bar width in cells (default 20).

    Returns:
        Single-line gauge: "🟢 [████████████████████] 100%"
    """
    pct = max(0.0, min(100.0, remain_pct))
    filled = int(round(pct / 100.0 * width))
    empty = width - filled
    bar = "█" * filled + "░" * empty
    if pct > 50:
        emoji = "🟢"
    elif pct >= 20:
        emoji = "🟡"
    else:
        emoji = "🔴"
    return f"{emoji} [{bar}] {pct:.1f}%"


def render_environmental_damage(
    remain_hp_pct: float,
    *,
    stealth_rock: bool = False,
    stealth_rock_multiplier: float = 1.0,
    sandstorm: bool = False,
    sandstorm_immune: bool = False,
    weather_chip: bool = False,
    weather_chip_immune: bool = False,
    turns: int = 1,
) -> str:
    """Render HP gauge showing remaining HP after environmental damage accumulation.

    Pure-Python calculation (NO calls to bin/pokechamp-calc — keeps T1 latency intact).

    Damage rules (Gen 9 standard, per PQG condition #3):
        - Stealth Rock: rock-type effectiveness × 1/8 max HP, applied ONCE on switch-in.
          stealth_rock_multiplier: 0.5 (resist), 1.0 (neutral), 2.0 (weak), 4.0 (4x weak).
          Caller is responsible for the multiplier; immunity = pass stealth_rock=False.
        - Sandstorm: 1/16 max HP per turn.
          IMMUNE: Rock, Steel, Ground types (pass sandstorm_immune=True).
        - Hail/Snow chip: 1/16 max HP per turn (legacy gens; Gen 9 'Snow' has no chip
          damage but the kwarg is provided for completeness/older-gen scenarios).
          IMMUNE: Ice type (pass weather_chip_immune=True).
        - Sun/Rain: NO chip damage at all (do not enable weather_chip for these).

    Args:
        remain_hp_pct: starting HP% (0-100). Clamped.
        stealth_rock: apply Stealth Rock damage once at start (regardless of turns).
        stealth_rock_multiplier: defender's rock-type effectiveness (default 1.0 neutral).
        sandstorm: apply sandstorm chip per turn (skipped if sandstorm_immune=True).
        sandstorm_immune: True if defender is Rock/Steel/Ground.
        weather_chip: apply non-sand chip per turn (skipped if weather_chip_immune=True).
        weather_chip_immune: True if defender immune (e.g. Ice for Hail).
        turns: number of turns to simulate (default 1).

    Returns:
        Multiline string with per-turn HP gauges + final state summary.
    """
    pct = max(0.0, min(100.0, float(remain_hp_pct)))
    lines: list[str] = []
    lines.append("## 環境ダメージシミュレーション")
    lines.append("```")

    # Build conditions summary
    conds: list[str] = []
    if stealth_rock:
        conds.append(f"ステロ x{stealth_rock_multiplier}")
    if sandstorm:
        conds.append("砂嵐" + (" (無効)" if sandstorm_immune else ""))
    if weather_chip:
        conds.append("天候チップ" + (" (無効)" if weather_chip_immune else ""))
    if not conds:
        conds.append("(条件なし)")
    lines.append(f"  条件: {' / '.join(conds)}")
    lines.append(f"  初期 HP: {render_hp_gauge(pct)}")

    # Stealth Rock applied once at start.
    if stealth_rock:
        sr_dmg = 12.5 * float(stealth_rock_multiplier)
        pct = max(0.0, pct - sr_dmg)
        lines.append(f"  ステロ ({sr_dmg:.1f}%): {render_hp_gauge(pct)}")

    # Per-turn chip damage.
    if turns > 0 and (sandstorm or weather_chip):
        per_turn = 0.0
        sources: list[str] = []
        if sandstorm and not sandstorm_immune:
            per_turn += 6.25
            sources.append("砂")
        if weather_chip and not weather_chip_immune:
            per_turn += 6.25
            sources.append("天候")
        if per_turn > 0:
            for t in range(1, turns + 1):
                pct = max(0.0, pct - per_turn)
                lines.append(
                    f"  T{t} ({'+'.join(sources)} -{per_turn:.2f}%): {render_hp_gauge(pct)}"
                )
        else:
            lines.append(f"  チップ無効 (immune): {render_hp_gauge(pct)}")

    lines.append(f"  最終 HP: {pct:.1f}%")
    lines.append("```")
    return "\n".join(lines)


def render_damage_table(
    calc_result: dict,
    attacker_name: str,
    defender_name: str,
    attacker_jp: Optional[str] = None,
    defender_jp: Optional[str] = None,
) -> str:
    """Render damage calc with Pokemon-battle-screen-like HP gauges (before/after).

    Visualization (HP fills from LEFT, drains from RIGHT — mirrors in-game UI):
        HP前  🟢 [████████████████████] 100% (414/414)
                  ↓ 流星群 304-358 dmg (73.4-86.5%)
        HP後  🟡 [█████░░░░░░░░░░░░░░░] 残 13.5-26.6% (56-110)
              ⚠ guaranteed 2HKO
    """
    pmin = calc_result.get("percent_min", 0)
    pmax = calc_result.get("percent_max", 0)
    ko = calc_result.get("ko_chance", {}) or {}
    desc = calc_result.get("desc", "")
    damage = calc_result.get("damage", []) or []
    def_hp = calc_result.get("defender_max_hp", 0)

    a = attacker_jp or attacker_name
    d = defender_jp or defender_name
    move_label = ""  # caller may pass via desc

    # Compute remaining HP after damage range
    # Worst case (max damage) = lowest remaining HP
    remain_min_pct = max(0.0, 100.0 - pmax)  # after taking max dmg → least HP left
    remain_max_pct = max(0.0, 100.0 - pmin)  # after taking min dmg → most HP left
    dmin = min(damage) if damage else 0
    dmax = max(damage) if damage else 0
    remain_hp_min = max(0, def_hp - dmax)
    remain_hp_max = max(0, def_hp - dmin)

    lines = []
    lines.append(f"## ダメ計: {a} → {d}")
    lines.append("")
    lines.append("| 指標 | 値 |")
    lines.append("|---|---|")
    lines.append(f"| ダメ% | {pmin:.1f} - {pmax:.1f}% ({dmin}-{dmax}) |")
    lines.append(f"| 残 HP | {remain_hp_min}-{remain_hp_max} / {def_hp} ({remain_min_pct:.1f}-{remain_max_pct:.1f}%) |")
    if ko:
        ko_text = ko.get("text", "-")
        # Add KO marker
        ko_marker = "💀" if "OHKO" in ko_text or "1HKO" in ko_text.replace(" ", "") else "⚠" if "2HKO" in ko_text else "ℹ"
        lines.append(f"| 確定 | {ko_marker} {ko_text} |")
    lines.append("")

    # HP gauges — Pokemon-battle-screen-like (fills from LEFT)
    if def_hp > 0 and (pmin > 0 or pmax > 0):
        lines.append("```")
        lines.append(f"{d} HP {def_hp}")
        lines.append(f"  HP前  {render_hp_gauge(100.0)} ({def_hp}/{def_hp})")
        lines.append(f"        ↓ {pmin:.1f}-{pmax:.1f}% dmg ({dmin}-{dmax})")
        # After: show range. Use the WORST-case (lowest remaining) as primary visual.
        if remain_min_pct == remain_max_pct:
            lines.append(f"  HP後  {render_hp_gauge(remain_min_pct)}")
        else:
            lines.append(f"  HP後  {render_hp_gauge(remain_min_pct)}  (max ダメ時)")
            lines.append(f"        {render_hp_gauge(remain_max_pct)}  (min ダメ時)")
        if ko:
            lines.append(f"        {ko.get('text', '')}")
        lines.append("```")

    if desc:
        lines.append("")
        lines.append(f"> {desc}")
    return "\n".join(lines)


# Backward compatibility alias (deprecated, kept for existing callers)
def render_damage_bar(calc_result: dict, **kwargs) -> str:  # pragma: no cover
    """Deprecated. Use render_damage_table (HP gauge style)."""
    return render_damage_table(
        calc_result,
        kwargs.get("attacker_name", "?"),
        kwargs.get("defender_name", "?"),
    )


# -----------------------------------------------------------------------------
# Pokemon Card UI (v0.5.0+)
# -----------------------------------------------------------------------------
# 1 体 1 体を「ポケモン対戦画面ライク」に大きく区切って表示するカード形式。
# 構築 6 体一覧表示や個別 spotlight に使う。

TYPE_EMOJI = {
    "Normal":   ("⚪", "ノーマル"), "Fire":    ("🔥", "ほのお"),
    "Water":    ("💧", "みず"),   "Electric": ("⚡", "でんき"),
    "Grass":    ("🌿", "くさ"),   "Ice":      ("🧊", "こおり"),
    "Fighting": ("🥊", "かくとう"), "Poison":  ("☠️", "どく"),
    "Ground":   ("🟫", "じめん"), "Flying":   ("🐦", "ひこう"),
    "Psychic":  ("🔮", "エスパー"), "Bug":     ("🐛", "むし"),
    "Rock":     ("🪨", "いわ"),   "Ghost":    ("👻", "ゴースト"),
    "Dragon":   ("🐉", "ドラゴン"), "Dark":    ("🌑", "あく"),
    "Steel":    ("⚙️", "はがね"), "Fairy":    ("🩷", "フェアリー"),
}

# 性格 → ステ補正 (英 + JP 両対応)
NATURE_HINT = {
    "Adamant": "A↑/C↓", "Modest": "C↑/A↓", "Jolly": "S↑/C↓", "Timid": "S↑/A↓",
    "Bold":    "B↑/A↓", "Impish": "B↑/C↓", "Calm":  "D↑/A↓", "Careful": "D↑/C↓",
    "Hasty":   "S↑/B↓", "Naive":  "S↑/D↓", "Brave": "A↑/S↓", "Quiet":   "C↑/S↓",
    "Relaxed": "B↑/S↓", "Sassy":  "D↑/S↓", "Gentle": "D↑/B↓",
    "Lax":     "B↑/D↓", "Rash":   "C↑/D↓", "Mild":  "C↑/B↓", "Lonely":  "A↑/B↓",
    "Naughty": "A↑/D↓",
    # JP
    "いじっぱり": "A↑/C↓", "ひかえめ": "C↑/A↓", "ようき": "S↑/C↓", "おくびょう": "S↑/A↓",
    "ずぶとい":   "B↑/A↓", "わんぱく": "B↑/C↓", "おだやか": "D↑/A↓", "しんちょう": "D↑/C↓",
    "せっかち":   "S↑/B↓", "むじゃき": "S↑/D↓", "ゆうかん": "A↑/S↓", "れいせい":   "C↑/S↓",
    "のんき":     "B↑/S↓", "なまいき": "D↑/S↓", "おっとり": "C↑/B↓", "うっかりや": "C↑/D↓",
    "やんちゃ":   "A↑/D↓", "さみしがり": "A↑/B↓", "おとなしい": "D↑/B↓",
    "ずぶとい":   "B↑/A↓",
}

CATEGORY_SHORT = {"Physical": "物", "Special": "特", "Status": "補"}


def _fmt_type_line(types: list[str]) -> str:
    """Render type line with emojis + JP names: '🐉 ドラゴン / 🟫 じめん'"""
    pairs = []
    for t in types:
        em, jp = TYPE_EMOJI.get(t, ("?", t))
        pairs.append(f"{em} {jp}")
    return " / ".join(pairs)


def _type_emoji(t: str) -> str:
    em, _ = TYPE_EMOJI.get(t, ("", t))
    return em


def _type_jp(t: str) -> str:
    _, jp = TYPE_EMOJI.get(t, ("", t))
    return jp


def render_stats_radar(base_stats: dict, *, scale_max: int = 255) -> str:
    """Render base stats as ASCII horizontal-bar radar chart.

    PQG accepts horizontal bars as a "radar" representation (true hexagon was
    not mandated). Format gives 3 visual cues per stat: numeric value, bar fill,
    and 5-stage dot scale (●●●●● = max, ●●●●○ = ~80%, etc.).

    Stat order: HP / Atk / Def / SpA / SpD / Spe (Showdown lowercase keys: hp/atk/def/spa/spd/spe).

    Args:
        base_stats: dict with hp/atk/def/spa/spd/spe (Showdown lowercase).
        scale_max: upper bound for normalization (default 255 — Blissey HP / Shuckle Def).

    Returns:
        Multi-line ASCII art (~7 lines: 1 header + 6 stat rows).
    """
    order = [
        ("HP",  "hp"),
        ("Atk", "atk"),
        ("Def", "def"),
        ("SpA", "spa"),
        ("SpD", "spd"),
        ("Spe", "spe"),
    ]
    bar_w = 20
    smax = max(1, int(scale_max))
    lines = [f"種族値レーダー (scale 0-{smax}):"]
    for label, key in order:
        v = int(base_stats.get(key, 0) or 0)
        ratio = max(0.0, min(1.0, v / smax))
        filled = int(round(ratio * bar_w))
        bar = "█" * filled + " " * (bar_w - filled)
        # 5-stage dot scale
        stages = max(0, min(5, int(round(ratio * 5))))
        dots = "●" * stages + "○" * (5 - stages)
        pct = ratio * 100
        lines.append(f"  {label:3s} {v:3d} [{bar}] {pct:4.1f}%  {dots}")
    return "\n".join(lines)


def render_pokemon_card(
    pokemon_id: str,
    build_meta: Optional[dict] = None,
    *,
    show_separator: bool = True,
    show_weakness: bool = False,
    show_radar: bool = False,
) -> str:
    """Render a single Pokemon as a Pokemon-battle-screen-like card.

    Sections (visually divided):
      1. Header (slot # + JP name + EN name + types)
      2. Identity (item, ability, nature, EVs)
      3. Stats (種族値 + optionally 実数値)
      4. Moves (4 技、power/category/type)
      5. Role + rationale (構築固有、build_meta から)
      6. Champions 適合 + 環境順位 (オプショナル)

    Args:
        pokemon_id: Showdown ID (e.g. "garchomp")
        build_meta: Optional dict with construction-specific info:
            {
              "slot": 1,                    # 構築内番号 1-6
              "jp_name": "ガブリアス",       # override
              "item": "きあいのタスキ",
              "ability": "さめはだ",
              "nature": "ようき",
              "evs": "AS252+B4",
              "moves": ["じしん","げきりん","ステロ","がんせきふうじ"],
              "role": "ステロ撒き要員 + 物理アタッカー",
              "rationale": ["環境 #1 のサイクル妨害", "タスキで初手対面確保"],
              "meta_rank": 1,               # 環境順位 (TOP20)
              "mega_form": False,           # メガ進化形態か
            }
        show_separator: Top/bottom の太線セパレータを表示するか
        show_weakness: True の場合、種族値セクションの後に弱点/耐性チャートを表示
                       (defaults False — opt-in、PQG condition #2)
        show_radar: True の場合、種族値セクションに ASCII レーダー (横棒) を表示
                    (defaults False — opt-in、PQG condition #2)

    Returns:
        Multiline string, ready to print.
    """
    # Lazy imports (avoid circular)
    from lib.lookup import get_pokedex_entry, get_jp_name, get_move, resolve_move
    from lib.champions_overlay import is_implemented

    bm = build_meta or {}
    pdex = get_pokedex_entry(pokemon_id) or {}
    bs = pdex.get("baseStats", {})
    types = pdex.get("types", [])
    name_en = pdex.get("name", pokemon_id)
    name_jp = bm.get("jp_name") or get_jp_name("pokemon", pokemon_id) or name_en

    SEP = "═" * 63
    lines = []

    # 1. Header
    if show_separator:
        lines.append(SEP)
    slot = bm.get("slot")
    slot_str = f"#{slot} / " if slot else ""
    type_line = _fmt_type_line(types)
    lines.append(f"  {slot_str}{name_jp}  ({name_en})        {type_line}")
    if show_separator:
        lines.append(SEP)
    lines.append("")

    # 2. Identity (item / ability / nature / EVs)
    item = bm.get("item", "—")
    ability = bm.get("ability", pdex.get("abilities", {}).get("0", "?"))
    nature = bm.get("nature", "—")
    nature_hint = NATURE_HINT.get(nature, "")
    nature_full = f"{nature} ({nature_hint})" if nature_hint else nature
    evs = bm.get("evs", "—")
    lines.append(f"  特性    : {ability}")
    lines.append(f"  持ち物  : {item}")
    lines.append(f"  性格    : {nature_full}")
    lines.append(f"  努力値  : {evs}")
    lines.append("")

    # 3. Stats (種族値)
    if bs:
        bs_line = " | ".join([
            f"H {bs.get('hp',0):3d}",
            f"A {bs.get('atk',0):3d}",
            f"B {bs.get('def',0):3d}",
            f"C {bs.get('spa',0):3d}",
            f"D {bs.get('spd',0):3d}",
            f"S {bs.get('spe',0):3d}",
        ])
        bst = sum(bs.values())
        lines.append(f"  種族値: {bs_line}  (合計 {bst})")
        if show_radar:
            radar = render_stats_radar(bs)
            for rl in radar.split("\n"):
                lines.append(f"  {rl}")
        lines.append("")

    # 3.5 Optional: weakness/resistance chart (PQG #2 opt-in)
    if show_weakness and types:
        wlines = render_type_weakness_chart(types).split("\n")
        lines.append("  弱点/耐性:")
        for wl in wlines:
            lines.append(f"    {wl}")
        lines.append("")

    # 4. Moves (JP/EN 両対応: resolve_move で id 解決 → get_move で詳細取得)
    moves = bm.get("moves", [])
    if moves:
        lines.append("  技構成:")
        for i, mv_name in enumerate(moves, 1):
            r = resolve_move(mv_name) if isinstance(mv_name, str) else None
            mid = r.get("id") if isinstance(r, dict) else None
            md = get_move(mid) if mid else {}
            md = md or {}
            power = md.get("basePower", 0)
            cat = md.get("category", "?")
            mtype = md.get("type", "?")
            cat_s = CATEGORY_SHORT.get(cat, "?")
            type_em = _type_emoji(mtype)
            type_jp = _type_jp(mtype)
            power_s = f"{power:3d}" if power else "  -"
            lines.append(f"    {i}. {mv_name:14s} {power_s} / {cat_s} / {type_em} {type_jp}")
        lines.append("")

    # 5. Role + rationale
    role = bm.get("role")
    rationale = bm.get("rationale", [])
    if role:
        lines.append(f"  役割    : {role}")
    if rationale:
        lines.append("  採用理由:")
        for r in rationale:
            lines.append(f"    ─ {r}")
    if role or rationale:
        lines.append("")

    # 6. Champions 適合 + 環境順位
    impl = is_implemented("pokemon", pokemon_id)
    if impl is True:
        impl_mark = "✓ 確定実装"
    elif impl is False:
        impl_mark = "❌ Champions 未実装"
    else:
        impl_mark = "⚠ TBD (公式要確認)"
    meta_rank = bm.get("meta_rank")
    rank_str = f"   |   環境順位: #{meta_rank} / TOP20" if meta_rank else ""
    lines.append(f"  Champions 適合: {impl_mark}{rank_str}")

    if show_separator:
        lines.append(SEP)

    return "\n".join(lines)


def render_pokemon_card_compact(
    pokemon_id: str,
    build_meta: Optional[dict] = None,
    *,
    sprite_text: Optional[str] = None,
    show_weakness: bool = False,
    show_radar: bool = False,
) -> str:
    """Render Pokemon Card in neofetch-style 2-column layout (sprite left, info right).

    If `sprite_text` is not provided, calls `render_pokemon_sprite(pokemon_id)`
    fail-soft. ANSI escape sequences in the sprite are PRESERVED in display
    but stripped for width measurement (PQG condition #4).

    Falls back to vertical `render_pokemon_card` if no sprite is available
    (so the function always returns non-empty output).

    Args:
        pokemon_id: Showdown ID.
        build_meta: same shape as `render_pokemon_card`.
        sprite_text: pre-rendered sprite (for testing / custom source).
        show_weakness: forwarded to render_pokemon_card.
        show_radar: forwarded to render_pokemon_card.

    Returns:
        Multiline 2-column string. Vertical fallback when no sprite exists.
    """
    if sprite_text is None:
        sprite_text = render_pokemon_sprite(pokemon_id)
    if not sprite_text:
        # Fail-soft: vertical fallback so output is never empty.
        return render_pokemon_card(
            pokemon_id, build_meta,
            show_weakness=show_weakness, show_radar=show_radar,
        )

    # Card without separator lines (compact context).
    card_text = render_pokemon_card(
        pokemon_id, build_meta,
        show_separator=False,
        show_weakness=show_weakness,
        show_radar=show_radar,
    )

    sprite_lines = sprite_text.split("\n")
    card_lines = card_text.split("\n")

    # Pad sprite to uniform visible width using ANSI-aware measurement.
    sprite_width = max((_visible_width(l) for l in sprite_lines), default=0)
    padded_sprite = [
        l + " " * (sprite_width - _visible_width(l)) for l in sprite_lines
    ]

    # Zip with empty padding on the shorter side.
    n = max(len(padded_sprite), len(card_lines))
    blank_sprite = " " * sprite_width
    out_lines = []
    for i in range(n):
        sl = padded_sprite[i] if i < len(padded_sprite) else blank_sprite
        cl = card_lines[i] if i < len(card_lines) else ""
        out_lines.append(f"{sl}  {cl}")
    return "\n".join(out_lines)


def render_party(
    party: list[dict],
    title: str = "構築 6 体",
    with_sprite: bool = True,
) -> str:
    """Render a 6-pokemon party as stacked cards (optionally with ASCII sprites).

    Args:
        party: list of build_meta dicts. Each must have at minimum 'pokemon_id'.
        title: top header
        with_sprite: try to render ASCII sprite via pokemon-colorscripts/pokeget/pokego
                     if any is installed. fail-soft if none available.
    """
    lines = []
    lines.append(f"# {title}")
    lines.append("")
    for i, member in enumerate(party, 1):
        pid = member.pop("pokemon_id") if "pokemon_id" in member else None
        if not pid:
            continue
        member.setdefault("slot", i)
        if with_sprite:
            sprite = render_pokemon_sprite(pid)
            if sprite:
                lines.append(sprite)
        lines.append(render_pokemon_card(pid, member))
        lines.append("")
    return "\n".join(lines)


# -----------------------------------------------------------------------------
# ASCII sprite integration (v0.5.0+)
# -----------------------------------------------------------------------------
# 世界の Pokemon CLI ツール群 (pokemon-colorscripts / pokeget / pokego / pokeshell) を
# auto-detect して ASCII sprite を card に埋め込む。fail-soft 設計、ツール無しでも動作。
# 既存 ~/.my_commands/poke (背景画像用) とは独立、inline ASCII art 用途。

import shutil
import subprocess


def _detect_sprite_tool() -> Optional[tuple[str, str]]:
    """Detect installed sprite tool and return (name, command) tuple, or None.

    Priority: pokemon-colorscripts → pokeget → pokego → pokeshell → None.
    """
    candidates = [
        ("pokemon-colorscripts", "pokemon-colorscripts"),
        ("pokeget",              "pokeget"),
        ("pokego",               "pokego"),
        ("pokeshell",            "pokeshell"),
    ]
    for name, cmd in candidates:
        if shutil.which(cmd):
            return (name, cmd)
    return None


_VALID_SIZES = {"small", "medium", "large"}


def render_pokemon_sprite(
    pokemon_id: str,
    *,
    shiny: bool = False,
    form: Optional[str] = None,
    big: bool = False,
    size: str = "medium",
) -> str:
    """Render ASCII sprite for a pokemon using detected CLI tool.

    Returns empty string if no sprite tool available (fail-soft).

    Tool flag conventions:
      pokemon-colorscripts: -n <name> [--small | (default)] [--shiny] [--form <form>] [--no-title]
                            (no native "large" flag — falls back to default)
      pokeget:              <name> [--shiny] [--form <form>] [--big]
                            (no "small" flag — default render is "small/medium")
      pokego:               -n <name> [--shiny]   (no size control — kwarg ignored)
      pokeshell:            <name>     [--shiny]   (no size control — kwarg ignored)

    Args:
        pokemon_id: Showdown ID (e.g. "garchomp"). Will be lowercased.
        shiny: shiny variant.
        form: alternate form (mega/regional/etc; tool-dependent).
        big: legacy alias — when True, equivalent to size="large".
        size: "small" / "medium" / "large" (default "medium" — neutral, PQG #2).
              Unknown values silently fall back to "medium".

    Returns:
        Sprite text (stdout) on success, "" on any failure.
    """
    tool = _detect_sprite_tool()
    if not tool:
        return ""
    name, cmd = tool
    # Normalize size; legacy `big` overrides to "large" if explicitly True.
    eff_size = size if size in _VALID_SIZES else "medium"
    if big:
        eff_size = "large"

    pid = pokemon_id.lower()
    args: list[str] = [cmd]
    try:
        if name == "pokemon-colorscripts":
            args += ["-n", pid, "--no-title"]
            if eff_size == "small":
                args.append("--small")
            # "medium" = default, "large" = no native flag → default
            if shiny:
                args.append("--shiny")
            if form:
                args += ["--form", form]
        elif name == "pokeget":
            args += [pid]
            if shiny:
                args.append("--shiny")
            if form:
                args += ["--form", form]
            if eff_size == "large":
                args.append("--big")
            # "small"/"medium" — no flag (default render)
        elif name in ("pokego", "pokeshell"):
            args += ["-n", pid] if name == "pokego" else [pid]
            if shiny:
                args.append("--shiny")
            # size kwarg ignored for these tools (documented above)
        else:
            return ""
        result = subprocess.run(args, capture_output=True, text=True, timeout=5)
        return result.stdout.rstrip("\n") if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


# -----------------------------------------------------------------------------
# Pokemon Showdown export format (v0.5.0+)
# -----------------------------------------------------------------------------
# 公式 PS export 形式 (Item / Ability / EVs / Nature / Moves) で party を出力。
# https://github.com/smogon/pokemon-showdown/blob/master/COMMANDLINE.md 準拠。

def export_showdown_format(party: list[dict]) -> str:
    """Export party as Pokemon Showdown text format (paste-able to Teambuilder).

    Args:
        party: list of build_meta dicts (same as render_party).
               Required keys: pokemon_id, item, ability, evs (string or dict), nature, moves.
               Optional: jp_name (ignored), gender, level (default 50), tera_type.

    Output (per Pokemon):
        Garchomp @ Focus Sash
        Ability: Rough Skin
        EVs: 252 Atk / 4 Def / 252 Spe
        Jolly Nature
        Tera Type: Steel
        - Earthquake
        - Outrage
        - Stealth Rock
        - Stone Edge
    """
    from lib.lookup import get_pokedex_entry, resolve_move

    blocks = []
    for member in party:
        pid = member.get("pokemon_id")
        if not pid:
            continue
        pdex = get_pokedex_entry(pid) or {}
        name_en = pdex.get("name", pid)

        item = member.get("item", "")
        ability = member.get("ability", pdex.get("abilities", {}).get("0", ""))
        nature = member.get("nature", "")
        evs = member.get("evs", "")
        tera = member.get("tera_type")
        moves = member.get("moves", [])

        # EVs: accept string ("AS252+B4") or dict ({"atk":252,"spe":252,"def":4})
        if isinstance(evs, dict):
            order = [("HP","hp"),("Atk","atk"),("Def","def"),("SpA","spa"),("SpD","spd"),("Spe","spe")]
            evs_str = " / ".join(f"{evs[k]} {label}" for label, k in order if evs.get(k))
        else:
            evs_str = str(evs)

        lines = [f"{name_en} @ {item}" if item else name_en]
        if ability:
            lines.append(f"Ability: {ability}")
        if evs_str:
            lines.append(f"EVs: {evs_str}")
        if nature:
            lines.append(f"{nature} Nature")
        if tera:
            lines.append(f"Tera Type: {tera}")
        for mv in moves:
            r = resolve_move(mv) if isinstance(mv, str) else None
            mid = r.get("id") if isinstance(r, dict) else None
            md = None
            if mid:
                from lib.lookup import get_move
                md = get_move(mid) or {}
            mv_en = md.get("name", mv) if md else mv
            lines.append(f"- {mv_en}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


# -----------------------------------------------------------------------------
# Type weakness chart (v0.5.1+)
# -----------------------------------------------------------------------------
# 図表ファースト原則 (SKILL.md §5) の「タイプ相性: 4倍/2倍/1倍/½/¼/0」に対応する
# defender 視点の弱点・耐性チャート。dual-type 対応、絵文字 + JP 名で表示。

def render_type_weakness_chart(types: list[str]) -> str:
    """Render type-based weakness/resistance chart for given pokemon types.

    Computes effectiveness when DEFENDING against each attack type, given
    the defender's typing (1 or 2 types). Pure function — only depends on
    `lib.lookup.get_typechart()` (read-only) and module-level TYPE_EMOJI.

    Showdown typechart conventions:
        - top-level keys are lowercase ("dragon", "ground")
        - damageTaken keys are PascalCase ("Dragon", "Ground", "Stellar")
        - codes: 0=neutral(×1), 1=weak(×2), 2=resist(×½), 3=immune(×0)

    Dual-type effectiveness: multiply each type's multiplier.

    Args:
        types: list of defender types (PascalCase English, e.g. ["Dragon", "Ground"])

    Returns:
        Multiline string grouped by multiplier (4x / 2x / 1x / ½ / ¼ / 0).
        Empty groups omitted. "Stellar" attack type filtered out (Tera-only,
        not relevant for general defensive analysis).
    """
    from lib.lookup import get_typechart  # local import to avoid cycles

    typechart = get_typechart() or {}

    # Valid attack types = the typechart's defender keys, capitalized (matches
    # damageTaken's PascalCase). damageTaken also contains non-type keys like
    # 'brn', 'par', 'sandstorm' — those must be filtered out.
    attack_types: set[str] = {k.capitalize() for k in typechart.keys()}
    # Drop Stellar — it's a Tera-only attack type, not used for defensive analysis.
    attack_types.discard("Stellar")

    # Compute defender's effectiveness vs each attack type.
    eff: dict[str, float] = {}
    for atk in sorted(attack_types):
        m = 1.0
        for def_t in types:
            entry = typechart.get(def_t.lower())
            if not entry:
                continue
            code = entry.get("damageTaken", {}).get(atk)
            if code == 1:
                m *= 2.0
            elif code == 2:
                m *= 0.5
            elif code == 3:
                m *= 0.0
        eff[atk] = m

    # Bucketize. Keys preserve canonical multiplier set for stable display order.
    buckets: dict[float, list[str]] = {4.0: [], 2.0: [], 1.0: [], 0.5: [], 0.25: [], 0.0: []}
    for atk, mult in eff.items():
        if mult in buckets:
            buckets[mult].append(atk)

    def fmt_types(tlist: list[str]) -> str:
        if not tlist:
            return "(該当なし)"
        return " / ".join(f"{_type_emoji(t)} {_type_jp(t)}" for t in tlist)

    label_map = [
        (4.0,  "弱点 4倍"),
        (2.0,  "弱点 2倍"),
        (1.0,  "等倍   "),
        (0.5,  "耐性 ½ "),
        (0.25, "耐性 ¼ "),
        (0.0,  "無効   "),
    ]
    lines = []
    for mult, label in label_map:
        items = buckets[mult]
        if not items:
            continue
        lines.append(f"{label}: {fmt_types(items)}")
    return "\n".join(lines) if lines else "(該当なし)"


# Type matchup table
TYPE_CHART_MULT_TO_SYMBOL = {
    4.0: "◎4倍",
    2.0: "○2倍",
    1.0: "  1倍",
    0.5: "△½",
    0.25: "△¼",
    0.0: "× 無",
}


def render_type_matchup(
    pokemon_types: list[str],
    typechart: dict,
    jp_type_names: Optional[dict[str, str]] = None,
) -> str:
    """Render an attack-type-vs-this-pokemon matchup grid.

    pokemon_types: e.g. ["Ground", "Fire"]
    typechart: data/typechart.json structure (mapping defender-type -> attacker-multipliers)
    jp_type_names: optional map TypeEN -> JP

    Returns markdown table.
    """
    # Effectiveness map: for each attacker type, multiplier vs the pokemon
    eff: dict[str, float] = {}
    for atk_type in typechart.keys():
        m = 1.0
        for def_type in pokemon_types:
            entry = typechart.get(def_type)
            if not entry:
                continue
            d = entry.get("damageTaken", {})
            code = d.get(atk_type)
            # Showdown encodes: 0 = neutral, 1 = weakness x2, 2 = resist x0.5, 3 = immune x0
            if code == 1:
                m *= 2.0
            elif code == 2:
                m *= 0.5
            elif code == 3:
                m *= 0.0
        eff[atk_type] = m

    # Bucket by multiplier
    buckets: dict[float, list[str]] = {4.0: [], 2.0: [], 1.0: [], 0.5: [], 0.25: [], 0.0: []}
    for t, mult in eff.items():
        if mult in buckets:
            buckets[mult].append(t)
        elif mult > 1.0:
            buckets[2.0 if mult == 2.0 else 4.0].append(t)
        elif mult < 1.0 and mult > 0:
            buckets[0.5 if mult == 0.5 else 0.25].append(t)
        elif mult == 0:
            buckets[0.0].append(t)

    def jp(t: str) -> str:
        return jp_type_names.get(t, t) if jp_type_names else t

    lines = []
    types_jp = " / ".join(jp(t) for t in pokemon_types)
    lines.append(f"## タイプ相性: {types_jp}")
    lines.append("")
    lines.append("| 倍率 | タイプ |")
    lines.append("|---|---|")
    for mult in [4.0, 2.0, 1.0, 0.5, 0.25, 0.0]:
        types = sorted(buckets[mult])
        if not types:
            continue
        lines.append(f"| {TYPE_CHART_MULT_TO_SYMBOL[mult]} | {', '.join(jp(t) for t in types)} |")
    return "\n".join(lines)


def render_role_matrix(
    self_team: list[str],
    opp_team: list[str],
    matchup_fn,
) -> str:
    """Render NxM matchup matrix as markdown table.

    matchup_fn(self_member, opp_member) -> str (e.g. '○', '×', '△') or short note.
    """
    lines = []
    lines.append("## 役割対象マトリクス")
    lines.append("")
    header = "| 自軍 \\ 相手 | " + " | ".join(opp_team) + " |"
    sep = "|---|" + "|".join(["---"] * len(opp_team)) + "|"
    lines.append(header)
    lines.append(sep)
    for s in self_team:
        cells = [matchup_fn(s, o) for o in opp_team]
        lines.append(f"| {s} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render_cycle_flow(chain: list[str]) -> str:
    """Render an ASCII chain: A → B → C ↩."""
    if not chain:
        return "(empty cycle)"
    return "## サイクル\n```\n" + " → ".join(chain) + " ↩\n```"


def render_usage_top(
    usage_data: dict,
    n: int = 20,
    jp_name_fn=None,
) -> str:
    """Render top-N usage stats as markdown bar chart."""
    rows = usage_data.get("pokemon", [])[:n]
    if not rows:
        return "(no usage data)"
    max_pct = max(r["usage_percent"] for r in rows)
    bar_w = 30
    lines = []
    lines.append(f"## 使用率 TOP {n} (total_battles={usage_data.get('total_battles', '?')})")
    lines.append("")
    lines.append("```")
    for r in rows:
        name = r["name"]
        pct = r["usage_percent"]
        bar_len = int(pct / max_pct * bar_w)
        bar = "█" * bar_len + " " * (bar_w - bar_len)
        if jp_name_fn:
            jp = jp_name_fn(name) or name
            label = f"{r['rank']:3d}. {jp:<14s}"
        else:
            label = f"{r['rank']:3d}. {name:<20s}"
        lines.append(f"{label} {bar} {pct:5.2f}%")
    lines.append("```")
    return "\n".join(lines)
