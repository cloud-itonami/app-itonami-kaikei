#!/usr/bin/env python3
"""Create a local-only isolation fixture from an already-built kaikei preview.

This synthetic harness supplies no authorized operations, uses no user data,
and is not an installer, product host, or publisher-admission implementation.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit("usage: python3 test/build-restricted-fixture.py PREVIEW EMPTY_OUTPUT_DIR")
preview, out = map(Path, sys.argv[1:])
if out.exists() and any(out.iterdir()):
    raise SystemExit("output directory must be empty")
out.mkdir(parents=True, exist_ok=True)
runtime = (preview / "runtime/kotoba-client-runtime.js").read_bytes()
expected = "37e826338686eefbb2b9c7a731b73c53f7f5d6864158c0790edad60f25682d6d"
if hashlib.sha256(runtime).hexdigest() != expected:
    raise SystemExit("unexpected canonical runtime digest")
(out / "console.js").write_bytes(runtime)

html = (preview / "index.html").read_text(encoding="utf-8")
pattern = r'<script(?P<attrs>[^>]*?)\s+src="\./(?P<path>[^"]+)"(?P<rest>[^>]*)></script>'


def inline(match):
    path = (preview / match.group("path")).resolve()
    if not path.is_relative_to(preview.resolve()):
        raise ValueError("script escapes preview")
    body = path.read_text(encoding="utf-8")
    if "</script" in body.lower():
        raise ValueError("script contains closing tag")
    return "<script" + match.group("attrs") + match.group("rest") + ">" + body + "</script>"


html, count = re.subn(pattern, inline, html)
if count == 0 or re.search(r'<script[^>]+\ssrc=', html, re.I):
    raise SystemExit("fixture cannot inline every script")
content = html.encode("utf-8")
(out / "kaikei-inline.html").write_bytes(content)
digest = hashlib.sha256(content).hexdigest()
host = '''<!doctype html><title>Kaikei isolated fixture</title>
<h1>Kaikei isolated fixture</h1><p id="status">Loading</p><div id="app"></div>
<script type="module">
import {createClientConsentHost,createClientOperationBroker,verifyClientArtifact,mountRestrictedClientApp} from './console.js';
try {
  const bytes = new Uint8Array(await (await fetch('./kaikei-inline.html')).arrayBuffer());
  const artifact = await verifyClientArtifact(bytes, {revision:'1111111111111111111111111111111111111111',
    sha256:FIXTURE_DIGEST, 'max-bytes':8388608});
  await mountRestrictedClientApp({artifact,container:document.querySelector('#app'),
    broker:createClientOperationBroker({runtime:{schema:'kotoba.app.client-runtime.v1',target:'browser',profile:'restricted-wasm-v1',entry:'app.html','local-state':{adapter:'localstorage',schema:'test.state.v1',version:1},workers:[],operations:[]},consentHost:createClientConsentHost()})});
  document.querySelector('#status').textContent = 'Mounted: no operations';
} catch (error) { document.querySelector('#status').textContent = 'FAIL ' + error.message; }
</script>'''.replace("FIXTURE_DIGEST", json.dumps(digest))
(out / "kaikei-host.html").write_text(host, encoding="utf-8")
print(f"Inlined {count} scripts; fixture SHA-256 {digest}; no eligible operations")
