# kaikei — 会計帳簿の itonami dapp（ブラウザ内完結）

**kaikei（会計）は accounting を指す。** 会計ソフトから書き出した仕訳を取り込み、
試算表・損益計算書・貸借対照表を**ブラウザの中だけで**作る itonami dapp。
請求書を作り・取り込み、適格請求書の記載事項を検査して、売掛金・買掛金の仕訳として
計上する（2026-10-22 から。Linear JUN-321）。仕訳は次の形式を読み書きする（Linear JUN-304）:

- マネーフォワード クラウド会計の仕訳帳 CSV
- freee 会計の仕訳 CSV（汎用形式）
- 弥生会計のインポート形式（仕訳日記帳）
- QuickBooks Online の Account・JournalEntry（API の JSON）と journal entries CSV
- Xero の Accounts・Journals・ManualJournals（API の JSON）と manual journal CSV

請求書は次の形式を読み書きする（Zoho Invoice と FreshBooks は読むだけ）:

- Xero の Invoices（API の JSON）と、請求書・受け取った請求書の取り込み CSV
- QuickBooks Online の Invoice・Bill（API の JSON）と invoices の取り込み CSV
- freee請求書 の帳票 CSV インポートと API の invoice
- マネーフォワード クラウド請求書 の CSV 一括追加と API v3 の Billing
- Zoho Invoice の invoice、FreshBooks の invoices・bills（API の JSON）

利用者が自分で落とした銀行・カードの明細を取り込み、請求書の消込・帳簿の仕訳との照合・
振替と、過去の仕訳と利用者の規則による仕訳の候補を出す。利用者が承認するまで計上しない
（2026-10-23 から。Linear JUN-327）。明細は次の形式を読む（OFX は読むだけ）:

- OFX 1.x（SGML）・2.x（XML）、QFX・QBO（Web Connect）
- 全銀協の入出金取引明細・振込入金通知（固定長・全銀 CSV）
- freee 会計・マネーフォワード クラウド会計・Xero・QuickBooks Online の明細の取り込み CSV
- 銀行・カードの CSV（列の割り当てと型。一次資料で確かめていない型は警告する）
- 経費・買掛: Ramp・Brex の API の JSON、Expensify（kaikei の template で書き出した CSV）、
  BILL v3 の請求書（どれも読むだけ）

銀行・カード会社には接続せず（口座連携をしない）、支払もしない。データは送信されない。
保存はこの端末の IndexedDB だけ。

| | 置き場所 |
|---|---|
| 判断コア（guest） | `aiueos/kaikei_journal.cljk`（仕訳の検証・試算表・段階利益・B/S の照合・請求書の税率ごとの税額・明細の残高と消込の強さ。`:effects #{}`） |
| adapter・形式・帳票・請求書・明細 | `src/kaikei/`（`core` `invoice` `statement` `ingest` `export` `compat/*` `view` `mcp`） |
| 画面 | `site/`（scittle + Re-frame／Reagent、DADS）。公開先は `https://itonami.cloud/sites/app/kaikei/` |
| agent の tool | `bin/kaikei-mcp`（stdio MCP、tool 11、pure） |
| 設計の正本 | `docs/aiueos-dapp.md` |
| 旧来の入口（Cloudflare Worker、静的） | `appview/kaikei-core-kaikei01/`（下の歴史の節） |

```bash
npm test
```

`npm test` は kbb で adapter・形式・帳票・画面・MCP を確かめる。guest は
`npm run test:guest`（amu、3 target）と `npm run test:guest-parity`（wasm）で確かめる。

**主張しないこと:**

- 計算は kaikei の規則で、各社の計算の再現ではない。
- 各社の API にはつながない。
- 電子帳簿保存法への適合は主張しない。
- 申告書を作らず、提出もしない。
- 適格請求書の要件を満たすことは保証しない（記載事項の欠けを知らせるだけ）。登録番号は
  形だけを見て、国税庁の公表サイトには照会しない。請求書を送付しない。
- 明細の候補は提案で、正しいことを主張しない。適格請求書の有無を知らないので、明細から
  起こした課税仕入は「未確認」と記録する。

各社の名前はそれぞれの権利者の商標で、kaikei は形式の互換を名乗るだけ。

---

以下は 2026-10-22 より前の、このリポジトリが「会計エージェントの入口 1 枚」
だった頃の記録（歴史として残す）。

当時の表:

| | 置き場所 |
|---|---|
| 入口（このリポジトリ） | `appview/kaikei-core-kaikei01/` |
| 会計ロジック | `40-engine/kotoba/crates/kotoba-kotodama/py/src/kotodama/ingest/kaikei.py`（**別リポジトリ**） |
| 業務フロー | `etzhayyim-root/00-contracts/bpmn/com/etzhayyim/kaikei`（**別リポジトリ**） |

## フロントエンドは cljs に移行済み（2026-09-07）

**Svelte（`svelte/`）は撤去した。** フロントエンドは reagent + re-frame +
`jp-go-dds`（デジタル庁デザインシステム）の ClojureScript single-page app
（`appview/kaikei-core-kaikei01/cljs/`、namespace `kaikei.app`）に置き換わった。
ビルド先は `cljs/public/`（`index.html` + `js/app.js`）で、`wrangler.jsonc` の
`assets.directory` はここを指す。

**内容は元の Svelte 版と同じ静的な状態表示ページ**（title / project / name /
kind / 空の routes リスト / 空の runtime-bindings リスト / source path）を、
re-frame の db + subs 経由で描画するだけ——`wrangler.jsonc` が名乗る
`APP_CAPABILITIES`（`journal-entry` / `trial-balance` / `profit-loss` /
`balance-sheet`）をこの移行で実装したわけではない。それらは元から実装が無い
（このセクション最上部のとおり、会計ロジックは別リポジトリ）。

**実測（2026-09-07、この移行で実行したビルド/テスト）:**

- `cljs/` で `npm install` → exit 0（129 packages）。
- `amu compile --target wasm32-browser app` → exit 0（111 files, 110 compiled, 0 warnings）。
  出力は `cljs/public/js/app.js`。
- `amu compile --target wasm32-browser test && node out/tests.js` → exit 0
  （6 tests, 14 assertions, 0 failures, 0 errors）。

**UNVERIFIED（この移行では検証していない）:**

- `wrangler dev` / `wrangler deploy` は実行していない。`wrangler.jsonc` の
  `assets.directory` を `./cljs/public` に向け、`main` キーを削除した
  （静的アセットのみを配る Worker になった——後述のとおり動的な Worker
  スクリプトは today 何も deploy されない）。この config 変更が実際に
  Cloudflare 上で動くかは未検証。

## XRPC の実装は 2 つとも残っているが、今日はどちらも deploy されない

移行前は SvelteKit の `+server.ts` が唯一 deploy される実装だった（`wrangler.jsonc`
の `main` が SvelteKit のビルド出力を指していたため）。この移行で `main` キーを
削除したので、**今日はこのリポジトリから動的コードは一切 deploy されない**——
配られるのは cljs の静的アセットだけである。

| | `src/app.ts` | `src/xrpc-mcp-router-proxy.ts`（旧 `svelte/src/routes/xrpc/[...path]/+server.ts`） |
|---|---|---|
| 上流 | `DISPATCHER_URL`（既定 `dispatcher.etzhayyim.com`） | `AGENTGATEWAY_MCP_ROUTER_URL`（既定 `mcp.etzhayyim.com`） |
| 形 | `POST /xrpc/<nsid>` に body を素通し | JSON-RPC 2.0 `tools/call` に包む |
| `/health` | 有る | 無い |
| **今日 deploy されるか** | **されない**（元から） | **されない**（この移行で main が消えたため） |

`src/xrpc-mcp-router-proxy.ts` は Svelte 撤去時に**中身を 1 バイトも変えず**
`svelte/src/routes/xrpc/[...path]/+server.ts` から移設したもの（ファイル冒頭に
provenance コメントあり）。`@sveltejs/kit` から import しており、SvelteKit の
ビルドが無くなった今はそのままでは動かない。`src/app.ts` は元から `main` が
指していない（`package.json` の `typecheck` が見る唯一のファイルであり、
`kotodama.jsonld` の `component.path` が指す先ではあるが、deploy 対象ではな
かった）。**どちらを、あるいは両方を、プレーンな Worker `fetch` ハンドラとして
再配線するかは未決の製品判断**——このリポジトリはそれを決めず、両方を
provenance 付きで保存しているだけ。

## 実測した現在地（2026-08-14、SvelteKit 版。今日の cljs 版の実測は上記）

以下は Svelte を撤去する前、SvelteKit 版が deploy されていた頃に実測した内容
——**歴史として残す**（実装の前提が変わったので今日の挙動の説明としては読まない）。

**動いていた:**

- `npm run build`（SvelteKit + `@sveltejs/adapter-cloudflare`）は通り、
  `wrangler.jsonc` の `main` が指す `svelte/.svelte-kit/cloudflare/_worker.js` を出した。
- `wrangler dev` でローカルに立ち、`GET /` が状態表示の 1 ページを返した。
- `OPTIONS /xrpc/<nsid>` → `204` + `access-control-allow-origin: *`。
- `POST /xrpc/<nsid>` → 到達可能な router を向ければ `200`。転送・封筒・
  unwrap まで通ることを stub で確認済みだった。

**動いていなかった（今日も未解消・cljs 版とは無関係に残る事実）:**

- **`etzhayyim.com` のサブドメインが 1 つも解決しない。** `kaikei01` /
  `kaikei` / `dispatcher` / `mcp` すべて NXDOMAIN（apex だけが引ける、実測
  2026-08-14。この移行では再測定していない）。
- `kotodama.jsonld` が名乗る `did:web:kaikei.etzhayyim.com` は、そのホストが
  NXDOMAIN なので **解決できない**（同上）。

## 由来と移行状態

`etzhayyim/root` の `60-apps/etzhayyim-project-kaikei` から 2026-05-21 に
TRANSFORM バッチで切り出した seed（`migration.edn` が出所 revision と tree を固定
している）。**現在は `cloud-itonami` org に居るが、中身は依然 etzhayyim 名前空間**
（`com.etzhayyim.apps.kaikei.*` / `did:web:*.etzhayyim.com`）で、codemod は未実施。

未処理項目の正本は `MIGRATION-TODO.md`。`NOTICE` は Apache-2.0 + Charter
Compliance Rider v3.1 を宣言するが、**`CHARTER-RIDER.md` も `LICENSE` も
このリポジトリには入っていない**（上流にある）。

## 近接リポジトリとの境界

- 会計の**計算**を探しているなら、ここではない（上表の kotodama ingest）。
- 会計の**業務フロー定義**を探しているなら、ここではない（上表の BPMN）。
- ここにあるのは **HTTP 境界と CORS と封筒の変換の設計だけ**（今日 deploy
  されているのは静的な状態表示ページのみ、上記のとおり）。

## 次に読む

- `docs/operator-quickstart.md` — clone から検証済みのローカル実行まで
- `MIGRATION-TODO.md` — Charter §2(a)-(h) 適合の未処理リスト
- `migration.edn` — 切り出し元の revision / tree / ファイル数

## aiueos 上の分散型 dapp 設計（2026-10-19〜）

kaikei を aiueos アプリ（分散型 dapp、itonami agent 前提）として実現する設計が
`docs/aiueos-dapp.md` にある。

- 第 1 スライス（JUN-115）: 判断コア guest。
- 第 2 スライス（JUN-304）: 5 社の形式・帳票・画面・MCP。
- 第 3 スライス（JUN-321）: 請求書（適格請求書の検査・計上・各社の請求書の形）。
- 第 4 スライス（JUN-327）: 明細（OFX・各社の明細 CSV）、入金・支払の消込、仕訳の候補。

adapter の正本は `src/kaikei/core.cljk`。`appview/.../cljs/src/kaikei/journal.cljk` は
第 1 スライスの adapter で、旧 SPA のビルドの再配線を決めるまで残してある。
appview の `npm test` はその adapter を kbb で回す（shadow 経路は `test:shadow`）。
