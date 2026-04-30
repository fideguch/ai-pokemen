#!/usr/bin/env python3
"""
Fetch YouTube transcripts for tracked Champions creator channels.

Workflow:
1. Pull each channel's RSS feed (no auth required) to discover videos in the
   last 24h.
2. For each new video, run yt-dlp to download auto-captions (Japanese first,
   English fallback) into cache/yt_transcripts/YYYY-MM-DD/.
3. Append a record to cache/yt_transcripts/INDEX.json.

Filtering: only videos whose title contains a Champions-relevant keyword
(構築/環境/ティア/対面/メタ/育成/採用率) are downloaded — random clips are skipped.

Fail-soft: If yt-dlp is not installed, this script logs a warning and exits 0.
Install with `brew install yt-dlp`. The skill keeps working without YT data.

Tracked channels:
- Kuroko_965: UCGDAdoVs7er9UOIF9KzP99Q
- KYOUPOKE:   UCmnZL4tFRl4sm-uJOxTLHmg
- pokesol:    UCeQNXy1ReMSa1GuK7nhMvIA

Usage:
    python3 scripts/fetch_yt_transcripts.py            # normal run
    python3 scripts/fetch_yt_transcripts.py --dry-run  # plan only
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPT_DIR = ROOT / "cache" / "yt_transcripts"
INDEX_PATH = TRANSCRIPT_DIR / "INDEX.json"

CHANNELS: list[dict] = [
    {"name": "Kuroko_965", "channel_id": "UCGDAdoVs7er9UOIF9KzP99Q"},
    {"name": "KYOUPOKE",   "channel_id": "UCmnZL4tFRl4sm-uJOxTLHmg"},
    {"name": "pokesol",    "channel_id": "UCeQNXy1ReMSa1GuK7nhMvIA"},
]

KEYWORDS = ["構築", "環境", "ティア", "対面", "メタ", "育成", "採用率", "選出"]
RSS_URL_FMT = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
USER_AGENT = "pokemon-champions-skill/1.0"
MAX_AGE_HOURS = 24


# -----------------------------------------------------------------------------
# Index helpers
# -----------------------------------------------------------------------------


def ensure_empty_index() -> None:
    """Initialize cache/yt_transcripts/INDEX.json if it does not exist."""
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    if INDEX_PATH.exists():
        return
    INDEX_PATH.write_text(
        json.dumps({"schema_version": "1.0.0", "videos": []}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )


def _load_index() -> dict:
    if not INDEX_PATH.exists():
        ensure_empty_index()
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def _save_index(idx: dict) -> None:
    INDEX_PATH.write_text(
        json.dumps(idx, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


# -----------------------------------------------------------------------------
# RSS discovery
# -----------------------------------------------------------------------------


def _http_get(url: str, timeout: float = 15.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_recent_videos(channel: dict, cutoff: datetime) -> list[dict]:
    """Return list of {video_id, title, published, channel_name} after cutoff."""
    url = RSS_URL_FMT.format(channel_id=channel["channel_id"])
    try:
        body = _http_get(url)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"[warn] RSS fetch failed for {channel['name']}: {e}", file=sys.stderr)
        return []

    # Parse Atom feed
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
    }
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        print(f"[warn] RSS parse failed for {channel['name']}: {e}", file=sys.stderr)
        return []

    out: list[dict] = []
    for entry in root.findall("atom:entry", ns):
        vid_elem = entry.find("yt:videoId", ns)
        title_elem = entry.find("atom:title", ns)
        pub_elem = entry.find("atom:published", ns)
        if vid_elem is None or title_elem is None or pub_elem is None:
            continue
        try:
            pub = datetime.fromisoformat(pub_elem.text.replace("Z", "+00:00"))
        except ValueError:
            continue
        if pub < cutoff:
            continue
        title = title_elem.text or ""
        if not any(kw in title for kw in KEYWORDS):
            continue
        out.append({
            "video_id": vid_elem.text,
            "title": title,
            "published": pub.isoformat(),
            "channel_name": channel["name"],
        })
    return out


# -----------------------------------------------------------------------------
# yt-dlp download
# -----------------------------------------------------------------------------


def download_subs(video: dict, outdir: Path) -> Path | None:
    """Run yt-dlp to fetch subtitles. Returns local path or None on failure."""
    outdir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^\w぀-ヿ一-鿿-]", "_", video["title"])[:60]
    out_template = str(outdir / f"{video['channel_name']}_{video['video_id']}_{slug}.%(ext)s")
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-auto-subs",
        "--write-subs",
        "--sub-langs", "ja.*,en.*",
        "--sub-format", "vtt/best",
        "--convert-subs", "srt",
        "-o", out_template,
        f"https://www.youtube.com/watch?v={video['video_id']}",
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
    except subprocess.CalledProcessError as e:
        print(f"[warn] yt-dlp failed for {video['video_id']}: {e.stderr[:200]}", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print(f"[warn] yt-dlp timeout for {video['video_id']}", file=sys.stderr)
        return None
    # Find produced subtitle file
    candidates = list(outdir.glob(f"{video['channel_name']}_{video['video_id']}_*.srt"))
    if candidates:
        return candidates[0]
    candidates = list(outdir.glob(f"{video['channel_name']}_{video['video_id']}_*.vtt"))
    return candidates[0] if candidates else None


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def run(dry_run: bool) -> int:
    # Fail-soft yt-dlp check
    try:
        subprocess.run(
            ["yt-dlp", "--version"],
            check=True, capture_output=True, text=True, timeout=5,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"WARNING: yt-dlp not installed or unusable ({e}). Run: brew install yt-dlp",
              file=sys.stderr)
        print("Skipping yt transcript fetch (fail-soft).", file=sys.stderr)
        ensure_empty_index()
        return 0

    ensure_empty_index()
    idx = _load_index()
    known_ids = {v["video_id"] for v in idx["videos"]}

    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daydir = TRANSCRIPT_DIR / today

    candidates: list[dict] = []
    for ch in CHANNELS:
        candidates.extend(fetch_recent_videos(ch, cutoff))

    new_videos = [v for v in candidates if v["video_id"] not in known_ids]
    print(f"[info] discovered {len(candidates)} candidate videos, "
          f"{len(new_videos)} new (filtered by keyword + dedupe)")

    if dry_run:
        print("[dry-run] would download:")
        for v in new_videos:
            print(f"  - [{v['channel_name']}] {v['title']} ({v['video_id']})")
        return 0

    for v in new_videos:
        path = download_subs(v, daydir)
        record = dict(v)
        record["fetched_at"] = datetime.now(timezone.utc).isoformat()
        record["local_path"] = str(path) if path else None
        idx["videos"].append(record)
        if path:
            print(f"[ok] downloaded {path.name}")

    _save_index(idx)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="plan only, no downloads")
    args = ap.parse_args()
    sys.exit(run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
