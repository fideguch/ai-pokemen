#!/usr/bin/env python3
"""Detect meaningful Champions usage-ranking shifts from local cached data.

Reads the two most recent cache/champs_usage/YYYY-MM-DD.json snapshots, parses
the champs.pokedb.tokyo usage ranking out of the stored raw HTML, and reports
TOP-N entries/exits and rank moves >= a threshold.

Design rule (anti-hallucination): this script ONLY reports diffs computed from
real local data. If today's ranking can't be parsed (fetch failed, HTML layout
changed), it prints NOTHING and exits non-zero so the caller stays silent rather
than inventing an alert. This is the direct fix for the 2026-06-20 incident where
a tool-starved cloud agent fabricated a meta alert.

Usage:
    python3 scripts/detect_meta_change.py            # compare latest two days
    python3 scripts/detect_meta_change.py --top 30 --threshold 3

Output (stdout): a Discord-ready alert body, or empty if no significant change.
Exit codes:
    0  ran successfully (alert on stdout if any; empty = no change)
    3  insufficient/unparseable data — caller must NOT notify
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USAGE_DIR = ROOT / "cache" / "champs_usage"
DATA_DIR = ROOT / "data"

# A ranking row: href .../show/{num}-{form}?rule=0  then  pokemon-rank">{rank}<
RANK_RE = re.compile(
    r'/pokemon/show/(\d{4})-(\d{2})\?rule=0"\s+class="list-pokemon[^"]*">\s*'
    r'<div class="pokemon-rank[^"]*">\s*(\d+)\s*</div>',
    re.S,
)
# A parse yielding fewer rows than this is treated as broken -> stay silent.
# champs.pokedb top page lists ~20; allow a few missed rows but bail on real breakage.
MIN_VALID_ROWS = 15


def _load_name_resolver():
    """Return f(num:int) -> Japanese name, falling back to '#num' on any miss."""
    try:
        pokedex = json.loads((DATA_DIR / "pokedex.json").read_text(encoding="utf-8"))
        ja = json.loads((DATA_DIR / "ja_names.json").read_text(encoding="utf-8"))
        by_id = ja.get("pokemon", {}).get("by_id", {})
    except (OSError, ValueError):
        return lambda num: f"#{num}"

    num_to_species: dict[int, str] = {}
    for species, entry in pokedex.items():
        if not isinstance(entry, dict):
            continue
        n = entry.get("num")
        if isinstance(n, int) and n not in num_to_species:  # keep base form
            num_to_species[n] = species

    def resolve(num: int) -> str:
        species = num_to_species.get(num)
        if species and species in by_id:
            return by_id[species]
        return f"#{num:04d}"

    return resolve


def parse_ranking(path: Path) -> dict[str, int]:
    """Parse {dexnum_str -> rank} from a daily snapshot's champs.pokedb HTML."""
    try:
        snap = json.loads(path.read_text(encoding="utf-8"))
        html = snap["sources"]["champs_pokedb"]["raw_html"]
    except (OSError, ValueError, KeyError, TypeError):
        return {}
    ranking: dict[str, int] = {}
    for m in RANK_RE.finditer(html):
        dexnum = f"{m.group(1)}-{m.group(2)}"
        rank = int(m.group(3))
        ranking.setdefault(dexnum, rank)
    return ranking


def _daily_files() -> list[Path]:
    """Return YYYY-MM-DD.json snapshots, newest first (excludes _meta.json)."""
    files = [p for p in USAGE_DIR.glob("*.json") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem)]
    return sorted(files, reverse=True)


def diff_rankings(today: dict[str, int], prev: dict[str, int], top_n: int, threshold: int) -> dict:
    """Compute TOP-N entries, exits, and rank moves >= threshold."""
    entered, exited, moved = [], [], []
    for dex, rank in today.items():
        if rank > top_n:
            continue
        prev_rank = prev.get(dex)
        if prev_rank is None or prev_rank > top_n:
            entered.append((dex, rank, prev_rank))
        elif abs(rank - prev_rank) >= threshold:
            moved.append((dex, rank, prev_rank))
    for dex, prev_rank in prev.items():
        if prev_rank <= top_n and today.get(dex, top_n + 1) > top_n:
            exited.append((dex, prev_rank, today.get(dex)))
    entered.sort(key=lambda x: x[1])
    moved.sort(key=lambda x: x[1])
    exited.sort(key=lambda x: x[1])
    return {"entered": entered, "exited": exited, "moved": moved}


def _dexnum_num(dexnum: str) -> int:
    return int(dexnum.split("-")[0])


def format_alert(changes: dict, name_of, today_date: str, prev_date: str, top_n: int) -> str:
    """Render a concise Discord message, or '' if nothing significant."""
    entered, exited, moved = changes["entered"], changes["exited"], changes["moved"]
    if not (entered or exited or moved):
        return ""
    lines = [f"📊 ポケチャン環境変動 (TOP{top_n} / {prev_date} → {today_date})", ""]
    if entered:
        lines.append("🆕 新規ランクイン")
        for dex, rank, prev_rank in entered:
            via = "圏外" if prev_rank is None else f"{prev_rank}位"
            lines.append(f"  ・{name_of(_dexnum_num(dex))}: {via} → **{rank}位**")
    if moved:
        lines.append("🔀 順位変動")
        for dex, rank, prev_rank in moved:
            arrow = "↑" if rank < prev_rank else "↓"
            lines.append(f"  ・{name_of(_dexnum_num(dex))}: {prev_rank}位 → {rank}位 {arrow}{abs(rank - prev_rank)}")
    if exited:
        lines.append("⬇️ 圏外へ")
        for dex, prev_rank, now in exited:
            now_txt = "圏外" if now is None else f"{now}位"
            lines.append(f"  ・{name_of(_dexnum_num(dex))}: {prev_rank}位 → {now_txt}")
    lines += ["", "出典: champs.pokedb.tokyo (ローカル実データ差分)。詳細は /pokechamp で確認。"]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--top", type=int, default=30, help="TOP-N window (default 30)")
    ap.add_argument("--threshold", type=int, default=3, help="min rank delta to report (default 3)")
    args = ap.parse_args(argv)

    files = _daily_files()
    if len(files) < 2:
        print("insufficient snapshots (need >= 2 days)", file=sys.stderr)
        return 3

    today_ranking = parse_ranking(files[0])
    prev_ranking = parse_ranking(files[1])
    if len(today_ranking) < MIN_VALID_ROWS or len(prev_ranking) < MIN_VALID_ROWS:
        print(
            f"unparseable ranking (today={len(today_ranking)} prev={len(prev_ranking)} rows) — staying silent",
            file=sys.stderr,
        )
        return 3

    changes = diff_rankings(today_ranking, prev_ranking, args.top, args.threshold)
    alert = format_alert(changes, _load_name_resolver(), files[0].stem, files[1].stem, args.top)
    if alert:
        print(alert)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
