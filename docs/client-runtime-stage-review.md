# Canonical client runtime: staging review (JUN-765)

This is a local preview candidate, not an integrated or qualified client host.
The source is `kotoba-lang/wasm-webcomponent` commit
`e00ae75e1c589f76b4f53a88a5e3256c98c9e162`,
`src/kotoba-client-runtime.js`, SHA-256
`7f760128c3a58098123c31ec3dd34b9c871932e3933f2c952facc4ab0e647212`.
The preview builder reads that exact path from Git and rejects a missing commit
or a digest mismatch. It does not load the module, create a consent host or
allow any external operation. `site.edn` uses the production generator's
`:client-runtime` asset declaration. Staging an asset is not host integration.

## Review boundary

The canonical source validates service origins, paths, methods and queries,
intersects declarations with requested and host-supported capabilities, and
starts with no eligible operations. Its consent host accepts a trusted click
for each invocation; denial sends no request. Requests are snapshotted,
credentials omitted, and redirects restricted and checked. These observations
are source review, not independent proof of production security.

The source requires a trusted shell: untrusted app JavaScript must not share
the document and consent handle. The restricted guest helper currently accepts
self-contained HTML, while kaikei's existing Scittle app consists of multiple
assets. Establishing a suitable host / guest boundary and complete CSP for
kaikei remains open. Do not attach the broker to the app's current page and
claim the boundary is enforced merely because the module is present.

The upstream `docs/evidence/client-runtime-browser-20261023.json` records
fixture checks including trusted consent, denial and one anonymous GitHub
request. It does not qualify live provider credentials, browser redirects,
kaikei's builder, or production deployment.

## Local checks

Build a preview using `scripts/build-site.cljk` with `KOTOBA_LANG` pointing to
the repository forest, then run `node test/client-runtime-stage.mjs <preview>
<wasm-webcomponent-repo>`. The test checks byte equality against the pinned Git
object, digest, absence from the HTML, an empty-operation descriptor, offline
CSP and refusal of a forged consent handle. A scratch copy with the expected
digest replaced by zeros must fail the preview build before writing the asset.
Neither check runs external requests or the interactive browser consent flow.

On 2026-11-02 the production generator at network-awai/cloud-itonami
`a219a36ddd05d6331cc7b1fc90bb40e2526e586b` was run from an isolated scratch
directory against this candidate. The output passed the same byte / inert-page
check; a zero-digest negative control failed with a digest mismatch. An initial
run from the generator checkout failed while resolving conflicting Git and
local dependencies for `io.github.kotoba-lang/edn`; the scratch run used the
same copied generator and an explicit source classpath. This is a local build,
not production deployment or host qualification.

Before any real connection, validate the actual app descriptor and publisher
pins, isolate and qualify the trusted
host, obtain service-specific API and authorization details, declare exact
operations and CSP, and test deny/allow/replay and redirects in a real browser.
Do not publish or cut over on the basis of this staging candidate.
