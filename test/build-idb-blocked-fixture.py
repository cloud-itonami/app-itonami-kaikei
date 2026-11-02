#!/usr/bin/env python3
"""Prepare a synthetic old-version connection and actual app for browser testing."""
import shutil
import sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit('usage: python3 test/build-idb-blocked-fixture.py PREVIEW NEW_OUTPUT_DIR')
preview, out = map(Path, sys.argv[1:])
if out.exists():
    raise SystemExit('output directory must not exist')
shutil.copytree(preview, out)
(out / 'app.cljs').write_bytes((Path(__file__).resolve().parents[1] / 'site/app.cljk').read_bytes())
(out / 'holder.html').write_text('''<!doctype html><title>synthetic blocked-open holder</title>
<p id="status">opening</p><button id="release">Release</button><button id="inspect">Inspect</button>
<script>
let db; const status=document.querySelector('#status');
const req=indexedDB.open('itonami.kaikei',1);
req.onupgradeneeded=()=>{const s=req.result.createObjectStore('state');s.put('synthetic sentinel','marker')};
req.onsuccess=()=>{db=req.result;status.textContent='holding version '+db.version};
req.onerror=()=>status.textContent='open failed';
document.querySelector('#release').onclick=()=>{db.close();status.textContent='released'};
document.querySelector('#inspect').onclick=()=>{
  const r=indexedDB.open('itonami.kaikei');
  r.onsuccess=()=>{const d=r.result, v=d.version, f=d.objectStoreNames.contains('files');
    const tx=d.transaction('state','readonly'), get=tx.objectStore('state').get('marker');
    tx.oncomplete=()=>{status.textContent='version '+v+' files '+f+' marker '+get.result;d.close()};
    tx.onabort=()=>{status.textContent='inspect failed';d.close()};
  };r.onerror=()=>status.textContent='inspect failed';
};
</script>''')
print('serve only on a fresh loopback origin; open holder.html before the app')
