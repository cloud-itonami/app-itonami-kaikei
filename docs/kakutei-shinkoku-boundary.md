# 確定申告の担当境界

対象は [AWAI-4074](https://linear.app/kotobalabs/issue/AWAI-4074) の棚卸し、[AWAI-4075](https://linear.app/kotobalabs/issue/AWAI-4075) の法域参照、[AWAI-4076](https://linear.app/kotobalabs/issue/AWAI-4076) の個人向け第1スライス。[AWAI-4073](https://linear.app/kotobalabs/issue/AWAI-4073) の本人提出、作成者と承認者の分離、追記専用の要件を引き継ぐ。

| 担当 | 現行資産を確認した箇所 | 統合境界 |
| --- | --- | --- |
| `app-itonami-kaikei` | `src/kaikei/core.cljk`、`invoice.cljk`、`mcp.cljk`、`site/` に記帳、帳票、請求書、明細照合、ローカル MCP | 個人の決算整理、所得・控除・税額の試算、申告書下書き、仕訳・証憑メタの訂正取消履歴、MCP / MCP Apps / Agent Plugin を既存リポジトリへ追加。 |
| `app-itonami-egov` / Shakai | `README.md`、`guest/itonami/egov/packs.clj`、`hermes/profiles/shakai/SOUL.md` に制度パックと個人・家族の手続候補。確定申告の候補は Draft PR #8 の `seido/jp.edn` で確認。 | 確定申告の条文出典、期限、提出先、不明点は制度パック側の責務。本スライスは日本向け試算の版付き出典参照と Shakai の候補への参照キーを持つ。 |
| `app-itonami-kaisha` | `README.md` に会社法の運営予定、計算書類、法人税の申告期限。行政手続候補には egov のパックを参照 | 法人運営、計算書類、法人税申告期限を担当する。Kaikei は確認済みの個人所得の下書きに限定する。 |
| Shigoto | AWAI-4074 の棚卸しにある ERP・業務連携の境界 | 企業 ERP を担当する。税務判断と申告は取扱範囲外。 |
| Gyosei / Banking / legal-entity collector | AWAI-4074 の棚卸し対象 | 行政手続の候補、金融業務、法人情報の収集は各担当に置く。Kaikei は既存のローカル取り込みと帳簿照合を利用する。 |

## ローカル運用

- 下書き・見積りは常に `:adjudicating false`。承認は下書きの内部確認で、提出状態は常に `:user-manual-required`。本人が期限と提出先を確認し、手動で署名・提出する。
- 訂正と取消は元の仕訳と証憑メタを履歴に残す。国税庁の無料インボイス公表サイトの照合結果は手元で確認し、不一致の保存は拒否する。
- IDE ACP は開発環境連携のみ。Commerce ACP は保留。MCP Apps と Agent Plugins は AWAI-4143 確定前の先行実装として、公開仕様を参照し合成データで検証する。

Kaikei の試算参照は `:pack/jurisdiction [:jp]`、`:pack/sources`、`:review/status :unreviewed` のキーを Shakai に揃えた。`:pack/procedure-ref` は Shakai の `:tax-return`（別名 `:kakutei-shinkoku`）と青色・白色の手続IDを固定版に紐づける。様式・期限・提出先・不明点、税理士業務の範囲と電子保存要件は上流が担当し、ローカルの値は未収録なら「未対応」と返す。[e-Gov パックの Draft PR #8](https://github.com/cloud-itonami/app-itonami-egov/pull/8)、[確認した制度パック](https://github.com/cloud-itonami/app-itonami-egov/blob/54e55c2ee5f594994c46117f8743504a06d43ade/seido/jp.edn)

## 第1スライスの利用範囲

- 会計帳簿から「確定申告を開く」。2025・2026年分のうち選んだ1年分の円建て仕訳と、帳簿内の証憑メタデータを端末内の作業領域に取り込む。ユーザーが仕訳の所得区分と調整仕訳を指定する。給与は控除後の所得金額を使う。青色申告特別控除は確認済みの区分を選び、事業所得の黒字額を上限に試算する。
- 対応するのは居住者の通常の確定申告の概算。ここでの給与所得、雑所得、事業所得の合算は、課税対象の非負の所得を前提とする。分離課税、損益通算、準確定申告、源泉徴収・税額控除、正式な帳票と納付・還付額は「未対応」。試算の出典は [国税庁の基礎控除](https://www.nta.go.jp/taxes/shiraberu/taxanswer/shotoku/1199.htm)、[青色申告特別控除](https://www.nta.go.jp/taxes/shiraberu/taxanswer/shotoku/2072.htm)、[所得税の税率](https://www.nta.go.jp/taxes/shiraberu/taxanswer/shotoku/2260.htm)。
- 作成者と承認者には別の担当者IDを使う。ブラウザで入力したIDはローカルの監査用で、身元や資格の認証はホストの責務。帳簿取り込み・決算整理を変更すると過去の履歴を保持したまま承認状態を再確認に戻す。通常の帳簿の一括消去は、確定申告領域の原本・証憑メタ・訂正履歴を保持する。証憑ファイル本体は既存の帳簿側にあり、この履歴は電子帳簿保存法上の適格性を判定しない。
- 人向け画面は現在の作業と承認カードを優先し、詳細は必要時に開く。文字階層と操作対象の見分けやすさを参照した。[Apple HIG のデザイン原則](https://developer.apple.com/design/human-interface-guidelines/design-principles)、[Nintendo の公開事例](https://www.nintendo.com/us/whatsnew/ask-the-developer-vol-3-big-brain-academy-brain-vs-brain-part-1/)
- `bin/kaikei-mcp` は接続単位のメモリに作業状態を持ち、ブラウザの保存領域からは読み出さない。合成帳簿で `taxreturn.read_state` から操作・スキーマを取得し、同じ接続で試算を進める。呼び出しごとに接続を開くホストは、合成帳簿・所得区分・試算条件を `taxreturn.preview_draft` にまとめて渡せる。承認と本人チェックはブラウザで行う。MCP Apps 対応ホストは `ui://kaikei/taxreturn.html` を埋め込める。標準 MCP では同じデータを `structuredContent` とテキストで返す。[SEP-1865](https://modelcontextprotocol.io/seps/1865-mcp-apps-interactive-user-interfaces-for-mcp)、[MCP Apps 2026-01-26](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx)
- Plugin のインポートで発見されるのはスキル。MCP 接続は、ホストで同意後に `mcp.json.example` と既存のローカル実行環境を使って明示的に設定する。[Agent Plugins 1.0.0](https://agent-plugins.org/specification)、[Agent Skills](https://agentskills.io/specification)

| 受入条件 | `npm test` で確認する箇所 |
| --- | --- |
| 提出・代理署名・判断の確定を行う経路がない | `negative-controls-for-prohibited-effects`、`tax-stdio-session-and-fallback` |
| 決算・下書き・訂正を承認する担当者が作成者と異なる | `dry-run-and-separation-of-approval`、`append-only-journal-and-evidence` |
| 元の仕訳と証憑メタを検索できる。登録番号の不一致は保存しない | `append-only-journal-and-evidence`、`invoice-registry-never-accepts-a-mismatch` |
| ブラウザと Agent の操作定義・状態スキーマが一致する | `ui-and-agent-read-the-same-semantic-contract`、`negotiated-app-resource`、`sandbox-bridge-lifecycle-and-read-only-refresh` |
