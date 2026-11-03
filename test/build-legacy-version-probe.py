#!/usr/bin/env python3
"""Build synthetic old-app / newer-IDB probe; do not use real data or origin."""
import shutil
import subprocess
import sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit('usage: python3 test/build-legacy-version-probe.py PREVIEW NEW_OUTPUT_DIR')
preview, out = map(Path, sys.argv[1:])
if out.exists():
    raise SystemExit('output directory must not exist')
root = Path(__file__).resolve().parents[1]
revision = '767104e0fbf9747332f6889ad379692ba56a7c49'
app = subprocess.check_output(['git', 'show', revision + ':site/app.cljk'], cwd=root, text=True)
app = app.replace('"itonami.kaikei.v1"', '"kaikei.jun771.legacy-v3-synthetic"')
app = app.replace('"itonami.kaikei"', '"kaikei-jun771-legacy-v3-synthetic"')
out.mkdir(parents=True)
shutil.copytree(preview, out / 'old-app')
(out / 'old-app' / 'app.cljs').write_text(app)
(out / 'seed.html').write_text('''<!doctype html><meta charset="utf-8"><title>Synthetic v3 seed</title>
<p id="result">preparing</p><script>
const req=indexedDB.open('kaikei-jun771-legacy-v3-synthetic',3);
req.onupgradeneeded=()=>{req.result.createObjectStore('state');req.result.createObjectStore('files');};
req.onsuccess=()=>{const db=req.result;const tx=db.transaction('state','readwrite');
tx.objectStore('state').put('{:data {:synthetic "v3-ledger"}}','kaikei.jun771.legacy-v3-synthetic');
tx.oncomplete=()=>{db.close();document.querySelector('#result').textContent='seeded v3 ledger';};};
req.onerror=()=>document.querySelector('#result').textContent='FAIL';</script>''')
print('built synthetic-only fixture; serve on an isolated loopback origin')
