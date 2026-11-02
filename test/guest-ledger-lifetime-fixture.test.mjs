import test from 'node:test';
import assert from 'node:assert/strict';
import {MessageChannel} from 'node:worker_threads';
import {once} from 'node:events';
import {bindFixturePort} from '../experiments/local-ledger-port-fixture.mjs';
import {watchFixtureGuest} from '../experiments/guest-ledger-lifetime-fixture.mjs';

class Observer {
  constructor(callback) { this.callback = callback; Observer.last = this; }
  observe() {}
  disconnect() { this.disconnected = true; }
  emit(records) { if (!this.disconnected) this.callback(records); }
}
globalThis.MutationObserver = Observer;
function fixture(store) {
  const container = {isConnected:true, ownerDocument:{}};
  const frame = new EventTarget(); frame.parentNode = container; frame.isConnected = true;
  const {port1,port2} = new MessageChannel();
  const bridge = bindFixturePort(port1, store);
  return {frame,container,guest:port2,life:watchFixtureGuest(frame,container,bridge),observer:Observer.last};
}
const message = id => ({protocol:'kaikei.fixture.local-ledger.v1',id,action:'read',expectedRevision:null,value:null});

test('guest removal aborts the active storage read and suppresses queued reads', async () => {
  let started, aborted = false, calls = 0;
  const begun = new Promise(resolve => {started=resolve;});
  const f = fixture({read:signal => new Promise((resolve,reject) => {calls++; started(); signal.addEventListener('abort',()=>{aborted=true;reject(Error('abort'));},{once:true});}),write:async()=>{}});
  f.guest.postMessage(message(1)); f.guest.postMessage(message(2));
  await begun;
  const closed = once(f.guest,'close');
  f.frame.isConnected = false; f.observer.emit([{removedNodes:[f.frame]}]);
  await closed;
  assert.equal(aborted,true); assert.equal(calls,1); assert.equal(f.observer.disconnected,true);
  f.guest.close();
});

test('removed and reinserted guest and second load both close the port', async () => {
  for (const kind of ['reinserted','navigation']) {
    const f=fixture({read:async()=>({}),write:async()=>({})});
    f.frame.dispatchEvent(new Event('load'));
    const closed=once(f.guest,'close');
    if (kind==='reinserted') f.observer.emit([{removedNodes:[f.frame]}]);
    else f.frame.dispatchEvent(new Event('load'));
    await closed;
    assert.equal(f.observer.disconnected,true);
    f.guest.close();
  }
});

test('unrelated removals do not close the storage port', async () => {
  const f=fixture({read:async()=>({revision:0,value:null}),write:async()=>({})});
  f.observer.emit([{removedNodes:[{}]}]);
  const reply=once(f.guest,'message'); f.guest.postMessage(message(1));
  assert.equal((await reply)[0].ok,true);
  f.life.close(); f.guest.close();
});
