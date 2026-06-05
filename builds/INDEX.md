# Builds INDEX (全構築の Status 管理)

> **役割**: 複数構築を並列管理する SSOT。Status で active/experimental/testing/archived を分類。
> **更新タイミング**: 構築追加 / Status 変更 / スコア再評価 時。
> **bochi 同期**: `~/.claude/bochi-data/memos/pokechamp-builds-index.md` (常に最新と同期)。

---

## Active Builds (現在実戦投入中、または投入予定)

| Build ID | Status | Score | Concept | File | Last Updated |
|----------|--------|-------|---------|------|--------------|
| **S2.1-MegaGren-v1.0** | active ⭐ | 86 | メガ2枚 (メガゲッコ特殊breaker + メガゲン滅びtrap) + 高速オフェンス + 二重ハザード | [`S2.1-MegaGren-v1.0.md`](./S2.1-MegaGren-v1.0.md) | 2026-06-05 21:25 (M-2 初版) |

## Archived Builds (旧シーズン / 引退)

| Build ID | Status | Score | Concept | File | Note |
|----------|--------|-------|---------|------|------|
| A.3-Final-v7.8 | archived (M-1) | 92 | メガ2体 (メガカイ + メガゲン) + 二重ハザード + 終盤詰め | [`A.3-Final-v7.8.md`](./A.3-Final-v7.8.md) | M-1 構築。M-2 でメガカイ軸→メガゲッコ軸に刷新 |

(将来構築 B / C / D を追加する際はこのテーブルに行追加)

---

## Status 凡例

| Status | 意味 | 想定数 |
|--------|------|--------|
| **active** ⭐ | ランクマ実戦投入中の現行構築 | 通常 1-2 個 |
| **experimental** | 仮説検証段階、まだ未投入 / シミュレーションのみ | 複数可 |
| **testing** | 数戦テスト対戦中、本格投入の判断待ち | 1-2 個 |
| **archived** | 引退、`archive/` 配下に退避 | 無制限 |

---

## 構築追加フロー (新構築 B / C を作る時)

```
1. 新 Build ID 採番 (例: B.1-CycleCore-v1.0)
   - A 系: メガ2体軸構築
   - B 系: サイクル軸構築
   - C 系: 受けループ / 特殊軸
   - D 系以降: 自由
   - **S 系: シーズン番号プレフィックス (例 S2.1 = シーズン M-2 の第1構築)**。シーズン切替で軸を作り直す場合に使用
   - バージョン v1.0, v1.1, ... の通し番号

2. _template.md → builds/{NEW_ID}.md にコピー
   `cp _template.md {NEW_ID}.md`

3. INDEX.md (このファイル) に Status: experimental で行追加

4. 内容を埋める (DB リサーチ + ダメ計 + 環境分析 + 当て込み)
   - §0 メタ情報
   - §0.5 構築仮説
   - §1-§12 全節埋め

5. 仮説段階完了 → Status: testing (数戦試す)

6. 実戦評価で Status: active (本格投入) or archived (採用見送り)

7. 旧 active 構築を引退する場合:
   - Status: archived
   - ファイルを builds/archive/ に移動
   - bochi 同期コピーは削除
```

---

## bochi 同期マッピング

| SSOT (skills 配下) | bochi 同期コピー (memos 配下) |
|---|---|
| `INDEX.md` | `pokechamp-builds-index.md` |
| `A.3-Final-v7.8.md` | `pokechamp-build-A.3-Final.md` |
| (将来) `B.1-XXX-v1.0.md` | (将来) `pokechamp-build-B.1-XXX.md` |
| `archive/*.md` | (bochi には同期しない、SSOT のみ保持) |

各 bochi ファイル冒頭に「同期コピー、直接編集禁止」注記。

---

## Quick Reference: S2.1-MegaGren-v1.0 (現 active, M-2)

```
1. メガゲッコ @ゲッコウガナイト おくびょう CS / ハイドロポンプ・冷ビ・くさむすび・じんつうりき
2. オオニューラ @きあいのタスキ いじっぱり AS / フェイタルクロー・じごくづき・インファ・どくびし
3. ガブ        @こだわりスカーフ いじっぱり AS / じしん・いわなだれ・げきりん・ステロ(→どくづき推奨)
4. メガゲンガー @ゲンガナイト おくびょう CS / シャドボ・みがわり・ほろびのうた・まもる
5. ブリジュラス @オボンのみ じきゅうりょく / 10万・ドラゴンテール・ラスカ・ステロ
6. アーマーガア @たべのこし プレッシャー / ブレバ・ビルドアップ・はねやすめ・とんぼがえり
```

---

## アーキタイプ別選出 (環境タイプ → 推奨選出)

詳細は `~/.claude/skills/pokemon-champions/references/environment_archetypes.md` + `../meta/META-LATEST.md §6` 参照。

| 環境タイプ | active 構築 (S2.1-MegaGren) の推奨選出 |
|---|---|
| AT-01 高速対面 | オオニューラ + スカガブ + メガゲッコ (メガゲッコ進化) |
| AT-02 サイクル | メガゲンガー + ブリジュ + スカガブ (メガゲン進化) |
| AT-03 受けループ | メガゲンガー + オオニューラ + ガブ (メガゲン進化) |
| AT-04 晴れ | スカガブ + メガゲッコ + ブリジュ (メガゲッコ進化) |
| AT-05 積み | スカガブ + メガゲンガー + オオニューラ (メガゲン進化) |
| AT-06 フェアリー特殊 | オオニューラ + メガゲッコ + アーマガ (メガゲッコ進化) |
| AT-07 中堅標準 | スカガブ + メガゲッコ + ブリジュ (メガゲッコ進化) |
| AT-08 トリル/鈍足 | スカガブ + メガゲンガー + メガゲッコ (状況判断) |

---

## 関連ファイル

- 構築テンプレ (新構築作成用): `./_template.md`
- 環境アーキタイプ定義: `../references/environment_archetypes.md`
- 過去構築 (Archived): `./archive/`
- 対戦ログ: `../battle_logs/`
- スキル本体: `../SKILL.md`
- **★ メタ対策メモ (LATEST)**: `../meta/META-LATEST.md` — 環境 TOP20 + 自構築対策マトリクス + アーキ別選出 (日次更新)
- メタ更新履歴: `../meta/CHANGELOG.md`
- メタ運用 SOP: `../meta/README.md`
- 過去メタスナップショット: `../meta/archive/`
