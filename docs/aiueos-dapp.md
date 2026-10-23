# kaikei 会計 dapp — aiueos 上の分散型設計（itonami agent 前提）

状態: 設計 + 第 1 スライス（2026-10-19、判断コア guest）+ 第 2 スライス
（2026-10-22、5 社の形式・帳票・画面・MCP）+ 第 3 スライス（2026-10-22、請求書）。
正本はこの文書。
追跡: Linear JUN-115（第 1）、JUN-304（第 2）、JUN-321（第 3）。

## 目標

kaikei を「サーバに会計状態を置かない分散型 dapp」として実現する。
実行面は aiueos（kotoba-lang/aiueos）、運用面は itonami agent
（kotoba-lang/itonami-agent）。中央 DB は持たない（AWAI policy: D1 / Durable
Object / KV を状態置き場にしない）。

現状の kaikei repo は「入口 1 枚」（README）だったが、この設計は判断コアを
この repo に置く。計算の正本はこの guest、会計ロジックの外部 adapter
（kotodama ingest、BPMN）は従来どおり別リポジトリ。

## 層構成

| 層 | 実体 | 状態 |
|---|---|---|
| 判断コア（guest） | `aiueos/kaikei_journal.cljk` — 仕訳の検証 / 帳簿の貸借一致 / 区分・期間の純額・段階利益・B/S の照合 / 請求書の税率ごとの税額（1 請求書・税率ごとに 1 回の端数処理）・登録番号の形・経過措置の控除割合。`:effects #{}` の pure 計算 | **実装済み・実測**（下記） |
| アプリ記述子 | `aiueos/kaikei.edn`（`examples/apps/notes.edn` 形、`:aiueos/kind :app`） | **実装済み**。aiueos session/grant への配線は未実装 |
| adapter | `src/kaikei/core.cljk` — guest と同名・同結果の判定 + 値モデル（帳簿・勘定科目・区分）+ 試算表・P/L・B/S | **実装済み・実測**（kbb、parity 表） |
| 形式 | `src/kaikei/ingest.cljk`・`export.cljk`・`compat/{native,xero,qbo,yayoi,mf,freee}.cljk`・`encoding.cljk`（Shift_JIS）、請求書は `compat/{xero,qbo}_invoices.cljk` | **実装済み・実測**（第 2・第 3 スライスの節） |
| 請求書 | `src/kaikei/invoice.cljk` — 値モデル・税率ごとの合計・適格請求書の記載事項の検査・売掛／買掛の仕訳の計上 | **実装済み・実測**（第 3 スライスの節） |
| 画面 | `src/kaikei/view.cljk`（純 hiccup）+ `site/app.cljk`（Re-frame / Reagent、scittle）+ `site/kaikei/page.cljk`（SSR の殻、DADS） | **実装済み・ブラウザで実測** |
| 状態 | IndexedDB（`itonami.kaikei` の `state`）。使えなければ localStorage。1 ブラウザに閉じる | **実装済み** |
| agent 統合（MCP） | `bin/kaikei-mcp` + `src/kaikei/mcp.cljk` — stdio MCP、tool 8 つ。pure | **実装済み・実測** |
| 旧 appview adapter | `appview/.../cljs/src/kaikei/journal.cljk` — 第 1 スライスの map API（正本は `src/kaikei/core.cljk`） | 旧 SPA のビルドの再配線を決めるまで残す |
| 分散状態 | 仕訳は署名済み topic エンベロープ（`aiueos.network-topic` v1）で複製。永続は AT Protocol MST + IPFS、参照を Base L2 に anchor | **未実装**（設計のみ） |
| 決済 | USDC on Base L2 + ERC-4337 + TitheRouter 10% split（MIGRATION-TODO の codemod 方向） | **未実装**（MIGRATION-TODO の正本どおり） |
| 運用 | itonami agent 常駐 bot（`hermes/profiles/kaikei`） | プロファイルは既存。dapp 連携は未実装 |

## 分散状態の設計（未実装。ここから下は設計）

1. **仕訳の生成**: 各デバイスが自分の鍵で仕訳に署名し、`aiueos.network-topic`
   v1 のエンベロープとして発行する。per-publisher / per-topic の連番を持ち、
   replay と gap は拒否される（docs/network-topic-protocol.md の規約に従う）。
2. **複製**: transport は問わない（TCP / QUIC / store-and-forward）。
   trust は itonami の peer 集合に一致させる（下記）。
3. **永続**: 仕訳の正本は AT Protocol MST 上、実体は IPFS。L2 への anchor は
   期間ごとの digest（例: 月次 trial-balance の digest）であり、個人の仕訳を
   チェーンに流さない。MIGRATION-TODO の Charter 適合項目と同一方向。
4. **crdt 的な競合解消は採らない**。仕訳は append-only ledger であり、
   二重記帳の検出（同一 origin event の重複）だけを判定側に持つ。

## itonami agent の前提

dapp の「動く」は itonami agent の分散実行モデルの上に乗る:

- **turn は trusted peer で実行される**（`itonami.edn :placement [:peer :local]`）。
  bundle は CID で移動する。kaikei の判断 guest は pure なので bundle に
  安全に載る（効果行ゼロ = capability なしで実行可能）。
- **推論 rail は murakumo 専用**（`itonami.edn :inference`）。Hermes agent CLI
  の profile と混ぜない（kotoba-lang/itonami-agent/AGENTS.md の Two CLIs 表）。
- **秘密は越えない**。署名鍵・browser vault 相当の資格情報は各 node の
  ローカルに留め、bundle にも peer 呼び出しにも載せない。
- **kaikei 常駐 bot**（`hermes/profiles/kaikei`）は入口面の成熟ループを回す
  従来どおりの位置づけ。dapp の判断コア自体は bot ではなく guest が担う。

## 実測（2026-10-19、このスライスで実行したもの）

- `amu check aiueos/kaikei_journal.cljk` → `:ok true`, `:effects #{}`。
- `amu test aiueos/kaikei_journal.cljk` → **30/30 passed**
  （test 10 本 × targets `[:jvm-kir :js :wasm]`）。
- `amu compile aiueos/kaikei_journal.cljk --target wasm32-browser` →
  `aiueos/kaikei_journal.wasm`（WebAssembly MVP module, 4,575 bytes）+
  provenance / publication の sidecar。18 definitions。
- kbb で cljs adapter の parity fixture: **4 tests, 13 assertions, 0 failures**
  （`npm test` = `kbb --backend sci --classpath src:test test/run_tests.cljk`）。

## 実測した「動かない」（このスライスで解消していない）

- **`npm test` の旧スクリプトと shadow-cljs :test ビルドは HEAD で壊れている。**
  旧 `amu compile --target wasm32-browser test`（build-id 渡し）は今日の amu
  CLI に存在せず（`source input must use .kotoba, .cljk, or .cljc`）、
  shadow-cljs 直叩きの :test ビルドは .cljk を解決できず「Ran 0 tests」。
  `package.json` の `test` は kbb runner に差し替え済み、旧経路は
  `test:shadow` として保存。`kaikei.app-test` と SPA の `npm run build` は
  このビルドチェーンの再配線待ち（XRPC 再配線と同じ未決事項）。
- **aiueos への配線は未実装**: `aiueos/kaikei.edn` を session/grant
  （`apps/session` の app catalog、ADR-0080 の grant 経路）に載せた実行は
  していない。kotoba-lang/aiueos 側の作業になる。
- **分散状態・L2 anchor・決済は 1 行も実装していない**（上記の設計のみ）。

## 次の一手（優先順）

1. aiueos 側で `:app/kaikei` を app catalog に載せ、grant 経路で guest を
   起動する（kotoba-lang/aiueos の work）。
2. topic 複製の adapter: 仕訳 → `aiueos.network-topic` エンベロープ化。
   判定（連番・replay 拒否）は protocol 側の実装を使う。
3. ビルドチェーンの再配線（shadow / amu のどちらで .cljk SPA を組むか）を
   決めて `kaikei.app-test` を gate に戻す。
4. MST/IPFS 永続と L2 anchor、USDC/ERC-4337/TitheRouter（MIGRATION-TODO の
   codemod と同時）。


## 実行 host と ABI（訂正: 2026-10-19、JUN-125）

guest は vector パラメータを使うため **KIR v4 / `kotoba.typed/externref-v1`**
（typed-value ABI）で、「平坦 i64」はレイアウトの話であって ABI の話ではない。
実行 host は契約どおり **kototama-browser-host-v1**（amu selfhost、
`amu/runtime/browser-host.mjs` の typed ホスト）。aiueos の Chicory kernel
ホストは typed ホストを持たず、kernel 経路では名前付き link 拒否
（kotoba-lang/aiueos の itonami-dapp-bundle-test に pin 済み）。L2 の証拠
（admission → selfhost 実行）は同 repo の itonami-dapp-selfhost-test。
なお credits の guest はスカラーのみのため KIR v3 / `kotoba.i64/direct-v1`。


## 第 2 スライス（2026-10-22、Linear JUN-304）

5 社の会計ソフトの形式を読み書きし、試算表・P/L・B/S をブラウザの中だけで作る。
mihari・dandori と同じ形（scittle の画面・stdio MCP・レジストリ）。

オーナーの指示は「api の互換性を持たせて」。workspace 契約により app origin は
静的配信だけなので、「API 互換」は次の 3 層で持つ。

1. 各社 API のリソース JSON と、取り込み・書き出し CSV の**データ形式**
2. ページ内の pure 関数（`kaikei.compat.*` が同じリソース形を返す）
3. pure な MCP tool

各社の REST パスを app origin で再現するサーバは置かない。

### 形式

| id | 形式 | 読み | 書き | 形の正本（2026-10-22 に確認） |
|---|---|---|---|---|
| `kaikei-json` | kaikei の帳簿 JSON（kaikei.ledger.v1） | ○ | ○ | kaikei。失う項目が無い |
| `xero-json` | Xero の Accounts・Journals・ManualJournals | ○ | Accounts + ManualJournals | XeroAPI/Xero-OpenAPI `5a115f3` の `xero_accounting.yaml` |
| `qbo-json` | QuickBooks Online の Account・JournalEntry（query の応答） | ○ | ○ | intuit/QuickBooks-V3-Java-SDK `c4d5dfa` の data クラスと XSD、Intuit の開発者向け文書の見本 |
| `yayoi` | 弥生会計の仕訳日記帳 インポート形式（25 項目、見出しなし） | ○ | ○ | 弥生サポート page_id=18545・18586・31478・18111 |
| `mf` | マネーフォワード クラウド会計の仕訳帳 CSV（27 列） | ○ | ○ | MF 使い方ガイド import-books/ib01 |
| `freee` | freee 会計の仕訳 CSV（取り込みテンプレート 33 列、[表題行]／[明細行]） | ○（freee の書き出しの見出しも見出し名で読む） | ○ | freee ヘルプ 204847430 の添付テンプレート |
| `qbo-csv` | QuickBooks Online の journal entries 取り込み CSV | ○ | ○ | QuickBooks Help「Import journal entries」 |
| `xero-csv` | Xero の manual journal 取り込み CSV | ○ | ○ | Xero Central「Add, import and post manual journals」（英・米） |

帳票は kaikei の JSON に加えて、QBO の Report の形（Header／Columns／Rows、group）と
Xero の Reports の形（Reports[].Rows[]、RowType）でも書き出す（`kaikei_report`、
`kaikei.export/report`）。

fixture は `test/fixtures/`。値は合成で、形の出所は `test/fixtures/README.md` に書いた。

### 変換の規則（kaikei のもの）

- **区分**: guest の 0〜14。
  - QBO の AccountType と Xero の Type からは決まった表で写す（`compat/qbo/type->class`・`compat/xero/type->class`）。
  - 各社の型は営業外・特別損益・法人税等を区別しないことが多い（例: Xero の EXPENSE）。そこで、P/L の収益側・費用側の中でだけ、勘定科目名の既定の表で細かくする（`core/refine-class`）。
  - 日本の CSV は勘定科目名しか持たないので、既定の表で当てる（`core/default-class`）。
  - 当たらない科目は未分類で、P/L・B/S に数えず「不完全」と表示する。画面で付けた区分（:user）は取り込みで上書きしない。
- **金額**: 最小通貨単位の整数。
  - ISO 4217 の桁で 10 進から変換する。小数の桁が通貨の桁を超える値は、丸めずに仕訳ごと落とす。
  - 表に無い通貨は取り込まない。
  - 1 帳簿 1 通貨で、通貨の違う取り込みは合流しない。
  - MF・freee・弥生は円の形式なので、円でない帳簿は書き出さない。
- **日付**: 和暦（R08/04/01）・Xero の MS date（`/Date(…)/`）を読む。
  - QBO・Xero の CSV の数だけの日付は利用者の地域で並びが違う。日付の列から推し、推せなければ（QBO は月/日/年、Xero は日/月/年と読んで）警告する。
  - 書き出しの並びは選べる。
- **仕訳のまとまり**:
  - MF は取引No と取引日が同じ連続した行。
  - 弥生は識別フラグ 2110〜2101（2000・2111 は 1 行）。
  - freee は伝票番号。
  - QBO の CSV は Journal No.。
  - Xero の CSV は Date と Narration が空の行を上の行に足す。
- **コードだけの勘定科目**（Xero の CSV、Accounts の無い ManualJournals）は、帳簿にあるコードで名前に引き直す。無ければコードを名前にして、コードごと登録する。
- **重複**: 同じ日付・同じ行（勘定科目・借方・貸方）の仕訳は、追加の取り込みで飛ばす。

### 往復で失うもの（書き出しの注記に出る）

| 項目 | kaikei-json | MF | 弥生 | freee | QBO JSON | QBO CSV | Xero JSON | Xero CSV |
|---|---|---|---|---|---|---|---|---|
| 補助科目 | ○ | ○ | ○ | ○ | ○（ParentRef の Account） | ○（`親:子`） | × | × |
| 部門 | ○ | ○ | ○ | ○ | 名前だけ（DepartmentRef） | ○（Location） | × | × |
| 取引先 | ○ | ○ | オンライン版のみ読む | ○ | 名前だけ（Entity） | ○（Name） | × | × |
| 税区分 | ○ | 同じ形式のものだけ | 同じ形式のものだけ（無ければ 対象外 と書いて注記） | 同じ形式のものだけ | 同じ形式のもの（TaxCodeRef） | × | 同じ形式のもの（TaxType） | 税率の名前だけ（TaxRate） |
| インボイス区分 | ○ | ○ | 税区分の末尾 | × | × | × | × | × |
| tracking | ○ | × | × | × | × | × | ○ | ○ |

税区分の形式をまたぐ写し方は推測しない（例: MF の「課税仕入 10%」と弥生の「課対仕入内10%」）。

### 実測（2026-10-22、このスライスで実行したもの）

amu は `kotoba-lang/amu` 74ca4aa6 の `bin/amu`。kbb の `kotoba-lang/text` は `bc551a3`（origin/main）。

- **guest**
  - `amu check aiueos/kaikei_journal.cljk` → `:ok true`, `:effects #{}`。
  - `amu test aiueos/kaikei_journal.cljk --fuel 4096` → **57/57 passed**（test 19 本 × `[:jvm-kir :js :wasm]`）。
    - fuel は関数の入口ごとに 1 減る。test-profit-stage は既定の 512 では足りない（1000 で不足、2000 で足りる）。
    - 期待値を 1 つ変えた写しでは 54/57 FAILED になり、3 target とも落ちる。
  - `amu compile … --target wasm32-browser --policy aiueos/kaikei_journal.policy.edn` → 9,440 bytes（sha256 `0b021f62…3824`）。
    - policy で記述子と同じ fuel 5,000,000 を wasm に焼き込む。
    - 既定（512、補充されない）で作った wasm は、parity 表の途中で `unreachable` で止まる（実測）。
  - **wasm parity**: `node test/guest_parity.mjs` → **52/52 rows match**（kototama-browser-host-v1、1 instance で全行）。
- **adapter・形式・帳票・画面・MCP**: `npm test`（kbb）→ **51 tests, 487 assertions, 0 failures**。内訳:
  - parity 表の全行
  - sample-import が guest の sample-ledger と同じ buffer になること
  - 8 形式の取り込み
  - 形式ごとの往復（その形式が持てる項目）
  - MF → Xero JSON → QBO JSON → 弥生 → MF の連鎖で日付・勘定科目・金額が保たれること
  - 形式をまたいでも P/L・B/S が同じこと
  - QBO・Xero の帳票の形と合計
  - Shift_JIS の符号化が Python の cp932 で作った fixture と 1 バイトずつ一致すること
  - SSR に関数が混ざらないこと
  - MCP の tool と stdio（cwd が `/` でも repo でも）
- **itonami-agent の MCP クライアント**（`kotoba-lang/itonami-agent` main `0c05574` の `itonami.agent.mcp`、`git archive` で取り出したもの）で実測した:
  - `discover` が `mcp__kaikei__kaikei_import` ほか 5 つを返し、errors は空。
  - `kaikei_import`（MF の fixture）→ `kaikei_report`（profit-and-loss、shape qbo）の NetIncome が 209000。
  - 不正な入力は error として agent に返る。
- **ブラウザ**（built-in browser、ローカルの静的サーバ、`scripts/build-site.cljk` で組んだ公開物）:
  - 次の流れを通した: サンプル → 試算表（貸借 767,500 で一致）→ P/L（当期純利益 103,500、米国式の切り替え）→ B/S（1,333,500 で一致）→ Shift_JIS の弥生ファイルを file input から取り込み（自動判定）→ MF の CSV を貼り付けて取り込み → 未分類の科目を「不完全」と表示 → 勘定科目の画面で区分を付けて「完全」→ 再読み込みで復元。
  - 5 形式の書き出しを Blob で受け、取り込み直して 10 件・落とした 0 件。
  - network の記録は localhost だけ（https の要求は 0）。console エラーなし。
  - 375px 幅で 5 つの画面とも横スクロールなし。
- **大きな帳簿**（1 万行 = 5,000 仕訳、73 万字の MF CSV、ブラウザの scittle、同期処理の時間）:

  | 処理 | 時間 |
  |---|---|
  | 全ソースの評価 | 172 ms |
  | 取り込み | 2.1 秒 |
  | 合流 | 0.14 秒 |
  | 帳票と検査 | 0.48 秒 |
  | MF の Shift_JIS 書き出し | 0.52 秒 |
  | 弥生の書き出し | 0.48 秒 |
  | 再読み込み後の描画 | 1.2 秒 |

  - 保存は約 269 万字。IndexedDB に入り、再読み込みで復元した。
  - localStorage の上限はブラウザごとに違い（この Chromium は 800 万字まで入った）、同じオリジンの mihari・dandori と分け合う。そのため保存を IndexedDB にした。
- **測れなかったもの**: ページの読み込みにかかる時間。
  - built-in browser の pane が隠れていて、scittle が .cljs を順に取得する間隔と Reagent の描画（requestAnimationFrame）が止められ、数十秒になった。
  - 同じ処理の同期部分は上の表のとおり短い。表示されたブラウザでの読み込み時間は未測定。

### 本家 API 直結の壁（2026-10-22 実測）と未実装境界

- **ライブ同期は無い**。理由は 3 つ。
  - 共通ブローカー `kotoba-lang/wasm-webcomponent/src/kotoba-client-runtime.js` が無い（main `c13cf00`）。
  - Origin `https://itonami.cloud` からの preflight に、次の 4 つが `Access-Control-Allow-Origin` を返さなかった: Xero の `api.xro/2.0` と `identity.xero.com`、QBO の `v3/company/…/query` と Intuit のトークン endpoint。
  - app origin の proxy は契約で禁止されている。
  - 残る経路は利用者の端末で動く itonami agent で、オーナーの判断が要る。
- **口座連携はしない**（電子決済等代行業）。明細ファイルの取り込みは第 4 スライスの案。
- **QBO の帳簿の全体**（請求書・支払いから起きた仕訳）は JournalEntry に入らない。QBO の Journal／General Ledger の帳票の形をまだ固定していないので、読まない。Xero は Journals が全体を持つ。
- Xero の ManualJournals で税額のある Exclusive／Inclusive の仕訳は、Xero が別に起こす税の行を含まない。警告し、検証で貸借不一致になる。
- 書き出した ManualJournals が Xero にそのまま登録できるとは限らない。Xero は手入力の仕訳に、銀行口座・売掛金・買掛金などのシステム科目を使わせないことがある（第三者の資料。未確認）。
- **未確認のまま実装したもの**（取り込みは見出しの表記ゆれを吸収する）:
  - 弥生の文字コード（「ANSI」を Shift_JIS と推定）
  - MF の取り込みが受ける文字コード
  - Xero のテンプレートの見出しの `*`
  - QBO の CSV で選べる日付の形
  - freee の仕訳帳の書き出しの見出しの正確な文字列
- 分散状態（mon／ito／nuno）・aiueos への配線・決済は、第 1 スライスのとおり未実装。
- **kotoba + amu だけの方向（JUN-295）**: amu#1470（状態 64 KiB）と amu#1471（イベント値 1 KiB、file／storage／download が無い）が、1 年分の帳簿と取り込み・書き出しを止める。JSON の形式は amu#1469 に当たる。判断は guest と parity 表に置いてあるので、移植でそのまま使える。

### 次の一手（第 2 スライスの後）

1. 公開（network-awai/cloud-itonami の sites.edn、app org）と登録（itonami-registry の `mcp/kaikei`）。→ 済み（JUN-304）
2. 第 3 スライス: 請求書（QBO・Xero の Invoice、Zoho Invoice・FreshBooks、freee／MF、適格請求書）。→ 下の節（JUN-321）
3. 第 4 スライス: 明細・経費・AP（CSV／OFX、Ramp・Expensify・Brex、BILL）と仕訳候補。→ 下の節（JUN-327）
4. QBO の Journal／General Ledger の帳票の形を固定して、帳簿の全体を読む。
5. ブラウザの判定を wasm guest に寄せる（parity 表はそのまま回帰テストになる）。


## 第 3 スライス（2026-10-22、Linear JUN-321）

請求書を、ブラウザの中だけで作り・取り込み・書き出し、適格請求書の記載事項を検査して、
売掛金・買掛金の仕訳として計上する。設計の承認はオーナー（2026-10-22）:

- 画面で作る・直す・印刷するまで入れる（送付はしない）。
- 入金・支払の消込は第 4 スライス（明細の取り込みと照合）に回す。第 3 では取り込み元の
  入金済み・未回収の額を表示するだけ。
- Zoho Invoice と FreshBooks は読むだけ。

国税庁の登録番号の照会（公表サイトの Web-API）、メールでの送付、Peppol は外部
operation で、共通ブローカー（`kotoba-lang/wasm-webcomponent/src/kotoba-client-runtime.js`、
未着地）が要るので行わない。

### 値モデル

db に `:invoices`・`:business`（自社の名称・登録番号）・`:invoice-settings`（経理方式・
端数処理の既定・科目）を足した。kaikei.ledger.v1 には任意のキー（`invoices`・`business`・
`invoice_settings`）として入り、版は v1 のまま。形は `src/kaikei/invoice.cljk` の docstring。

- 金額は最小通貨単位の整数。数量と単価は 10 進の文字列のまま持つ（表示と往復のため）。
- 税率は basis points（1000 = 10%）。免税・非課税・不課税は税率 0 で `:category` が区別する。
  8% の軽減と 8% の標準は、税率の数が同じでも区分が違うので別に丸める。
- `:stated` は取り込み元が書いていた税率ごとの税額。仕訳には書かれた額を使う（請求書は
  発行したとおりに記帳する）。売上の請求書で kaikei の計算と違えば検査で知らせる。
- 取り込みでは、書かれた税額を再現する端数処理の向き（切捨て → 四捨五入 → 切上げ）を
  請求書ごとに選ぶ（向きは任意。国税庁 Q&A 問 57）。どれでも再現できなければ差を出す。

### 数の規則（guest）

`[rate amount] × n` の buffer に、`rate-base` `rate-tax` `invoice-tax` `invoice-total`
`rate-net` `tax-share` `invoice-buffer-valid?` `registration-format?` `deduction-percent`
を足した（式は guest の docstring）。

- 税率ごとの消費税額は、税率ごとに合計した対価に 1 回だけ掛けて丸める。税抜は
  合計 × rate / 10000、税込は 合計 × rate / (10000 + rate)（消費税法施行令 70 条の 10、
  基通 1-8-15）。
- `tax-share` は行への割り当て: 他の行は行の税額を切り捨て、差は同じ税率でいちばん
  大きい行（同額なら上の行）が持つ。freee が取引を起こすときと同じ規則（freee ヘルプ
  23500770784153）。仕訳を科目ごとに分けるときと、Xero の `LineItem.TaxAmount` に書く
  ときに使う。
- 掛け算は base = a·d + b に分けて a·rate + R(b·rate / d) とし、guest の i64 と adapter の
  JS の数（2^53 まで正確）で同じ値にする（9×10^14 の行で確かめた）。
- `registration-format?` は「T」＋数字 13 桁（国税庁 Q&A 問 18、公表サイトのリソース
  定義書）。全角→半角と T の後の「-」の除去は adapter が先に行う。法人番号の検査用数字は
  使わない（個人事業者の登録番号に当てはまるという一次資料が無く、公表サイトの Web-API も
  形しか検査しない）。
- `deduction-percent` は仕入税額控除の割合: 適格なら 100、そうでなければ経過措置
  （国税庁 Q&A 問 113、令和 8 年 5 月改訂）で 2026-09-30 まで 80、2028-09-30 まで 70、
  2030-09-30 まで 50、2031-09-30 まで 30、以降 0。

### 適格請求書の検査

法 57 条の 4 ①の 6 項目（発行者の名称と登録番号、取引年月日、内容と軽減税率の旨、
税率ごとの対価と適用税率、税率ごとの消費税額、受け取る事業者の名称）の欠けを、請求書
ごとに「要確認」として出す。売上の請求書は自社が発行者、受け取った請求書は取引先が
発行者。適格請求書であることは保証しない。登録番号の無い受け取った請求書には、経過措置の
割合を表示する（控除できない分の振替はしない）。

### 計上

画面の「帳簿に計上」・MCP の `kaikei_invoice_post` で仕訳を起こす。取り込んだだけでは
起こさない（Xero の Journals を取り込んだ帳簿には、請求書の仕訳がもう入っているため）。

- 税抜経理（既定）: 売上は 借 売掛金 ／ 貸 科目・税率ごとの税抜 ／ 貸 仮受消費税（税率
  ごと）。仕入は左右が逆で仮払消費税と買掛金。税込の請求書の税抜は、行の税込から
  `tax-share` を引いたもの。税込経理では税の行を起こさない。
- 仕訳の origin は `{:format :invoice :invoice-id …}`。計上したかはこの仕訳があるかで
  決まる。取消にすると仕訳を消し、直すと計上し直す。
- 同じ請求書の仕訳が帳簿にあれば計上しない（Xero の Journals の SourceID を origin に
  残すようにした）。源泉徴収のある請求書は計上しない。
- 生成した仕訳を MF・freee・弥生に書き出すときは、全行の税区分を「対象外」と書いて
  注記する。消費税はもう仮受・仮払の行に分けてあり、税区分を空にすると取り込み先が科目の
  既定の税区分で税を計算し直して二重になるため。

### 形式（請求書）

| id | 形式 | 読み | 書き | 形の正本（2026-10-22 に確認） |
|---|---|---|---|---|
| `kaikei-json` | kaikei.ledger.v1（invoices・business・invoice_settings を含む） | ○ | ○ | kaikei |
| `xero-invoices-json` | Xero の Invoices（ACCREC・ACCPAY）。TaxRates・Accounts が同じ JSON にあれば引く | ○ | ○ | XeroAPI/Xero-OpenAPI `5a115f3`（Invoice L22386、LineItem L20731、TaxRate L25200）、Xero developer docs（invoices、Rounding in Xero） |
| `qbo-invoices-json` | QuickBooks Online の Invoice・Bill（query の応答） | ○ | ○ | intuit/QuickBooks-V3-Java-SDK `c4d5dfa`（Finance.xsd の Invoice L5803、Bill L9498、TxnTaxDetail L5094）、Intuit developer docs（invoice、bill、sales tax） |
| `xero-invoice-csv` | Xero の customer invoices 取り込み CSV | ○ | ○ | Xero Central「Import customer invoices」（英・米・豪） |
| `xero-bill-csv` | Xero の bills 取り込み CSV | ○ | ○ | Xero Central「Import bills and credit notes」（英・米） |
| `qbo-invoice-csv` | QuickBooks Online の invoices 取り込み CSV（売上の請求書） | ○ | ○ | QuickBooks Help「Import multiple invoices at once」（米・英）、Intuit の PDF（2018） |
| `freee-invoice-csv` | freee請求書 の帳票 CSV インポート（請求書。本文と明細の行、47 列） | ○ | ○ | freee ヘルプ 18895523266841 の添付フォーマット |
| `freee-invoice-json` | freee請求書 API の invoice | ○ | ○ | freee/freee-api-schema `ac1acd4` の `iv/open-api-3/api-schema.yml`（L5887） |
| `mf-invoice-csv` | MF クラウド請求書 の CSV 一括追加（縦並び） | ○ | ○ | MF ガイド「帳票をCSVアップロードする方法」（do019） |
| `mf-invoice-json` | MF クラウド請求書 API v3 の Billing | ○ | ○ | `iv_web_api.yaml` 3.6.0（sha256 `74a681dd…`、Billing L1773） |
| `zoho-invoice-json` | Zoho Invoice API v3 の invoice | ○ | — | Zoho の OpenAPI の zip（`invoices.yml` sha256 `53e03d28…`） |
| `freshbooks-invoice-json` | FreshBooks の invoices・bills | ○ | — | FreshBooks の API の文書（invoices・bills）、freshbooks-nodejs-sdk `f1e2d61b` |

- **Xero**: 行ごとに 2 桁で丸めて足す（「Rounding in Xero」）ので、取り込んだ売上の請求書は
  日本の規則と差が出ることがある。`TaxType` は組織ごとのコードで、税率は `TaxRates` の
  `EffectiveRate` にある。書き出しでは Xero から来ていない行に kaikei の仮のコード
  （`KAIKEI-10`・`KAIKEI-8-REDUCED`・`KAIKEI-EXEMPT` など）を書いて `TaxRates` を添える
  （読み戻すと同じ税率に戻る。Xero に入れる前に組織の TaxType に置き換える）。
  `TaxAmount` には `tax-share` の額を書く。DRAFT・SUBMITTED は下書き、AUTHORISED は発行済み、
  PAID は入金・支払済み、VOIDED・DELETED は取消。支払済みは AUTHORISED と書く（支払いは
  Xero で別に登録する）。クレジットノート・前受・過払いと、帳簿と違う通貨の請求書は数えて飛ばす。
- **QBO**: 税は `TxnTaxDetail.TaxLine` が税率ごとに持つ（課税の行の合計に掛ける）。行の税率は、
  同じ `TaxCodeRef` の行の合計が `NetAmountTaxable` と一致する TaxLine から決める（推測は
  しない）。1 つの税コードに TaxLine が 2 つ以上当たる請求書（米国の税のグループ）は飛ばす。
  `TaxInclusive` でも `Line.Amount` は税抜で、すべての課税の行に `TaxInclusiveAmt` があれば
  税込で読む。取消は金額 0 で `PrivateNote` が Voided で始まるもの。書き出しの
  `TaxCodeRef` は QBO から来た行だけ value を持ち、どの行にも name（「10%」「8%（軽減）」）を書く。
- **CSV**（Xero・QBO・freee請求書・MF クラウド請求書）は状態の欄が無ければ下書きで読む（計上の前に
  確かめる。Xero も取り込んだ請求書を下書きにする）。税込・税抜の欄が無い形（Xero・QBO・MF の CSV）は
  税抜として読み、書き出しでは税抜にする（税込の請求書は行の税込から `tax-share` を引く）。税率は
  税率の表示名の %（「20% (VAT on Income)」）か区分の名前（非課税・不課税・免税）から読み、読めなければ
  税率不明にする（推測しない）。
- **freee請求書・MF クラウド請求書**は明細の金額の欄を持たないので、単価 × 数量 を取り込み元の明細行の
  端数処理で丸める（筆算で正確に）。どちらも売上の請求書だけで円だけ。自社の登録番号は先方の設定
  （freee の template、MF の registration_code）から来るので、取り込みでは帳簿に自社の設定が無ければ
  使う。どちらの API の形にも下書きの印は無い。
- **Xero の bills の CSV** は customer invoices と見出しが同じなので、自動の判定では売上の請求書として
  読む（受け取った請求書は形式を選ぶ）。
- **Zoho Invoice**: 税額は請求書の `taxes[]` だけにあり、行は税率だけ。請求書全体の値引き・送料のある
  請求書は飛ばし、`adjustment` は不課税の行にする。**FreshBooks**: `taxAmount1` は税の率で、税額の欄は
  無い。1 行に 2 つの税・請求書全体の値引き・削除（vis_state 1）は飛ばす。
- 取り込み元が税額を書いていて丸めの向きを書かない形（Xero・Zoho・MF の CSV など）は、書かれた額を
  再現する向きを選ぶ。どの向きでも再現できなければ、検査で差を出す。
- **登録番号**の受け皿は QBO・Xero・Zoho・FreshBooks の形に無い（kaikei-json だけが持つ）。

### 未確認のまま実装したもの

- Xero の丸めの向き（「rounding to two decimal places」としか書かれていない）と、数が
  文字列で来る文書の例。
- QBO の売上の税が入る勘定と、取消の Bill の形（取消の操作が文書に無い）。
- QBO の `TxnStatus` の Draft が請求書の応答に現れるか（書き出しの下書きはこれで表す）。
- Xero の取り込み CSV の見出しの正確な文字列（`*` の有無、空白の有無、列の順。テンプレートはログインが要る）。
- QBO の invoices の取り込み CSV の今の見本の見出し（2018 年の PDF を使った）と、英国版の税の列の名前
  （kaikei は `ItemTaxCode` と書く）。
- freee請求書 の CSV の文字コード（ヘルプの本文は BOM 付きの UTF-8、添付のファイルは BOM なし）と、
  7 列目の名前（フォーマットは「支払予定日」、見本は「予定日」）。CSV の書き出しは文書に無い。
- MF クラウド請求書 の CSV の見出し（2023 年の画面写しから読んだ）、日付の形、ダウンロードの CSV の列。
  MF が消費税を税率ごとに 1 回丸めると明言した文書は無い。
- MF の API の応答の日付（例は `/` 区切り、仕様は date）。
- freee請求書 の API が税率ごとに 1 回丸めるか（ヘルプの帳票の説明はそう言う）。
- FreshBooks の行の amount が税込か、税の丸め、bill の取引先の名前の欄（`vendor.vendor_name` を読む）。
- Zoho の見本は数が合わないものがある（total・balance の型も宣言と見本で違う）。

### 実測（2026-10-22）

- **guest**
  - `amu check aiueos/kaikei_journal.cljk` → `:ok true`, `:effects #{}`。
  - `amu test aiueos/kaikei_journal.cljk --fuel 4096` → **84/84 passed**（test 28 本 × `[:jvm-kir :js :wasm]`）。
    期待値を 1 つ変えた写し（`tax-share` の 211 → 212）は 81/84 FAILED で、3 target とも落ちる。
  - `amu compile … --policy aiueos/kaikei_journal.policy.edn` → 16,412 bytes（sha256 `fefc27ec…d003`）。
    別の出力先にもう一度作って同じ sha256。
  - **wasm parity**: `node test/guest_parity.mjs` → **110/110 rows match**（第 2 スライスの 52 行 + 請求書の 58 行）。
  - 例の出所: 国税庁 Q&A 問 57（税込 60,000・40,000 → 5,454 + 2,962）、freee ヘルプの配分
    （426・2,100・1,885・220 → 463、2,100 の行が 211）、Xero の「Rounding in Xero」（行ごと 11.44、
    税率ごと 11.45）。
- **adapter・形式・画面・MCP**: `npm test`（kbb）→ **86 tests, 816 assertions, 0 failures**（2 つ目の PR の後）。
  形式ごとの取り込み・往復と、kaikei → Xero JSON → QBO JSON → freee JSON → MF JSON → MF の CSV → kaikei の
  連鎖で、番号・日付・取引先・税率ごとの対価と税額・合計が保たれること。
- **MCP**: `bin/kaikei-mcp` を `/` から起こし、`kaikei_invoice_totals` が Q&A 問 57 の 8,416 を返す。
- **itonami-agent の MCP クライアント**（`kotoba-lang/itonami-agent` main `0c05574` の `itonami.agent.mcp`、
  `git archive` で取り出したもの）: `discover` が 8 つの tool を返し（errors は空）、`kaikei_invoice_totals`
  が 8,416・100,000、MF の Billing の JSON を `kaikei_import` → `kaikei_invoice_post` で 2 件計上して貸借一致。
  不正な入力は tool の error として返る。
- **ブラウザ**（built-in browser、ローカルの静的サーバ、`scripts/build-site.cljk` の公開物）:
  - サンプル → 検査の欄に「未計上 2 件」「記載事項の欠け 1 件」→ 請求書の詳細（6 項目）→ 計上 →
    印刷（`window.print` を差し替えて呼び出しを確かめ、印刷用の CSS を画面に当てて請求書だけが
    残ることを見た）→ 新しい請求書を作る（10% 30,000・8%（軽減）1,620 → 消費税 3,129、合計 34,749）→
    保存 → 未計上をすべて計上 → 試算表で 売掛金 424,069・仮受消費税 8,449・仮払消費税 330、貸借一致。
  - 再読み込みで IndexedDB から請求書 4 件・仕訳 13 件・自社の設定が戻る。
  - Xero・QBO の請求書 JSON・kaikei-json・MF の書き出しを Blob で受け、Xero の JSON を取り込み直すと
    4 件とも同じ請求書として飛ばされる。
  - 375px 幅で 10 の画面（帳票 5・請求書の一覧・詳細・編集・設定・取り込み）とも横スクロールなし。
  - 2 つ目の PR の後: Shift_JIS の MF クラウド請求書の CSV・freee請求書 の JSON・Xero の請求書の CSV を
    取り込み（形式は自動の判定、USD の 1 件は飛ばす）、未計上をすべて計上（下書きと取消を除く 3 件）、
    freee・MF の CSV・Xero の bills の CSV・MF の JSON を Blob で書き出す。読むだけの Zoho・FreshBooks は
    書き出しの選択肢に出ない。375px で一覧・詳細・取り込み・試算表とも横スクロールなし。
  - network は 127.0.0.1 だけ（https の要求は 0）。console のエラーは調べるために打った式のものだけ。
  - built-in browser の pane が隠れていると `requestAnimationFrame` が止まり、再読み込みの後の描画が
    進まない（第 2 スライスの「測れなかったもの」と同じ原因）。描画の確認は、`requestAnimationFrame` を
    setTimeout に差し替える 1 行を先頭に入れた調べる用の写し（公開物には入れない）で行った。


## 第 4 スライス（2026-10-23、Linear JUN-327）

利用者が自分で落とした明細（銀行・カード）を取り込み、第 3 スライスの請求書の消込・
帳簿の仕訳との照合・口座の間の振替を突き合わせ、過去の仕訳と利用者の規則から仕訳の
候補を出す。どれも提案で、利用者が承認するまで計上しない。設計の承認はオーナー
（2026-10-23、判断 1〜6 を推奨のとおり）:

- 売手負担の振込手数料（入金が手数料の分だけ少ない）は、科目「支払手数料」・税は売上の
  対価の返還（その請求書の税率。国税庁インボイス Q&A 問 30）。取引先ごとに課税仕入へ変えられる。
- 一次資料の無い銀行・カードの CSV は、汎用の CSV（列の割り当てと型）で読む（2 つ目の PR）。
- 取り込んだ過去の仕訳からも学ぶ。
- 取り込んだ元のファイルを端末に保存する（2 つ目の PR。準拠は主張しない）。
- Ramp・Brex・Expensify・BILL は読むだけ（3 つ目の PR）。

口座連携（銀行・カード会社への接続。電子決済等代行業、銀行法 2 条 21 項）・支払の実行・
遠隔の推論はしない。共通ブローカー（`kotoba-lang/wasm-webcomponent/src/kotoba-client-runtime.js`）は
未着地のまま。

### 値モデル

db に `:statement-accounts`（口座）・`:statement-lines`（行）・`:rules`（利用者の規則）・
`:statement-settings`（手数料の扱い・窓の日数・規則の強さの閾値・確かめた振込名義）を足した。
kaikei.ledger.v1 には任意のキー（`statement_accounts`・`statement_lines`・`rules`・
`statement_settings`）として入り、版は v1 のまま。形は `src/kaikei/statement.cljk` の docstring。

- 行の金額は口座の持ち主から見た向き（入金が正、出金が負。カードは利用が負、返金が正）。
- 計上したかは、帳簿の仕訳の origin（`{:format :statement :line-id … :allocations […] :fee …}`、
  振替は `:line-ids`）で決まる。行の側には持たない。照合（帳簿にもうある仕訳と結ぶ）は
  行の `:match`。
- 学んだ規則は保存せず、帳簿から毎回作る（`statement/learn`）。
- 請求書の残額 = 取り込み元の未回収額（無ければ合計）− 帳簿にある消込の割り当て。請求書の
  `:status` は書き換えない。
- 取り込みの重複: 一意な id（OFX の FITID）があれば口座とそれで、無ければ内容（口座・日付・
  金額・摘要・残高）と同じ内容の何番目かで判定する。OFX の CORRECTFITID（REPLACE・DELETE）は
  同じファイルの中の行にも当てる（計上・照合した行は消さずに警告）。
- 取り込み元の id（a1・l1・e1・i1）は、帳簿で使われていなければ保つ（MCP の tool の間で帳簿
  JSON を受け渡しても id が変わらない）。振り直したときは、仕訳の origin と行の `:match` も
  合わせる。仕訳の id も保つようにした（第 3 スライスまでは振り直していた）。

### 数の規則（guest）

明細の buffer `[amount balance] × n` と、未消込の請求書の buffer `[open] × n`（期日の順）に、
`days-between` `consumption-rate` `aging-bucket` `running-break` `closing-gap`
`line-buffer-valid?` `payment-kind` `cover-count` `allocate` `date-fit` `match-level`
`suggestion-level` を足した（式は guest の docstring）。

- `consumption-rate` は確かめた表だけを持つ: 2014-04-01 から 8%、2019-10-01 から 10%・
  軽減 8%（財務省「消費税率の引上げと使途の明確化」、国税庁タックスアンサー No.6303）。
  2014-04-01 より前と、2027-04-01 からの飲食料品は -1（国税庁リーフレット 令和 8 年 9 月の
  「飲食料品に係る２年間の消費税率引下げ」は、法案が成立した場合のもの）。-1 のときは
  税率を選んでもらう。
- `match-level` は点数の重みではなく段の順（Xero・QBO・freee・MF のどれも点数の付け方を
  公開していない）: 3 有力（金額が合い、摘要に請求書番号があるか振込名義が一致）、
  2 中（名義の前方一致。銀行の欄の長さ 30・40・48 文字での切り詰め）、1 弱い（金額だけ、
  または一部・過入金で番号か名前が合う）、0 出さない。部分一致の名前は 0。
- `cover-count` は 1 件の入金で同じ取引先の請求書を期日の順の先頭から払う数。組み合わせの
  探索はしない（MF の照合のシミュレーションは候補が複数あると無作為に 1 つを出す）。
- `suggestion-level` は学んだ規則の強さ: 2 回以上・割合 70% 以上・金額が過去の幅
  （最小の半分〜最大の 2 倍）の中なら強い、ほかは弱い。

### 消込・照合・振替・規則（adapter、`src/kaikei/statement.cljk`）

- **名前の正規化**: NFKC、ひらがな → カタカナ、小さいカナ → 大きいカナ、ヲ → オ、長音・
  ハイフンの類を 1 つに、中黒・ピリオド・空白を除く、法人略語を 3 つの位置（`カ)` `(カ)`
  `(カ`）で除く（三井住友銀行・77 銀行の表）、漢字の会社の種類を除く、先頭の数字
  （振込依頼人番号）を分ける。全銀ネットの ZEDI ガイダンス表 2-4 と、三菱 UFJ・三井住友・
  77 銀行の表の違いをまとめるため。確かめた消込の振込名義は取引先の別名として覚える。
- **候補**: 請求書（入金は売上、出金は仕入。発行日より前と 期日 + 90 日より後は除く）、
  帳簿にもうある仕訳（口座の科目に同じ向き・同じ額、7 日以内。照合済みと明細から起こした
  仕訳を除く）、別の口座の逆向き同額の行（3 日以内）、利用者の規則（並べた順に最初に
  当たったもの）か学んだ規則。最初から選ぶのは「有力」が 1 件だけのとき。
- **学ぶ元**: 明細の口座の科目に 1 行だけあり、税の科目を除いた相手が 1 つの仕訳。消込・
  振替・請求書の計上の仕訳は除く。鍵は正規化した摘要から数字と振込の語を除いたもの＋向き＋
  帳簿の科目。税率そのものは学ばない（税の区分だけ。税率は日付から）。
- **利用者の規則**: 摘要の完全・前方・後方・部分一致、向き、口座、金額の幅。規則の文字列と
  摘要は学んだ規則の鍵と同じ形にして比べる。提案した回数とそのまま承認された回数を数える。
  部分一致の規則が過去に別の科目へ記帳した摘要にも当たるなら知らせる。

### 計上

- 承認した行だけを計上する（画面の「この候補で計上」「計上する」「選んだ行を計上する
  （有力の候補だけ）」、MCP の `kaikei_statement_post`）。
- 請求書の消込: 入金は 借 預金 ／ 貸 売掛金、支払は 借 買掛金 ／ 貸 預金。消込む請求書が
  まだ計上されていなければ、先に計上する（売掛金・買掛金が立たないまま消込むと逆の残高に
  なるため。結果に「請求書 … も計上しました」と出す）。計上できない請求書（下書きなど）は止める。
- 手数料の差額（判断 2）: 既定は 借 支払手数料（税抜）／ 借 仮受消費税、税区分「売上の
  対価の返還 10%」（その請求書の税率。8% と 10% の混ざった請求書は Q&A に割り当ての定めが
  無いので税率を選んでもらう）。取引先ごとに「課税仕入 10%」（適格請求書は「未確認」）、
  科目「売上値引高」にできる。差額が 1 万円以上なら返還インボイスが要る旨を出す（消費税法
  57 条の 4 ③ただし書、施行令 70 条の 9 ③二の外）。支払から手数料を差し引いた仕入の消込は、
  仕入の対価の返還として貸方に起こし、取適法の注意を出す（Q&A 問 29 の注）。
- 科目を選んだ計上: 明細の額は税込として、`rate-tax`（税込、1 回の端数処理）で税を分ける。
  課税仕入の行の適格請求書は「未確認」（規則か過去の仕訳が「適格」と言うときだけ「適格」）。
  検査の欄に「適格請求書の有無を確かめていない課税仕入の仕訳」を数える。
- 振替: 借 入金の口座の科目 ／ 貸 出金の口座の科目。2 行で 1 つの仕訳。
- 照合は仕訳を起こさず、行と帳簿の仕訳を結ぶだけ。
- 明細から起こした仕訳を MF・freee・弥生に書き出すときも、請求書と同じく全行の税区分を
  「対象外」と書く（消費税はもう仮受・仮払の行に分けてあるため）。

### 残高の照合と年齢表

- 口座ごとに、明細の最後の残高（行の残高か OFX の LEDGERBAL）と、同じ日の帳簿の科目の
  残高（借方 − 貸方）を並べる。残高の続き具合を `running-break` で見る（同じ日の中が
  新しい順の CSV は逆の順でも見る）。
- 請求書タブに、残額と、取引先ごとの年齢表（`aging-bucket`、期日から 30 日ごと）を出す。

### 形式（明細、1 つ目の PR）

| id | 形式 | 読み | 書き | 形の正本（2026-10-23 に確認） |
|---|---|---|---|---|
| `ofx` | OFX 1.x（SGML）・2.x（XML）、QFX・QBO | ○ | — | OFX Banking Specification 2.3（FDX、2020-10-16）と XSD、1.0.2・1.6 |
| `freee-statement-csv` | freee 会計の明細のテンプレート（銀行・カード） | ○ | ○ | freee ヘルプ 202847120・202847810 と添付のテンプレート |
| `mf-statement-csv` | MF クラウド会計の明細の取り込み | ○ | ○ | MF サポート im01・im02 |
| `xero-statement-csv` | Xero の明細の CSV | ○ | ○ | Xero Central「Import a CSV bank statement」ほか |
| `qbo-bank-csv` | QuickBooks Online の明細の CSV（3 列・4 列） | ○ | ○（3 列） | QuickBooks Help L4BjLWckq |

- 明細の形式の書き出しは口座ごと（画面の「明細」タブ、MCP の `statement_account`）。
- OFX: 葉の要素の終わりのタグを省いた 1.x も、2.x の XML も 1 つの読み方で読む。日付は
  DTPOSTED の先頭 8 桁（時差は書かれたまま）。小数点は `.` か `,`。CURRENCY の付いた行は
  換算されていないので取り込まない。保留の行（BANKTRANLISTP）は読まない。口座は金融機関
  （ORG-FID か BANKID）・口座番号の下 4 桁・種類で見分け、口座番号は下 4 桁だけを持つ。

### 未確認のまま実装したもの（明細）

- 日本の OFX の文字コード（仕様は USASCII・UTF-8 だけ）。取り込みは BOM → UTF-8 →
  Shift_JIS の順に試す。今 OFX を出す日本の銀行は見つからない（みずほは 2024-11-10 に廃止）。
  JCB（カード）は出す。
- Intuit の `INTU.*` の正本（私的なタグとして読み飛ばす）。
- Xero の明細の CSV の見出しの正確な文字列（`*`・Cheque／Check）。読みは揃えてから見る。
- MF の明細の取り込みの見出しのバイト列（見本はログインの後でしか落とせない）。
- freee・MF が受ける文字コード。
- QBO の 4 列の例の向き（Intuit の表のとおりに読み、書き出しは 3 列だけ）。
- 利用者が落としたファイルだけを読むソフトが電子決済等代行業の外だと直接に書いた金融庁の
  一次資料（パブリックコメントの回答 2018-05-30 No.29 がいちばん近い）。
- 8% と 10% の混ざった請求書の手数料の差額の割り当て（Q&A に定めが無い）。

### 実測（2026-10-23、1 つ目の PR）

- **guest**
  - `amu check aiueos/kaikei_journal.cljk` → `:ok true`, `:effects #{}`。
  - `amu test aiueos/kaikei_journal.cljk --fuel 4096` → **120/120 passed**（test 40 本 × `[:jvm-kir :js :wasm]`）。
    設計の段の試作（repo の外）で、期待値を 1 つ変えた写しが 3 target とも落ちることを 2 通り確かめた。
  - `amu compile … --policy aiueos/kaikei_journal.policy.edn` → 23,385 bytes（sha256 `2f2b1bd1…27be`）。
    別の出力先にもう一度作って同じ sha256。
  - **wasm parity**: `node test/guest_parity.mjs` → **192/192 rows match**（第 3 スライスまでの 110 行 + 明細の 82 行。
    明細の行は guest の test-* の式から写した）。
- **adapter・形式・画面・MCP**: `npm test`（kbb）→ **118 tests, 1128 assertions, 0 failures**。
- **ブラウザ**（built-in browser、ローカルの静的サーバ、`scripts/build-site.cljk` の公開物に
  `requestAnimationFrame` の差し替えを 1 行足した調べる用の写し）:
  - サンプル → 検査の欄に「未処理 5 行」「残高の合わない口座 1 つ」→ 明細タブ（明細の残高 977,650・
    帳簿の残高 1,003,500・差 −25,850）→ 有力の候補のある行を選ぶ（3 行）→ 計上 → Amazon の行を
    消耗品費で計上（10% で 1,000 + 100、適格請求書は「未確認」）・「規則にする」→ 家賃の行を
    弱い候補（過去の仕訳）で計上 → 差が「一致」。
  - INV-0001 の入金を、まだ計上していない請求書のまま消込む → 「請求書 INV-0001 も計上しました」、
    請求書タブの残額が「消込済み」。
  - 規則の欄に、足した規則（完全一致）と提案・承認の回数（1／1）、学んだ規則の一覧。
  - 再読み込みで IndexedDB から明細・規則・計上の状態が戻る。
  - OFX を貼り付けて取り込む → 口座「OFX 預金 ****4567」が増える（2 行）。
  - 明細タブから freee の明細の CSV を書き出す（Blob を読んで、テンプレートの形を確かめた）。
  - 375px 幅で、明細タブ（設定・規則・行の詳細を開いたまま）と請求書タブに横スクロールなし。
  - network は 127.0.0.1 と blob: だけ。console のエラーは無し。
