# Builds INDEX (全構築の Status 管理)

> **役割**: 複数構築を並列管理する SSOT。Status で active/experimental/testing/archived を分類。
> **更新タイミング**: 構築追加 / Status 変更 / スコア再評価 時。
> **bochi 同期**: `~/.claude/bochi-data/memos/pokechamp-builds-index.md` (常に最新と同期)。

---

## Active Builds (現在実戦投入中、または投入予定)

| Build ID | Status | Score | Concept | File | Last Updated |
|----------|--------|-------|---------|------|--------------|
| **A.3-Final-v7.8** | active ⭐ | 92 | メガ2体 (メガカイ + メガゲン) + 二重ハザード + 終盤詰め | [`A.3-Final-v7.8.md`](./A.3-Final-v7.8.md) | 2026-04-30 |

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

## Quick Reference: A.3-Final-v7.8 (現 active)

```
1. ガブ      @きあいのタスキ ようき AS / じしん・げきりん・ステロ・がんせきふうじ
2. カバ      @たべのこし のんき HBD / じしん・ステロ・あくび・なまける
3. ギルガルド @のろいおふだ いじっぱり HA / ポルガイ・かげうち・インファ・キンシ
4. ブラ      @オボン おだやか HD せいしんりょく / イカサマ・まもる・ねがい・どくどく
5. メガカイ  @カイリューナイト ひかえめ CS / しんそく・りゅうせい・エアスラ・10万
6. メガゲン  @ゲンガナイト おくびょう CS / シャドボ・ヘドロウェ・こご・みちづれ
```

---

## アーキタイプ別選出 (環境タイプ → 推奨選出)

詳細は `~/.claude/skills/pokemon-champions/references/environment_archetypes.md` 参照。

| 環境タイプ | active 構築 (A.3-Final-v7.8) の推奨選出 |
|---|---|
| AT-01 対面 | ブラ + メガカイ + ガブ (メガカイ進化) |
| AT-02 サイクル | ブラ + カバ + メガゲン (メガゲン進化) |
| AT-03 受けループ | ガブ + メガゲン + ギルガ (メガゲン進化) |
| AT-04 晴れ | ガブ + ギルガ + メガカイ (メガカイ進化) |
| AT-05 積み | ブラ + メガゲン + ギルガ (メガゲン進化) |
| AT-06 トリル | ガブ + メガカイ + メガゲン (メガカイ進化) |
| AT-07 中堅 | ガブ + カバ + メガカイ (メガカイ進化) |
| AT-08 特殊 | ブラ + メガゲン + ガブ (メガゲン進化) |

---

## 関連ファイル

- 構築テンプレ (新構築作成用): `./_template.md`
- 環境アーキタイプ定義: `../references/environment_archetypes.md`
- 過去構築 (Archived): `./archive/`
- 対戦ログ: `../battle_logs/`
- スキル本体: `../SKILL.md`
