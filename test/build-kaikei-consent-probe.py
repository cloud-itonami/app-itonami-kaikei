#!/usr/bin/env python3
"""Build a synthetic kaikei + shared broker consent probe; not a release host."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

if len(sys.argv) not in (4, 5) or (len(sys.argv) == 5 and sys.argv[4] != '--http'):
    raise SystemExit('usage: python3 test/build-kaikei-consent-probe.py PREVIEW REVIEWED_RUNTIME NEW_OUTPUT_DIR [--http]')
preview, runtime, out = map(Path, sys.argv[1:4])
http = len(sys.argv) == 5
data = runtime.read_bytes()
if hashlib.sha256(data).hexdigest() != '4e6ef6eea88641b20c490692d271ce57891e53e01fcc5c303135a325b2f5b693':
    raise SystemExit('unexpected reviewed monorepo runtime digest')
root = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, str(root / 'test/build-kaikei-storage-probe.py'), str(preview), str(out)], check=True)
(out / 'console.js').write_bytes(data)
page = out / 'kaikei-inline.html'
html = page.read_text()
guest = '''<script>
(() => {
  let port, n=0;
  addEventListener('message', e => {
    if (e.source!==parent || e.data?.protocol!=='kotoba.client.host.v1' || port || e.ports.length!==1) return;
    port=e.ports[0]; port.onmessage=e=>{document.querySelector('#fixture-result').textContent=e.data.ok?'allowed':'denied';};
  });
  addEventListener('DOMContentLoaded',()=>{
    const section=document.createElement('section');
    section.innerHTML='<button id="fixture-request">Request synthetic counter</button><p id="fixture-result">waiting</p>';
    document.body.prepend(section);
    section.querySelector('button').onclick=()=>{
      if (!port) {document.querySelector('#fixture-result').textContent='port unavailable';return;}
      port.postMessage({protocol:'kotoba.client.operation.v1',id:'request-'+(++n),selector:{capability:'test/browser-counter',service:'local-fixture',operation:'increment'},payload:{value:1}});
    };
  });
})();
</script>'''
if http:
    guest = guest.replace("e.data.ok?'allowed':'denied'", "e.data.ok?'HTTP status '+e.data.status:'denied'")
    guest = guest.replace('Request synthetic counter', 'Request public fixture')
    guest = guest.replace("capability:'test/browser-counter',service:'local-fixture',operation:'increment'", "capability:'test/public-metadata',service:'github-public-fixture',operation:'read'")
    guest = guest.replace('payload:{value:1}', "payload:{input:'https://api.github.com/repos/holochain/holochain'}")
if html.count('<head>') != 1:
    raise SystemExit('expected one head')
page.write_text(html.replace('<head>', '<head>' + guest, 1))
digest = hashlib.sha256(page.read_bytes()).hexdigest()
host = out / 'index.html'
text = host.read_text()
old = "import {verifyClientArtifact,mountRestrictedClientApp} from './console.js';"
new = "import {createClientConsentHost,createClientOperationBroker,verifyClientArtifact,mountRestrictedClientApp} from './console.js';"
if text.count(old) != 1:
    raise SystemExit('unexpected host import')
text = text.replace(old, new)
old = "await mountRestrictedClientApp({artifact,container,broker:{invoke:async()=>{throw Error('no eligible operations')}}});"
new = '''const op={capability:'test/browser-counter',service:'local-fixture',operation:'increment',consent:'each-operation','data-categories':['fixture-number'],endpoint:{origin:'https://fixture.invalid','browser-action':'test/counter'}};
  const runtime={schema:'kotoba.app.client-runtime.v1',target:'browser',profile:'restricted-wasm-v1',entry:'app.html','local-state':{adapter:'localstorage',schema:'test.state.v1',version:1},workers:[],operations:[op]};
  let calls=0; const counter=document.createElement('p');counter.id='counter';counter.textContent='handler calls 0';document.body.prepend(counter);
  const consentHost=createClientConsentHost();
  const broker=createClientOperationBroker({runtime,requestedCapabilities:[op.capability],approvedOperations:[op],hostSupportedOperations:[[op.capability,op.service,op.operation]],consentHost,browserAdapters:{'local-fixture':{increment:()=>{counter.textContent='handler calls '+(++calls);return {value:1};}}}});
  await mountRestrictedClientApp({artifact,container,broker});'''
if http:
    new = '''const url='https://api.github.com/repos/holochain/holochain';
  const op={capability:'test/public-metadata',service:'github-public-fixture',operation:'read',consent:'each-operation','data-categories':['public-repository-metadata'],endpoint:{origin:'https://api.github.com',method:'GET',path:'/repos/holochain/holochain'}};
  const runtime={schema:'kotoba.app.client-runtime.v1',target:'browser',profile:'restricted-wasm-v1',entry:'app.html','local-state':{adapter:'localstorage',schema:'test.state.v1',version:1},workers:[],operations:[op]};
  const counter=document.createElement('p');counter.id='counter';document.body.prepend(counter);
  const count=()=>performance.getEntriesByType('resource').filter(e=>e.name===url).length;
  counter.textContent='HTTP resource entries '+count();
  new PerformanceObserver(()=>counter.textContent='HTTP resource entries '+count()).observe({type:'resource',buffered:true});
  const consentHost=createClientConsentHost();
  const broker=createClientOperationBroker({runtime,requestedCapabilities:[op.capability],approvedOperations:[op],hostSupportedOperations:[[op.capability,op.service,op.operation]],consentHost});
  await mountRestrictedClientApp({artifact,container,broker});'''
    text = text.replace("frame-src 'none'", "frame-src 'none'; connect-src 'self' https://api.github.com")
if text.count(old) != 1:
    raise SystemExit('unexpected no-operation broker')
text = text.replace(old, new)
text, n = re.subn(r"sha256:\s*\"[0-9a-f]{64}\"", 'sha256:' + json.dumps(digest), text, count=1)
if n != 1:
    raise SystemExit('expected guest digest')
host.write_text(text)
print('synthetic kaikei consent fixture; ' + ('one public GET on approval' if http else 'no network operation') + '; self-digest is not publisher admission')
