# 対戦ログ運用ガイド

> **目的**: ランクマ後の反省を構築改善サイクルに乗せる SSOT。
> 自然言語のしゃべりを `_template.md` に当てはめてファイル化、週次で集計、構築改善案に紐付ける。

---

## ディレクトリ構造

```
battle_logs/
├── _template.md              # 1 対戦の記録テンプレート
├── README.md                 # このファイル
├── summary.md                # 週次/月次集計 (随時更新)
├── improvement_proposals.md  # 対戦から抽出した構築改善案 (随時追加)
└── YYYY/
    └── MM/
        └── DD/                                  # 日別フォルダ
            ├── 001-vs-メガガル軸-loss.md
            ├── 002-vs-メガリザY軸-win.md
            └── ...
```

ファイル命名規則: `NNN-vs-[相手構築特徴]-[結果].md`
- NNN: 当日の連番 (3 桁)
- 相手構築特徴: 1-2 単語で識別 (例: `メガガル軸`, `クエスパトラ起点`)
- 結果: `win` / `loss` / `draw`

---

## 1 対戦の記録フロー

### Step 1: ユーザーがしゃべる (自然言語 OK)

ランクマで 1 戦終わったら、記憶が新鮮なうちに `/pokechamp` セッションで以下のような口語で投げる:

```
「メガガル + メガカイ + カバの相手に負けた。
ブラ先発したけど、相手にハッサム居て虫4倍で持ってかれた。
裏のメガカイで挽回しようとしたけど、ハバタクカミに先制で落ちた。
最初の選出ミスったかも」
```

### Step 2: Claude (pokechamp) が自動でテンプレートに当てはめ

`_template.md` の §1-7 を埋めて以下に保存:
```
battle_logs/2026/MM/DD/NNN-vs-メガガル軸-loss.md
```

### Step 3: 週次集計 (毎週日曜 or 「今週の対戦集計して」呼び出し)

`summary.md` に以下を集計:
- 勝率 (全体 / 構築タイプ別)
- 多発した負けパターン Top 3
- 自パで困った瞬間 Top 5
- 改善仮説 → `improvement_proposals.md` に転記

### Step 4: 構築改善 (必要なら)

改善仮説が積み上がったら `/pokechamp 構築修正案出して` で:
- `improvement_proposals.md` から優先度高い項目を選定
- 新構築 ID 採番 (例: A.4-XXX-v8.0)
- `builds/_template.md` から新構築ファイル作成
- `builds/ACTIVE.md` を新構築に切り替え
- 旧構築を `builds/archive/` に退避
- bochi 同期 (`pokechamp-active-build.md` を新内容で上書き)

---

## ユーザー側の呼び出し例

| やりたいこと | 言い方の例 |
|---|---|
| 1 戦記録 | 「対戦記録: [自然言語で対戦内容]」 |
| 当日サマリ | 「今日の対戦まとめて」 |
| 週次集計 | 「今週の対戦集計して」 / 「最近の負けパターン教えて」 |
| 構築改善案 | 「改善案を構築に反映して」 / 「次の構築考えて」 |
| 過去対戦検索 | 「メガガル相手の対戦どうだった?」 |

---

## 設計原則

1. **SSOT (Single Source of Truth)**: 構築は `builds/ACTIVE.md` 1 ファイルで管理、過去は `archive/` へ
2. **対戦は積み上げ**: 過去の対戦ファイルは削除せず学習資産として保持
3. **bochi 同期は active build のみ**: 過去構築は bochi に出さない (混乱防止)
4. **改善は集計から**: 1 戦の偶発事故では構築変更しない、複数対戦の傾向で変更

---

## 関連ファイル

- 構築 SSOT: `~/.claude/skills/pokemon-champions/builds/ACTIVE.md`
- 対戦テンプレート: `./_template.md`
- 改善提案集: `./improvement_proposals.md`
- bochi 同期先: `~/.claude/bochi-data/memos/pokechamp-active-build.md`
