# meta/ ディレクトリ — 運用 SOP

> Pokemon Champions メタ対策メモの管理規則。
> 日々のメタ変動に追従するための SSOT 構造と更新フロー。

---

## ファイル構成

```
meta/
├── README.md             ← このファイル (運用ルール)
├── META-LATEST.md        ← 常に最新の対策メモ (上書き運用)
├── CHANGELOG.md          ← 日次差分ログ (append-only)
└── archive/
    └── YYYY-MM-DD.md     ← 大変動時 or 週次スナップショット
```

---

## SSOT と同期マッピング

| ファイル | 役割 | 編集権限 |
|---|---|---|
| `meta/META-LATEST.md` | **SSOT、常に最新版** | 廃人モード時に編集可 |
| `meta/CHANGELOG.md` | 差分ログ append-only | 編集時に上から追記 |
| `meta/archive/*.md` | 過去スナップショット | 作成のみ、変更しない |
| `~/.claude/bochi-data/memos/pokechamp-meta-counter.md` | bochi 同期コピー | **read-only**、SSOT から自動上書き |

---

## 日次更新フロー (SOP)

### 朝 7:00 JST 自動 (既存 schedule agent が実行)

```
1. fetch_champs_usage.py → cache/champs_usage/YYYY-MM-DD.json
2. fetch_yt_transcripts.py → cache/yt_transcripts/YYYY-MM-DD/
3. (将来) nitter RSS → cache/x_posts/YYYY-MM-DD.json
```

### ユーザー /pokechamp 起動時 (手動)

```
1. META-LATEST.md の §0 鮮度マトリクスを確認
2. stale (>6h) のセクションがあれば「更新する?」と提案
3. ユーザー承認 → 該当セクションだけ書き換え
4. CHANGELOG.md の冒頭に新エントリ append (v0.0.X 単位)
5. 大変動 (TOP10 入替 3+ / 新アーキ出現) なら:
   a. archive/YYYY-MM-DD.md に META-LATEST.md をコピー
   b. CHANGELOG にも snapshot リンク追記
6. bochi 同期 (cat redirect でヘッダー付き上書き)
7. 手動 S3 push (PostToolUse hook 発火しないので必須)
   echo '{"file_path":"~/.claude/bochi-data/memos/pokechamp-meta-counter.md"}' | bash ~/.claude/scripts/hooks/bochi-s3-push.sh
8. (オプション) git add + commit + push (大変動時のみ)
```

---

## 品質基準 (HARD-GATE)

更新時は **必ず以下 5 項目** を grep / Bash で実機検証:

| # | 項目 | 検証コマンド |
|---|---|---|
| HG-1 | Champions 適合性 | `python3 -c "from lib.champions_overlay import is_implemented; ..."` で全環境ポケ TBD/False チェック |
| HG-2 | 出典明記 | `grep -c "https://" META-LATEST.md` ≥ §1〜§5 セクション数 |
| HG-3 | 鮮度マーク | §0 マトリクス必須、各セクションに last_updated 記載 |
| HG-4 | 構築リンク整合 | `grep -E "ガブ\|カバ\|ギルガ\|ブラ\|メガカイ\|メガゲン" META-LATEST.md` が builds/A.3-Final-v7.8.md と一致 |
| HG-5 | 推測排除 | `grep -E "概ね\|だいたい\|強そう\|多分\|たぶん"` 検出 0 件 |

### ファイル末尾の §9 検証ログ

更新時に `§9 検証ログ` を毎回更新。失敗項目があれば PASS にせず、修正してから保存。

---

## データソース信頼度 (Tier 制)

| ソース | Tier | 用途 | TTL |
|---|---|---|---|
| champs.pokedb.tokyo | **S+** | §1 使用率 (公式 DB) | 6h |
| pokechamdb.com/en | S | §1 使用率 (英、補完) | 24h |
| Kuroko YT 字幕 (yt-dlp 必要) | S | §2 構築アーキタイプ | 24h |
| KYOUPOKE X (nitter) | S | §5 即時メタ変動 | 6h |
| game8.jp / altema.jp | A | §2 補助 + §1 確認 | 24h |
| yakkun.com/ch/ | A | §2 補助 | 48h (403 多発で実質非可用) |
| note.com (個人記事) | B | §2 構築解説 | 7d |
| ✗ Smogon stats | - | **使わない** (Champions 環境ではない) | - |

---

## 大変動の定義 (archive 作成基準)

以下のいずれか発生時に **archive/YYYY-MM-DD.md にスナップショット作成必須**:

- TOP 10 のうち **3 件以上が入替** (順位変動でなく入退場)
- **新アーキタイプ** が観測された (KYOUPOKE / Kuroko で「新型」言及)
- **公式パッチ** (ナーフ/バフ/新ポケ実装/レギュ変更)
- **チャンピオン級** 等の新ランク開放
- 自構築の **active 構築 (A.3-Final-v7.8)** が後手に回る重大変動

---

## bochi 同期手順 (詳細)

```bash
SYNC_DATE="2026-04-DD (差分内容)"
{
  printf '> ⚠ **同期コピー、直接編集禁止**\n'
  printf '> SSOT: `~/.claude/skills/pokemon-champions/meta/META-LATEST.md`\n'
  printf '> メタ更新時はスキル側で更新後、このファイルが上書きされます。\n'
  printf '> Last Synced: %s\n\n---\n\n' "$SYNC_DATE"
  cat ~/ai-pokemen/meta/META-LATEST.md
} > ~/.claude/bochi-data/memos/pokechamp-meta-counter.md

# bash redirect は PostToolUse hook 発火しないので手動 push 必須
echo '{"file_path":"/Users/fumito_ideguchi/.claude/bochi-data/memos/pokechamp-meta-counter.md"}' \
  | bash ~/.claude/scripts/hooks/bochi-s3-push.sh
```

---

## バージョニング (CHANGELOG.md と同期)

- **Major (vX.0.0)**: アーキタイプ追加 / マトリクス構造変更 / 自構築 active 変更
- **Minor (v0.X.0)**: TOP 入替 3+ / アーキ #1 中心ポケ変更 / archive 新規作成
- **Patch (v0.0.X)**: TOP 入替 1-2 / 新動画/X 反映 / 軽微修正

---

## 関連ドキュメント

- 自構築マスター: `../builds/A.3-Final-v7.8.md`
- 構築 INDEX: `../builds/INDEX.md`
- 環境アーキタイプ: `../references/environment_archetypes.md`
- Champions 適合性 SSOT: `../data/champions_implementation.json`
- 権威ソース: `../references/authoritative_sources.md`
