import assert from 'node:assert/strict';
import {test,before,after} from 'node:test';
import {chromium,webkit} from 'playwright';
import {mkdir} from 'node:fs/promises';
const base=process.env.RELICRAT_TEST_WEB_URL;
assert.ok(base&&new URL(base).hostname==='127.0.0.1'&&new URL(base).port!=='56742','Use a disposable loopback stack');
const engine=process.env.RELICRAT_BROWSER==='webkit'?webkit:chromium;let browser;
before(async()=>{browser=await engine.launch({headless:true,...(engine===chromium?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE}:{})});});
after(async()=>{await browser?.close();});
async function setup(t){
 const context=await browser.newContext({viewport:{width:1440,height:1050}});t.after(()=>context.close());
 assert.equal((await context.request.post(base+'/api/v1/auth/login',{data:{password:'synthetic-only-owner-password'},headers:{Origin:base}})).status(),200);
 const page=await context.newPage();const errors=[];page.on('pageerror',error=>errors.push(error.message));t.after(()=>assert.deepEqual(errors,[]));await page.goto(base);
 return {page,context};
}
async function capture(page,name){
 if(!process.env.RELICRAT_MOVIE_SCREENSHOTS)return;
 const root=process.env.RELICRAT_MOVIE_SCREENSHOTS;await mkdir(root,{recursive:true});
 await page.setViewportSize({width:1440,height:1050});await page.screenshot({path:`${root}/${name}-desktop.png`,fullPage:true});
 await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:`${root}/${name}-mobile.png`,fullPage:true});await page.setViewportSize({width:1440,height:1050});
}
const moviePrefix='Synthetic '+(process.env.RELICRAT_MOVIE_RUN ? process.env.RELICRAT_MOVIE_RUN+' ' : process.env.RELICRAT_BROWSER==='webkit'?'WebKit ':'')+'movie';
const csv=['Title,Studio,UPC,EAN,Product ID,Casing,Blu-ray discs,DVD discs,Comment,Price',...Array.from({length:389},(_,index)=>`${moviePrefix} ${index},Synthetic studio,${index===2?'':'012345678905'},${index===2?'':index===1?'1234567890128':'0012345678905'},synthetic-shared,SteelBook,${index===2?'-1':'20'},${index===2?'-1':'2'},=literal source text,not a valuation`)].join('\r\n');

test('Movie setup, title-only intake, custom format, retained history and type changes',async t=>{
 const {page,context}=await setup(t);const form=page.getByRole('form',{name:'Add a find',exact:true});
 await page.getByRole('button',{name:/Set up your collection|Collection settings/,exact:true}).click();
 const wizard=page.getByRole('form',{name:'Set up collection',exact:true});
 await wizard.getByRole('checkbox',{name:'Movies',exact:true}).check();await wizard.getByLabel('Start new finds as',{exact:true}).selectOption('movie');
 await wizard.getByRole('button',{name:'Continue',exact:true}).click();await wizard.getByRole('checkbox',{name:'Notes',exact:true}).last().uncheck();
 await wizard.getByRole('button',{name:'Continue',exact:true}).click();await page.getByRole('region',{name:'Movie preview',exact:true}).waitFor();
 await capture(page,'movie-setup');await wizard.getByRole('button',{name:'Save setup',exact:true}).click();
 await form.getByLabel('What are you adding?',{exact:true}).selectOption('movie');await form.getByLabel('Movie or box-set title',{exact:true}).fill('Synthetic title-only movie');
 await form.getByRole('button',{name:'Save copy',exact:true}).click();await page.getByRole('heading',{name:'Synthetic title-only movie',exact:true}).waitFor();
 const detail=page.getByRole('form',{name:'Edit copy details',exact:true});await detail.getByLabel('Format (optional)',{exact:true}).selectOption('__other__');
 await detail.getByLabel('Other format',{exact:true}).fill('UMD');await detail.getByLabel('Studio (optional)',{exact:true}).fill('Synthetic manual studio');await detail.getByRole('button',{name:'Save details',exact:true}).click();
 await page.getByRole('status').filter({hasText:'Copy details saved.'}).waitFor();
 await page.getByText('Copy edit history',{exact:true}).click();await page.getByText('Movie format: Not entered to UMD',{exact:true}).waitFor();
 const suggestions=await context.request.get(base+'/api/v1/collection-settings/studio-suggestions?q=Synthetic');assert.equal(suggestions.status(),200);assert.ok((await suggestions.json()).includes('Synthetic manual studio'));
 await page.waitForTimeout(300);assert.equal(await detail.getByText('Suggestions unavailable. You can still type here.',{exact:true}).count(),0);
 await capture(page,'movie-edit');
 const copies=await (await context.request.get(base+'/api/v1/inventory?collection_type=movie')).json();const copy=copies.find(value=>value.title==='Synthetic title-only movie');assert.equal(copy.movie_details.media_format,'UMD');
 await detail.getByLabel('Collection type',{exact:true}).selectOption('other');await detail.getByRole('button',{name:'Save details',exact:true}).click();await page.getByRole('status').filter({hasText:'Copy details saved.'}).waitFor();
 const updated=await (await context.request.get(base+'/api/v1/inventory/'+copy.id)).json();assert.equal(updated.collection_type,'other');assert.deepEqual(updated.movie_details,copy.movie_details);assert.equal(updated.id,copy.id);
});

test('Blu-ray.com preview, 389 synthetic imports, warnings, source evidence, retry and Movie filtering',async t=>{
 const {page,context}=await setup(t);await page.getByRole('button',{name:'Import CSV',exact:true}).click();
 const imports=page.getByRole('region',{name:'CSV imports',exact:true});
 async function preview(){await imports.getByLabel('Export format',{exact:true}).selectOption('bluray');await imports.getByLabel('CSV file',{exact:true}).setInputFiles({name:'synthetic-movies.csv',mimeType:'text/csv',buffer:Buffer.from(csv)});await imports.getByRole('button',{name:'Preview import',exact:true}).click();await imports.getByRole('heading',{name:'Review the import',exact:true}).waitFor();}
 const before=await (await context.request.get(base+'/api/v1/imports')).json();await preview();
 assert.equal(await imports.getByRole('button',{name:'Import 389 copies',exact:true}).isDisabled(),true);
 assert.equal((await (await context.request.get(base+'/api/v1/imports')).json()).length,before.length);
 await imports.getByText(/UPC and EAN differ/).waitFor();await imports.getByText(/Unknown disc counts remain unknown/).waitFor();await capture(page,'movie-import');
 await imports.getByRole('checkbox',{name:'I reviewed the preview and want to create these 389 physical copies.',exact:true}).check();await imports.getByRole('button',{name:'Import 389 copies',exact:true}).click();
 await imports.getByRole('status').filter({hasText:'Imported 389 physical copies into Movies.'}).waitFor({timeout:35000});
 await preview();await imports.getByRole('status').filter({hasText:'This exact file was already imported'}).waitFor();assert.equal(await imports.getByRole('button',{name:'Import 389 copies',exact:true}).count(),0);
 await imports.getByRole('button',{name:'Reload import history',exact:true}).click();await imports.getByRole('button',{name:/Blu-ray.com Movies · 389 copies/}).first().click();
 await imports.getByRole('button',{name:'Open copy from row 2, copy 1',exact:true}).waitFor();await imports.getByRole('button',{name:'Open copy from row 2, copy 1',exact:true}).click();
 await page.getByRole('heading',{name:moviePrefix+' 0',exact:true}).waitFor();
 await imports.getByRole('button',{name:'Close imports',exact:true}).click();await page.getByLabel('Show collection type',{exact:true}).selectOption('movie');await page.getByLabel('Browse view',{exact:true}).selectOption('groups');
 await page.getByLabel('Find a copy',{exact:true}).fill(moviePrefix+' 0');await page.getByRole('button',{name:'Search',exact:true}).click();
 const collection=page.getByRole('region',{name:'Saved copies',exact:true});await collection.getByRole('button',{name:new RegExp(moviePrefix+' 0.*Open group')}).click();
 await collection.getByRole('button',{name:'Open '+moviePrefix+' 0 · SteelBook',exact:true}).waitFor();await capture(page,'movie-collection');
 const batches=await (await context.request.get(base+'/api/v1/imports')).json();const batch=batches.find(row=>row.source==='bluray');assert.equal(batch.copy_count,389);
 const rows=await (await context.request.get(base+`/api/v1/imports/${batch.id}/rows`)).json();assert.equal(rows[0].source.Price,'not a valuation');assert.equal(rows[0].source['Blu-ray discs'],'20');
});
