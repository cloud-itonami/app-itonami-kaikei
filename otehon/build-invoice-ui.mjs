// Otehon-only static product hook. No native fallback, BFF or deployment.
import fs from 'node:fs';import path from 'node:path';import cp from 'node:child_process';import{fileURLToPath}from'node:url';
const here=path.dirname(fileURLToPath(import.meta.url)),pin=JSON.parse(fs.readFileSync(path.join(here,'invoice-ui-source.json')));
const[source,canonical,target]=process.argv.slice(2);if(!source||!canonical||!target)throw Error('explicit pinned UI repo, canonical repo and fresh output required');
const repo=fs.realpathSync(source),out=path.resolve(target);
const revision=cp.execFileSync('git',['rev-parse','HEAD'],{cwd:repo,encoding:'utf8'}).trim();
if(revision!==pin.revision)throw Error('invoice UI source revision mismatch');
cp.execFileSync('git',['diff','--exit-code','HEAD','--',pin.entry],{cwd:repo,stdio:'pipe'});
const entry=path.join(repo,pin.entry);
cp.execFileSync(process.execPath,[path.join(entry,'build.mjs'),fs.realpathSync(canonical)],{stdio:'inherit'});
cp.execFileSync(process.execPath,[path.join(entry,'install-owned.mjs'),out,pin.product],{stdio:'inherit'});
console.log(JSON.stringify({product:pin.product,revision:pin.revision,published:false,host:'requires trusted local Otehon credential host'}));
