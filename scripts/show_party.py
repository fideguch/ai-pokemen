#!/usr/bin/env python3
"""Display a 6-pokemon party from a build file as Pokemon Cards.

Usage:
    python3 scripts/show_party.py <build_id>            # default vertical layout
    python3 scripts/show_party.py A.3-Final-v7.8 --compact
    python3 scripts/show_party.py A.3-Final-v7.8 --weakness --radar
    python3 scripts/show_party.py A.3-Final-v7.8 --no-sprite

Build files: builds/<build_id>.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
BUILDS_DIR = ROOT / "builds"
BUILD_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")

# Mega prefix stripping: resolver lacks "メガXXX" entries; strip leading mega-marker
# and pass to resolver. Also strip trailing form indicators like "(白)" / "(剣)".
MEGA_PREFIX_RE = re.compile(r"^(?:メガ|Mega-?|M-)")
PAREN_TRAIL_RE = re.compile(r"\s*\([^)]*\)\s*$")


def validate_build_id(build_id: str) -> Path:
    """Validate build_id and resolve to a path inside BUILDS_DIR.

    Implements PQG condition #1 (path traversal mitigation):
      1. regex check on build_id allowed chars
      2. resolve and assert is_relative_to(BUILDS_DIR.resolve())
      3. file existence check
    """
    if not build_id or not BUILD_ID_RE.match(build_id):
        print(
            f"[ERROR] Invalid build_id: {build_id!r} "
            f"(must match {BUILD_ID_RE.pattern})",
            file=sys.stderr,
        )
        sys.exit(2)
    target = (BUILDS_DIR / f"{build_id}.md").resolve()
    builds_root = BUILDS_DIR.resolve()
    if not target.is_relative_to(builds_root):
        print(f"[ERROR] Path traversal denied: {build_id!r}", file=sys.stderr)
        sys.exit(2)
    if not target.exists():
        print(f"[ERROR] Build not found: {target}", file=sys.stderr)
        sys.exit(1)
    return target


def _resolve_jp_pokemon(jp_name: str) -> tuple[str | None, str]:
    """Resolve a JP pokemon name (possibly with メガ prefix / parenthetical form)
    to a (showdown_id, jp_canonical) pair.

    Returns (None, original) if unresolvable.
    """
    from lib.lookup import resolve_pokemon

    raw = jp_name.strip()
    cleaned = PAREN_TRAIL_RE.sub("", raw).strip()
    candidates = [cleaned]
    stripped = MEGA_PREFIX_RE.sub("", cleaned).strip()
    if stripped and stripped != cleaned:
        candidates.append(stripped)

    for c in candidates:
        r = resolve_pokemon(c)
        if r.get("id"):
            return r["id"], c
    return None, raw


def parse_party_table(md_text: str) -> list[dict]:
    """Parse §1 構築 6 体一覧 markdown table into a list of build_meta dicts.

    Expected header (8 columns):
        | # | ポケ | 持ち物 | 特性 | 性格 | EV | EV意図 | 技構成 |

    Walks lines after `## §1` header until blank/next heading. Skips header
    row (`| #`) and separator (`|---`).

    Returns list of dicts: {pokemon_id, jp_name, item, ability, nature, evs,
                            evs_intent, moves, slot}.
    """
    party: list[dict] = []
    in_section = False
    slot = 0

    for line in md_text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## §1"):
            in_section = True
            continue
        if in_section and stripped.startswith("## "):
            # Reached next section heading.
            break
        if not in_section:
            continue
        if not stripped.startswith("|"):
            continue
        if stripped.startswith("|---") or stripped.startswith("| #"):
            continue

        # Split table row, drop empty leading/trailing.
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 8:
            continue
        # Expect: [#, ポケ, 持ち物, 特性, 性格, EV, EV意図, 技構成]
        try:
            slot_num = int(cells[0])
        except ValueError:
            continue
        slot = slot_num
        jp_raw = cells[1]
        item = cells[2]
        ability = cells[3]
        nature = cells[4]
        evs = cells[5]
        evs_intent = cells[6]
        moves_raw = cells[7]

        pid, jp_canonical = _resolve_jp_pokemon(jp_raw)
        if not pid:
            print(
                f"[WARN] slot {slot}: unresolved pokemon {jp_raw!r}, skipping",
                file=sys.stderr,
            )
            continue

        moves = [m.strip() for m in moves_raw.split("/") if m.strip()]
        party.append({
            "slot": slot,
            "pokemon_id": pid,
            "jp_name": jp_raw,  # preserve original (may include メガ prefix for display)
            "item": item,
            "ability": ability,
            "nature": nature,
            "evs": evs,
            "rationale": [evs_intent] if evs_intent else [],
            "moves": moves,
        })

    return party


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Display a 6-pokemon party from a build file as Pokemon Cards.",
    )
    parser.add_argument("build_id", help="Build identifier (e.g. A.3-Final-v7.8)")
    parser.add_argument("--compact", action="store_true",
                        help="2-column compact layout (sprite left, info right)")
    parser.add_argument("--weakness", action="store_true",
                        help="Show weakness/resistance section per pokemon")
    parser.add_argument("--radar", action="store_true",
                        help="Show base-stats radar (horizontal bars)")
    parser.add_argument("--shiny", action="store_true",
                        help="Render shiny variant of sprites")
    parser.add_argument("--size", choices=["small", "medium", "large"],
                        default="medium", help="Sprite size (default medium)")
    parser.add_argument("--no-sprite", action="store_true",
                        help="Disable sprite rendering")
    args = parser.parse_args()

    build_path = validate_build_id(args.build_id)
    md_text = build_path.read_text(encoding="utf-8")

    party = parse_party_table(md_text)
    if not party:
        print(f"[ERROR] No party rows found in §1 of {build_path}", file=sys.stderr)
        return 1

    # Lazy import after sys.path setup.
    from lib.visualizer import (
        render_pokemon_card,
        render_pokemon_card_compact,
        render_pokemon_sprite,
    )

    print(f"# 構築 {args.build_id}")
    print()
    for member in party:
        pid = member["pokemon_id"]
        # Build a copy without pokemon_id for the card kwargs.
        meta = {k: v for k, v in member.items() if k != "pokemon_id"}

        if args.compact:
            sprite_text = "" if args.no_sprite else render_pokemon_sprite(
                pid, shiny=args.shiny, size=args.size,
            )
            print(render_pokemon_card_compact(
                pid, meta,
                sprite_text=sprite_text or None,
                show_weakness=args.weakness,
                show_radar=args.radar,
            ))
        else:
            if not args.no_sprite:
                sprite = render_pokemon_sprite(pid, shiny=args.shiny, size=args.size)
                if sprite:
                    print(sprite)
            print(render_pokemon_card(
                pid, meta,
                show_weakness=args.weakness,
                show_radar=args.radar,
            ))
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
