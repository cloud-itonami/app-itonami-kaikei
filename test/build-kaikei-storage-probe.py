#!/usr/bin/env python3
"""Build a synthetic-only, offline kaikei storage probe; never a release host."""
import hashlib
import json
import re
import sys
from pathlib import Path

options = ('--corrupt-ledger', '--read-failure', '--legacy-empty', '--legacy-present', '--legacy-failure')
if len(sys.argv) not in (3, 4) or (len(sys.argv) == 4 and sys.argv[3] not in options):
    raise SystemExit('usage: python3 test/build-kaikei-storage-probe.py PREVIEW EMPTY_OUTPUT_DIR [option]')
preview, out = map(Path, sys.argv[1:3])
mode = sys.argv[3] if len(sys.argv) == 4 else None
legacy_probe = mode in ('--legacy-empty', '--legacy-present', '--legacy-failure')
if out.exists() and any(out.iterdir()):
    raise SystemExit('output directory must be empty')
out.mkdir(parents=True, exist_ok=True)
runtime = (preview / 'runtime/kotoba-client-runtime.js').read_bytes()
expected = '7f760128c3a58098123c31ec3dd34b9c871932e3933f2c952facc4ab0e647212'
if hashlib.sha256(runtime).hexdigest() != expected:
    raise SystemExit('unexpected runtime digest')
(out / 'console.js').write_bytes(runtime)
root = Path(__file__).resolve().parents[1]
store = (root / 'experiments/local-ledger-fixture.mjs').read_text()
assert store.count('kaikei-jun771-synthetic-fixture') == 1
store = store.replace('kaikei-jun771-synthetic-fixture', 'kaikei-jun771-actual-app-fixture')
if mode in ('--corrupt-ledger', '--read-failure'):
    marker = 'export async function readFixture(signal) {'
    if store.count(marker) != 1:
        raise SystemExit('expected fixture read not found')
    injection = (' return {revision: 1, value: JSON.stringify("{invalid-edn")};'
                 if mode == '--corrupt-ledger' else ' throw Error("synthetic-read-failure");')
    store = store.replace(marker, marker + injection)
(out / 'store.mjs').write_text(store)
(out / 'port.mjs').write_bytes((root / 'experiments/local-ledger-port-fixture.mjs').read_bytes())

# Only the generated test artifact is rewritten. Production source is unchanged.
replacement = '''(defn- idb-request
  ([mode f] (idb-request idb-store mode f))
  ([store mode f]
   (if (= store idb-store)
     (try
       (let [fake #js {:get (fn [k] #js {:action "read" :key k})
                       :put (fn [v k] #js {:action "write" :key k :value v})
                       :delete (fn [k] #js {:action "write" :key k :value nil})}]
         (.request js/kaikeiFixtureLedger (f fake)))
       (catch :default e (js/Promise.reject e)))
     (js/Promise.reject (js/Error. "fixture does not support original files")))))
'''
pattern = r'<script(?P<attrs>[^>]*?)\s+src="\./(?P<path>[^"]+)"(?P<rest>[^>]*)></script>'
html = (preview / 'index.html').read_text()


def inline(match):
    path = (preview / match.group('path')).resolve()
    if not path.is_relative_to(preview.resolve()):
        raise ValueError('script escapes preview')
    body = path.read_text()
    if match.group('path') == 'app.cljs':
        body, n = re.subn(r'\(defn- idb-request\b.*?(?=\(defn- local-get\b)', replacement, body, count=1, flags=re.S)
        if n != 1:
            raise ValueError('expected kaikei state adapter not found')
        if legacy_probe:
            old = '(defn- local-get [] (try (.getItem js/localStorage storage-key) (catch :default _ nil)))'
            if body.count(old) != 1:
                raise ValueError('expected legacy accessor not found')
            body = body.replace(old, '(defn- local-get [] (try (.legacy js/kaikeiFixtureLedger) (catch :default _ nil)))')
            old = '(if (some? v) (local-get) (.getItem js/localStorage storage-key))'
            if body.count(old) != 1:
                raise ValueError('expected legacy load not found')
            body = body.replace(old, '(.legacy js/kaikeiFixtureLedger)')
    if '</script' in body.lower():
        raise ValueError('script contains closing tag')
    return '<script' + match.group('attrs') + match.group('rest') + '>' + body + '</script>'


html, count = re.subn(pattern, inline, html)
if count == 0 or re.search(r'<script[^>]+\ssrc=', html, re.I):
    raise SystemExit('fixture cannot inline every script')
guest = '''<script>
(() => {
  const protocol = 'kaikei.fixture.local-ledger.v1'; let port, revision = 0, id = 0, legacy;
  const pending = new Map(); let start;
  const ready = new Promise((resolve, reject) => { start = resolve; setTimeout(() => reject(Error('fixture storage unavailable')), 10000); });
  addEventListener('message', event => {
    if (event.source !== parent || event.data !== 'fixture-storage-port' || port || event.ports.length !== 1) return;
    port = event.ports[0]; port.onmessage = ({data}) => { if (data.protocol !== protocol) return; const p = pending.get(data.id); if (!p) return; pending.delete(data.id); data.ok ? p.resolve(data.result) : p.reject(Error(data.error)); }; start();
  });
  const send = (action, expectedRevision, value) => new Promise((resolve,reject) => { const requestId = ++id; pending.set(requestId,{resolve,reject}); port.postMessage({protocol,id:requestId,action,expectedRevision,value}); });
  globalThis.kaikeiFixtureLedger = Object.freeze({request: async request => {
    await ready; if (request.key !== 'itonami.kaikei.v1') throw Error('fixture key refused');
    if (request.action === 'read') { const record = await send('read',null,null); revision=record.revision; legacy=record.legacy; return record.value === null ? null : JSON.parse(record.value); }
    if (request.action === 'write' && (typeof request.value === 'string' || request.value === null)) {
      const result = await send('write',revision,JSON.stringify(request.value)); if (!result.ok) throw Error('fixture write conflict'); revision=result.revision; return null;
    }
    throw Error('fixture operation refused');
  }, legacy: () => { if (legacy !== null && typeof legacy !== 'string') throw Error('fixture legacy unavailable'); return legacy; }});
})();
</script>'''
if html.count('<head>') != 1:
    raise SystemExit('expected one head')
html = html.replace('<head>', '<head>' + guest, 1)
content = html.encode()
(out / 'kaikei-inline.html').write_bytes(content)
digest = hashlib.sha256(content).hexdigest()
host = '''<!doctype html><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="frame-src 'none'"><title>Kaikei synthetic storage probe</title>
<h1>kaikei 合成保存 probe</h1><p id="status">準備中</p><div id="app"></div>
<script type="module">
import {verifyClientArtifact,mountRestrictedClientApp} from './console.js';
import {bindFixturePort} from './port.mjs';
import {readFixture,compareAndSwapFixture} from './store.mjs';
try {
  const bytes=new Uint8Array(await (await fetch('./kaikei-inline.html')).arrayBuffer());
  const artifact=await verifyClientArtifact(bytes,{revision:'1111111111111111111111111111111111111111',sha256:DIGEST,'max-bytes':8388608});
  const container=document.querySelector('#app');
  await mountRestrictedClientApp({artifact,container,broker:{invoke:async()=>{throw Error('no eligible operations')}}});
  const frame=container.querySelector('iframe'), channel=new MessageChannel();
  const bridge=bindFixturePort(channel.port1,{read:readFixture,write:compareAndSwapFixture}); let loaded=false;
  frame.addEventListener('load',()=>{ if(loaded){bridge.close();document.querySelector('#status').textContent='切断';return;} loaded=true;frame.contentWindow.postMessage('fixture-storage-port','*',[channel.port2]);document.querySelector('#status').textContent='合成 probe 稼働中'; });
} catch(error) {document.querySelector('#status').textContent='FAIL: '+error.message;}
</script>'''.replace('DIGEST', json.dumps(digest))
if legacy_probe:
    legacy_value = '{:data {:entries [{:id "l1" :date "2026-04-01" :memo "synthetic legacy" :lines [{:account "現金" :debit 123 :credit 0} {:account "売上高" :debit 0 :credit 123}]}]}}'
    if mode == '--legacy-present':
        setup = 'localStorage.setItem("kaikei.jun771.synthetic-legacy",' + json.dumps(legacy_value, ensure_ascii=False) + ');'
    else:
        setup = ''
    legacy_read = ('throw Error("synthetic legacy read failure");' if mode == '--legacy-failure' else
                   'const legacy=localStorage.getItem("kaikei.jun771.synthetic-legacy");'
                   'if(legacy!==null && new TextEncoder().encode(legacy).byteLength>65536) throw Error("legacy too large");'
                   'return {...record,legacy};')
    host = host.replace('try {\n  const bytes=', 'try {\n  ' + setup + '\n  const bytes=')
    host = host.replace('{read:readFixture,write:compareAndSwapFixture}',
                        '{read:async signal=>{const record=await readFixture(signal);' + legacy_read + '},write:compareAndSwapFixture}')
(out / 'index.html').write_text(host)
print(f'fixture: {count} inlined scripts, sha256={digest}, mode={mode}, no eligible external operations')
