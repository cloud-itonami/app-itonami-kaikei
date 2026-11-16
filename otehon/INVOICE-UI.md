# AWAI-2973 — Otehon invoice UI integration

This owning product builds the exact shared invoice UI revision declared in
`invoice-ui-source.json`. It imports the canonical client-runtime module and the
existing Mail/Kaikei/dango/WNFS executor through the shared implementation; no
product-local verifier, consent broker or accounting math is copied.

```
node otehon/build-invoice-ui.mjs <pinned-apex-checkout> <canonical-kotoba-git> <output>
```

Install the shared checkout's lockfile dependencies first. The helper rejects a
wrong revision or tracked source changes, rebuilds local assets, verifies their
manifest and installs the product panel. The Kaikei output must be a fresh built
static site; Mail uses a new output directory. No live route, MX, mail send,
accounting database or deployment is changed. Host-less static previews allow
parsing only, and refuse organization mutations. A trusted local Otehon Desktop
connects via the exported `invoice-workflow/product.mjs:connectTrustedHost(host)`
capability. No untrusted postMessage/global credential bootstrap is added.

The shared browser qualification injects a synthetic trusted host and exercises
real domain/crypto APIs. Production credential enrollment, hardware Passkey,
Desktop embedding and user acceptance remain separately unqualified. These
static assets do not authorize an app-origin API/BFF or remote fallback.

The dependency is apex PR242, stacked after PR241. Merge in dependency order,
repeat final-head checks, and qualify the owning artifact before publication.

The owning app repository is public while apex is private. Its default
`GITHUB_TOKEN` cannot read that source. CI therefore requires a narrowly scoped
`AWAI_INVOICE_UI_SOURCE_READ_TOKEN` secret with Contents: read on **apex only**;
it is used only for the pinned checkout and not persisted. Missing credentials
fail the check explicitly, never skip the build or report success. No broad
personal token was copied into CI. Org-wide secret inventory was not available
to this session, so an existing suitable org secret remains unknown.
