# data/ — SSOT 全体マップ

> Pokemon Champions スキルの全データレイヤを記述する SSOT 文書。
> 3 レイヤアーキテクチャ + 補助データの位置付けを 1 枚で把握する。

## 3 レイヤ SSOT 構造

```
┌──────────────────────────────────────────────────────────────┐
│ Layer 1: Showdown Raw (commit 808f8584 pinned)               │
│  - data/{pokedex,moves,abilities,items,learnsets,            │
│            typechart,natures}.json                           │
│  - data/ja_names.json (PokeAPI CSV)                          │
│  - 用途: ダメ計、種族値、技性能                              │
│  - 鮮度: 1ヶ月 (枯れた知識)                                   │
└──────────────────────────────────────────────────────────────┘
                       │
                       ▼ (lib/champions_overlay.py)
┌──────────────────────────────────────────────────────────────┐
│ Layer 2: Champions Overrides (Showdown 値からの差分)         │
│  - data/champions_overrides.json                             │
│  - 例: ムーンフォース 30%→10%, アイヘ 30%→20%, par 25%→12.5%   │
│  - 用途: ユーザー向け表示、構築アドバイス、Tier 別応答       │
│  - 鮮度: Champions パッチに追従 (手動)                        │
└──────────────────────────────────────────────────────────────┘
                       │
                       ▼ (lib/champions_overlay.is_implemented)
┌──────────────────────────────────────────────────────────────┐
│ Layer 3: Implementation Flag (使用可否)                       │
│  - data/champions_implementation.json                         │
│  - 例: rockyhelmet=False, gmax=False, regional=TBD            │
│  - 用途: 構築提案前の HARD-GATE チェック                       │
│  - 鮮度: Champions 公式アナウンスに追従 (手動)                 │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ 補助データ (判断には使わない)                                 │
│  - data/stats/ — Smogon gen9ou 統計 (SV メタの参考のみ)      │
│  - cache/champs_usage/ — Champions 使用率 SSOT (6h TTL)      │
│  - cache/yt_transcripts/ — YouTube 字幕 (24h 鮮度トレンド)    │
└──────────────────────────────────────────────────────────────┘
```

## ファイル一覧

### 必須 (Showdown raw)

| ファイル | サイズ | 件数 | 用途 | 再生成方法 |
|---------|-------|------|------|-----------|
| `pokedex.json`     | 488KB  | 1516 | 種族値・タイプ・特性候補 | `bun scripts/extract_data.ts` |
| `moves.json`       | 260KB  | 954  | 技データ | 同上 |
| `abilities.json`   | 30KB   | 318  | 特性データ | 同上 |
| `items.json`       | 78KB   | 583  | 持ち物 (mega stone 含む) | 同上 |
| `learnsets.json`   | 3.2MB  | 1287 | 技マシン覚え判定 | 同上 |
| `typechart.json`   | 5KB    | -    | 18 タイプ相性表 | 同上 |
| `natures.json`     | 1KB    | 25   | 性格補正表 | 同上 |
| `ja_names.json`    | 312KB  | 1417 | 日本語↔Showdown ID | 同上 |
| `VERSION.json`     | 1.5KB  | -    | SSOT pin情報 (commit/timestamp) | 同上 |

### Champions レイヤ

| ファイル | 件数 | 用途 | 再生成方法 |
|---------|------|------|-----------|
| `champions_overrides.json`      | 8 moves + 6 buffs + 3 conditions | Showdown 値 → Champions 値 | `python3 scripts/build_champions_overrides.py` |
| `champions_implementation.json` | 18 items + 7 moves + 89 pokemon (gmax 34 + 形態 55) + 93 megastones | 実装済み/未実装 | `python3 scripts/build_champions_implementation.py` |

### 補助データ

| ディレクトリ/ファイル | 内容 | 鮮度 | Champions 判断利用 |
|---------------------|------|------|-------------------|
| `data/stats/gen9ou-*.json` | Smogon SV 月次統計 | 月次 | NG (補助参考のみ) |
| `data/stats/README.md`     | 上記の利用方針 | - | - |
| `cache/champs_usage/`      | champs.pokedb / pokechamdb fetch | 6h TTL | OK (SSOT) |
| `cache/yt_transcripts/`    | YouTube auto-caption | 24h | OK (鮮度トレンド) |

## 1516 vs 1287 の解釈

| 統計 | 値 | 解釈 |
|------|-----|------|
| pokedex 件数 | 1516 | base + forme + cosmetic 全部入り |
| learnsets 件数 | 1287 | base + 技習得が独立した forme のみ |
| 差分 | 229 | cosmetic forme (見た目だけ違うが技は base 共通) |

→ **これは Showdown のデータ設計通り、修正不要**。lookup.py は pokedex を SSOT として、必要時に learnsets[base_id] で技候補を引く。

## lookup vs lookup_raw 使い分けガイド

`lib/lookup.py` には 2 系統の getter がある:

| 関数 | 戻り値 | 利用先 |
|------|-------|-------|
| `get_move(mid)`     | Showdown raw 値 (overlay 適用しない) | ダメ計エンジンへの入力 (精度最優先) |
| `get_item(iid)`     | 同上 | 同上 |
| `get_ability(aid)`  | 同上 | 同上 |
| `get_move_raw(mid)` | 同上 (alias、意図明示用) | 明示的に raw が必要な場面 |
| `get_item_raw(iid)` | 同上 | 同上 |
| `get_ability_raw(aid)` | 同上 | 同上 |

`lib/champions_overlay.py` には overlay 適用済 getter がある:

| 関数 | 戻り値 | 利用先 |
|------|-------|-------|
| `get_move_overlayed(mid)`    | Champions 値 (ナーフ/バフ反映) | ユーザー向け表示、構築提案 |
| `get_item_overlayed(iid)`    | 同上 | 同上 |
| `get_ability_overlayed(aid)` | 同上 | 同上 |
| `is_implemented(category, sid)` | bool | 構築提案前の HARD-GATE チェック |
| `get_implementation_note(category, sid)` | str/None | 未実装理由の取得 |

### 使い分けの原則

- **ダメ計に流す値は必ず `get_*_raw`**: overlay 値が damage formula に混入すると精度が壊れる
- **ユーザーに「ムンフォは 30% C-1」と表示するときは `get_move_overlayed`**: Champions 仕様で 10% と返す
- **構築提案前は必ず `is_implemented` で確認**: 未実装持ち物を提案するのは HG-1 違反

## champions_implementation.json schema (v1.1.0)

各 entry は以下のフィールドを持つ:

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `implemented` | bool / "TBD" | ✅ | true=使用可 / false=使用不可 / "TBD"=確認待ち |
| `kind` | string | ✅ (v1.1.0+) | "item" / "move" / "gmax" / "regional" / "megastone" |
| `region` | string / null | ✅ (v1.1.0+) | "alola" / "galar" / "hisui" / "paldea" / null |
| `jp_name` | string | optional | 日本語名 |
| `reason` | string | optional | implemented=false/TBD の理由 |
| `_note` | string | optional | 補足メモ |

### kind/region による集計クエリ例

```bash
# Gmax 全件 (Champions 未実装)
jq -r '.pokemon | to_entries[] | select(.value.kind == "gmax") | .key' data/champions_implementation.json

# ヒスイ形態だけリストアップ
jq -r '.pokemon | to_entries[] | select(.value.region == "hisui") | .key' data/champions_implementation.json

# 実装確認済みメガストーン
jq -r '.megastones | to_entries[] | select(.value.implemented == true) | .key' data/champions_implementation.json

# region 別集計
jq '.pokemon | to_entries[] | select(.value.kind == "regional") | .value.region' data/champions_implementation.json | sort | uniq -c
```

### schema 変更履歴

- **1.0.0** (初期): `implemented` + `reason` + `jp_name` フラット構造
- **1.1.0** (強化): `kind` + `region` 追加。**API 不変、追加フィールドのみ後方互換**。

## 関連ドキュメント

- `references/champions_overrides_sources.md` — overrides の出典スナップショット (game8/altema/gamepedia/note)
- `references/implementation_status.md` — 実装状況の文章版 (このディレクトリ単体で読みたい人向け)
- `lib/champions_overlay.py` — overlay 実装の詳細
- `SKILL.md` Sec 13 — HARD-GATE 運用ルール
- `SKILL.md` Sec 14.6 — 用語 SSOT (overrides/implementation/補助データ/Champions 適合)
