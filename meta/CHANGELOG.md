# Meta 対策メモ 更新履歴 (CHANGELOG)

> META-LATEST.md の差分ログ (append-only)。
> 大きな変動 (TOP10 入替 3 件以上 / 新アーキ出現) があった日は archive/YYYY-MM-DD.md にスナップショット。

---

## v2.0.0 — 2026-06-05 21:19 JST (M-2 全面更新 + 構築刷新)

### シーズン切替

- Champions シーズン **M-1 → M-2** (Reg M-A、2026-05-13〜06-17)
- M-1 メモは `archive/2026-04-30.md`、M-2 スナップショットは `archive/2026-06-05.md`

### データ取得 (信頼ソースのみ)

| ソース | 結果 |
|---|---|
| champs.pokedb.tokyo (Battle Database) | TOP30 取得成功 (本日 16:12 JST) |
| pokechamdb.com (Battle Support) | WebFetch で TOP30 取得成功、champs.pokedb と完全一致 (本日 05:00 PT) |
| YouTube 字幕 (ポケソル/KYOUPOKE/くろこ) | cache 最新 2026-05-27、日次 fetch 新規0件 |
| game8 / gamewith | **数値・事実確認のみ** に限定 (ユーザー方針) |

### 主要発見 (使用率変動)

- ブリジュ 5→2 / マスカ 11→3 / イダイトウ 12→7 / ルカリオ 20→9 が大幅上昇
- 新規ランクイン: ギャラドス#13 / フラエッテ:永遠#17 / ウルガモス#18 / スターミー#19
- 後退: ドドゲ 13→24 / サザン 17→21 / ウォロト 18→22 / ブラ 19→32
- M-2 は「高速メガ多様化 + フェアリー特殊台頭」が構造的特徴

### 構築刷新

- 自構築を A.3-Final-v7.8 (M-1) → **S2.1-MegaGren-v1.0** (M-2, メガゲッコ+メガゲン2枚) に切替
- Lv50 ダメ計 30本超で対策マトリクス再算出
- FB: スカガブのステロ死に技 / 鋼受け2枚の炎・晴れ弱点 / メガ被り選出規律 を指摘

### スキル本体修正 (forge_ace + gatekeeper 規律、push 済)

- `scripts/build_champions_implementation.py`: `greninjite` を KNOWN_IMPLEMENTED に追加 (M-2実装確認、TBD→True)
- `references/authoritative_sources.md`: game8/gamewith をメタ不使用 (事実のみ) と明文化、2DB+YT日次を主軸化
- `references/pokemon_champions_rules.md`: 道具被り禁止 (6種別個必須) を 公式確定 に格上げ、M-2/Lv50 を反映
- `SKILL.md`: HARD-GATE self-check に megastones カテゴリ照会の注意を追記

### HARD-GATE 検証結果

```
HG-1 Champions 適合性: ✓ PASS (TOP20全件、ゲッコウガナイト修正済)
HG-2 出典明記:        ✓ PASS (2DB + YT cache)
HG-3 鮮度マーク:      ✓ PASS
HG-4 構築リンク整合:  ✓ PASS (S2.1-MegaGren)
HG-5 推測排除:        ✓ PASS (calc 確定数ベース)
```

---

## v1.0.0 — 2026-04-30 16:00 JST (初版)

### 作成

- `meta/` ディレクトリ新規作成
- `META-LATEST.md` 8 章フルセット 作成
- `archive/2026-04-30.md` 初版スナップショット
- `meta/README.md` 運用 SOP 整備

### データ取得

| ソース | 結果 |
|---|---|
| champs.pokedb.tokyo | TOP 20 取得成功 (順位のみ、% 非公開) |
| pokechamdb.com/en | TOP 30 取得成功 (last_updated 2026-04-28、48h stale) |
| Kuroko YT RSS | 404 (チャンネル ID drift、要確認) |
| KYOUPOKE X (nitter) | 直近 24-72h 10 件取得成功 |
| WebSearch | game8/altema/yakkun/note 関連リンク 10 件 |

### 主要発見

- **自構築 A.3-Final-v7.8 の 6 体すべて TOP 20 入り** (1, 6, 7, 8, 9, 19 位) → 鉄板構築
- **メガカイは環境メタの最適解** (TOP15 中 14 体に対して互角以上)
- **ブラはミミ/ドドゲ/マスカに弱く、補完候補検討対象**
- **アーキ #5 物理対面型 (メガクチート + ドドゲ + マスカ) が最大苦手**
- **TBD ガード対象ポケ (パラドックス/禁忌四災/禁伝) は TOP 30 に混入なし**

### HARD-GATE 検証結果

```
HG-1 Champions 適合性: ✓ PASS (TOP30 全件)
HG-2 出典明記:        ✓ PASS
HG-3 鮮度マーク:      ✓ PASS
HG-4 構築リンク整合:  ✓ PASS
HG-5 推測排除:        ✓ PASS (禁止語句 0 件)
```

---

## 更新ルール (Append-only)

新規エントリは **このセクションの上** (v1.0.0 の直前) に追加する。
形式:

```
## vX.Y.Z — YYYY-MM-DD HH:MM JST (差分タイトル)

### 変更
- 何が変わったか (3-5 行)

### データ取得
- ソース別 fetch 結果

### 検証
- HARD-GATE 5 軸 PASS/FAIL
```

### バージョニング

- **Major (X)**: アーキタイプ追加 / マトリクス構造変更
- **Minor (Y)**: TOP 入替 3 件以上 / アーキ #1 中心ポケ変更
- **Patch (Z)**: TOP 入替 1-2 件 / 新動画/X ポスト反映 / 軽微修正
