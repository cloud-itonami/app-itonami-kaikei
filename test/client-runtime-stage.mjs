// Validate the inert local-preview candidate. This does not qualify a host.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const [preview, runtimeRepo] = process.argv.slice(2);
if (!preview || !runtimeRepo) throw new Error('expected preview directory and canonical runtime repository');
const sha = '86fce2b078dfcab7d58061afd53c716cc574f85c';
const expected = '0d8ed12a795fdf46de32ac01c0675adec9f22df64f24769a4d4a960d6a345ac5';
const staged = readFileSync(join(preview, 'runtime/kotoba-client-runtime.js'));
const canonical = execFileSync('git', ['-C', runtimeRepo, 'show', `${sha}:lib/kotoba.wasmWebcomponent/src/kotoba-client-runtime.js`]);
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
