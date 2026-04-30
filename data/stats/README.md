# data/stats/ について

> このディレクトリには **Smogon gen9ou (Pokemon SV)** の使用率統計が入っている。
> Champions の判断には**直接使わない**。下記を参照。

## 役割の整理

| ディレクトリ | データ起源 | Champions 判断への利用可否 |
|--------------|-----------|---------------------------|
| `data/stats/` | Smogon gen9ou (1500/1825 レーティング) | **NG** (過去作 SV メタの参考のみ) |
| `cache/champs_usage/` | champs.pokedb.tokyo / pokechamdb.com | **OK** (Champions 環境 SSOT) |

## なぜ Smogon gen9ou を判断に使わないか

Pokemon Champions と Pokemon SV は **別ゲーム**:

- 弱体化されている技 / 状態異常が多い (詳細: `data/champions_overrides.json`)
- 持ち物の実装状況が異なる (詳細: `data/champions_implementation.json`)
- ルール (6vs3 シングル) が異なる (Smogon gen9ou は 6v6)
- メガストーンの戻し / キョダイマックス / テラスタルの有無が違う

ハイパー〜マスター帯の Champions 環境を語る際は、必ず
`cache/champs_usage/` の最新スナップショットと
`cache/yt_transcripts/` の 24-72h 動画を組み合わせて判断する。

## Smogon データを参考として読むときの注意

- 「Champions の○○の前世代の傾向」程度のヒントとして使う
- 個別ポケのコア技構成 (例: ガブの三色牙) など、汎用的な役割理論の参考にする
- 採用率の絶対値を Champions に流用してはいけない

## 更新方法

```bash
# Smogon gen9ou stats を月次取得 (参考用、優先度低)
python3 scripts/parse_usage.py 2026-04 gen9ou 1500
python3 scripts/parse_usage.py 2026-04 gen9ou 1825
```

## 関連

- SSOT 全体マップ: `data/README.md`
- Champions overlay 仕様: `lib/champions_overlay.py` の docstring
- 鮮度管理: `SKILL.md` Sec 13 (HARD-GATE)
