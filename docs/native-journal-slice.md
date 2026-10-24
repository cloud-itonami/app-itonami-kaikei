# Native journal validation slice

JUN-379 adds `kotoba/kaikei/journal.kotoba` for the Murakumo NixOS workspace.
This ports the existing first journal-validation slice from
`aiueos/kaikei_journal.cljk` at
`8e128c838a57d6d7a47f359f6d6f2247afcb8b6d` into canonical Kotoba. Helpers
precede callers for the selfhost subset. Buffer layout and error values are
preserved. The port does not replace the rest of the accounting core.

`test-journal` checks the seven existing validation cases (balanced, empty,
odd length, negative amount, zero row, both sides, unbalanced) and two balance
predicate cases, returning 511 only when all pass. The owning NixOS package
uses the digest-pinned Amu native compiler, emits `wasm32-browser`, and invokes
this check inside the browser Worker before enabling the app.

The VM preview UI validates two-row balanced entries in integer minor units
and keeps local working state in the browser. Real browser checks refused a
1,200/1,100 imbalance, saved a 1,200/1,200 entry, reloaded it and restored an
export into an empty workspace. Existing-work restore refused to overwrite.
The NixOS desktop gate also booted the browser and both app-core checks.
These are local journal/host observations, not tax, payment, full accounting,
Cell, signature, replication or distributed-state qualification.

Source and compiler pins, browser Worker and OS evidence are maintained by
network-awai/cloud-murakumo-usb-installer's native preview profile.
