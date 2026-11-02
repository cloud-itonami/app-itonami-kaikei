#!/usr/bin/env python3
"""Build a synthetic consent/CSP fixture; not a production host."""
import hashlib
import sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit('usage: python3 test/build-host-consent-fixture.py RUNTIME EMPTY_OUTPUT_DIR')
runtime, out = map(Path, sys.argv[1:])
expected = '4e6ef6eea88641b20c490692d271ce57891e53e01fcc5c303135a325b2f5b693'
data = runtime.read_bytes()
if hashlib.sha256(data).hexdigest() != expected:
    raise SystemExit('unexpected shared runtime digest')
if out.exists() and any(out.iterdir()):
    raise SystemExit('output directory must be empty')
out.mkdir(parents=True, exist_ok=True)
(out / 'runtime.js').write_bytes(data)
(out / 'index.html').write_bytes(Path(__file__).with_name('host-consent-fixture.html').read_bytes())
print('built local synthetic consent fixture; no provider operations')
