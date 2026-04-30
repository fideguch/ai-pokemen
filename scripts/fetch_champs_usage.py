#!/usr/bin/env python3
"""
Fetch Champions usage stats from champs.pokedb.tokyo and pokechamdb.com.

Champions usage SSOT lives at cache/champs_usage/YYYY-MM-DD.json with metadata
in cache/champs_usage/_meta.json. TTL is 6 hours unless --force is given.

Behavior:
- TTL hit (last_fetched_at within 6h, no --force): no-op, exit 0
- HTTP failure on either source: keep prior cache, log warning, exit 0 (fail-soft)
- --dry-run: print plan and skip writes (used for verification)

WebFetch fallback: if both sources fail repeatedly, manually fetch via
the Claude WebFetch tool and write the JSON to cache/champs_usage/YYYY-MM-DD.json
with the same schema (see _empty_payload below).

Usage:
    python3 scripts/fetch_champs_usage.py            # respect TTL
    python3 scripts/fetch_champs_usage.py --force    # bypass TTL
    python3 scripts/fetch_champs_usage.py --dry-run  # plan only
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache" / "champs_usage"
META_PATH = CACHE_DIR / "_meta.json"
TTL_SECONDS = 6 * 60 * 60  # 6 hours

POKEDB_URL = "https://champs.pokedb.tokyo/"
POKECHAMDB_URL = "https://pokechamdb.com/en?view=pokemon"

USER_AGENT = "pokemon-champions-skill/1.0 (cache fetcher; respects robots)"


# -----------------------------------------------------------------------------
# Source fetchers (network)
# -----------------------------------------------------------------------------


def _http_get(url: str, timeout: float = 15.0) -> str:
    """GET a URL, return the body text. Raises urllib.error on failure."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def fetch_champs_pokedb() -> dict:
    """Fetch champs.pokedb.tokyo and return raw HTML in a payload envelope.

    The actual parser is intentionally minimal — full HTML parsing requires
    lxml/bs4 which we avoid for portability. Downstream consumers should
    inspect raw_html and parse on demand.
    """
    body = _http_get(POKEDB_URL)
    return {
        "source": "champs.pokedb.tokyo",
        "url": POKEDB_URL,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "raw_html_len": len(body),
        "raw_html": body[:200_000],  # cap at 200KB to keep cache files reasonable
    }


def fetch_pokechamdb() -> dict:
    body = _http_get(POKECHAMDB_URL)
    return {
        "source": "pokechamdb.com",
        "url": POKECHAMDB_URL,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "raw_html_len": len(body),
        "raw_html": body[:200_000],
    }


def merge_sources(pokedb: dict | None, pokechamdb: dict | None) -> dict:
    """Combine source payloads into a single cache record."""
    return {
        "schema_version": "1.0.0",
        "merged_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "champs_pokedb": pokedb,
            "pokechamdb": pokechamdb,
        },
    }


# -----------------------------------------------------------------------------
# Cache helpers
# -----------------------------------------------------------------------------


def _load_meta() -> dict:
    if not META_PATH.exists():
        return {"last_fetched_at": None, "last_success_at": None, "last_error": None}
    return json.loads(META_PATH.read_text(encoding="utf-8"))


def _save_meta(meta: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _ttl_satisfied(meta: dict) -> bool:
    ts = meta.get("last_success_at")
    if not ts:
        return False
    try:
        last = datetime.fromisoformat(ts)
    except ValueError:
        return False
    age = (datetime.now(timezone.utc) - last).total_seconds()
    return age < TTL_SECONDS


def _empty_payload() -> dict:
    return {
        "schema_version": "1.0.0",
        "merged_at": datetime.now(timezone.utc).isoformat(),
        "sources": {"champs_pokedb": None, "pokechamdb": None},
        "_note": "Empty payload (no successful fetch yet).",
    }


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def run(force: bool, dry_run: bool) -> int:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    meta = _load_meta()

    if not force and _ttl_satisfied(meta):
        print(
            f"[ttl] cache fresh (last_success_at={meta['last_success_at']}); "
            "skipping. Use --force to override."
        )
        return 0

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = CACHE_DIR / f"{today}.json"

    if dry_run:
        print("[dry-run] would fetch:")
        print(f"  - {POKEDB_URL}")
        print(f"  - {POKECHAMDB_URL}")
        print(f"  - write to: {out_path}")
        print(f"  - update meta: {META_PATH}")
        return 0

    pokedb_payload = None
    pokechamdb_payload = None
    errors = []

    try:
        pokedb_payload = fetch_champs_pokedb()
        print(f"[ok] fetched {POKEDB_URL} ({pokedb_payload['raw_html_len']} bytes)")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        errors.append(f"pokedb: {e!r}")
        print(f"[warn] pokedb fetch failed: {e}", file=sys.stderr)

    try:
        pokechamdb_payload = fetch_pokechamdb()
        print(f"[ok] fetched {POKECHAMDB_URL} ({pokechamdb_payload['raw_html_len']} bytes)")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        errors.append(f"pokechamdb: {e!r}")
        print(f"[warn] pokechamdb fetch failed: {e}", file=sys.stderr)

    now = datetime.now(timezone.utc).isoformat()
    if pokedb_payload is None and pokechamdb_payload is None:
        # Both failed: keep existing cache untouched, log warning, exit 0
        meta["last_fetched_at"] = now
        meta["last_error"] = " | ".join(errors)
        _save_meta(meta)
        print(
            "[warn] both sources failed; existing cache preserved (fail-soft).",
            file=sys.stderr,
        )
        return 0

    payload = merge_sources(pokedb_payload, pokechamdb_payload)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[ok] wrote {out_path}")

    meta["last_fetched_at"] = now
    meta["last_success_at"] = now
    meta["last_error"] = " | ".join(errors) if errors else None
    _save_meta(meta)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="ignore TTL and re-fetch")
    ap.add_argument("--dry-run", action="store_true", help="plan only, no writes")
    args = ap.parse_args()
    sys.exit(run(force=args.force, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
