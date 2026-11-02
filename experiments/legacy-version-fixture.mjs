// JUN-771 synthetic schema-upgrade experiment; never touches a real ledger.
const PREFIX = 'kaikei-jun771-version-synthetic-';

function openOld(name) {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(name, 2);
    request.onupgradeneeded = () => {
      request.result.createObjectStore('state');
      request.result.createObjectStore('files');
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}
function seed(db) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(['state', 'files'], 'readwrite');
    tx.objectStore('state').put('old-synthetic-ledger', 'ledger');
    tx.objectStore('files').put('old-synthetic-file', 'file');
    tx.oncomplete = () => resolve();
    tx.onabort = () => reject(tx.error || Error('seed aborted'));
  });
}
function upgrade(name, old) {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(name, 3);
    let blocked = false;
    request.onblocked = () => { blocked = true; old.close(); };
    request.onupgradeneeded = () => request.result.createObjectStore('revisions');
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve({db: request.result, blocked});
  });
}
function readData(db) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(['state', 'files'], 'readonly');
    const ledger = tx.objectStore('state').get('ledger');
    const file = tx.objectStore('files').get('file');
    tx.oncomplete = () => resolve([ledger.result, file.result]);
    tx.onabort = () => reject(tx.error || Error('read aborted'));
  });
}
function legacyReopen(name) {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(name, 2);
    request.onsuccess = () => { request.result.close(); reject(Error('old version unexpectedly reopened')); };
    request.onerror = () => request.error?.name === 'VersionError' ? resolve() : reject(request.error);
  });
}
export async function runLegacyVersionFixture() {
  const name = PREFIX + crypto.randomUUID();
  const old = await openOld(name);
  await seed(old);
  // Deliberately keep the old connection open; upgrade must first report blocked.
  const {db, blocked} = await upgrade(name, old);
  try {
    if (!blocked) throw Error('upgrade unexpectedly bypassed old connection');
    const [ledger, file] = await readData(db);
    if (ledger !== 'old-synthetic-ledger' || file !== 'old-synthetic-file') throw Error('upgrade changed old data');
    await legacyReopen(name);
    return 'PASS: upgrade blocked until old connection closed; both values preserved; old version refused';
  } finally { db.close(); }
}
