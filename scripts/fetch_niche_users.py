#!/usr/bin/env python3
"""
fetch_niche_users.py — Champions niche-tech 採用率網羅取得 (HG-niche-depth)

Usage:
    python3 fetch_niche_users.py <niche技日本語名>
    python3 fetch_niche_users.py            # 一覧表示
    python3 fetch_niche_users.py ちょうはつ
    python3 fetch_niche_users.py --force ちょうはつ   # cache 無視

Output:
    cache/niche_users/YYYY-MM-DD/<move_name>.json

実装方針:
- TOP213 全件 fetch は重いため、niche 技ごとの候補ポケ seed を持つ
- 各候補の個別ページから採用率% を正規表現で抽出
- 24h cache (cache/niche_users/YYYY-MM-DD/)
- いたずらごころ / ばけのかわ / ふゆう 特性での先制 / 無効化を脅威度に反映

権威ソース (HARD-GATE 遵守):
- champs.pokedb.tokyo (Tier S+)

NEVER fetch from: game8 / altema / gamewith / その他 Tier 外
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
CACHE_ROOT = SKILL_ROOT / "cache" / "niche_users"
RAW_CACHE_ROOT = SKILL_ROOT / "cache" / "champs_pokedb_raw"
CACHE_ROOT.mkdir(parents=True, exist_ok=True)
RAW_CACHE_ROOT.mkdir(parents=True, exist_ok=True)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 pokemon-champions-skill/0.5.4"
CACHE_TTL_HOURS = 24

# niche 技 → 候補ポケ seed
# (zukan_id_4digit, form_2digit, 日本語名, 英名, 特性で先制/無効化フラグ)
NICHE_USERS_SEED = {
    "ちょうはつ": [
        ("0547", "00", "エルフーン", "whimsicott", "いたずらごころ:先制"),
        ("0302", "00", "ヤミラミ", "sableye", "いたずらごころ:先制"),
        ("0302", "50", "メガヤミラミ", "sableye-mega", "マジックミラー:無効化"),
        ("0094", "00", "ゲンガー", "gengar", ""),
        ("0094", "50", "メガゲンガー", "gengar-mega", ""),
        ("0778", "00", "ミミッキュ", "mimikyu", "ばけのかわ:1回耐性"),
        ("0479", "10", "ウォッシュロトム", "rotom-wash", ""),
        ("0479", "20", "ヒートロトム", "rotom-heat", ""),
        ("0006", "50", "メガリザードンY", "charizard-mega-y", ""),
        ("0911", "00", "ラウドボーン", "skeledirge", ""),
        ("0658", "00", "ゲッコウガ", "greninja", ""),
        ("0635", "00", "サザンドラ", "hydreigon", ""),
        ("0488", "00", "クレセリア", "cresselia", ""),
        ("0908", "00", "マスカーニャ", "meowscarada", ""),
    ],
    "トリック": [
        ("0479", "10", "ウォッシュロトム", "rotom-wash", ""),
        ("0479", "20", "ヒートロトム", "rotom-heat", ""),
        ("0094", "00", "ゲンガー", "gengar", ""),
        ("0635", "00", "サザンドラ", "hydreigon", ""),
        ("0567", "00", "アーケオス", "archeops", ""),
        ("0429", "00", "ムウマージ", "mismagius", ""),
    ],
    "みちづれ": [
        ("0094", "00", "ゲンガー", "gengar", ""),
        ("0094", "50", "メガゲンガー", "gengar-mega", ""),
        ("0570", "00", "ゾロア", "zorua", ""),
        ("0571", "00", "ゾロアーク", "zoroark", ""),
    ],
    "アンコール": [
        ("0547", "00", "エルフーン", "whimsicott", "いたずらごころ:先制"),
        ("0302", "00", "ヤミラミ", "sableye", "いたずらごころ:先制"),
        ("0302", "50", "メガヤミラミ", "sableye-mega", ""),
        ("0429", "00", "ムウマージ", "mismagius", ""),
        ("0571", "00", "ゾロアーク", "zoroark", ""),
        ("0428", "00", "ミミロップ", "lopunny", ""),
        ("0428", "50", "メガミミロップ", "lopunny-mega", ""),
    ],
    "おきみやげ": [
        ("0547", "00", "エルフーン", "whimsicott", "いたずらごころ:先制"),
        ("0302", "00", "ヤミラミ", "sableye", "いたずらごころ:先制"),
    ],
    "コットンガード": [
        ("0547", "00", "エルフーン", "whimsicott", ""),
        ("0556", "00", "マラカッチ", "maractus", ""),
    ],
    "こうそくスピン": [
        ("0660", "00", "ホルード", "diggersby", ""),
        ("0908", "00", "マスカーニャ", "meowscarada", ""),
        ("0903", "00", "オオニューラ", "sneasler", ""),
        ("0121", "00", "スターミー", "starmie", ""),
        ("0306", "00", "ボスゴドラ", "aggron", ""),
    ],
    "どくびし": [
        ("0970", "00", "キラフロル", "glimmora", "どくよけ:設置"),
        ("0073", "00", "ドククラゲ", "tentacruel", ""),
        ("0211", "00", "ハリーセン", "qwilfish", ""),
        ("0958", "00", "サーフゴー", "gholdengo", ""),
    ],
    "キノコのほうし": [
        ("0286", "00", "キノガッサ", "breloom", ""),
        ("0598", "00", "ナットレイ", "ferrothorn", ""),
    ],
}


def fetch_url(url: str, ttl_hours: int = CACHE_TTL_HOURS) -> str:
    """raw HTML を 24h cache 付きで取得。"""
    cache_key = re.sub(r"[^A-Za-z0-9_.-]", "_", url)[-180:]
    cache_path = RAW_CACHE_ROOT / cache_key
    if cache_path.exists():
        age_h = (time.time() - cache_path.stat().st_mtime) / 3600
        if age_h < ttl_hours:
            return cache_path.read_text(encoding="utf-8")

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        return f"<!-- ERROR: {e} -->"
    cache_path.write_text(html, encoding="utf-8")
    return html


def extract_move_rate(html: str, move_jp: str) -> dict:
    """個別ポケページから niche 技 listing 確認 + 採用率%抽出を試行。

    champs.pokedb.tokyo は SPA (Vue.js) で render 済みの数値は生 HTML に
    含まれない (採用率% は API から JS で挿入される)。生 HTML で確認できるのは
    `pokemon-trend__move-name` セクション内に技名があるか (= 採用率 5%以上で
    表示閾値を越えているか) のみ。

    実数 % が必要な場合は Claude が WebFetch で個別ページを取り直すべし。
    本関数は二値判定 (listed / not_listed) と挿入位置を返す。
    """
    out = {"move": move_jp, "rate": None, "listed": False, "raw_excerpt": None}
    if "ERROR" in html[:200]:
        out["error"] = html[:200].strip()
        return out

    listed_pattern = (
        rf'pokemon-trend__move-name"\s*>\s*{re.escape(move_jp)}\s*<'
    )
    m = re.search(listed_pattern, html)
    if m:
        out["listed"] = True
        out["raw_excerpt"] = html[max(0, m.start() - 30): m.end() + 80]
        out["note"] = "個別ページに掲載 (採用率 ≥5%)、実数% は WebFetch で別途取得"

    if not out["listed"]:
        if html.find(move_jp) >= 0:
            out["note"] = "HTML 内に技名は出現するが trend listing 外 (採用率<5%の可能性)"
        else:
            out["note"] = "個別ページ非掲載 (採用率 <5% / 表示閾値外)"

    for m2 in re.finditer(
        rf"{re.escape(move_jp)}[^0-9]{{0,500}}?([0-9]{{1,2}}\.[0-9])\s*%",
        html,
    ):
        try:
            v = float(m2.group(1))
            if 0 < v <= 100:
                out["rate"] = v
                break
        except (TypeError, ValueError):
            continue

    return out


def extract_ability_top(html: str) -> dict:
    """主要特性 1 件抽出 (上位採用率)。"""
    m = re.search(
        r"(いたずらごころ|ばけのかわ|ふゆう|てんねん|のろわれボディ|"
        r"マルチスケイル|すながくれ|すなおこし|バトルスイッチ|"
        r"せいしんりょく|きんちょうかん|きもったま)[^0-9<>]{0,40}([0-9]+\.[0-9])\s*%",
        html,
    )
    if m:
        return {"name": m.group(1), "rate": float(m.group(2))}
    return {}


def fetch_pokemon_data(zid: str, form: str, jp: str, en: str, special: str, move: str) -> dict:
    url = f"https://champs.pokedb.tokyo/pokemon/show/{zid}-{form}?rule=0"
    html = fetch_url(url)
    move_data = extract_move_rate(html, move)
    ability_top = extract_ability_top(html)
    return {
        "zukan_id": zid,
        "form": form,
        "name_jp": jp,
        "name_en": en,
        "special_note": special,
        "url": url,
        "move_data": move_data,
        "ability_top": ability_top,
    }


def threat_score(entry: dict) -> float:
    """脅威度スコア = 採用率% × 特性 boost。
    rate が None でも listed=True なら 5.0% 仮置き、特性 boost で並び替え可能に。"""
    move_data = entry.get("move_data") or {}
    rate = move_data.get("rate")
    if rate is None:
        rate = 5.0 if move_data.get("listed") else 0.0
    boost = 1.0
    note = entry.get("special_note", "")
    if "先制" in note:
        boost = 2.5
    elif "1回耐性" in note:
        boost = 1.4
    elif "無効化" in note:
        boost = 1.8
    elif "設置" in note:
        boost = 1.3
    return round(rate * boost, 2)


def fetch_all(move_jp: str, force: bool = False) -> dict:
    seed = NICHE_USERS_SEED.get(move_jp)
    if not seed:
        return {
            "error": f"niche move not in seed list: {move_jp}",
            "available": sorted(NICHE_USERS_SEED.keys()),
        }

    today = datetime.now().strftime("%Y-%m-%d")
    out_dir = CACHE_ROOT / today
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{move_jp}.json"

    if out_path.exists() and not force:
        age_h = (time.time() - out_path.stat().st_mtime) / 3600
        if age_h < CACHE_TTL_HOURS:
            data = json.loads(out_path.read_text(encoding="utf-8"))
            data["_from_cache"] = True
            return data

    rows = []
    for zid, form, jp, en, special in seed:
        entry = fetch_pokemon_data(zid, form, jp, en, special, move_jp)
        entry["threat_score"] = threat_score(entry)
        rows.append(entry)

    rows.sort(key=lambda x: x["threat_score"], reverse=True)

    result = {
        "move": move_jp,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "source": "champs.pokedb.tokyo (Tier S+)",
        "method": "seed-list + individual page regex extraction",
        "skill_version": "0.5.4 (HG-niche-depth)",
        "candidates": rows,
    }
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["_cache_path"] = str(out_path)
    return result


def render_summary(result: dict) -> str:
    if "error" in result:
        return (
            f"[ERROR] {result['error']}\n"
            f"available niche moves: {', '.join(result.get('available', []))}"
        )
    lines = [
        f"# niche-users: {result['move']}",
        f"  fetched_at: {result['fetched_at']}",
        f"  source:     {result['source']}",
        f"  cache_hit:  {result.get('_from_cache', False)}",
        "",
        f"{'#':<3} {'ポケ':<14} {'掲載':<6} {'採用率':<8} {'特性 boost':<22} {'脅威度':<6}",
        "-" * 70,
    ]
    for i, e in enumerate(result["candidates"], 1):
        md = e.get("move_data") or {}
        listed = "○" if md.get("listed") else "×"
        rate = md.get("rate")
        rate_s = f"{rate:>5.1f}%" if rate is not None else (" ≥5.0%" if md.get("listed") else "  <5%")
        special = e.get("special_note") or "-"
        lines.append(
            f"{i:<3} {e['name_jp']:<14} {listed:<6} {rate_s:<8} {special:<22} {e['threat_score']:<6}"
        )
    lines.append("")
    lines.append("注: 「掲載 ○」 = champs.pokedb 個別ページの trend section に記載 = 採用率 ≥5%。")
    lines.append("    実数% は Claude が WebFetch で当該 URL を再取得して取得すべし。")
    lines.append("    特性 boost で先制/無効化/設置を脅威度補正済 (HG-niche-depth)。")
    lines.append("")
    lines.append("WebFetch URL list (掲載 ○ のみ、実数% 取得用):")
    for e in result["candidates"]:
        if (e.get("move_data") or {}).get("listed"):
            lines.append(f"  - {e['name_jp']:<14} {e['url']}")
    lines.append("")
    lines.append(f"cache: {result.get('_cache_path', '(re-used)')}")
    return "\n".join(lines)


def main():
    args = [a for a in sys.argv[1:] if a not in ("--force", "-f")]
    force = "--force" in sys.argv or "-f" in sys.argv

    if not args:
        print("Usage: fetch_niche_users.py [--force] <niche技日本語名>")
        print("")
        print("登録済 niche 技:")
        for k, v in NICHE_USERS_SEED.items():
            print(f"  {k:<14} ({len(v)} candidates)")
        sys.exit(0)

    move_jp = args[0]
    result = fetch_all(move_jp, force=force)
    print(render_summary(result))


if __name__ == "__main__":
    main()
