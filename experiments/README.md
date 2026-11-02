# JUN-771: synthetic local-storage experiment

This is **not wired into kaikei**, not a broker, not a production host, and
must not handle real financial data. The first experiment uses the fixed IndexedDB name
`kaikei-jun771-synthetic-fixture` and one fixed key; it never opens, reads,
migrates or removes the existing `itonami.kaikei` database.

`test/atomic-ledger-fixture.html` separately uses the fixed test database
`kaikei-jun771-atomic-synthetic` with a fresh random key per run. It tests a
revision-checked write across synthetic ledger and file stores, concurrent
conflict rejection, rollback after queued writes, and file deletion in the same
transaction. This models only one synthetic file per ledger and leaves its
test records in the test origin. It is not a migration, production transaction,
guest authentication or a solution for older clients that write without a
revision check. Multi-file operations, quota, process termination, cross-tab
lifecycle and integration with the real kaikei model remain unqualified.

`test/legacy-version-fixture.html` creates a fresh synthetic database per run.
It holds a version-2 connection open, observes a version-3 upgrade blocked,
closes the old connection, verifies the two original values after upgrade, and
checks that reopening version 2 fails with `VersionError`. The test database is
retained on the test origin. This is not sufficient to block legacy kaikei:
the current main app falls back to localStorage when IndexedDB open or write
fails, so an old tab can continue editing a different state after the upgrade.
Application compatibility, existing connections and transactions, cross-tab
notifications, recovery and downgrade remain unqualified.

`test/build-legacy-version-probe.py PREVIEW NEW_OUTPUT_DIR` builds a second
isolated probe with `site/app.cljk` from pinned main revision `767104e0` and
the supplied preview's other assets, replacing the database and storage key.
Serve the output directory on a fresh loopback port,
open `seed.html`, then open `old-app/`. In one in-app browser, the old app
opened an empty editable ledger despite the version-3 synthetic ledger;
after loading the built-in sample, it showed the sample again after reload.
The old source selects localStorage after the version-2 open fails. The probe
does not establish production rollout behavior or safe reconciliation.

The experiment performs a read and a revision-checked update in one IndexedDB
transaction. The successful result is returned only on transaction completion;
stale revisions return a conflict and a UTF-8 limit of 65,536 bytes is enforced.
It rejects malformed stored records rather than silently starting over. This
is a model for conflict handling, not a complete ledger or file store.

From the repository root, serve the repository on loopback with a local static
server and open `test/local-ledger-fixture.html`. The first button checks that
two concurrent writes with the same expected revision yield one success and
one conflict, that an over-limit value is rejected, and that the committed
value remains. Reload and press the second button to check recovery.

`test/hosted-ledger-fixture.html` is a separate synthetic, opaque-origin
`sandbox="allow-scripts"` iframe and a test-only MessageChannel to a parent
that calls the same experiment. In an in-app browser on 2026-11-02 the guest
saved and reloaded a synthetic value through that channel; a fixture probe
also observed rejection of direct parent-DOM, localStorage and external fetch
access. Its fixture protocol now rejects malformed or replayed messages,
out-of-order IDs, transferred ports, overly large strings and a flood of
pending requests. `node --test test/local-ledger-port-fixture.test.mjs` covers
these refusals. The fixture closes its port after a subsequent iframe load;
an `about:blank` navigation showed the disconnected state in the browser.
Closing the fixture port now signals cancellation to the IndexedDB adapter.
In the in-app browser, a test hook closed the port immediately after a
synthetic `put` was queued; the transaction aborted and the prior value and
revision remained. A separate active-transaction abort test checked the same
property without a port. The hook deliberately forces one timing and does not
prove behavior for every race or crash. The corresponding Node port test
fails against the previous version as a negative control.
`test/sibling-port-fixture.html` separately sends a fake port from one sandboxed
sibling to another. In one in-app browser, the target rejected it based on
`event.source` and accepted the host's port; `?unsafe=1` disables that check as
a test-only negative control, where the fake port received the read request.
This tests a small synthetic guest, not the generated kaikei guest, publisher
authentication, navigation races, cross-origin delivery or egress.
The local server supplied only static test files; no real provider or
account was contacted. Browser-local synthetic test data may remain in the test
database on the loopback origin.

`test/build-kaikei-storage-probe.py PREVIEW EMPTY_OUTPUT_DIR` builds a separate
diagnostic fixture from a prebuilt kaikei preview. It checks the staged runtime
digest, inlines the preview scripts, and replaces only the generated guest's
state-store adapter. The canonical runtime mounts the modified guest as an
opaque iframe; a test-only parent MessageChannel connects it to a different,
fixed synthetic IndexedDB database. The digest is calculated from the modified
artifact by the fixture itself, and the revision is synthetic: neither proves
publisher identity or release admission. Original-file storage is refused.

The opt-in `--legacy-empty`, `--legacy-present` and `--legacy-failure` modes
modify only the generated test guest. The synthetic host reads a fixed test
localStorage key and includes that value in its test ledger-read response;
the guest uses that response in place of direct localStorage access. The host
never reads the actual kaikei key, and does not remove the synthetic legacy
copy. These modes model only the initial handoff, not guest authentication,
origin migration, conflict resolution, or a production storage protocol.
With the combined #14/#15 candidate, one in-app browser showed an empty editor
when no synthetic legacy existed, a 123/123 trial balance for a synthetic old
ledger, and a load warning with editing stopped on simulated read failure.
After adding the built-in sample to the synthetic old ledger and reloading,
the fixture restored a 767,623/767,623 trial balance and warned that the old
copy remained. The host and guest are test-modified and self-digested; no real
data, actual provider, or publisher admission was exercised.

On 2026-11-02, an in-app browser on loopback loaded the actual generated kaikei
UI, saved its built-in sample, and recovered the sample trial balance after a
page reload (767,500 on each side). With two tabs opened on the same sample,
saving again in the first and then the second produced a visible save error in
the second. The existing `site/app.cljk` localStorage fallback masked the
underlying conflict with a sandbox localStorage error; the UI did not explain
how to resolve it. The payloads were identical, so this observation alone does
not prove that distinct competing edits are preserved. Same-guest concurrent
requests and all navigation and crash races remain unqualified. The test
used synthetic data only and did not exercise provider consent or access.

The subsequent `site/app.cljk` change keeps the selected IndexedDB backend on
write failure and surfaces that failure instead of silently reporting success
from a fallback store that the next IndexedDB load would not read. A repeated
two-tab synthetic test displayed `fixture write conflict` rather than the
sandbox localStorage error. This diagnostic uses an injected test adapter; it
does not add conflict detection to the existing production IndexedDB store.
The initial-load localStorage fallback remains. Real quota failures, asynchronous
save-result ordering, different competing edits and conflict recovery still need
dedicated validation before release.

If persisted ledger text is malformed or lacks a map-valued `:data`, the
candidate `site/app.cljk` now stops the editor and displays a recovery warning
instead of silently opening an empty ledger. In an in-app browser the
`--corrupt-ledger` probe caused the warning and showed no editing controls;
the earlier app candidate opened an empty editable ledger for the same
synthetic input. A normal empty store and the built-in sample's save/reload
also worked in the synthetic bridge. This is not comprehensive schema or
corruption recovery. The injected corrupt value and all stores used in the
probe are synthetic.

The candidate also stops editing if the primary IndexedDB read fails, rather
than assuming that an absent or older localStorage value is the current book.
The `--read-failure` synthetic bridge probe showed the warning and no editor;
the earlier candidate opened an empty editor for the same failure, while a
successful empty read still opened normally. This intentionally removes the
previous ability to continue editing via localStorage when IndexedDB cannot be
read, even for a browser that only ever used localStorage. If legacy
localStorage is readable, the candidate now offers an explicit, read-only raw
EDN backup without treating it as the current book. The file may be stale and
does not contain original attachments. Legacy localStorage is still read if
IndexedDB opens successfully and has no ledger. Real IndexedDB failures and
legacy migration require further browser validation before release.

`test/build-legacy-backup-fixture.py PREVIEW NEW_OUTPUT_DIR` makes a synthetic
preview that seeds localStorage and forces the IndexedDB read to reject. Serve
only on an isolated loopback origin: it writes a fixed test value there. On
2026-11-02, the in-app browser displayed the recovery warning and backup button;
the downloaded EDN exactly matched the synthetic source. The test used a
normal top-level page, not the restricted iframe, whose download permission and
storage access still need a separately reviewed host solution. No real ledger,
attachment restoration or automatic migration was tested.

The candidate recovery screen additionally offers a user-triggered conversion
to the existing kaikei JSON import format, preserving the raw EDN separately.
Using `--sample`, the in-app browser produced a synthetic file with 10 journal
entries, 3 invoices, 1 statement account, 5 statement lines and 1 rule; its
bytes matched the existing native exporter for that sample. Re-import into the
model preserved the sample's currency, accounts, entries, statement accounts,
statement lines and rules, but exact invoice-map equality initially failed: a
stored explicit `:reduced? false` was omitted by the JSON writer/reader.
The candidate now preserves boolean true, false and absence for invoice lines
and stated tax rows. After that change the same sample exported by the browser
and re-imported in the local adapter matched all seven tested model fields,
including the invoices; the old implementation fails the new regression test.
The screen still warns that other values and UI settings may be lost; this is
not a lossless recovery or validation of all fields. `--invalid` confirmed malformed
EDN reports an error and keeps the raw backup option. Original files are not
included, and actual user data, recovery import UI, storage write and migration
remain unqualified.

The diagnostic host now adds `frame-src 'none'` before loading the guest.
In a 2026-11-02 in-app browser test, an opaque synthetic guest's attempted
cross-origin self-navigation reached the loopback destination without parent
CSP; with parent `frame-src 'none'` as an HTTP header or early meta policy, the
browser blocked that specific navigation and the receiving server observed no
request. A separate scripted guest ran under the header, and the modified
kaikei diagnostic loaded its built-in sample under the meta policy. These are
limited tests in one browser, not proof that all egress is blocked. The parent
must itself be trusted, the policy must be delivered before the guest, and
other navigation schemes, requests, browsers, redirects, consent flows and
storage admission remain unqualified. No production host or live operation is
enabled by this test. See KOTOBA-159 and JUN-765 for the boundary finding.

`test/build-navigation-probe.py RUNTIME EMPTY_OUTPUT_DIR` generates ten
loopback-only cases for the shared runtime with SHA-256 `4e6ef6ee…b693`.
Serve the output at port 18777 and a separate loopback receiver at port 18778.
The cases use synthetic fixed query values; filenames ending `-0` omit the
parent frame policy and `-1` include it. In the in-app browser on 2026-11-02,
without that policy the receiver saw one request each from `location.href`,
`location.replace`, meta refresh and a script-clicked link; with the policy it
saw none of those four. Form submission reached neither receiver in either
configuration, so it is not a positive control for the parent policy. The
receiver returned 404 for the four controls: the request arriving, not the
response status, is the observation. Tests do not establish other browsers,
redirects, host trust, or complete egress prevention.

`test/build-host-consent-fixture.py RUNTIME EMPTY_OUTPUT_DIR` generates a
synthetic consent test using the monorepo runtime digest `4e6ef6ee…b693`, a
parent `frame-src 'none'` policy, an opaque guest and a host-only in-memory
counter adapter. In the in-app browser on 2026-11-02, a guest request showed
the operation details; denial left the counter at zero, approval of the next
request incremented it once, and another request displayed a fresh dialog;
denial left the count at one. No provider request or browser permission API was
used. The fixture's synthetic artifact digest is self-generated and does not
demonstrate publisher admission, provider transport, full egress isolation or
production consent. The separate canonical path mandated by the workspace
contract, provider specifications and production host remain unresolved.

With the builder's explicit `--http` option, a second fixture declares a
single anonymous public GitHub metadata GET (no credentials or financial
data). In one in-app browser, the guest requested it through the shared broker:
denial left the browser resource-entry count at zero, approval of the next
request returned HTTP 200 and count one, and a further denial left count one.
The parent CSP included `frame-src 'none'` and the declared service origin in
`connect-src`. A resource entry is browser-side evidence, not a server-side
audit log; this does not test redirect, provider OAuth, production descriptor
admission or all network paths. Running this optional fixture and approving
the dialog makes an actual request to GitHub.

`test/build-guest-egress-fixture.py RUNTIME EMPTY_OUTPUT_DIR` builds a separate
fixed loopback probe for the same monorepo runtime digest. Serve it at 18782
with a receiver at 18783. In one in-app browser run, the receiver saw no
requests from guest fetch, sendBeacon, image, WebSocket, or a blob Worker's
fetch. For a negative control, `--negative-control` creates a deliberately
weakened CSP runtime in the output directory; with that version the receiver
saw all five requests. Never use the negative-control runtime outside this
loopback test. Client-visible `blocked` errors and `sendBeacon` returning true
did not distinguish these cases: the receiver logs were essential because
CORS and HTTP errors occur after transmission. This comparison covers only
these fixed probes, one browser and loopback destinations; it does not prove
complete egress isolation or qualify a production host.

`test/origin-isolation-fixture.html` uses only the fixed synthetic store above.
In an in-app browser on 2026-11-02, a page at loopback port 18785 wrote the
synthetic sentinel; a second page on that same origin read it, while the same
fixture at port 18786 reported an empty store. This confirms that URL paths do
not isolate IndexedDB and illustrates a separate-origin candidate; it does
not establish trusted hosting, protection against other code on that origin,
owner authentication, or safe migration of existing data. Serve the repository
on two loopback ports and open this fixture on each to reproduce. Synthetic
test records can remain on the test origins.

Important limits before any production use:

- The fixture's parent creates a raw iframe; it does not use the canonical
  broker's verified-artifact mount, descriptor admission, or trusted consent.
  Its one-shot MessageChannel transfer is not a reviewed navigation-safe or
  multi-session protocol. The navigation check observes `load`, not the start
  of navigation. Cancellation aborts an active IndexedDB transaction, but a
  transaction already committed before cancellation cannot be undone, and a
  crash or untested timing may leave the outcome ambiguous. A sibling document
  on the same origin can access the
  fixture database. Do not treat the demonstration as a security boundary.
- It does not store original files, bind storage to an authenticated owner,
  migrate old state, handle rollback, deletion, schema changes, corruption
  recovery, quota exhaustion, abrupt process termination, or multi-device
  synchronization. Browser reload is not a full crash/restart test.
- `KOTOBA-159` independent broker review remains in progress, and the staged
  canonical revision is affected by the known `KOTOBA-158` delayed close bug.
  No service access or operation approval follows from this experiment.

The next integration must specify verified guest admission and a bounded,
navigation-safe storage bridge, protect data from unrelated same-origin apps,
and test synthetic guest/host failures and existing-state migration before any
production cutover. Track this work in [JUN-771](https://linear.app/kotobalabs/issue/JUN-771).
