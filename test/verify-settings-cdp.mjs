// Synthetic-only probe: use an isolated Chrome profile and loopback preview.
// It changes the preview's fiscal-year setting and reloads the page.
const [debugPort, fixtureUrl] = process.argv.slice(2);
if (!/^\d+$/.test(debugPort || "") || !fixtureUrl?.startsWith("http://127.0.0.1:")) throw Error("usage: node test/verify-settings-cdp.mjs DEBUG_PORT FIXTURE_URL");
const pages = await (await fetch(`http://127.0.0.1:${debugPort}/json`)).json();
const page = pages.find(p => p.type === 'page' && p.url === fixtureUrl);
const ws = new WebSocket(page.webSocketDebuggerUrl); await new Promise(r => ws.onopen = r);
let id=0; const pending=new Map(); ws.onmessage=({data})=>{const x=JSON.parse(data);if(x.id){let p=pending.get(x.id);pending.delete(x.id);x.error?p.reject(Error(x.error.message)):p.resolve(x.result)}};
const call=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method,params}))});
async function run(expression){const x=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true}); if(x.exceptionDetails) throw Error(JSON.stringify(x.exceptionDetails));return x.result.value}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
await run(`scittle.core.eval_string('(re-frame.core/dispatch-sync [:set-fy-start 7])')`);
let stored;for(let i=0;i<50;i++){await sleep(100);stored=await run(`new Promise((resolve,reject)=>{const q=indexedDB.open('itonami.kaikei',2);q.onerror=()=>reject(q.error);q.onsuccess=()=>{const db=q.result,r=db.transaction('state').objectStore('state').get('itonami.kaikei.v1');r.onsuccess=()=>{db.close();resolve(r.result??null)};r.onerror=()=>reject(r.error)}})`);if(stored?.includes(':fy-start 7'))break}
if(!stored?.includes(':fy-start 7')) throw Error('settings-only state not persisted: '+stored);
await call('Page.reload');await sleep(3000);
const value=await run(`scittle.core.eval_string('(get-in @re-frame.db/app-db [:ui :fy-start])')`);
if(value!==7) throw Error('settings not restored: '+value);
console.log('PASS: empty ledger fiscal-year setting persisted to IndexedDB and restored after reload');ws.close();
