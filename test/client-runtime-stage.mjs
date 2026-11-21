// Validate the inert local-preview candidate. This does not qualify a host.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const [preview, runtimeRepo] = process.argv.slice(2);
if (!preview || !runtimeRepo) throw new Error('expected preview directory and canonical runtime repository');
const sha = 'a1b90e38c9e5334facfa993062e237299c70de10';
const expected = 'd6f67c058c5c40fc56fe500648dc79704a2eee02d4af75fc17898aad1f560a75';
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
// KOTOBA-159 (2026-11-22): every operation needs a complete disclosure; internal addresses need
// scope: "lan"; only a canonical broker can be mounted. The controls use a synthetic recipient.
const disclosure = {recipient: 'Synthetic Test Recipient', country: 'JP', data: ['テスト用のデータ'], 'special-care': false,
  purpose: '契約の確認のための合成の操作です。', frequency: 'one-time', withdrawal: '設定 › 許可した送信'};
const op = {capability: 'test/read', service: 'probe', operation: 'read', consent: 'each-operation',
  'data-categories': ['probe'], endpoint: {origin: 'https://probe.example.com', method: 'GET', path: '/probe'}};
const problems = (operation) => runtime.clientRuntimeProblems({...descriptor, operations: [operation]}, ['test/read']);
const refusedWith = (operation, error) => problems(operation).some((p) => p.error === error);
assert.deepEqual(problems({...op, disclosure}), []);
assert.ok(refusedWith(op, 'invalid-disclosure'));
for (const key of ['recipient', 'country', 'data', 'purpose', 'frequency', 'withdrawal']) {
  const {[key]: _omitted, ...partial} = disclosure;
  assert.ok(refusedWith({...op, disclosure: partial}, 'invalid-disclosure'), key);
}
assert.ok(refusedWith({...op, disclosure: {...disclosure, country: 'US'}}, 'invalid-disclosure'));
const internal = {...op, disclosure, endpoint: {...op.endpoint, origin: 'https://192.168.1.10'}};
assert.ok(refusedWith(internal, 'internal-address-requires-lan-scope'));
assert.deepEqual(problems({...internal, scope: 'lan'}), []);
await assert.rejects(() => runtime.mountRestrictedClientApp({artifact: {html: '<p></p>'}, container: {}, broker: {invoke: async () => null}}), /trusted host broker required/);
console.log('Canonical bytes, no-operation candidate and KOTOBA-159 refusals verified; host integration is not qualified.');
