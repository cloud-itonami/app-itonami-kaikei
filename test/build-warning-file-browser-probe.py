#!/usr/bin/env python3
"""Build a synthetic correction-file browser probe on a fresh loopback origin."""
import json
import re
import shutil
import sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit('usage: python3 test/build-warning-file-browser-probe.py PREVIEW NEW_OUTPUT_DIR')
preview, out = map(Path, sys.argv[1:])
if out.exists():
    raise SystemExit('output directory must not exist')
root = Path(__file__).resolve().parents[1]
shutil.copytree(preview, out)
(out / 'kaikei/core.cljs').write_bytes((root / 'src/kaikei/core.cljk').read_bytes())
source = (root / 'site/app.cljk').read_text()
original = (root / 'test/fixtures/ofx-bank.ofx').read_text()
records = re.findall(r'<STMTTRN>.*?</STMTTRN>', original, flags=re.S)
if len(records) != 3 or '<FITID>20261128-0001' not in records[0]:
    raise SystemExit('unexpected synthetic fixture')
replacement = records[0].replace('<FITID>20261128-0001', '<FITID>synthetic-replacement\n<CORRECTFITID>20261128-0001\n<CORRECTACTION>REPLACE').replace('<TRNAMT>58880', '<TRNAMT>58000')
corrected = original.replace(records[0], replacement).replace(records[1], '').replace(records[2], '')
(out / 'synthetic-correction.ofx').write_text(corrected)
marker = '(rf/dispatch-sync [:init])'
if source.count(marker) != 1:
    raise SystemExit('unexpected app initialization')
# Seed once; on reload keep the test database. The data is a repository fixture.
seed = '''(-> (idb-request "readonly" #(.get % storage-key))
 (.then (fn [v]
   (if v (js/Promise.resolve nil)
     (let [parsed (ingest/ingest-text ORIGINAL {})
           db (:db (core/merge-import core/empty-db parsed))
           db (-> db
                  (assoc-in [:statement-lines 0 :match] {:entry-id "synthetic"})
                  (assoc :entries [{:id "synthetic" :date "2026-11-28"
                                    :lines [{:account "普通預金" :debit 58880 :credit 0}
                                            {:account "売掛金" :debit 0 :credit 58880}]}]))]
       (idb-request "readwrite" #(.put % (pr-str {:data db}) storage-key))))))
 (.then (fn [_] (rf/dispatch-sync [:init]))))'''.replace('ORIGINAL', json.dumps(original, ensure_ascii=False))
(out / 'app.cljs').write_text(source.replace(marker, seed))
print('synthetic browser probe: open on fresh loopback origin; select synthetic-correction.ofx')
