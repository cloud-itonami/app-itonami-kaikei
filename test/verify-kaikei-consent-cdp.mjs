// Manual synthetic-only Chrome DevTools probe. Start an isolated Chrome profile
// with a loopback debugging port and pass DEBUG_PORT and FIXTURE_URL.
// CDP-dispatched trusted input is automation, not a human consent record.
const [debugPort,fixtureUrl]=process.argv.slice(2);
if (!/^\d+$/.test(debugPort || '') || !/^http:\/\/127\.0\.0\.1:\d+\//.test(fixtureUrl || '')) throw Error('usage: node test/verify-kaikei-consent-cdp.mjs DEBUG_PORT FIXTURE_URL');
const debugOrigin=`http://127.0.0.1:${debugPort}`;
const targets=await (await fetch(`${debugOrigin}/json`)).json();
const page=targets.find(t=>t.type==='page' && t.url===fixtureUrl);
if(!page) throw Error('page not found');
const ws=new WebSocket(page.webSocketDebuggerUrl); await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j});
let id=0;const pending=new Map();ws.onmessage=({data})=>{const m=JSON.parse(data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}};
const call=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method,params}))});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function evaluate(expression,contextId){const r=await call('Runtime.evaluate',{expression,contextId,returnByValue:true,awaitPromise:true});if(r.exceptionDetails) throw Error(r.exceptionDetails.text);return r.result.value}
async function until(f,expected){for(let n=0;n<120;n++){const v=await f();if(expected(v))return v;await sleep(100)}throw Error('condition timeout')}
await call('Page.enable'); await call('Runtime.enable');
await until(()=>evaluate("document.querySelector('#status')?.textContent"),v=>v==='合成 probe 稼働中');
const iframe= (await (await fetch(`${debugOrigin}/json`)).json()).find(t=>t.type==='iframe' && t.parentId===page.id);if(!iframe)throw Error('guest target missing');
const child=new WebSocket(iframe.webSocketDebuggerUrl); await new Promise((r,j)=>{child.onopen=r;child.onerror=j});
let cid=0;const cp=new Map();child.onmessage=({data})=>{const m=JSON.parse(data);if(m.id){const p=cp.get(m.id);cp.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}};
const childCall=(method,params={})=>new Promise((resolve,reject)=>{const n=++cid;cp.set(n,{resolve,reject});child.send(JSON.stringify({id:n,method,params}))});
const originalEvaluate=evaluate;evaluate=async(expression,contextId)=>{if(contextId!=='guest')return originalEvaluate(expression,contextId);const r=await childCall('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.text);return r.result.value};
const context='guest';
await until(()=>evaluate("!!document.querySelector('#fixture-request')",context),Boolean);
async function click(selector,ctx,offset={x:0,y:0}){const rect=await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e)return null;const r=e.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2,disabled:e.disabled}})()`,ctx);if(!rect||rect.disabled)throw Error('button absent or disabled '+selector);const x=rect.x+offset.x,y=rect.y+offset.y;await call('Input.dispatchMouseEvent',{type:'mouseMoved',x,y});await call('Input.dispatchMouseEvent',{type:'mousePressed',x,y,button:'left',clickCount:1});await call('Input.dispatchMouseEvent',{type:'mouseReleased',x,y,button:'left',clickCount:1})}
async function request(){const pos=await evaluate("(()=>{const r=document.querySelector('iframe').getBoundingClientRect();return {x:r.left,y:r.top}})()");await click('#fixture-request',context,pos);await until(()=>evaluate("document.querySelector('dialog')?.open"),Boolean)}
const count=()=>evaluate("document.querySelector('#counter').textContent");
const guestResult=()=>evaluate("document.querySelector('#fixture-result').textContent",context);
await request();await click('dialog button:first-of-type');await until(guestResult,v=>v==='denied');if(await count()!=='HTTP resource entries 0')throw Error('denied request recorded');console.log('DENY',await count());await sleep(500);
await request();await evaluate("document.querySelector('#fixture-result').textContent='waiting'",context);await until(()=>evaluate("!document.querySelector('dialog button:last-of-type').disabled"),Boolean);await click('dialog button:last-of-type');const allowed=await until(guestResult,v=>v.startsWith('HTTP status') || v==='denied');if(allowed!=='HTTP status 200')throw Error('approved request failed: '+allowed);console.log('ALLOW_RESULT',allowed);await until(count,v=>v.includes(' 1'));console.log('AFTER_ALLOW',await count());
await sleep(500);await request();await evaluate("document.querySelector('#fixture-result').textContent='waiting'",context);await click('dialog button:first-of-type');await until(guestResult,v=>v==='denied');if(await count()!=='HTTP resource entries 1')throw Error('second denial recorded a request');console.log('DENY_AGAIN',await count());
child.close();ws.close();
