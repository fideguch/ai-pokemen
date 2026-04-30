# 構築改善提案集 (対戦ログから抽出)

> 対戦ログ集計から出た「次の構築変更案」を蓄積。
> 優先度高 + 複数戦で再現する仮説のみが構築変更の根拠になる。
> 1 戦の偶発事故は反映しない。

---

## 提案テンプレート

```yaml
proposal_id: P-001
created: YYYY-MM-DD
priority: High / Medium / Low
status: open / in_review / accepted / rejected / implemented
title: [1 行の要約]
trigger:
  - 関連対戦ログ: [パス x N]
  - 出現頻度: N/M 戦
  - 共通する負けパターン: [説明]
hypothesis: [仮説]
proposed_change:
  type: [技変更 / EV調整 / 持ち物変更 / メンバー入れ替え / 構築コンセプト変更]
  detail: [具体的な変更内容]
risk: [変更で犠牲になる強み]
verification:
  - [この変更が機能するか確認するシナリオ]
implemented_at: [YYYY-MM-DD or null]
implemented_in_build: [Build ID or null]
```

---

## Open Proposals (未対応)

> _まだ提案なし。対戦ログが溜まると自動で提案が追加されます。_

---

## In Review (検討中)

_なし_

---

## Implemented (反映済み)

_なし_

---

## Rejected (採用見送り)

_なし_

---

## 関連

- 集計サマリ: `./summary.md`
- 構築 SSOT: `../builds/ACTIVE.md`
- 構築テンプレート: `../builds/_template.md`
