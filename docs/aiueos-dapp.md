# kaikei 会計 dapp — aiueos 上の分散型設計（itonami agent 前提）

状態: 設計 + 第 1 スライス（2026-10-19、判断コア guest）+ 第 2 スライス
（2026-10-22、5 社の形式・帳票・画面・MCP）。正本はこの文書。
追跡: Linear JUN-115（第 1）、JUN-304（第 2）。

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
| 判断コア（guest） | `aiueos/kaikei_journal.cljk` — 仕訳の検証 / 帳簿の貸借一致 / 区分・期間の純額・段階利益・B/S の照合。`:effects #{}` の pure 計算 | **実装済み・実測**（下記） |
| アプリ記述子 | `aiueos/kaikei.edn`（`examples/apps/notes.edn` 形、`:aiueos/kind :app`） | **実装済み**。aiueos session/grant への配線は未実装 |
| adapter | `src/kaikei/core.cljk` — guest と同名・同結果の判定 + 値モデル（帳簿・勘定科目・区分）+ 試算表・P/L・B/S | **実装済み・実測**（kbb、parity 表） |
| 形式 | `src/kaikei/ingest.cljk`・`export.cljk`・`compat/{native,xero,qbo,yayoi,mf,freee}.cljk`・`encoding.cljk`（Shift_JIS） | **実装済み・実測**（第 2 スライスの節） |
| 画面 | `src/kaikei/view.cljk`（純 hiccup）+ `site/app.cljk`（Re-frame / Reagent、scittle）+ `site/kaikei/page.cljk`（SSR の殻、DADS） | **実装済み・ブラウザで実測** |
| 状態 | IndexedDB（`itonami.kaikei` の `state`）。使えなければ localStorage。1 ブラウザに閉じる | **実装済み** |
| agent 統合（MCP） | `bin/kaikei-mcp` + `src/kaikei/mcp.cljk` — stdio MCP、tool 5 つ。pure | **実装済み・実測** |
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

1. 公開（network-awai/cloud-itonami の sites.edn、app org）と登録（itonami-registry の `mcp/kaikei`）。
2. 第 3 スライス: 請求書（QBO・Xero の Invoice、Zoho Invoice・FreshBooks、freee／MF、適格請求書）。
3. 第 4 スライス: 明細・経費・AP（CSV／OFX、Ramp・Expensify・Brex、BILL）と仕訳候補。
4. QBO の Journal／General Ledger の帳票の形を固定して、帳簿の全体を読む。
5. ブラウザの判定を wasm guest に寄せる（parity 表はそのまま回帰テストになる）。
