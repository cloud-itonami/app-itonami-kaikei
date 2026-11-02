// Validate the inert local-preview candidate. This does not qualify a host.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const [preview, runtimeRepo] = process.argv.slice(2);
if (!preview || !runtimeRepo) throw new Error('expected preview directory and canonical runtime repository');
const sha = 'e00ae75e1c589f76b4f53a88a5e3256c98c9e162';
const expected = '7f760128c3a58098123c31ec3dd34b9c871932e3933f2c952facc4ab0e647212';
const staged = readFileSync(join(preview, 'runtime/kotoba-client-runtime.js'));
const canonical = execFileSync('git', ['-C', runtimeRepo, 'show', `${sha}:src/kotoba-client-runtime.js`]);
assert.deepEqual(staged, canonical);
assert.equal(createHash('sha256').update(staged).digest('hex'), expected);
assert.ok(!readFileSync(join(preview, 'index.html'), 'utf8').includes('kotoba-client-runtime.js'));
const runtime = await import(`data:text/javascript;base64,${staged.toString('base64')}`);
const descriptor = {schema: 'kotoba.app.client-runtime.v1', target: 'browser', profile: 'trusted-page-v1',
  entry: 'index.html', 'local-state': {adapter: 'indexeddb', schema: 'itonami.kaikei.v1', version: 1},
  workers: [], operations: []};
assert.deepEqual(runtime.clientRuntimeProblems(descriptor, []), []);
assert.equal(runtime.clientRuntimeConnectSrc(descriptor, []), "connect-src 'none'");
assert.deepEqual(runtime.effectiveClientOperations(descriptor), []);
assert.throws(() => runtime.createClientOperationBroker({runtime: descriptor, consentHost: {}}));
console.log('Canonical bytes and no-operation candidate verified; host integration is not qualified.');
