#!/usr/bin/env python3
"""Build an isolated, synthetic real-IndexedDB abort probe; never a release."""
import shutil
import sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit('usage: python3 test/build-idb-abort-fixture.py PREVIEW NEW_OUTPUT_DIR')
preview, out = map(Path, sys.argv[1:])
if out.exists():
    raise SystemExit('output directory must not exist')
shutil.copytree(preview, out)
root = Path(__file__).resolve().parents[1]
(out / 'app.cljs').write_bytes((root / 'site/app.cljk').read_bytes())
page = out / 'index.html'
html = page.read_text()
if html.count('<head>') != 1:
    raise SystemExit('expected one head')
# Use a real transaction and abort it after its get request succeeds, before
# commit. No user's database is touched when served on a fresh loopback origin.
shim = '''<script>
const originalGet = IDBObjectStore.prototype.get;
IDBObjectStore.prototype.get = function (...args) {
  const request = originalGet.apply(this, args);
  request.addEventListener('success', () => {
    console.log('SYNTHETIC-ABORT-FIRED');
    request.transaction.abort();
  }, {once: true});
  return request;
};
</script>'''
page.write_text(html.replace('<head>', '<head>' + shim, 1))
print('built synthetic IDB abort probe; serve only on an isolated loopback origin')
