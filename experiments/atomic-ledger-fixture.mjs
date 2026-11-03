// JUN-771 experiment: synthetic data only, not connected to kaikei.
// Each run uses a fresh random key in this fixed test database. Never opens user data.
const DB = 'kaikei-jun771-atomic-synthetic';
const STORES = ['ledgers', 'files'];

function open() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB, 1);
    request.onupgradeneeded = () => { for (const name of STORES) request.result.createObjectStore(name); };
    request.onerror = () => reject(request.error);
    request.onblocked = () => reject(Error('test database blocked'));
    request.onsuccess = () => resolve(request.result);
  });
}

// Fixed single synthetic file per run. The key is created internally, never guest supplied.
function write(db, key, expected, ledger, file, abortAfterRequests = false, signal, afterQueue) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) { reject(Error('synthetic abort')); return; }
    const tx = db.transaction(STORES, 'readwrite');
    const onAbort = () => { try { tx.abort(); } catch {} };
    signal?.addEventListener('abort', onAbort, {once:true});
    const finish = () => signal?.removeEventListener('abort', onAbort);
    const ledgers = tx.objectStore('ledgers');
    const files = tx.objectStore('files');
    let conflict = false;
    const read = ledgers.get(key);
    read.onsuccess = () => {
      const record = read.result;
      const revision = record === undefined ? 0 : record.revision;
      if (!Number.isSafeInteger(revision) || revision !== expected) {
        conflict = true; tx.abort(); return;
      }
      ledgers.put({revision: revision + 1, value: ledger}, key);
      if (file === null) files.delete(key); else files.put(file, key);
      if (abortAfterRequests) tx.abort();
      else if (afterQueue) afterQueue();
    };
    tx.oncomplete = () => { finish(); resolve('committed'); };
    tx.onabort = () => { finish(); conflict ? resolve('conflict') : reject(tx.error || Error('synthetic abort')); };
  });
}

function read(db, key) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORES, 'readonly');
    const ledger = tx.objectStore('ledgers').get(key);
    const file = tx.objectStore('files').get(key);
    tx.oncomplete = () => resolve({ledger: ledger.result, file: file.result});
    tx.onabort = () => reject(tx.error || Error('read aborted'));
  });
}

function requireState(state, revision, ledger, file) {
  if (state.ledger?.revision !== revision || state.ledger?.value !== ledger || state.file !== file)
    throw Error('unexpected atomic state: ' + JSON.stringify(state));
}

export async function runAtomicFixture() {
  const db = await open();
  const key = crypto.randomUUID();
  try {
    if (await write(db, key, 0, 'original', 'original-file') !== 'committed') throw Error('seed failed');
    const race = await Promise.all([write(db, key, 1, 'A', 'file-A'), write(db, key, 1, 'B', 'file-B')]);
    if (race.filter(x => x === 'committed').length !== 1 || race.filter(x => x === 'conflict').length !== 1)
      throw Error('race did not reject exactly one write');
    const winner = await read(db, key);
    if (winner.ledger?.revision !== 2 || ![['A', 'file-A'], ['B', 'file-B']].some(([l, f]) => winner.ledger.value === l && winner.file === f))
      throw Error('winning ledger and file differ');
    try {
      await write(db, key, 2, 'must-not-commit', null, true);
      throw Error('synthetic abort unexpectedly committed');
    } catch (error) {
      if (error.message === 'synthetic abort unexpectedly committed') throw error;
    }
    requireState(await read(db, key), 2, winner.ledger.value, winner.file);
    if (await write(db, key, 2, 'deleted-file', null) !== 'committed') throw Error('delete failed');
    requireState(await read(db, key), 3, 'deleted-file', undefined);
    return 'PASS: competing writes, rollback of both stores, and atomic file deletion';
  } finally { db.close(); }
}

// Fixture-only primitives for the guest-lifetime experiment.
export {open as openAtomicFixture, write as writeAtomicFixture, read as readAtomicFixture};
