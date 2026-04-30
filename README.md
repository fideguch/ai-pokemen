# pokemon-champions (ai-pokemen)

Pokemon Champions シングル6vs3対戦の **廃人トレーナーモード** Claude Code スキル。
`/pokechamp` で発動するとセッション持続でガチ廃人ペルソナが起動し、ダメ計即時 / 構築アドバイス / 最新メタを 3-tier latency で提供する。
**Champions 公式ナーフ (ムンフォ 30→10%, par 25→12.5% 等) を内部 overlay 適用**、ダメ計には Showdown 素値、ユーザー表示には Champions 仕様で完全分離。
パラドックス・禁忌の四災・禁伝など **Reg M-A 規格外候補は TBD ガード** で誤評価防止 (v0.3.2)。
**日次メタ対策メモ運用基盤** で環境 TOP20 + 自構築対策マトリクスを管理、構築マスターと並べて勝率改善サイクルを回せる (v0.4.x)。

---

## ⚠ 著作権・免責事項 (重要)

本スキルは **非公式のファン制作物** であり、任天堂株式会社・株式会社ポケモン・株式会社ゲームフリーク・The Pokémon Company International およびその関連会社・関連事業者とは **一切関係ありません**。

- ポケットモンスター / Pokémon / Pokémon Champions / 各ポケモン名 / キャラクター / グラフィック / ロゴ / 図像等に関する **すべての知的財産権 (商標権・著作権・意匠権を含む) は、任天堂株式会社・株式会社ポケモン・株式会社ゲームフリーク** に帰属します
- 本スキルの目的は **個人のローカル環境における対戦補助・学習** に限定されます
- **商用利用・再配布・公開サービスへの組込み・収益化は一切行わないこと**
- 公式・準公式コンテンツ (公式ガイドブック / 公式大会データ / 公式生放送等) からの **無断転載・複製は行わないこと**
- ポケモン名・技名・特性名等は対戦識別目的でのみ使用しており、**商用利用の意図は無い**
- データソース (後述) は MIT/BSD 等の OSS ライセンス準拠データのみを使用しており、公式アセット (画像・サウンド等) は **一切含まない**
- 本スキルは **対戦補助の自動化ツール** であって、ゲーム改造・チート・通信妨害等の不正行為を一切目的とせず、サポートもしない
- 本スキルの利用によって生じたいかなる損害 (アカウント制裁を含む) について、作者は責任を負わない

公式または権利者から削除・改変要請があった場合、**速やかに該当部分を削除・修正する**。連絡先: GitHub Issues。

> Pokémon ©2026 Pokémon. ©1995-2026 Nintendo/Creatures Inc./GAME FREAK inc.
> Pokémon、ポケットモンスター、Pokémon Champions は任天堂・クリーチャーズ・ゲームフリークの登録商標です。

---

## クイックスタート

新しい Mac でゼロから動かす最短手順:

```bash
# 1. リポジトリ取得
git clone git@github.com:fideguch/ai-pokemen.git ~/ai-pokemen

# 2. Claude Code スキルとしてシンボリックリンク
mkdir -p ~/.claude/skills
ln -sfn ~/ai-pokemen ~/.claude/skills/pokemon-champions

# 3. セットアップ (依存チェック → bun install → calc binary → Champions overrides/implementation)
bash ~/ai-pokemen/scripts/setup.sh

# 4. 動作確認
python3 ~/ai-pokemen/scripts/lookup_move.py ポルターガイスト
# 期待: 威力 110 / 命中 100% / Physical / Ghost (Showdown 値)

python3 ~/ai-pokemen/scripts/lookup_move.py ムーンフォース
# 期待: 追加効果 spa-1 10% [Champions 仕様適用] — Showdown 標準は 30%

# 5. テストスイート
python3 ~/ai-pokemen/tests/test_lib.py                      # 31 unit tests
python3 ~/ai-pokemen/tests/test_champions_overlay.py        # 19 overlay/schema tests
cd ~/ai-pokemen/scripts && bun run_fixtures.ts              # 10 calc fixtures
```

依存:
- 必須: `bun` / `python3` / `git` (`brew install bun` で全部入る、Python は pyenv/system 何でも可)
- オプション: `yt-dlp` (YouTube 字幕自動収集機能を使う場合のみ、`brew install yt-dlp`)

## 個人機能 (オプショナル)

以下は **作者個人の dotfiles 連携** であり、無くてもスキルは完全動作する (fail-soft):

| 機能 | 依存 | 不在時の挙動 |
|------|------|------------|
| 応答末尾 `poke -n <name>` でターミナル背景 | `~/.my_commands/poke` (作者の dotfiles) | スキップ (応答は維持) |
| bochi メモ自動同期 | `~/.claude/bochi-data/memos/pokechamp-*` | スキップ (個人ノート機能なので不要) |
| YouTube 字幕自動収集 | `yt-dlp` CLI | スキップ + WARN (他機能は完全動作) |

`scripts/` / `lib/` のコードは上記の有無に依存しないよう設計済み (絶対パス 0、ハードコード 0)。

---

## できること

| 用途 | Tier | 想定レイテンシ | 出力 |
|---|---|---|---|
| ダメ計 (対面確認) | T1 | <300ms | 確定数 + 16通り乱数 + ASCIIバー |
| 構築アドバイス / サイクル設計 | T2 | 1-5秒 | 役割対象マトリクス + 並び案複数 |
| 最新メタ / 環境調査 | T3 | 5-30秒 | usage統計 + 鮮度マーク + 出典URL |
| Champions 適合性判定 | 任意 | <10ms | `is_implemented(category, id)` で持ち物/技/ポケ/メガストーンの可否 (3 値: True/False/"TBD") |
| **メタ対策メモ参照** (v0.4.x) | 任意 | <100ms | `meta/META-LATEST.md` で環境 TOP20 + 対策マトリクス 90 セル + アーキ別選出 |
| **構築 × メタ クロス分析** (v0.4.1) | 任意 | <100ms | `builds/A.3-Final-v7.8.md §13` で構築の環境位置付け + 直近変動の影響 |

ペルソナは **ガチ廃人標準語・データ主導・図表ファースト・勝率最優先**。会話の中心ポケモン1体を選定し、応答末尾で `poke -n <英名>` を1回だけ呼んでターミナル背景を切替える (既存pokeコマンドへの依存)。

## 対応スコープ

- **対戦フォーマット**: シングル6vs3 のみ (ダブル/VGC/トリプル/ローテは non-goals)
- **メカニクス**: Gen 1-9 全世代 (テラスタル / ダイマックス / Z技 / メガ進化 全対応、@smogon/calc 委譲)
- **キョダイマックス**: Champions 未実装として処理 (gmax 全 34 体 = `implemented: false`)
- **ポケモン**: 1516体 (リージョン形態 55 含む / パラドックス含む)
- **技**: 954技 (Champions ナーフ反映 8 件 + バフ 6 件) / **特性**: 318 / **道具**: 583
- **メガストーン**: 93 件 (確認済 44 / TBD 49)
- **TBD ガード対象** (構築提案前に ⚠ 警告): パラドックス 18 + 禁忌の四災 4 + 禁伝 12 + 準伝/幻 5 = **39 体** (Champions Reg M-A 規格外/未アナウンス、公式確認要)
- **状態異常 Champions 仕様**: par 12.5% / frz 3T 解除 / slp 3T 起き保証 / やどりぎ 1/16
- **日次メタ対策メモ** (v0.4.x): 環境 TOP20 + 対策マトリクス 90 セル + アーキ別選出 + メガ進化選択ガイド、HARD-GATE HG-1〜HG-5 検証付き
- **日本語名**: 1221体 + 196形態 (PokeAPI 公式翻訳 + Showdown翻訳)

## 使い方

```
あなた:    /pokechamp
廃人:      ガチ環境モード起動した。
           データ: pokedex 1516 / moves 954 / abilities 318。Showdown commit pinned。
           ダメ計: bin/pokechamp-calc (T1 wall-clock 中央値 ~80ms / 予算 300ms)。
           Champions overrides: 8 moves + 3 conditions, implementation: 18 items + 89 pokemon。
           何聞きたい？対面?選出?ダメ計?今期トップ?

あなた:    鉢巻ガブのEQでミミ確定？
廃人:      ## ダメ計: ガブリアス → ミミッキュ
           | 指標 | 値 |
           |---|---|
           | ダメ% | 117.1 - 138.1% (295-348) |
           | 残 HP | 0-0 / 252 (0.0-0.0%) |
           | 確定 | 💀 guaranteed OHKO |
           ```
           ミミッキュ HP 252
             HP前  🟢 [████████████████████] 100.0% (252/252)
                   ↓ 117.1-138.1% dmg (295-348)
             HP後  🔴 [░░░░░░░░░░░░░░░░░░░░] 0.0%
                   guaranteed OHKO
           ```
           → 1Hで沈むからミミ初手は危ない。テラ電気で透かしてくる前提で動け。

あなた:    ガブにゴツメ持たせて
廃人:      ❌ ゴツゴツメット は Champions 未実装 (`is_implemented` False)。
           代替: オボンのみ / きあいのタスキ (実装済リストから)。

あなた:    ガブのムンフォは何%でC下げる？
廃人:      Champions 仕様: 10% (Showdown 標準は 30%)。
           overlay 経由で表示、ダメ計には素値が流れるので確定数は不変。

あなた:    今期OUのTOP10は？
廃人:      [T3: cache/champs_usage/2026-04-30.json + 鮮度マーク "📅 6h 以内 / champs.pokedb.tokyo"]

あなた:    /pokechamp off
廃人:      モード解除。
```

## アーキテクチャ

### 3 層 SSOT 構造 (Champions 対応の核)

```
┌──────────────────────────────────────────────────────┐
│ Layer 3: Champions 仕様レイヤー (overlay 適用後の値)     │
│  → ユーザー表示、構築提案、HARD-GATE 判定               │
│  → lib/champions_overlay.py 経由                      │
├──────────────────────────────────────────────────────┤
│ Layer 2: Champions 差分レイヤー                         │
│  - data/champions_overrides.json (ナーフ/バフ差分のみ)  │
│    例: ムンフォ chance 30→10, par 0.25→0.125           │
│  - data/champions_implementation.json (使用可否フラグ)  │
│    例: ベンサウルキョダイ → false / ゴツメ → false      │
├──────────────────────────────────────────────────────┤
│ Layer 1: Showdown 生データレイヤー (commit 808f8584)    │
│  - data/{pokedex,moves,abilities,items,...}.json       │
│  → ダメ計 (bin/pokechamp-calc) はこの素値を使う        │
└──────────────────────────────────────────────────────┘
```

**設計原則**: Layer 1 はダメ計に流す (overlay 混入 禁止)、Layer 3 はユーザーに見せる。`get_move()` は Layer 1 (raw)、`get_move_overlayed()` は Layer 3 (Champions 適用済) — `lib/lookup.py` のシグネチャは不変、計算精度を構造的に保証。

### ファイル構成

```
~/ai-pokemen/                              ← 独立 repo (= ~/.claude/skills/pokemon-champions symlink先)
├── SKILL.md                               # ペルソナ起動指示 + T1/T2/T3 ルーター + 3 HARD-GATE
├── README.md                              # このファイル
├── bin/pokechamp-calc                     # Bun 単一バイナリ (@smogon/calc 0.11.0 ラップ、59MB、gitignore)
├── data/
│   ├── pokedex.json (488KB)               # 1516体 (Showdown 由来、gitignore)
│   ├── moves.json (260KB)                 # 954技 (gitignore)
│   ├── abilities.json / items.json / learnsets.json / typechart.json / natures.json / ja_names.json
│   ├── champions_overrides.json           # ★ Champions ナーフ差分 (8 moves + 6 buffs + 3 conditions)
│   ├── champions_implementation.json      # ★ Champions 使用可否 (89 pokemon + 93 megastones + 18 items + 7 moves)
│   ├── VERSION.json                       # SSOT pin情報 (Showdown commit + Champions versions)
│   ├── README.md                          # ★ 3 層 SSOT 解説 + lookup vs lookup_raw 使い分けガイド
│   └── stats/                             # Smogon usage stats (補助参考、Champions 用ではない)
├── lib/
│   ├── lookup.py                          # 日英/部分一致 → 内部ID解決 (raw 系統)
│   ├── champions_overlay.py               # ★ overlay 適用 + is_implemented + 補助関数
│   ├── intent_router.py                   # T1/T2/T3キーワード分類
│   ├── visualizer.py                      # ダメ計table / 役割マトリクス / 横棒グラフ
│   ├── persona.py                         # 廃人用語40語 GLOSSARY
│   ├── session_state.py                   # 会話継続state
│   └── meta_fetcher.py                    # WebFetch + 6h cache + stale fallback
├── scripts/
│   ├── setup.sh                           # 初回セットアップ (idempotent, 6 step + smoke test)
│   ├── extract_data.ts                    # Showdown TS → JSON 抽出
│   ├── calc_wrapper.ts / build_calc.sh    # bun build --compile → bin/
│   ├── build_champions_overrides.py       # ★ overrides JSON 再生成
│   ├── build_champions_implementation.py  # ★ implementation JSON 再生成 (kind/region 自動付与)
│   ├── fetch_champs_usage.py              # ★ champs.pokedb.tokyo / pokechamdb.com から 6h TTL fetch
│   ├── fetch_yt_transcripts.py            # ★ YouTube RSS + yt-dlp で字幕収集
│   ├── lookup_move.py                     # CLI: 技データ overlay 適用済表示
│   ├── run_fixtures.ts                    # 10 fixture 精度検証 + T1 latency計測
│   └── parse_usage.py / update_meta.sh
├── builds/                                # 構築 SSOT (multi-build 管理)
│   ├── INDEX.md                           # 全構築 Status 表 (active/experimental/testing/archived)
│   ├── A.3-Final-v7.8.md                  # 現 active 構築 (メガ2体軸、§13 メタ統合分析含む)
│   ├── _template.md                       # 新構築用テンプレ (13 節)
│   └── archive/                           # 引退構築
├── meta/                                  # ★ 日次メタ対策メモ運用基盤 (v0.4.0+)
│   ├── META-LATEST.md                     # 環境 TOP20 + 対策マトリクス 90 セル + アーキ TOP5
│   ├── CHANGELOG.md                       # 日次差分ログ (append-only)
│   ├── README.md                          # 運用 SOP (HARD-GATE HG-1〜HG-5)
│   └── archive/YYYY-MM-DD.md              # 大変動時スナップショット
├── battle_logs/                           # 対戦ログ (年/月別)
├── cache/
│   ├── champs_usage/                      # 日次使用率 (gitignore)
│   └── yt_transcripts/                    # 動画字幕 (gitignore)
├── tests/                                 # 31 unit + 19 overlay/schema + 10 calc fixtures
└── references/                            # 廃人 spec 集
    ├── pokemon_champions_rules.md         # PCルール
    ├── damage_formula.md                  # @smogon/calc準拠 SSOT宣言
    ├── champions_overrides_sources.md     # ★ overrides 出典 (game8/altema/gamepedia/note)
    ├── implementation_status.md           # 実装状況の文章版
    ├── environment_archetypes.md          # 環境タイプ AT-01〜08
    ├── build_proposal_protocol.md         # 構築提案手順書
    ├── modern_team_building.md            # 現代構築論
    ├── role_theory.md / meta_glossary.md / persona_guide.md
    ├── authoritative_sources.md / realtime_access_methods.md / data_extraction_guide.md
    └── remote_trigger_yt_spec.md          # ★ YT 自動収集 RemoteAgent 仕様書
```

## データ戦略

### 3-tier latency

| Tier | データ | レイテンシ | ソース |
|---|---|---|---|
| **T1 即時** | ダメ計・種族値・タイプ・技性能・特性・道具 | <300ms (中央値 80ms) | ローカル (Showdown 同梱 + Champions overlay) |
| **T2 研究** | 構築・サイクル・選出 | 1-5秒 | T1 + ローカル思考 |
| **T3 最新** | 上位構築・使用率・型・立ち回り対策・メタ | 5-30秒 | `cache/champs_usage/` (6h TTL) + `cache/yt_transcripts/` (24h) |

### 鮮度二層

| 層 | 内容 | TTL | 鮮度マーク |
|---|---|---|---|
| **スピード層** | ダメ計式・種族値・タイプ・技・特性・道具 | 1ヶ月 | 不要 (枯れた知識) |
| **鮮度命層** | Champions 上位構築・使用率・型 | **6時間** | **必須** (タイムスタンプ + 出典URL) |

### Champions vs Smogon の使い分け

| 用途 | データソース |
|---|---|
| Champions 環境の使用率 / 構築トレンド | `cache/champs_usage/` (champs.pokedb.tokyo / pokechamdb.com) |
| Smogon competitive 統計 (補助参考のみ) | `data/stats/gen9ou-*.json` |
| Champions 仕様のナーフ確率・状態異常 | `data/champions_overrides.json` 経由 |
| 各ポケ/持ち物/メガストーンの Champions 使用可否 | `data/champions_implementation.json` 経由 (`is_implemented()`) |

## 品質保証

### forge_ace v4.0 (5-Agent Quality Gate) 通過

| Agent | Verdict | スコア |
|---|---|---|
| **Writer** | WRITER_DONE_OK | Phase 0-8 完遂 |
| **Guardian** (Opus, 8-axis) | GUARDIAN_PASS_WITH_NOTES | **73/80** (ship-ready ≥70) |
| **Overseer** (architect/Opus) | OVERSEER_PASS | 7/7 要件 COVERED, 計算機隔離 watertight |
| **PM-Admin** (Opus, E2E mandate) | PM_ADMIN_PASS_WITH_NOTES | **36/40** (ship ≥35), E2E **5/5 PASS** |

### テスト

```bash
python3 ~/ai-pokemen/tests/test_lib.py                    # 31/31 PASS (lookup, intent_router, visualizer, persona, session_state)
python3 ~/ai-pokemen/tests/test_champions_overlay.py      # 26/26 PASS (overlay + schema + TBD ガード + design invariant)
cd ~/ai-pokemen/scripts && bun run_fixtures.ts            # 10/10 PASS, T1 median ~80ms
bash ~/ai-pokemen/scripts/setup.sh                        # idempotent, end-to-end smoke test (OHKO assertion)
```

### セキュリティ / Portability チェック

- 絶対パスハードコード: **0 件** (`grep -r "/Users/" --include="*.py"`)
- シークレット (API_KEY/TOKEN): **0 件**
- bochi/poke 個人依存: lib/scripts に **0 件** (fail-soft 設計)

## 既知の制約

| 項目 | 状態 | 影響度 |
|---|---|---|
| Pokemon Champions 公式 URL/レギュレーション | 未確定 (公式アナウンス待ち、`_PENDING` マーカー) | 低 (graceful fallback) |
| Form 名英名フォールバック | 295件 (リージョン形態の一部) JP未マッチ | 低 (英名+注釈表示で動作) |
| Champions overrides の出典 | 4 個別ソース (game8/altema/gamepedia/note) を手動照合 | 中 (公式ソース確定後に再照合推奨) |
| メガストーン 49 件 TBD | 公式アナウンス未確認 | 中 (`is_implemented` で TBD 返却、fail-safe) |
| YouTube 字幕収集 | yt-dlp 別途 install 必要 | 低 (fail-soft、他機能は完全動作) |
| 公式ルール変更時のデータ更新 | 手動 (`extract_data.ts` + Champions overrides 再キュレーション) | 中 (Champions パッチ通知に追従が必要) |

## 設計方針

### 持続型ペルソナ (Persistence)

`/pokechamp` 発動 → セッション終了 or `/pokechamp off` までガチ廃人モード継続。会話文脈を保持し、「さっきの計算」「もっと受け足したい」等の参照解決に対応。

### Champions overlay の安全側設計 (Calc Isolation)

- `lib/lookup.py` の `get_move/get_item/get_ability` は **Showdown 素値を返す** (overlay 適用しない)
- `lib/champions_overlay.py` の `get_move_overlayed` は Champions 仕様 (ムンフォ 10% 等) を返す
- ダメ計 (`bin/pokechamp-calc`) は build 時に `@smogon/calc` をバンドル、Python 系統に依存しない → **構造的に overlay 混入不可能**
- `tests/test_champions_overlay.py::TestLookupDesignInvariant` がこの不変条件を強制 (将来回帰防止)

### TBD ガード (v0.3.2 — Default-Permissive Trap 修正)

過去の事故 (パオジアンを「Tier S 環境最強格」と誤評価) を構造的に防ぐ仕組み:

- `is_implemented(category, sid)` は **3 値返却**: `True` (確定実装) / `False` (確定未実装) / `"TBD"` (公式未確認)
- `bool("TBD") == True` の罠を閉じるため、**素朴な `if is_implemented(...):` ではなく `is True` で厳密判定** を SKILL.md Sec 13 で mandate
- `requires_tbd_warning()` 補助関数で「⚠ TBD 警告必須」を 1 行判定可能
- パラドックス/禁忌四災/禁伝/準伝の **39 体** を `champions_implementation.json` に明示登録 (kind: `paradox` / `treasures_of_ruin` / `legendary` / `mythical`)
- forge_ace v4.0 に **anti-pattern #13 Default-Permissive Trap** を追加、今後の Type B 変更でも自動検出される (上流リポジトリ `my_dotfiles/claude/skills/forge_ace/` 側で管理)

### 既存 `poke` との完全独立 (Decoupling)

- 既存 `~/my_dotfiles/.my_commands/poke*` は **改変なし**
- スキルは独立したデータ・ロジックを持つ
- 連携は出力末尾で `poke -n <英名>` を1回呼び出すのみ (オプショナル、不在時 skip)

### 現代構築論ベース (Modern Team Building)

- 古典的分類 (対面/サイクル/受けループ/バランス) は実戦では融合
- 採用理由言語化が最優先 (「強いから」じゃなく「何の役割か」)
- 環境最適に型を可変、採用理由は不変
- 使用率上位ポケに2体以上の対応駒を確保

詳細: `references/modern_team_building.md`

### multi-build 管理 (Build SSOT)

- `builds/INDEX.md` で全構築の Status (active/experimental/testing/archived) を一元管理
- 構築追加は `_template.md` から複製して 13 節埋める
- bochi 同期メモ (`~/.claude/bochi-data/memos/pokechamp-*`) は本家 `builds/` の参照コピー (read-only)

### 日次メタ運用 (v0.4.x)

`meta/META-LATEST.md` で環境スナップショットを管理、`builds/A.3-Final-v7.8.md §13` でクロス分析:

```
朝 7:00 JST 自動 (schedule agent):
  cache/champs_usage/ + cache/yt_transcripts/ 更新

ユーザー /pokechamp 起動時:
  1. META-LATEST §0 鮮度マトリクス確認 → stale なら更新提案
  2. 該当セクションだけ書き換え + CHANGELOG に追記
  3. 大変動時 archive/YYYY-MM-DD.md にスナップショット
  4. bochi 同期 + 手動 S3 push (bash redirect は hook 発火しないため)
```

**HARD-GATE 5 軸** (HG-1 Champions 適合性 / HG-2 出典明記 / HG-3 鮮度マーク / HG-4 構築リンク整合 / HG-5 推測排除) で品質保証。
詳細: `meta/README.md`

## ライセンス・出典

- **@smogon/calc** (MIT, https://github.com/smogon/damage-calc) — ダメ計エンジン
- **smogon/pokemon-showdown** (MIT, https://github.com/smogon/pokemon-showdown) — データソース (commit `808f8584` pinned)
- **PokeAPI CSV data** (BSD 3-Clause) — 日本語名 (1221体 + 196形態)
- **champs.pokedb.tokyo / pokechamdb.com** — Champions 使用率参考 (公開 web データ、cache のみ保存)
- **game8.jp / altema.jp / app.gamepedia.jp / note.com** — Champions ナーフ情報出典 (`references/champions_overrides_sources.md` に記録)

## バージョン履歴

| Version | Date | 内容 |
|---|---|---|
| **v0.4.1** | 2026-04-30 | **構築 × メタ クロス統合**: A.3-Final-v7.8 §13 メタ統合分析追加 (構築本体不変、9 サブ節)、META-LATEST.md と双方向リンク、メガゲン弱体化分析 + メガカイ環境最適性スコアリング、苦手アーキ #5 物理対面型対応運用ルール |
| v0.4.0 | 2026-04-30 | **日次メタ対策メモ運用基盤**: `meta/` ディレクトリ新設、META-LATEST.md (8 章 + 90 セル対策マトリクス + アーキ TOP5)、CHANGELOG.md (バージョニング規則)、META README.md (運用 SOP + HG-1〜HG-5)、archive/ スナップショット、bochi 同期 |
| v0.3.2 | 2026-04-30 | **Default-Permissive Trap 修正**: パオジアン誤評価事故の根本対策。`is_implemented` を 3 値返却 (True/False/"TBD") に修正、パラドックス 18 + 禁忌四災 4 + 禁伝 12 + 準伝 5 = 39 体を TBD 登録、schema 1.2.0、`requires_tbd_warning()` 追加、SKILL.md Sec 13 に「LLM 自己チェック手順」追加。forge_ace 上流に anti-pattern #13 同期 |
| v0.3.1 | 2026-04-30 | implementation.json schema 1.1.0 (kind/region 追加 — region 単位クエリ可)、setup.sh yt-dlp WARN 追加、README フル書換 |
| v0.3.0 | 2026-04-30 | Champions overrides architecture (3 層 SSOT、overlay/raw 分離)、portability (clone-and-run、abs-path 0)、forge_ace 5-Agent Gate 通過 |
| v0.2.0 | 2026-04-30 | 14 source tier system + DB-first build proposals |
| v0.1.0 | 2026-04-29 | 初回リリース、forge_ace + gatekeeper SHIP_WITH_CONDITIONS |
