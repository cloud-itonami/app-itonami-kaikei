#!/usr/bin/env python3
"""Build a synthetic preservation probe. Serve only on a fresh loopback origin."""
import shutil
import sys
from pathlib import Path

if len(sys.argv) != 4 or sys.argv[3] not in ('--both', '--legacy-only', '--empty'):
    raise SystemExit('usage: python3 test/build-legacy-preserve-probe.py PREVIEW NEW_OUTPUT_DIR --both|--legacy-only|--empty')
preview, out = map(Path, sys.argv[1:3])
if out.exists():
    raise SystemExit('output directory must not exist')
shutil.copytree(preview, out)
app = (Path(__file__).resolve().parents[1] / 'site/app.cljk').read_text()
app = app.replace('"itonami.kaikei.v1"', '"kaikei.jun771.preserve.v1"')
app = app.replace('"itonami.kaikei"', '"kaikei-jun771-preserve"')
(out / 'app.cljs').write_text(app)
seed = "localStorage.setItem('kaikei.jun771.preserve.v1', '{:data {:synthetic \\\"legacy-backup\\\"}}');"
if sys.argv[3] == '--empty':
    seed = ''
if sys.argv[3] == '--both':
    seed += '''const req=indexedDB.open('kaikei-jun771-preserve',2);
req.onupgradeneeded=()=>{req.result.createObjectStore('state');req.result.createObjectStore('files');};
req.onsuccess=()=>{const db=req.result;const tx=db.transaction('state','readwrite');
tx.objectStore('state').put('{:data {:synthetic "idb-current"}}','kaikei.jun771.preserve.v1');
tx.oncomplete=()=>{db.close();document.querySelector('#result').textContent='seeded';};};'''
else:
    seed += "document.querySelector('#result').textContent='seeded';"
(out / 'seed.html').write_text('<!doctype html><meta charset="utf-8"><p id="result">preparing</p><script>' + seed + '</script>')
(out / 'change.html').write_text('''<!doctype html><p>changed legacy</p><script>localStorage.setItem('kaikei.jun771.preserve.v1','{:data {:synthetic "legacy-changed"}}');</script>''')
(out / 'writer.html').write_text('''<!doctype html><meta charset="utf-8"><button id="other">別のキー</button><button id="legacy">旧帳簿を書込</button><script>document.querySelector('#other').onclick=()=>localStorage.setItem('unrelated','synthetic');document.querySelector('#legacy').onclick=()=>localStorage.setItem('kaikei.jun771.preserve.v1','{:data {:synthetic "legacy-live"}}');</script>''')
(out / 'inspect.html').write_text('''<!doctype html><p id="result"></p><script>document.querySelector('#result').textContent='legacy='+localStorage.getItem('kaikei.jun771.preserve.v1');</script>''')
print('built synthetic-only preservation probe')
