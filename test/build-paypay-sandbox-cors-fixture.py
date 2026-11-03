#!/usr/bin/env python3
"""Build opt-in synthetic CORS probe; does not authenticate or fetch data."""
import hashlib
import sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit('usage: python3 test/build-paypay-sandbox-cors-fixture.py RUNTIME EMPTY_OUTPUT_DIR')
runtime, out = map(Path, sys.argv[1:])
data = runtime.read_bytes()
expected = '0d8ed12a795fdf46de32ac01c0675adec9f22df64f24769a4d4a960d6a345ac5'
if hashlib.sha256(data).hexdigest() != expected:
    raise SystemExit('unexpected runtime digest')
if out.exists() and any(out.iterdir()):
    raise SystemExit('output directory must be empty')
out.mkdir(parents=True, exist_ok=True)
(out / 'runtime.js').write_bytes(data)
(out / 'index.html').write_bytes(Path(__file__).with_name('paypay-sandbox-cors-fixture.html').read_bytes())
print('synthetic sandbox probe built; consent precedes external request; no real credentials')
