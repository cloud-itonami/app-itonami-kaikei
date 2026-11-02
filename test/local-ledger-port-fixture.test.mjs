import test from 'node:test';
import assert from 'node:assert/strict';
import {MessageChannel} from 'node:worker_threads';
import {once} from 'node:events';
import {bindFixturePort} from '../experiments/local-ledger-port-fixture.mjs';

const protocol = 'kaikei.fixture.local-ledger.v1';
const read = id => ({protocol, id, action:'read', expectedRevision:null, value:null});
const write = (id, value = 'synthetic') => ({protocol, id, action:'write', expectedRevision:0, value});
const pair = store => {
  const {port1, port2} = new MessageChannel();
  const bridge = bindFixturePort(port1, store);
  return {guest:port2, bridge};
};

test('ordered requests are serialized and receive bounded responses', async () => {
  const calls = [];
  const {guest, bridge} = pair({read:async()=>{calls.push('read'); return {revision:0,value:null};},
    write:async(revision,value)=>{calls.push('write'); return {ok:true,revision:revision+1,value};}});
  const replies = [];
  guest.on('message', value => replies.push(value));
  guest.postMessage(read(1)); guest.postMessage(write(2));
  while (replies.length < 2) await once(guest, 'message');
  assert.deepEqual(calls, ['read','write']);
  assert.deepEqual(replies.map(x=>x.id), [1,2]);
  assert.ok(replies.every(x=>x.ok && x.protocol === protocol));
  bridge.close(); guest.close();
});

for (const [name, message] of [
  ['unexpected operation', {...read(1), action:'delete'}],
  ['extra field', {...read(1), key:'another-ledger'}],
  ['id gap', read(2)],
  ['oversize UTF-8', write(1, 'あ'.repeat(22000))],
  ['invalid revision', {...write(1), expectedRevision:-1}],
]) test(`${name} closes the port before any storage access`, async () => {
  let calls = 0;
  const {guest} = pair({read:async()=>{calls++;}, write:async()=>{calls++;}});
  const closed = once(guest, 'close'); guest.postMessage(message); await closed;
  assert.equal(calls, 0);
});

test('replay closes the port and cannot cause a second read', async () => {
  let calls = 0;
  const {guest} = pair({read:async()=>{calls++; return {};}, write:async()=>{calls++;}});
  const first = once(guest, 'message'); guest.postMessage(read(1)); await first;
  const closed = once(guest, 'close'); guest.postMessage(read(1)); await closed;
  assert.equal(calls, 1);
});

test('transferred port is refused', async () => {
  let calls = 0;
  const {guest} = pair({read:async()=>{calls++;}, write:async()=>{calls++;}});
  const transferred = new MessageChannel();
  const closed = once(guest, 'close');
  guest.postMessage(read(1), [transferred.port1]); await closed;
  assert.equal(calls, 0); transferred.port2.close();
});

test('flood closes the port and queued calls do not start', async () => {
  let release, calls = 0;
  const blocked = new Promise(resolve => {release = resolve;});
  const {guest} = pair({read:async()=>{calls++; await blocked; return {};}, write:async()=>{calls++;}});
  const closed = once(guest, 'close');
  for (let id = 1; id <= 9; id++) guest.postMessage(read(id));
  await closed;
  release();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(calls, 1);
});
