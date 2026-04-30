"""Phase 4: Visualizers — Markdown tables + ASCII bars + matrices.

All renderers are pure functions returning markdown strings.
"""

from __future__ import annotations

from typing import Iterable, Optional


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


def render_pokemon_card(
    pokemon_id: str,
    build_meta: Optional[dict] = None,
    *,
    show_separator: bool = True,
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


def render_pokemon_sprite(
    pokemon_id: str,
    *,
    shiny: bool = False,
    form: Optional[str] = None,
    big: bool = False,
) -> str:
    """Render ASCII sprite for a pokemon using detected CLI tool.

    Returns empty string if no sprite tool available (fail-soft).
    Tools' flag conventions:
      pokemon-colorscripts: -n <name> [--shiny] [--form <form>] [--no-title]
      pokeget:              <name> [--shiny] [--form <form>] [--big]
      pokego:               -n <name> [--shiny]
      pokeshell:            <name> [--shiny]

    Args:
        pokemon_id: Showdown ID (e.g. "garchomp"). Will be lowercased.
        shiny: shiny variant
        form: alternate form (mega/regional/etc; tool-dependent)
        big: large render (pokeget only)
    """
    tool = _detect_sprite_tool()
    if not tool:
        return ""
    name, cmd = tool
    pid = pokemon_id.lower()
    args: list[str] = [cmd]
    try:
        if name == "pokemon-colorscripts":
            args += ["-n", pid, "--no-title"]
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
            if big:
                args.append("--big")
        elif name in ("pokego", "pokeshell"):
            args += ["-n", pid] if name == "pokego" else [pid]
            if shiny:
                args.append("--shiny")
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
