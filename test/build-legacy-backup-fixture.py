#!/usr/bin/env python3
"""Build an isolated synthetic legacy-backup probe, never a release artifact."""
import re
import shutil
import sys
from pathlib import Path

if len(sys.argv) not in (3, 4) or (len(sys.argv) == 4 and sys.argv[3] not in ('--sample', '--invalid')):
    raise SystemExit('usage: python3 test/build-legacy-backup-fixture.py PREVIEW NEW_OUTPUT_DIR [--sample|--invalid]')
preview, out = map(Path, sys.argv[1:3])
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
if len(sys.argv) == 4 and sys.argv[3] == '--sample':
    marker = '(rf/dispatch-sync [:init])'
    if app.count(marker) != 1:
        raise SystemExit('expected app initialization not found')
    seed = '''(.setItem js/localStorage storage-key
               (pr-str {:data (:db (core/merge-import core/empty-db core/sample-import))
                        :settings {:fy-start 4}}))
'''
    app = app.replace(marker, seed + marker)
(out / 'app.cljs').write_text(app)
p = out / 'index.html'
html = p.read_text()
if html.count('<head>') != 1:
    raise SystemExit('expected one head')
if len(sys.argv) == 3 or sys.argv[3] == '--invalid':
    value = '{invalid-edn' if len(sys.argv) == 4 else '{:data {:synthetic \\"legacy-test\\"} :settings {}}'
    seed = '<script>localStorage.setItem("itonami.kaikei.v1", "' + value + '")</script>'
    html = html.replace('<head>', '<head>' + seed, 1)
p.write_text(html)
print('built synthetic legacy backup probe; serve only on an isolated loopback origin')
