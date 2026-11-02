#!/usr/bin/env python3
"""Build a synthetic delayed-save probe; never use as a production artifact."""
import re
import shutil
import sys
from pathlib import Path

if len(sys.argv) not in (3, 4) or (len(sys.argv) == 4 and sys.argv[3] != '--fail-first'):
    raise SystemExit('usage: python3 test/build-save-order-probe.py PREVIEW NEW_OUTPUT_DIR [--fail-first]')
preview, out = map(Path, sys.argv[1:3])
if out.exists():
    raise SystemExit('output directory must not exist')
shutil.copytree(preview, out)
app = (Path(__file__).resolve().parents[1] / 'site/app.cljk').read_text()
app = app.replace('itonami.kaikei.v1', 'kaikei.jun771.synthetic.save-order')
fail = 'true' if len(sys.argv) == 4 else 'false'
adapter = '''(defn- idb-request
  ([mode f] (idb-request idb-store mode f))
  ([store mode f]
   (if (= mode "readonly") (js/Promise.resolve nil)
     (let [fake #js {:put (fn [value key] value) :delete (fn [key] "deleted")}
           value (f fake)
           older? (.includes value "older")
           delay (if older? 400 10)]
       (js/Promise. (fn [resolve reject]
         (js/setTimeout (fn []
           (if (and older? FAIL_FIRST) (reject (js/Error. "synthetic-write-failure"))
             (do (aset js/globalThis "fixtureResult" value) (resolve nil)))) delay)))))))

'''.replace('FAIL_FIRST', fail)
app, n = re.subn(r'\(defn- idb-request\b.*?(?=\(defn- local-get\b)', lambda _: adapter, app, count=1, flags=re.S)
if n != 1:
    raise SystemExit('expected storage adapter not found')
writer = '''(defn- idb-write-with-file [text file-op clear-snapshot]
  (if file-op (js/Promise.reject (js/Error. "fixture does not support original files"))
    (idb-request "readwrite" #(if text (.put % text storage-key) (.delete % storage-key)))))

'''
app, n = re.subn(r'\(defn- idb-write-with-file\b.*?(?=\(rf/reg-fx\s+::store)', lambda _: writer, app, count=1, flags=re.S)
if n != 1:
    raise SystemExit('expected atomic writer not found')
app += '''\n(rf/reg-event-fx :fixture-save (fn [_ [_ tag]] {::store {:saved {:data {:tag tag}} :backend :indexeddb}}))
(rf/dispatch-sync [:fixture-save "older"])
(rf/dispatch-sync [:fixture-save "newer"])
(js/setTimeout (fn [] (let [p (.createElement js/document "p")]
  (set! (.-id p) "fixture-result")
  (set! (.-textContent p) (str "save-order=" (aget js/globalThis "fixtureResult")))
  (.appendChild (.-body js/document) p))) 900)
'''
(out / 'app.cljs').write_text(app)
print('built synthetic delayed-write probe; serve only on an isolated loopback origin')
