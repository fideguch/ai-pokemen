# Meta 対策メモ 更新履歴 (CHANGELOG)

> META-LATEST.md の差分ログ (append-only)。
> 大きな変動 (TOP10 入替 3 件以上 / 新アーキ出現) があった日は archive/YYYY-MM-DD.md にスナップショット。

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
