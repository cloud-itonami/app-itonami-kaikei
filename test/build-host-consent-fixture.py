#!/usr/bin/env python3
"""Build a synthetic consent/CSP fixture; not a production host."""
import hashlib
import sys
from pathlib import Path

if len(sys.argv) not in (3, 4) or (len(sys.argv) == 4 and sys.argv[3] not in ('--http', '--close-pending')):
    raise SystemExit('usage: python3 test/build-host-consent-fixture.py RUNTIME EMPTY_OUTPUT_DIR [--http|--close-pending]')
runtime, out = map(Path, sys.argv[1:3])
expected = '4e6ef6eea88641b20c490692d271ce57891e53e01fcc5c303135a325b2f5b693'
data = runtime.read_bytes()
if hashlib.sha256(data).hexdigest() != expected:
    raise SystemExit('unexpected shared runtime digest')
if out.exists() and any(out.iterdir()):
    raise SystemExit('output directory must be empty')
out.mkdir(parents=True, exist_ok=True)
(out / 'runtime.js').write_bytes(data)
mode = sys.argv[3] if len(sys.argv) == 4 else None
fixture = 'host-http-consent-fixture.html' if mode == '--http' else 'host-consent-fixture.html'
html = Path(__file__).with_name(fixture).read_text()
if mode == '--close-pending':
    html = html.replace('<p id="state">preparing</p>', '<p id="state">preparing</p><p id="lifecycle">guest open</p>')
    old = "await mountRestrictedClientApp({artifact,container:document.querySelector('main'),broker});state.textContent='handler calls 0';"
    new = "let mount;const wrapped={invoke(...args){const result=broker.invoke(...args);queueMicrotask(()=>{mount.close();document.querySelector('#lifecycle').textContent='guest closed while awaiting consent';});return result;}};mount=await mountRestrictedClientApp({artifact,container:document.querySelector('main'),broker:wrapped});state.textContent='handler calls 0';"
    if html.count(old) != 1:
        raise SystemExit('expected mount not found')
    html = html.replace(old, new)
(out / 'index.html').write_text(html)
print('built synthetic consent fixture; --http permits an anonymous public GET, --close-pending uses only an in-memory counter')
