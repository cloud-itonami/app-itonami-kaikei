# kaikei 会計 dapp — aiueos 上の分散型設計（itonami agent 前提）

状態: 設計 + 第 1 スライス実装（2026-10-19）。正本はこの文書。
追跡: Linear JUN-115。

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
| 判断コア（guest） | `aiueos/kaikei_journal.cljk` — journal-entry 検証 / trial-balance。`:effects #{}` の pure 計算 | **実装済み・実測**（下記） |
| アプリ記述子 | `aiueos/kaikei.edn`（`examples/apps/notes.edn` 形、`:aiueos/kind :app`） | **実装済み**。aiueos session/grant への配線は未実装 |
| appview adapter | `appview/.../cljs/src/kaikei/journal.cljk` — 同セマンティクスの map API。re-frame SPA 用 | **実装済み・実測**（kbb cljs.test） |
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
