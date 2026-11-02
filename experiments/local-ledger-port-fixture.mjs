// JUN-771: protocol experiment for a *pre-bound*, synthetic-only port.
// Binding a port is not guest authentication; do not use with real data.
const PROTOCOL = 'kaikei.fixture.local-ledger.v1';
const MAX_PENDING = 8;
const MAX_BYTES = 65536;
const fields = ['action', 'expectedRevision', 'id', 'protocol', 'value'];

function validMessage(data) {
  if (!data || Object.getPrototypeOf(data) !== Object.prototype
      || Object.keys(data).sort().join(',') !== fields.join(',')
      || data.protocol !== PROTOCOL || !Number.isSafeInteger(data.id) || data.id < 1) return false;
  if (data.action === 'read') return data.expectedRevision === null && data.value === null;
  return data.action === 'write' && Number.isSafeInteger(data.expectedRevision)
    && data.expectedRevision >= 0 && data.expectedRevision < Number.MAX_SAFE_INTEGER
    && typeof data.value === 'string' && new TextEncoder().encode(data.value).byteLength <= MAX_BYTES;
}

export function bindFixturePort(port, store) {
  if (!port || typeof port.postMessage !== 'function' || typeof port.addEventListener !== 'function'
      || typeof store?.read !== 'function' || typeof store?.write !== 'function') throw new TypeError('invalid-fixture-port');
  let closed = false, pending = 0, lastId = 0, tail = Promise.resolve();
  function close() {
    if (closed) return;
    closed = true;
    port.removeEventListener('message', onMessage);
    port.close();
  }
  function onMessage(event) {
    if (closed) return;
    const data = event.data;
    if (event.ports?.length || !validMessage(data) || data.id !== lastId + 1 || pending >= MAX_PENDING) {
      close(); return;
    }
    lastId = data.id;
    pending += 1;
    tail = tail.then(async () => {
      if (closed) return;
      try {
        const result = data.action === 'read' ? await store.read() : await store.write(data.expectedRevision, data.value);
        if (!closed) port.postMessage({protocol: PROTOCOL, id: data.id, ok: true, result});
      } catch {
        if (!closed) port.postMessage({protocol: PROTOCOL, id: data.id, ok: false, error: 'fixture-storage-failed'});
      } finally { pending -= 1; }
    });
  }
  port.addEventListener('message', onMessage);
  port.start();
  return Object.freeze({close});
}
