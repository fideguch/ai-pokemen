# Champions Overrides — 出典スナップショット

> Pokemon Champions の Showdown 素値からの差分情報の出典記録。
> data/champions_overrides.json および data/champions_implementation.json の根拠ソース。

## 取得日

- **2026-04-30** (planner Opus が WebFetch で確認済、Writer 再fetch 不要)

## 出典 URL (Tier 順)

| Tier | URL | 取得日 | 用途 |
|------|-----|-------|------|
| S | https://game8.jp/pokemon-champions/777049 | 2026-04-30 | 弱体化技・状態異常変更の一次まとめ |
| S | https://altema.jp/pokemonchampions/jyakutaika | 2026-04-30 | 弱体化リスト + 持ち物未実装 |
| A | https://gamepedia.jp/pokemonchampions/archives/133 | 2026-04-30 | 仕様変更・削除技・追加技 |
| A | https://note.com/silkcream2/n/nacd8291b5e2c | 2026-04-30 | 個別ポケ補正・技調整事例 |
| 補完 | https://yakkun.com/ch/changes.htm | 2026-04-30 | **403 で取得不可**、上記 4 ソースで網羅 |

## 25 件差分項目 (overrides 適用対象)

### 技ナーフ (基礎パラメータ)

| # | Showdown ID | JP 名 | Showdown 素値 | Champions 値 | 出典 |
|---|-------------|-------|--------------|-------------|------|
| 1 | moonblast | ムーンフォース | 30% C-1 | **10% C-1** | game8 |
| 2 | ironhead | アイアンヘッド | 30% ひるみ | **20% ひるみ** | altema |
| 3 | fakeout | ねこだまし | 100% ひるみ | **30% ひるみ** | gamepedia |
| 4 | shadowball | シャドーボール | 20% D-1 | **10% D-1** | game8 |
| 5 | freezedry | フリーズドライ | 10% 凍結 | **凍結効果削除** | gamepedia |
| 6 | leechseed | やどりぎのタネ | 1/8 ドレイン | **1/16 ドレイン** | altema |
| 7 | saltcure | しおづけ | 1/8 ダメ (水/鋼は 1/4) | **1/16 ダメ (水/鋼は 1/8 維持)** | game8 |
| 8 | toxicspikes | どくびし | 1/8 毒ダメ | **1/16 毒ダメ** | gamepedia |

### 技強化

| # | Showdown ID | JP 名 | Showdown 素値 | Champions 値 | 出典 |
|---|-------------|-------|--------------|-------------|------|
| 9 | gforce | Gフォース (旧名/新規?) | 80 | **90** | note |
| 10 | tropicalkick | トロピカルキック | 70 | **85** | note |
| 11 | iceberg | こおりやま (新技?) | 100 | **120** | note |
| 12 | wakeupslap | めざめるビンタ | 70 | **100 (Showdown 70 → +30)** | gamepedia |
| 13 | crabhammer | クラブハンマー | 90 命中 | **95 命中** | game8 |
| 14 | toxicthread | どくのいと | S-1 | **S-2** | altema |

### 状態異常

| # | 状態 | Showdown 素値 | Champions 値 | 出典 |
|---|------|--------------|-------------|------|
| 15 | par (まひ) | 25% 行動不能 | **12.5% 行動不能** | game8/altema |
| 16 | frz (こおり) | 永久 (20%/T 解除) | **3 ターンで自動回復** | game8 |
| 17 | slp (ねむり) | 1-3 ターン (rand) | **3 ターンで保証起床** | gamepedia |

### 特性挙動

| # | Ability | 内容 | 出典 |
|---|---------|------|------|
| 18 | ironfist (ふかしのこぶし) | 守る貫通時 1/4 ダメ追加 (Champions 仕様) | note |

### ポケ別 技削除

| # | Pokemon | 削除技 | 出典 |
|---|---------|--------|------|
| 19 | kommoo (ジャラランガ) | bodypress (ボディプレス) | altema |
| 20 | gengar (ゲンガー) | encore (アンコール) | implementation_status |
| 21 | dragonite (カイリュー) | encore | implementation_status |
| 22 | kangaskhan (ガルーラ) | powerupperch (?) | note |
| 23 | incineroar (ガオガエン) | knockoff, uturn | note |
| 24 | gliscor (グライオン) | taunt (ちょうはつ) | game8 |

### ポケ別 技追加

| # | Pokemon | 追加技 | 出典 |
|---|---------|--------|------|
| 25 | aegislash (ギルガルド) | poltergeist (ポルターガイスト) | note |
| - | gyarados (ギャラドス) | powerwhip (パワーウィップ) | note |
| - | charizard (リザードン) | scaleshot (うろこのいし) | note |
| - | greninja (ゲッコウガ) | flipturn (フリップターン) | note |
| - | sylveon (ニンフィア) | mysticalfire (マジカルフレイム) | note |
| - | tyranitar (バンギラス) | superpower (ばかぢから) | note |
| - | scizor (ハッサム) | roost (はねやすめ) | note |

## 持ち物実装状況サマリ (詳細は data/champions_implementation.json)

- **未実装 (構築提案禁止)**: rockyhelmet, choiceband, choicespecs, lifeorb, assaultvest, heavydutyboots, weaknesspolicy, redcard, custapberry, ejectbutton, ejectpack
- **実装済**: focussash, leftovers, sitrusberry, lumberry, choicescarf, 各種半減きのみ, タイプ強化系, メガストーン約 40 種

## メモ

- Smogon gen9ou は Champions と別ゲーム。本スキルでは過去作 SV メタの参考データとして data/stats/ に保持するのみ。
- Champions 使用率 SSOT は cache/champs_usage/ (champs.pokedb / pokechamdb から fetch)。
- 24h 以内の鮮度は YouTube/X (cache/yt_transcripts/) で別途取得。
