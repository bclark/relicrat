import assert from 'node:assert/strict';
import {mkdir} from 'node:fs/promises';
import {after,before,test} from 'node:test';
import {chromium} from 'playwright';
import {chooseCollection} from './journey-test-helpers.mjs';

const base=process.env.RELICRAT_TEST_WEB_URL;
assert.ok(base&&new URL(base).hostname==='127.0.0.1'&&new URL(base).port!=='56742','Use only a disposable synthetic stack');
let browser;
before(async()=>{browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE});});
after(async()=>{await browser?.close();});
for(const [layout,viewport] of [['desktop',{width:1440,height:1050}],['mobile',{width:320,height:840}]]){
 test(`review a bulk move, preserve history and reject stale selections on ${layout}`,async t=>{
  const context=await browser.newContext({viewport});t.after(()=>context.close());
  const post=async(path,data)=>{const r=await context.request.post(base+'/api/v1/'+path,{headers:{Origin:base},data});assert.ok(r.ok(),await r.text());return r.json();};
  const get=async path=>{const r=await context.request.get(base+'/api/v1/'+path);assert.ok(r.ok(),await r.text());return r.json();};
  await post('auth/login',{password:'synthetic-only-owner-password'});
  const boxes=[];for(const suffix of ['A','B'])boxes.push(await post('storage-locations',{name:`Synthetic bulk ${layout} box ${suffix}`}));
  const prefix=`Synthetic bulk ${layout} copy`;
  const copies=[];
  for(let i=0;i<2;i++){
   const copy=await post('inventory',{title:`${prefix} ${i}`,collection_type:'other'});
   await post(`inventory/${copy.id}/location`,{storage_location_id:boxes[0].id,expected_storage_revision:0});copies.push(copy);
  }
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));t.after(()=>assert.deepEqual(errors,[]));
  await page.goto(base);await chooseCollection(page,'other');
  async function search(){await page.getByLabel('Find a copy',{exact:true}).fill(prefix);await page.getByRole('button',{name:'Search',exact:true}).click();for(const copy of copies)await page.locator(`#copy-row-${copy.id}`).waitFor();}
  await search();
  await page.locator(`#copy-row-${copies[0].id}`).click();
  await page.getByText(`Current location: ${boxes[0].name}`,{exact:true}).waitFor();
  await page.getByRole('button',{name:'Back to collection',exact:true}).click();
  let capturedSelection=false;
  async function select(destination,start=true){
   if(start)await page.getByRole('button',{name:'Select copies to move',exact:true}).click();
   for(const copy of copies)await page.getByRole('checkbox',{name:`Select ${copy.title} · Copy ${copy.id}`,exact:true}).check();
   await page.getByLabel('Move selected copies to',{exact:true}).selectOption(destination.id);
   if(!capturedSelection){await capture('selection');capturedSelection=true;}
   await page.getByRole('button',{name:'Review move',exact:true}).click();
  }
  async function confirm(){await page.getByRole('checkbox',{name:'I reviewed these copies and their destination.',exact:true}).check();await page.getByRole('button',{name:'Move 2 copies',exact:true}).click();}
  async function capture(state){
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No horizontal overflow');
   if(process.env.RELICRAT_SCREENSHOTS){await mkdir(process.env.RELICRAT_SCREENSHOTS,{recursive:true});await page.screenshot({path:`${process.env.RELICRAT_SCREENSHOTS}/bulk-${layout}-${state}.png`,fullPage:true});}
  }
  await select(boxes[1]);
  await page.getByRole('heading',{name:`Review move to ${boxes[1].name}`,exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Move 2 copies',exact:true}).isEnabled(),false);
  await capture('review');await confirm();
  await page.getByRole('status').filter({hasText:`Moved 2 copies to ${boxes[1].name}.`}).waitFor();
  await page.locator(`#copy-row-${copies[0].id}`).click();
  await page.getByText(`Current location: ${boxes[1].name}`,{exact:true}).waitFor();
  await page.getByRole('button',{name:'Back to collection',exact:true}).click();
  await page.reload();await chooseCollection(page,'other');await search();
  for(const copy of copies){
   const saved=await get(`inventory/${copy.id}`);assert.equal(saved.id,copy.id);assert.equal(saved.storage_location_id,boxes[1].id);
   const history=await get(`inventory/${copy.id}/locations`);assert.equal(history.length,2);assert.deepEqual(history.map(e=>[e.before_location_id,e.after_location_id]),[[null,boxes[0].id],[boxes[0].id,boxes[1].id]]);
  }
  await page.locator(`#copy-row-${copies[0].id}`).click();
  await page.getByText(`Current location: ${boxes[1].name}`,{exact:true}).waitFor();
  const movement=page.locator('details.movement-history').filter({has:page.locator('summary').filter({hasText:/^Movement history/})});
  await movement.locator('summary').click();
  assert.equal(await movement.locator('li').count(),2);
  await page.getByRole('button',{name:'Back to collection',exact:true}).click();
  await select(boxes[0]);
  await post(`inventory/${copies[1].id}/location`,{storage_location_id:boxes[0].id,expected_storage_revision:2});
  let submissions=0;page.on('request',r=>{if(r.url().endsWith('/move-copies')&&r.method()==='POST')submissions++;});
  await confirm();
  await page.getByRole('alert').filter({hasText:'Selection changed. No copies moved.'}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Move 2 copies',exact:true}).isEnabled(),false);
  assert.equal((await get(`inventory/${copies[0].id}`)).storage_location_id,boxes[1].id);
  assert.equal((await get(`inventory/${copies[1].id}`)).storage_location_id,boxes[0].id);
  assert.equal((await get(`inventory/${copies[0].id}/locations`)).length,2);
  assert.equal(submissions,1);await capture('stale');
  await page.getByRole('button',{name:'Reload copies to review',exact:true}).click();
  await page.getByRole('heading',{name:'0 copies selected',exact:true}).waitFor();
  await select(boxes[0],false);await confirm();
  await page.getByRole('status').filter({hasText:`Moved 1 copy to ${boxes[0].name}. 1 already there; no extra history added.`}).waitFor();
  for(const copy of copies)assert.equal((await get(`inventory/${copy.id}/locations`)).length,3);
  // Simulate a committed POST whose response is lost. Inspect before any new save.
  await select(boxes[1]);
  await page.route('**/move-copies',async route=>{const response=await route.fetch();assert.equal(response.status(),200);await route.abort('failed');});
  await confirm();await page.getByRole('button',{name:'Reload copies to review',exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Move 2 copies',exact:true}).isEnabled(),false);
  for(const copy of copies){assert.equal((await get(`inventory/${copy.id}`)).storage_location_id,boxes[1].id);assert.equal((await get(`inventory/${copy.id}/locations`)).length,4);}
  assert.equal(submissions,3);
 });
}
