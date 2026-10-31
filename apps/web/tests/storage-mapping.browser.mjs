import assert from 'node:assert/strict';
import {test,before,after} from 'node:test';
import {chromium} from 'playwright';
import {mkdir} from 'node:fs/promises';
const base=process.env.RELICRAT_TEST_WEB_URL;
assert.ok(base&&new URL(base).hostname==='127.0.0.1'&&new URL(base).port!=='56742','Use only a disposable loopback stack');
const runId=Date.now();
let browser;
before(async()=>{browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE});});
after(async()=>{await browser?.close();});
async function setup(t,number){
 number=`${number}-${runId}`;
 const context=await browser.newContext({viewport:{width:1440,height:1050}});t.after(()=>context.close());
 assert.equal((await context.request.post(base+'/api/v1/auth/login',{data:{password:'synthetic-only-owner-password'},headers:{Origin:base}})).status(),200);
 const json=async(path,body)=>{const r=await context.request.post(base+'/api/v1/'+path,{data:body,headers:{Origin:base}});assert.ok(r.ok(),await r.text());return r.json();};
 const raw=['Series,Issue,Publisher,Quantity,Collection Status,Core ComicID,Storage Box',`Synthetic mapping ${number},1,Test Press,25,In Collection,shared,Trial Box`,...Array.from({length:22},(_,i)=>`Synthetic mapping ${number},${i+2},Test Press,1,In Collection,shared,Label ${i.toString().padStart(2,'0')}`)].join('\r\n');
 const upload=async(path)=>{const r=await context.request.post(base+'/api/v1/imports/'+path,{data:raw,headers:{Origin:base,'Content-Type':'text/csv'}});assert.ok(r.ok(),await r.text());return r.json();};
 const preview=await upload('preview?source=clz');const result=await upload('commit?source=clz&reviewed_sha256='+preview.sha256);const batch=result.batch;
 const rows=await (await context.request.get(base+`/api/v1/imports/${batch.id}/rows?limit=100`)).json();
 const destination=await json('storage-locations',{name:`Synthetic mapping destination ${number}`});
 await json(`inventory/${rows[0].copy_id}/location`,{storage_location_id:destination.id,expected_storage_revision:0});
 const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));t.after(()=>assert.deepEqual(errors,[]));
 await page.goto(base);await page.getByRole('button',{name:'Import CSV',exact:true}).click();await page.getByRole('button',{name:'Reload import history',exact:true}).click();
 await page.getByRole('button',{name:'Map storage boxes',exact:true}).first().click();
 const section=page.getByRole('region',{name:'Map imported storage boxes',exact:true});
 await section.getByRole('button',{name:'Next labels',exact:true}).click();
 await section.getByRole('radio',{name:/Trial Box/}).check();
 await section.getByLabel('Physical location',{exact:true}).selectOption(destination.id);
 return {page,section,context,json,batch,rows,destination};
}

test('review, paginate, create destination, then confirm manual storage moves',async t=>{
 const {page,section,context,batch,rows,destination}=await setup(t,1);
 await section.getByText('Create a physical location',{exact:true}).click();
 await section.getByLabel('New location name',{exact:true}).fill('Synthetic new mapping box');
 await section.getByLabel('Parent location (optional)',{exact:true}).selectOption(destination.id);
 await section.getByRole('button',{name:'Create location for mapping',exact:true}).click();
 await section.getByRole('status').filter({hasText:'Location created. No copies moved.'}).waitFor();
 assert.equal((await (await context.request.get(base+`/api/v1/inventory/${rows[1].copy_id}`)).json()).storage_revision,0);
 const target=await section.getByLabel('Physical location',{exact:true}).inputValue();
 await section.getByRole('button',{name:'Preview storage mapping',exact:true}).click();
 await section.getByRole('heading',{name:'3. Review copies for Synthetic new mapping box'}).waitFor();
 assert.equal(await section.getByRole('button',{name:'Assign 24 copies',exact:true}).isDisabled(),true);
 await section.getByRole('button',{name:'Next mapping copies',exact:true}).click();await section.getByRole('navigation',{name:'Mapping copy pages',exact:true}).getByText('Page 2',{exact:true}).waitFor();
 assert.equal(await section.locator('ol li').count(),4);
 if(process.env.RELICRAT_SCREENSHOTS){await mkdir(process.env.RELICRAT_SCREENSHOTS,{recursive:true});await section.screenshot({path:process.env.RELICRAT_SCREENSHOTS+'/mapping-desktop.png'});await page.setViewportSize({width:390,height:844});await section.screenshot({path:process.env.RELICRAT_SCREENSHOTS+'/mapping-mobile.png'});await page.setViewportSize({width:1440,height:1050});}
 await section.getByRole('checkbox',{name:'I reviewed the 24 eligible copies and their destination.',exact:true}).check();
 await section.getByRole('button',{name:'Assign 24 copies',exact:true}).dblclick();
 await section.getByRole('status').filter({hasText:'Added 24 copies to Synthetic new mapping box. Preserved 1 copy.'}).waitFor();
 const placed=await (await context.request.get(base+'/api/v1/inventory?limit=100&q='+encodeURIComponent('Synthetic mapping 1-'+runId))).json();
 for(const row of rows.slice(1,25)){
  const copy=placed.find(copy=>copy.id===row.copy_id);assert.ok(copy);assert.equal(copy.storage_location_id,target);assert.equal(copy.storage_revision,1);
 }
 for(const row of [rows[1],rows[24]]){
  const history=await (await context.request.get(base+`/api/v1/inventory/${row.copy_id}/locations`)).json();assert.equal(history.length,1);
 }
 assert.equal((await (await context.request.get(base+`/api/v1/inventory/${rows[0].copy_id}`)).json()).storage_location_id,destination.id);
 assert.equal((await (await context.request.get(base+`/api/v1/imports/${batch.id}/rows?limit=100`)).json())[1].source['Storage Box'],'Trial Box');
 await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
});

test('stale review requires another preview and preserves a manual placement',async t=>{
 const {section,json,rows,destination}=await setup(t,2);
 await section.getByRole('button',{name:'Preview storage mapping',exact:true}).click();
 await section.getByRole('checkbox',{name:/I reviewed the 24/}).check();
 await json(`inventory/${rows[1].copy_id}/location`,{storage_location_id:destination.id,expected_storage_revision:0});
 await section.getByRole('button',{name:'Assign 24 copies',exact:true}).click();
 await section.getByRole('alert').filter({hasText:'Copies or the destination changed'}).waitFor();
 assert.equal(await section.getByRole('checkbox',{name:/I reviewed/}).count(),0);
 await section.getByRole('button',{name:'Preview storage mapping',exact:true}).click();
 await section.getByRole('button',{name:'Assign 23 copies',exact:true}).waitFor();
});

test('uncertain mapping is never automatically retried or left confirmable',async t=>{
 const {page,section}=await setup(t,3);
 await section.getByRole('button',{name:'Preview storage mapping',exact:true}).click();
 await section.getByRole('checkbox',{name:/I reviewed the 24/}).check();let writes=0;
 await page.route('**/storage-apply',async route=>{writes++;await route.fulfill({status:502,contentType:'application/json',body:JSON.stringify({detail:'Synthetic uncertain mapping'})});});
 await section.getByRole('button',{name:'Assign 24 copies',exact:true}).click();
 await section.getByRole('alert').filter({hasText:'Synthetic uncertain mapping'}).waitFor();assert.equal(writes,1);
 assert.equal(await section.getByRole('button',{name:'Assign 24 copies',exact:true}).count(),0);
 await section.getByRole('button',{name:'Preview storage mapping',exact:true}).click();
 assert.equal(await section.getByRole('button',{name:'Assign 24 copies',exact:true}).isDisabled(),true);
});

test('uncertain location creation requires inspection before another creation',async t=>{
 const {page,section}=await setup(t,4);
 await section.getByText('Create a physical location',{exact:true}).click();
 await section.getByLabel('New location name',{exact:true}).fill('Synthetic uncertain location');let writes=0;
 await page.route('**/api/v1/storage-locations',async route=>{if(route.request().method()!=='POST')return route.continue();writes++;await route.fulfill({status:502,contentType:'application/json',body:JSON.stringify({detail:'Synthetic uncertain creation'})});});
 await section.getByRole('button',{name:'Create location for mapping',exact:true}).click();
 await section.getByRole('alert').filter({hasText:'Creation could not be confirmed'}).waitFor();
 assert.equal(writes,1);assert.equal(await section.getByRole('button',{name:'Create location for mapping',exact:true}).isDisabled(),true);
});
