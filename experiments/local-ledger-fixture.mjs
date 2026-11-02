// JUN-771: synthetic-only IndexedDB experiment. Not a product storage bridge.
// The fixed test database never opens or migrates the user's kaikei database.
const DATABASE = 'kaikei-jun771-synthetic-fixture';
const STORE = 'ledger';
const KEY = 'synthetic';
const MAX_BYTES = 65536;

function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(STORE);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(new Error('storage-open-failed'));
    request.onblocked = () => reject(new Error('storage-open-blocked'));
  });
}

function validRecord(record) {
  return record && Number.isSafeInteger(record.revision) && record.revision > 0
    && typeof record.value === 'string'
    && new TextEncoder().encode(record.value).byteLength <= MAX_BYTES;
}

// All callers use the same fixed test key. No caller-supplied DB/store/key.
export async function readFixture() {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readonly');
    const request = tx.objectStore(STORE).get(KEY);
    let result;
    request.onsuccess = () => {
      const record = request.result;
      if (record === undefined) result = {revision: 0, value: null};
      else if (validRecord(record)) result = {revision: record.revision, value: record.value};
      else { tx.abort(); }
    };
    tx.oncomplete = () => { db.close(); resolve(result); };
    tx.onabort = tx.onerror = () => { db.close(); reject(new Error('storage-read-failed')); };
  });
}

// IndexedDB serializes readwrite transactions for this store. Compare and write
// occur in the same transaction; success is returned only after commit.
export async function compareAndSwapFixture(expectedRevision, value) {
  if (!Number.isSafeInteger(expectedRevision) || expectedRevision < 0
      || expectedRevision >= Number.MAX_SAFE_INTEGER || typeof value !== 'string'
      || new TextEncoder().encode(value).byteLength > MAX_BYTES) {
    throw new TypeError('invalid-fixture-write');
  }
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite');
    const store = tx.objectStore(STORE);
    const request = store.get(KEY);
    let result;
    request.onsuccess = () => {
      const old = request.result;
      if (old !== undefined && !validRecord(old)) { tx.abort(); return; }
      const revision = old === undefined ? 0 : old.revision;
      if (revision !== expectedRevision) { result = {ok: false, revision}; return; }
      const next = revision + 1;
      store.put({revision: next, value}, KEY);
      result = {ok: true, revision: next};
    };
    tx.oncomplete = () => { db.close(); resolve(result); };
    tx.onabort = tx.onerror = () => { db.close(); reject(new Error('storage-write-failed')); };
  });
}
