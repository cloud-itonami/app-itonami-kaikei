#!/usr/bin/env python3
"""Build a synthetic-only app probe for ledger/file transaction failure."""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

if len(sys.argv) not in (3, 4) or (len(sys.argv) == 4 and sys.argv[3] != '--old'):
    raise SystemExit('usage: python3 test/build-atomic-app-probe.py PREVIEW NEW_OUTPUT_DIR [--old]')
preview, out = map(Path, sys.argv[1:3])
if out.exists():
    raise SystemExit('output directory must not exist')
root = Path(__file__).resolve().parents[1]
app = (subprocess.check_output(['git', 'show', 'e1355bc:site/app.cljk'], cwd=root, text=True)
       if len(sys.argv) == 4 else (root / 'site/app.cljk').read_text())
app = app.replace('"itonami.kaikei.v1"', '"kaikei.jun771.atomic-pair.v1"')
app = app.replace('"itonami.kaikei"', '"kaikei-jun771-atomic-pair"')
app += '''\n(rf/reg-event-fx :fixture-pair
 (fn [{:keys [db]} [_ label byte]]
   (let [db2 (assoc-in db [:data :business] {:name label})]
     (with-store db db2 {::store-file {:id "fixture-file" :bytes (js/Uint8Array. #js [byte])}}))))
(rf/reg-event-fx :fixture-ledger-only
 (fn [{:keys [db]} _] (with-store db (assoc-in db [:data :business] {:name "C"}) {})))
(doseq [[label byte] [["A" 1] ["B" 2]]] (let [b (.createElement js/document "button")]
 (set! (.-textContent b) (str "fixture " label))
 (set! (.-onclick b) (fn [] (rf/dispatch-sync [:fixture-pair label byte])))
 (.appendChild (.-body js/document) b)))
(let [b (.createElement js/document "button")]
 (set! (.-textContent b) "fixture C")
 (set! (.-onclick b) (fn [] (rf/dispatch-sync [:fixture-ledger-only])))
 (.appendChild (.-body js/document) b))
(let [b (.createElement js/document "button")]
 (set! (.-textContent b) "fixture clear")
 (set! (.-onclick b) (fn [] (rf/dispatch-sync [:clear-all])))
 (.appendChild (.-body js/document) b))
'''
ofx = (root / 'test/fixtures/ofx-bank.ofx').read_bytes()
app += ('\n(let [b (.createElement js/document "button")] (set! (.-textContent b) "fixture OFX") '
        '(set! (.-onclick b) (fn [] (rf/dispatch-sync [:run-import-bytes (js/Uint8Array. #js '
        + json.dumps(list(ofx)) + ') "synthetic.ofx" "' + hashlib.sha256(ofx).hexdigest()
        + '"]))) (.appendChild (.-body js/document) b))\n')
shutil.copytree(preview, out)
(out / 'app.cljs').write_text(app)
index = out / 'index.html'
html = index.read_text()
hook = '''<script>const original=IDBObjectStore.prototype.put;IDBObjectStore.prototype.put=function(value,key){const r=original.call(this,value,key);if(this.name==='files' && value instanceof Uint8Array && value[0]===2)this.transaction.abort();return r;};const originalClear=IDBObjectStore.prototype.clear;IDBObjectStore.prototype.clear=function(){const r=originalClear.call(this);if(this.name==='files')this.transaction.abort();return r;};</script>'''
if html.count('<head>') != 1:
    raise SystemExit('expected one head')
index.write_text(html.replace('<head>', '<head>' + hook, 1))
(out / 'inspect.html').write_text('''<!doctype html><meta charset="utf-8"><p id="result">reading</p><script>const r=indexedDB.open('kaikei-jun771-atomic-pair',2);r.onsuccess=()=>{const db=r.result;const tx=db.transaction(['state','files']);const state=tx.objectStore('state').get('kaikei.jun771.atomic-pair.v1');const file=tx.objectStore('files').get('fixture-file');tx.oncomplete=()=>{document.querySelector('#result').textContent='ledger='+state.result+' file='+file.result?.[0];db.close();}};</script>''')
(out / 'inspect-import.html').write_text('''<!doctype html><meta charset="utf-8"><p id="result">reading</p><script>const r=indexedDB.open('kaikei-jun771-atomic-pair',2);r.onsuccess=()=>{const db=r.result;const tx=db.transaction(['state','files']);const state=tx.objectStore('state').get('kaikei.jun771.atomic-pair.v1');const file=tx.objectStore('files').get('f1');tx.oncomplete=async()=>{const digest=await crypto.subtle.digest('SHA-256',file.result);const hex=Array.from(new Uint8Array(digest),x=>x.toString(16).padStart(2,'0')).join('');document.querySelector('#result').textContent='ledger-file-id='+String(state.result).includes(':file-id "f1"')+' sha256='+hex;db.close();}};</script>''')
print('built synthetic-only app probe; serve on a fresh loopback origin')
