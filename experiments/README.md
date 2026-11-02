# JUN-771: synthetic local-storage experiment

This is **not wired into kaikei**, not a broker, not a production host, and
must not handle real financial data. It uses only the fixed IndexedDB name
`kaikei-jun771-synthetic-fixture` and one fixed key; it never opens, reads,
migrates or removes the existing `itonami.kaikei` database.

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
