"""Build synthetic loopback-only navigation probes, never a production host."""
import hashlib
import json
import sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit('usage: python3 test/build-navigation-probe.py RUNTIME EMPTY_OUTPUT_DIR')
runtime, root = map(Path, sys.argv[1:])
expected = '4e6ef6eea88641b20c490692d271ce57891e53e01fcc5c303135a325b2f5b693'
source = runtime.read_bytes()
if hashlib.sha256(source).hexdigest() != expected:
    raise SystemExit('unexpected shared runtime digest')
if root.exists() and any(root.iterdir()):
    raise SystemExit('output directory must be empty')
root.mkdir(parents=True, exist_ok=True)
(root / 'runtime.js').write_bytes(source)
base='http://127.0.0.1:18778/'
tests={
 'assign': f"<script>location.href='{base}assign?synthetic=1'</script>",
 'replace': f"<script>location.replace('{base}replace?synthetic=1')</script>",
 'refresh': f'<meta http-equiv="refresh" content="0;url={base}refresh?synthetic=1">',
 'anchor': f"<a id='a' href='{base}anchor?synthetic=1'>test</a><script>document.getElementById('a').click()</script>",
 'form': f"<form id='f' method='get' action='{base}form'><input name='synthetic' value='1'></form><script>document.getElementById('f').submit()</script>",
}
for name,guest in tests.items():
  for protected in (False,True):
    policy="<meta http-equiv=\"Content-Security-Policy\" content=\"frame-src &#39;none&#39;\">" if protected else ''
    encoded=json.dumps(guest).replace('<','\\u003c')
    doc=f'''<!doctype html><meta charset="utf-8">{policy}<title>{name} {protected}</title><p>mounted</p><main></main><script type="module">
import {{verifyClientArtifact,mountRestrictedClientApp}} from './runtime.js';
const bytes=new TextEncoder().encode({encoded});
const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');
const artifact=await verifyClientArtifact(bytes,{{revision:'1111111111111111111111111111111111111111',sha256:hash,'max-bytes':1048576}});
await mountRestrictedClientApp({{artifact,container:document.querySelector('main'),broker:{{invoke:async()=>{{throw Error('denied')}}}}}});
</script>'''
    (root/f'{name}-{int(protected)}.html').write_text(doc)

print("built ten synthetic cases; destinations limited to loopback:18778")
