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

The independent review [KOTOBA-159](https://linear.app/kotobalabs/issue/KOTOBA-159)
is still in progress. The pinned revision is also affected by the known
late-dialog-close regression in [KOTOBA-158](https://linear.app/kotobalabs/issue/KOTOBA-158):
a delayed close event can incorrectly deny a following invocation. It fails
closed but can break multi-request synchronization. A separately reviewed
canonical fix and browser acceptance are required before connecting services.

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

On 2026-11-02 the upstream canonical fixture was also exercised in an in-app
browser against `127.0.0.1`: 42/42 automatic checks passed, denial caused no
new request, one approved anonymous GitHub GET returned 200, and a synthetic
click was refused before a real click executed a local fixture action once.
Invoking the same GET again displayed a fresh consent dialog; denying it was
correctly rejected. The fixture's allow-only handler records that deliberate
second denial as a failed allow test; the resource list contained only the
first GET. These results test the canonical fixture, not kaikei's consent UI.

For a kaikei-specific isolation probe, run
`python3 test/build-restricted-fixture.py <production-candidate> <empty-dir>`
and serve that directory on loopback; open `kaikei-host.html`. It inlines the
built candidate's scripts only for this diagnostic, verifies the canonical
runtime bytes, and mounts a synthetic no-operation guest. In this run 36
scripts produced fixture SHA-256
`61077bd209c865a1f1e24a5f135e5fee7912f8a4b642e5506c1a323bb4ead3d5`.
The app rendered and loaded its synthetic sample, but reported that saving
failed: the opaque sandbox lacked `allow-same-origin`, so `localStorage` was
inaccessible. This is not an acceptable production storage path. The host's
fixture broker is a no-operation stub; the probe does not establish secure
storage, signed publisher admission, service connectivity, or replay safety.
[JUN-771](https://linear.app/kotobalabs/issue/JUN-771) tracks a persistent,
isolated storage and recovery design. No user's data was used.

Before any real connection, validate the actual app descriptor and publisher
pins, isolate and qualify the trusted
host, obtain service-specific API and authorization details, declare exact
operations and CSP, and test deny/allow/replay and redirects in a real browser.
Do not publish or cut over on the basis of this staging candidate.

## 2026-11-22 re-pin (AWAI-3810)

`site/site.edn` and `test/client-runtime-stage.mjs` now pin `kotoba-lang/kotoba`
`a1b90e38c9e5334facfa993062e237299c70de10` (#1367, KOTOBA-159),
SHA-256 `d6f67c058c5c40fc56fe500648dc79704a2eee02d4af75fc17898aad1f560a75`.
That revision requires a `disclosure` for every operation (recipient legal name,
country, data, purpose, frequency, withdrawal; country-name and foreign-info-url
outside Japan), `scope: "lan"` for internal addresses, and mounts only a broker
made by `createClientOperationBroker`. The stage test checks those refusals.
The restricted, storage and consent fixtures now mount a canonical no-operation
broker and expect the new digest (they still expected the archived
`wasm-webcomponent` digest before). The GitHub and PayPay sandbox fixtures carry
no disclosure because their recipients are not confirmed, so the runtime refuses
them and they send nothing. kaikei still declares no operations; this remains an
inert staged asset, not host integration.

## 2026-11-22 re-pin to e7bcd2d7 (AWAI-3821)

`site/site.edn`, `test/client-runtime-stage.mjs` and the fixtures now pin `kotoba-lang/kotoba`
`ee75001ee44a9b793602d1549e5e977c4562a5fe` (#1370, with #1369), SHA-256
`e7bcd2d729ceeed3460cc766335a2ff4d0937f9af7a82b038c5df9d20e427ebe`. The dialog now also shows the
declared frequency, withdrawal place and foreign line in trusted-page-v1 and accepts an optional
`disclosure.note`. kaikei still declares no operations; this remains an inert staged asset.

## 2026-11-22 re-pin to 37e82633 (AWAI-3826)

Pinned `kotoba-lang/kotoba` `e58ae70b4bdc818b3feec767f7ac9908cd6e7a2c` (#1371: the dialog's links are in its
Tab cycle), SHA-256 `37e826338686eefbb2b9c7a731b73c53f7f5d6864158c0790edad60f25682d6d`. kaikei still declares no
operations; this remains an inert staged asset.
