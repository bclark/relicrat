import assert from 'node:assert/strict';
import {before,after,test} from 'node:test';
import {chromium} from 'playwright';
import {mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
const base=process.env.RELICRAT_TEST_WEB_URL;assert.ok(base&&new URL(base).hostname==='127.0.0.1'&&new URL(base).port!=='56742','Use only an owned disposable loopback stack');
let browser;
before(async()=>{browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE});});after(async()=>{await browser?.close();});
async function setup(t){const context=await browser.newContext({viewport:{width:1440,height:1050}});t.after(()=>context.close());const r=await context.request.post(base+'/api/v1/auth/login',{data:{password:'synthetic-only-owner-password'},headers:{Origin:base}});assert.equal(r.status(),200);const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));t.after(()=>assert.deepEqual(errors,[]));return {page,context};}
function encoded(source,count){return source==='clz'?['Series,Issue,Publisher,Quantity,Collection Status',...Array.from({length:count},(_,i)=>`Synthetic series ${String(i%54).padStart(2,'0')},${Math.floor(i/54)+1},Test press,1,In Collection`)].join('\n'):['Title,Artist,Format,release_id',...Array.from({length:count},(_,i)=>`Synthetic album ${String(i).padStart(3,'0')},Synthetic artist ${String(i%45).padStart(2,'0')},CD,${i}`)].join('\n');}

test('whole-collection groups browse large synthetic Comics/Albums and preserve drafts across filters',async t=>{
 const {page,context}=await setup(t);
 for(const [source,count] of [['clz',1450],['discogs',465]]){const raw=encoded(source,count),sha=createHash('sha256').update(raw).digest('hex');const r=await context.request.post(base+`/api/v1/imports/commit?source=${source}&reviewed_sha256=${sha}`,{headers:{Origin:base,'Content-Type':'text/csv'},data:raw});assert.equal(r.status(),200,await r.text());}
 const unknown=await context.request.post(base+'/api/v1/inventory',{headers:{Origin:base},data:{title:'Synthetic unknown artist',collection_type:'record'}});assert.equal(unknown.status(),201);
 await page.goto(base);assert.equal(await page.getByLabel('Browse view',{exact:true}).inputValue(),'groups');
 await page.getByRole('button',{name:/^Comics \d+ copies · Browse collection$/}).click();
 await page.getByRole('button',{name:'Synthetic series 00 27 copies · Open group',exact:true}).click();
 const group=page.getByRole('region',{name:'Synthetic series 00 copies',exact:true});await group.getByRole('status').filter({hasText:'20 copies on this group page'}).waitFor();
 assert.equal(await group.getByRole('button',{name:'Open Synthetic series 00 #1',exact:true}).count(),1);
 await group.getByRole('button',{name:'Next copies',exact:true}).click();await group.getByRole('status').filter({hasText:'7 copies on this group page'}).waitFor();
 await group.getByRole('button',{name:'Open Synthetic series 00 #21',exact:true}).click();
 const editor=page.getByRole('form',{name:'Edit copy details',exact:true});await editor.getByLabel('Series/title',{exact:true}).fill('Keep this edit draft');
 const intake=page.getByRole('form',{name:'Add a find',exact:true});await intake.getByLabel(/^(Title|Series\/title|Album title|Movie or box-set title)$/).fill('Keep this intake draft');
 await page.getByRole('button',{name:'Next groups',exact:true}).click();await page.getByRole('button',{name:'Synthetic series 20 27 copies · Open group',exact:true}).waitFor();
 await page.getByLabel('Show collection type',{exact:true}).selectOption('record');await page.getByRole('button',{name:'Synthetic artist 00 11 copies · Open group',exact:true}).waitFor();
 assert.equal(await editor.getByLabel('Series/title',{exact:true}).inputValue(),'Keep this edit draft');assert.equal(await intake.getByLabel(/^(Title|Series\/title|Album title|Movie or box-set title)$/).inputValue(),'Keep this intake draft');
 await page.getByRole('button',{name:'Synthetic artist 00 11 copies · Open group',exact:true}).click();await page.getByRole('button',{name:'Open Synthetic artist 00 — Synthetic album 000',exact:true}).waitFor();
 if(process.env.RELICRAT_SCREENSHOTS){const p=resolve(process.env.RELICRAT_SCREENSHOTS);await mkdir(p,{recursive:true});await page.locator('.collection').screenshot({path:p+'/groups-desktop.png'});}
 await page.getByLabel('Find a copy',{exact:true}).fill('Synthetic album 000');await page.getByRole('button',{name:'Search',exact:true}).click();await page.getByRole('button',{name:'Synthetic artist 00 1 copy · Open group',exact:true}).waitFor();
 await page.getByRole('button',{name:'Clear search',exact:true}).click();await page.getByLabel('Find a copy',{exact:true}).fill('Synthetic unknown artist');await page.getByRole('button',{name:'Search',exact:true}).click();await page.getByRole('button',{name:'Artist not recorded 1 copy · Open group',exact:true}).click();await page.getByRole('button',{name:'Open Synthetic unknown artist',exact:true}).waitFor();
 await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));if(process.env.RELICRAT_SCREENSHOTS)await page.locator('.collection').screenshot({path:resolve(process.env.RELICRAT_SCREENSHOTS)+'/groups-mobile.png'});
 await page.getByLabel('Browse view',{exact:true}).selectOption('copies');await page.getByRole('button',{name:'Open Synthetic unknown artist',exact:true}).waitFor();
 const original=await(await context.request.get(base+'/api/v1/inventory/'+(await unknown.json()).id)).json();assert.equal(original.title,'Synthetic unknown artist');
});

test('storage filters apply to group counts and copies; errors retry and obsolete reads are ignored',async t=>{
 const {page,context}=await setup(t);let fail=true;let held=false;
 await page.route('**/api/v1/collection-groups?**',async route=>{const url=new URL(route.request().url());if(fail){await route.fulfill({status:502,contentType:'application/json',body:JSON.stringify({detail:'Synthetic group read failed'})});return;}if(url.searchParams.get('q')==='Old'){held=true;await new Promise(r=>setTimeout(r,600));}await route.continue();});
 await page.goto(base);await page.getByRole('alert').filter({hasText:'Synthetic group read failed'}).waitFor();fail=false;await page.getByRole('button',{name:'Reload inventory',exact:true}).click();await page.getByRole('button',{name:/^Albums \d+ copies · Browse collection$/}).waitFor();
 const location=await context.request.post(base+'/api/v1/storage-locations',{headers:{Origin:base},data:{name:'Synthetic grouping box'}});const box=(await location.json()).id;
 const r=await context.request.post(base+'/api/v1/inventory',{headers:{Origin:base},data:{title:'Synthetic shelved album',collection_type:'record',record_details:{artist:'Shelved artist'}}});const copy=await r.json();
 const move=await context.request.post(base+`/api/v1/inventory/${copy.id}/location`,{headers:{Origin:base},data:{storage_location_id:box,expected_storage_revision:0}});assert.equal(move.status(),200,await move.text());
 await page.getByRole('button',{name:'Reload inventory',exact:true}).click();await page.getByLabel('Storage location',{exact:true}).selectOption(box);await page.getByRole('button',{name:'Albums 1 copy · Browse collection',exact:true}).click();await page.getByRole('button',{name:'Shelved artist 1 copy · Open group',exact:true}).click();await page.getByRole('button',{name:'Open Shelved artist — Synthetic shelved album',exact:true}).waitFor();
 await page.getByLabel('Storage location',{exact:true}).selectOption('unassigned');await page.getByRole('button',{name:'Synthetic artist 00 11 copies · Open group',exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:/^Shelved artist/}).count(),0);
 const oldSeen=page.waitForRequest(r=>r.url().includes('collection-groups?')&&new URL(r.url()).searchParams.get('q')==='Old');await page.getByLabel('Find a copy',{exact:true}).fill('Old');await page.getByRole('button',{name:'Search',exact:true}).click();await oldSeen;
 await page.getByLabel('Find a copy',{exact:true}).fill('Synthetic album 000');await page.getByRole('button',{name:'Search',exact:true}).click();await page.getByRole('button',{name:'Synthetic artist 00 1 copy · Open group',exact:true}).waitFor();await page.waitForTimeout(700);assert.equal(await page.getByRole('button',{name:'Synthetic artist 00 1 copy · Open group',exact:true}).count(),1);
});

test('filter locations can page beyond 100 and failed pages require retry rather than skipping',async t=>{
 const {page}=await setup(t);let fail=true;const offsets=[];
 const locations=Array.from({length:101},(_,i)=>({id:`00000000-0000-0000-0000-${String(i+1).padStart(12,'0')}`,name:`Synthetic filter location ${i}`,parent_id:null}));
 await page.route('**/api/v1/storage-locations?**',async route=>{const offset=Number(new URL(route.request().url()).searchParams.get('offset')||0);offsets.push(offset);if(offset===100&&fail){await route.fulfill({status:502,contentType:'application/json',body:JSON.stringify({detail:'Synthetic location page failed'})});return;}await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(locations.slice(offset,offset+100))});});
 await page.goto(base);const more=page.getByRole('button',{name:'Load more filter locations',exact:true});await more.click();await page.getByRole('alert').filter({hasText:'Synthetic location page failed'}).waitFor();assert.equal(await more.isDisabled(),true);fail=false;await page.getByRole('button',{name:'Reload filter locations',exact:true}).click();await page.getByLabel('Storage location',{exact:true}).locator('option').filter({hasText:'Synthetic filter location 100'}).waitFor({state:'attached'});assert.deepEqual(offsets,[0,100,100]);assert.equal(await more.count(),0);assert.equal(await page.getByLabel('Storage location',{exact:true}).locator('option').count(),103);
});
