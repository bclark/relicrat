import {chooseCollection,openDisclosure,showTools} from './journey-test-helpers.mjs';
import assert from 'node:assert/strict';
import {test,before,after} from 'node:test';
import {chromium} from 'playwright';
import {mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
const base=process.env.RELICRAT_TEST_WEB_URL;
assert.ok(base&&new URL(base).hostname==='127.0.0.1'&&new URL(base).port!=='56742','Use only a disposable loopback test stack');
let browser;
before(async()=>{browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE});});
after(async()=>{await browser?.close();});
async function pageFor(t){const context=await browser.newContext({viewport:{width:1440,height:1050}});t.after(()=>context.close());const r=await context.request.post(base+'/api/v1/auth/login',{data:{password:'synthetic-only-owner-password'},headers:{Origin:base}});assert.equal(r.status(),200);const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));t.after(()=>assert.deepEqual(errors,[]));await page.goto(base);await showTools(page);await page.getByLabel('Browse view',{exact:true}).selectOption('copies');await page.getByRole('button',{name:'Import CSV',exact:true}).click();return {page,context};}
const csv=(type,count)=>type==='clz'?['Series,Issue,Publisher,Quantity,Collection Status,Core ComicID,Storage Box',...Array.from({length:count},(_,i)=>`Synthetic volume comic ${i},${i+1}A,Test Press,1,In Collection,${i},Synthetic Box`)].join('\r\n'):['Title,Artist,Format,release_id,CollectionFolder',...Array.from({length:count},(_,i)=>`Synthetic volume album ${i},Synthetic band,CD,${i},Synthetic folder`)].join('\r\n');
async function upload(page,type,text){
 const back=page.getByRole('button',{name:'Back to file',exact:true});
 const another=page.getByRole('button',{name:'Import another file',exact:true});
 if(await back.isVisible())await back.click();
 if(await another.isVisible())await another.click();
 await page.getByLabel('Export format',{exact:true}).selectOption(type);
 await page.getByLabel('CSV file',{exact:true}).setInputFiles({name:'synthetic.csv',mimeType:'text/csv',buffer:Buffer.from(text)});
 await page.getByRole('button',{name:'Preview import',exact:true}).click();
 await page.getByRole('heading',{name:'Review the import',exact:true}).waitFor();
}

test('real UI imports 1915 synthetic copies, retains source, scopes pages and blocks exact-file duplication',async t=>{
 const {page,context}=await pageFor(t);
 for(const [type,count] of [['clz',1450],['discogs',465]]){
  await upload(page,type,csv(type,count));
  if(type==='clz'&&process.env.RELICRAT_SCREENSHOTS){
   const path=resolve(process.env.RELICRAT_SCREENSHOTS);await mkdir(path,{recursive:true});
   await page.getByRole('region',{name:'CSV imports',exact:true}).screenshot({path:path+'/review-desktop.png'});
  }
  const button=page.getByRole('button',{name:`Import ${count} copies`,exact:true});assert.equal(await button.isDisabled(),true);
  assert.equal((await (await context.request.get(base+'/api/v1/imports')).json()).some(b=>b.source===type),false);
  await page.getByRole('checkbox',{name:`I reviewed the preview and want to create these ${count} physical copies.`,exact:true}).check();
  const historyUrl=base+'/api/v1/imports?limit=21&offset=0';
  if(type==='clz')await page.route(historyUrl,route=>route.fulfill({status:502,json:{detail:'Synthetic history outage'}}));
  await button.click();
  await page.getByRole('status').filter({hasText:`Imported ${count} physical copies`}).waitFor({timeout:35000});
  if(type==='clz'){
   await page.getByRole('alert').filter({hasText:'Import completed; history could not be loaded.'}).waitFor();
   await page.unroute(historyUrl);
   await page.getByRole('button',{name:'Review imported storage labels',exact:true}).click();
   await page.getByRole('region',{name:'Map imported storage boxes',exact:true}).getByText(/Synthetic Box · 1450 eligible/).waitFor();
  }
  await upload(page,type,csv(type,count));
  await page.getByRole('status').filter({hasText:'This exact file was already imported'}).waitFor();
  assert.equal(await page.getByRole('button',{name:`Import ${count} copies`,exact:true}).count(),0);
  await page.getByRole('button',{name:'View previous import',exact:true}).click();
  await page.getByRole('heading',{name:'Previous import',exact:true}).waitFor();
 }
 const batches=await (await context.request.get(base+'/api/v1/imports')).json();assert.equal(batches.length,2);assert.equal(batches.reduce((n,b)=>n+b.copy_count,0),1915);
 await openDisclosure(page,'Import history');await page.getByRole('button',{name:'Reload import history',exact:true}).click();
 const rowButton=page.getByRole('button',{name:/Discogs Albums · 465 copies/});await rowButton.click();await page.getByRole('heading',{name:'Original source rows · Discogs Albums'}).waitFor();await page.getByRole('button',{name:'Next source rows',exact:true}).click();await page.getByRole('button',{name:'Open copy from row 22, copy 1',exact:true}).waitFor();
 await page.getByRole('button',{name:'Close imports',exact:true}).click();
 await chooseCollection(page,'record');await page.getByRole('status').filter({hasText:'20 copies on this page · Albums'}).waitFor();await page.getByRole('button',{name:'Next',exact:true}).click();await page.getByRole('navigation',{name:'Inventory pages'}).getByText('Page 2',{exact:true}).waitFor();
 if(process.env.RELICRAT_SCREENSHOTS){const path=resolve(process.env.RELICRAT_SCREENSHOTS);await mkdir(path,{recursive:true});await page.screenshot({path:path+'/volume-desktop.png',fullPage:true});}
 await page.getByLabel('Find a copy',{exact:true}).fill('Synthetic volume album 464');await page.getByRole('button',{name:'Search',exact:true}).click();await page.getByRole('button',{name:'Open Synthetic band — Synthetic volume album 464',exact:true}).waitFor();
 await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Import CSV',exact:true}).click();await upload(page,'discogs',csv('discogs',465));await page.getByRole('status').filter({hasText:'This exact file was already imported'}).waitFor();assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 if(process.env.RELICRAT_SCREENSHOTS)await page.locator('section[aria-label="CSV imports"]').screenshot({path:resolve(process.env.RELICRAT_SCREENSHOTS)+'/import-mobile.png'});
});

test('invalid rows block confirmation; changing source invalidates preview; ambiguous commit requires preview again',async t=>{
 const {page,context}=await pageFor(t);
 await upload(page,'clz',csv('clz',1).replace('In Collection','Wish List'));await page.getByRole('alert').filter({hasText:'every row is valid'}).waitFor();assert.equal(await page.getByRole('checkbox',{name:/I reviewed/}).count(),0);
 await page.getByRole('button',{name:'Back to file',exact:true}).click();
 assert.equal(await page.getByLabel('CSV file',{exact:true}).evaluate(el=>el.files[0]?.name),'synthetic.csv');
 await page.getByLabel('Export format',{exact:true}).selectOption('discogs');
 assert.equal(await page.getByLabel('CSV file',{exact:true}).inputValue(),'');assert.equal(await page.getByRole('heading',{name:'Review the import',exact:true}).count(),0);
 await upload(page,'discogs',csv('discogs',1)+'\r\nUnique synthetic test,Test band,CD,other,Folder');
 await page.getByRole('checkbox',{name:/I reviewed/}).check();let writes=0;
 await page.route('**/api/v1/imports/commit?**',async route=>{
  writes++;
  const saved=await route.fetch();
  assert.ok(saved.ok(),await saved.text());
  await route.fulfill({status:502,contentType:'application/json',body:JSON.stringify({detail:'Synthetic unconfirmed save'})});
 });
 await page.getByRole('button',{name:'Import 2 copies',exact:true}).click();
 await page.getByRole('heading',{name:'Import result needs checking',exact:true}).waitFor();
 assert.equal(writes,1);
 assert.equal(await page.getByRole('button',{name:'Import 2 copies',exact:true}).count(),0);
 await page.getByRole('button',{name:'Close imports',exact:true}).click();
 await page.getByRole('button',{name:'Import CSV',exact:true}).click();
 await page.getByRole('button',{name:'Check this exact file',exact:true}).click();
 await page.getByRole('status').filter({hasText:'This exact file was already imported (2 copies)'}).waitFor();
 await page.getByRole('button',{name:'View previous import',exact:true}).click();
 await page.getByRole('button',{name:'View original rows',exact:true}).click();
 await page.getByRole('heading',{name:'Original source rows · Discogs Albums'}).waitFor();
 assert.equal(writes,1);
 const batches=await (await context.request.get(base+'/api/v1/imports')).json();
 assert.equal(batches.filter(b=>b.source==='discogs'&&b.copy_count===2).length,1);
 await page.getByRole('button',{name:'View Albums',exact:true}).click();
 await page.getByRole('heading',{name:'Albums',exact:true}).waitFor();
});
