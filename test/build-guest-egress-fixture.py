#!/usr/bin/env python3
"""Build loopback egress probes; the negative control deliberately weakens CSP."""
import hashlib
import sys
from pathlib import Path

if len(sys.argv) not in (3, 4) or (len(sys.argv) == 4 and sys.argv[3] != '--negative-control'):
    raise SystemExit('usage: python3 test/build-guest-egress-fixture.py RUNTIME EMPTY_OUTPUT_DIR [--negative-control]')
runtime, out = map(Path, sys.argv[1:3])
data = runtime.read_bytes()
if hashlib.sha256(data).hexdigest() != '4e6ef6eea88641b20c490692d271ce57891e53e01fcc5c303135a325b2f5b693':
    raise SystemExit('unexpected shared runtime digest')
if out.exists() and any(out.iterdir()):
    raise SystemExit('output directory must be empty')
out.mkdir(parents=True, exist_ok=True)
if len(sys.argv) == 4:
    text = data.decode('utf-8')
    old, new = "connect-src \\'none\\'", 'connect-src * ws: http:'
    if text.count(old) != 1 or text.count('img-src data: blob:') != 1:
        raise SystemExit('unexpected runtime CSP')
    data = text.replace(old, new).replace('img-src data: blob:', 'img-src * data: blob:').encode()
(out / 'runtime.js').write_bytes(data)
(out / 'index.html').write_bytes(Path(__file__).with_name('guest-egress-fixture.html').read_bytes())
print('built loopback egress probe; negative control weakens CSP and is never for production')
