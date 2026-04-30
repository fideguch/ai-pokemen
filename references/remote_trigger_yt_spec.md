# Remote Trigger 拡張仕様: YouTube 字幕自動取得

> このドキュメントは「リモエ (Remote Trigger)」の拡張指示書。
> Writer はリモエ実体を変更しない (RemoteTrigger ツール権限が必要)。
> ユーザー側で別途 RemoteTrigger を更新する際の参照仕様として扱う。

## 既存リモエの現状

| 項目 | 値 |
|------|-----|
| Trigger ID | `trig_01QACKUUMb7oQtUm1WwNR5U5` |
| 起動時刻 | 毎朝 7:00 JST (cron `0 7 * * *`) |
| 既存スクリプト | (champs_usage の更新等) |
| 起動主体 | Claude RemoteTrigger サービス |

## 拡張内容 (追加コマンド)

既存スクリプトに以下を **末尾追加** する:

```bash
bash -c "cd ~/.claude/skills/pokemon-champions && python3 scripts/fetch_yt_transcripts.py"
```

## 期待動作

1. 7:00 JST にトリガー発火
2. champs_usage を 6h TTL で fetch (既存)
3. yt_transcripts を最近 24h 分追加 fetch (拡張)
4. INDEX.json に新規動画を追記
5. yt-dlp 不在時は fail-soft で exit 0 (skip)

## 失敗時挙動

- HTTP 失敗: 警告 log + 既存 cache 維持 + exit 0 (champs_usage)
- yt-dlp 不在: 警告 log + INDEX.json 初期化のみ + exit 0
- yt-dlp 失敗: 該当動画のみ skip、INDEX.json には null path で記録

## Implementation Status

| コンポーネント | 状態 | 備考 |
|---|---|---|
| scripts/fetch_yt_transcripts.py | OK 実装済 | yt-dlp 依存、fail-soft 対応 |
| cache/yt_transcripts/INDEX.json | OK 初期化済 | スキーマ v1.0.0 |
| scripts/fetch_champs_usage.py | OK 実装済 | 6h TTL、--dry-run / --force 対応 |
| cache/champs_usage/_meta.json | OK 自動生成 | 初回 fetch 時に作成 |
| リモエ拡張 (trig_01QACKUUMb7oQtUm1WwNR5U5 への script 追加) | NG 別途実装 | RemoteTrigger ツール権限が必要 |
| Discord 通知 (失敗時) | NG 別途実装 | 拡張オプション |

## 検証手順

リモエ拡張後、以下で動作確認:

```bash
# Dry-run で計画確認
python3 ~/.claude/skills/pokemon-champions/scripts/fetch_yt_transcripts.py --dry-run

# 実 fetch (yt-dlp 必要)
brew install yt-dlp
python3 ~/.claude/skills/pokemon-champions/scripts/fetch_yt_transcripts.py

# INDEX 確認
cat ~/.claude/skills/pokemon-champions/cache/yt_transcripts/INDEX.json | jq '.videos | length'
```

## 関連

- `scripts/fetch_yt_transcripts.py` — 本体スクリプト
- `scripts/fetch_champs_usage.py` — 同時に走らせる usage fetcher
- `references/realtime_access_methods.md` — リアルタイム情報取得の全体方針
- `references/authoritative_sources.md` — 監視対象チャンネル/X の根拠
