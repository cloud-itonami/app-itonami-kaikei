#!/usr/bin/env python3
"""Build an isolated synthetic legacy-backup probe, never a release artifact."""
import re
import shutil
import sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit('usage: python3 test/build-legacy-backup-fixture.py PREVIEW NEW_OUTPUT_DIR')
preview, out = map(Path, sys.argv[1:])
if out.exists():
    raise SystemExit('output directory must not exist')
shutil.copytree(preview, out)
app = (Path(__file__).resolve().parents[1] / 'site/app.cljk').read_text()
replacement = '''(defn- idb-request
  ([mode f] (js/Promise.reject (js/Error. "synthetic IDB failure")))
  ([store mode f] (js/Promise.reject (js/Error. "synthetic IDB failure"))))

'''
app, count = re.subn(r'\(defn- idb-request\b.*?(?=\(defn- local-get\b)', lambda _: replacement, app, count=1, flags=re.S)
if count != 1:
    raise SystemExit('expected storage adapter not found')
(out / 'app.cljs').write_text(app)
p = out / 'index.html'
html = p.read_text()
if html.count('<head>') != 1:
    raise SystemExit('expected one head')
seed = '<script>localStorage.setItem("itonami.kaikei.v1", "{:data {:synthetic \\"legacy-test\\"} :settings {}}")</script>'
p.write_text(html.replace('<head>', '<head>' + seed, 1))
print('built synthetic legacy backup probe; serve only on an isolated loopback origin')
