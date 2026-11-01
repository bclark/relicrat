import assert from 'node:assert/strict';
import {test,before,after} from 'node:test';
import {readFile,mkdir} from 'node:fs/promises';
import {chromium,webkit} from 'playwright';
const base=process.env.RELICRAT_TEST_WEB_URL;
assert.ok(base&&new URL(base).hostname==='127.0.0.1'&&new URL(base).port!=='56742','Disposable loopback stack only');
const fixture=await readFile(new URL('./fixtures/synthetic-upca.svg',import.meta.url),'utf8');
let browser;
before(async()=>{browser=await (process.env.RELICRAT_BROWSER==='webkit'?webkit:chromium).launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE}:{})});});
after(async()=>{await browser?.close();});
async function setup(t,mode='read'){
 const context=await browser.newContext({viewport:{width:390,height:844}});t.after(()=>context.close());
 assert.equal((await context.request.post(base+'/api/v1/auth/login',{data:{password:'synthetic-only-owner-password'},headers:{Origin:base}})).status(),200);
 const page=await context.newPage(),writes=[],external=[],errors=[];
 page.on('pageerror',e=>errors.push(e.message));t.after(()=>assert.deepEqual(errors,[]));
 page.on('request',r=>{if(r.method()==='POST')writes.push(new URL(r.url()).pathname);if(new URL(r.url()).origin!==base)external.push(r.url());});
 await page.addInitScript(({mode,fixture})=>{
  window.__cameraMode=mode;window.__cameraRequests=[];window.__cameraStreams=[];
  const fakeGetUserMedia=async options=>{
   window.__cameraRequests.push(options);
   if(window.__cameraMode==='deny')throw new DOMException('Synthetic camera permission refusal','NotAllowedError');
   if(window.__cameraMode==='pending')await new Promise(resolve=>{window.__grantCamera=resolve;});
   const canvas=document.createElement('canvas');canvas.width=1280;canvas.height=720;const drawing=canvas.getContext('2d');drawing.fillStyle='white';drawing.fillRect(0,0,1280,720);drawing.fillStyle='black';drawing.font='32px sans-serif';drawing.fillText('Synthetic camera frame: no barcode',60,360);
   const image=new Image();image.src='data:image/svg+xml;base64,'+btoa(fixture);await image.decode();
   const draw=()=>{if(window.__cameraMode==='read')drawing.drawImage(image,0,0,1280,720);else {drawing.fillStyle='white';drawing.fillRect(0,0,1280,720);drawing.fillStyle='black';drawing.fillText('Synthetic camera frame: no barcode',60,360);}};draw();
   const stream=canvas.captureStream(5);window.__cameraStreams.push(stream);
   const timer=setInterval(()=>{if(stream.getTracks().every(t=>t.readyState==='ended'))clearInterval(timer);else draw();},200);
   return stream;
  };
  Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:fakeGetUserMedia}});window.__fakeGetUserMedia=fakeGetUserMedia;
 },{mode,fixture});
 await page.goto(base);assert.equal(await page.evaluate(()=>navigator.mediaDevices.getUserMedia===window.__fakeGetUserMedia),true,'Synthetic camera must replace the real camera before any scan');const scanner=page.getByRole('region',{name:'Barcode scanning trial',exact:true});
 return {page,scanner,writes,external};
}
async function stopped(page){await page.waitForFunction(()=>window.__cameraStreams.length>0&&window.__cameraStreams.every(s=>s.getTracks().every(t=>t.readyState==='ended')));}

test('actual decoder reads a synthetic UPC frame, stops camera, retains zeros and never saves or uploads',async t=>{
 const {page,scanner,writes,external}=await setup(t);
 const input=page.locator('#find-title');await input.fill('Unsaved synthetic find');
 assert.equal(await page.evaluate(()=>window.__cameraRequests.length),0);
 await scanner.getByRole('button',{name:'Scan barcode',exact:true}).click();
 await scanner.getByRole('heading',{name:'Barcode read',exact:true}).waitFor({timeout:35000});
 await stopped(page);assert.equal(await input.inputValue(),'Unsaved synthetic find');
 assert.ok((await scanner.innerText()).includes('012345678905'));assert.ok((await scanner.innerText()).includes('UPC-A'));
 assert.equal(await page.evaluate(()=>window.__cameraRequests[0].audio),false);
 if(process.env.RELICRAT_SCREENSHOTS){await mkdir(process.env.RELICRAT_SCREENSHOTS,{recursive:true});await page.screenshot({path:process.env.RELICRAT_SCREENSHOTS+'/barcode-mobile.png',fullPage:true});await page.setViewportSize({width:1440,height:1050});await page.screenshot({path:process.env.RELICRAT_SCREENSHOTS+'/barcode-desktop.png',fullPage:true});}
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.deepEqual(writes,[]);assert.deepEqual(external,[]);
 await scanner.getByRole('button',{name:'Scan another barcode',exact:true}).click();await scanner.getByRole('heading',{name:'Barcode read',exact:true}).waitFor();
 assert.equal(await page.evaluate(()=>window.__cameraRequests.length),2);await stopped(page);
 await scanner.getByRole('button',{name:'Close scanner',exact:true}).click();assert.equal(await scanner.getByRole('heading',{name:'Barcode read',exact:true}).count(),0);
});

test('denied camera access explains recovery and permits an explicit retry',async t=>{
 const {page,scanner,writes}=await setup(t,'deny');
 await scanner.getByRole('button',{name:'Scan barcode',exact:true}).click();await scanner.getByRole('alert').filter({hasText:'browser settings'}).waitFor();
 await page.evaluate(()=>{window.__cameraMode='read';});await scanner.getByRole('button',{name:'Start camera',exact:true}).click();await scanner.getByRole('heading',{name:'Barcode read',exact:true}).waitFor();await stopped(page);assert.deepEqual(writes,[]);
});

test('cancelled permission request stops a late stream without replacing a later scan',async t=>{
 const {page,scanner}=await setup(t,'pending');
 await scanner.getByRole('button',{name:'Scan barcode',exact:true}).click();await page.waitForFunction(()=>!!window.__grantCamera);
 await scanner.getByRole('button',{name:'Stop camera',exact:true}).click();
 await page.evaluate(()=>{window.__cameraMode='read';});await scanner.getByRole('button',{name:'Start camera',exact:true}).click();await scanner.getByRole('heading',{name:'Barcode read',exact:true}).waitFor();
 await page.evaluate(()=>window.__grantCamera());await page.waitForFunction(()=>window.__cameraStreams.length===2);await stopped(page);
 assert.ok((await scanner.innerText()).includes('012345678905'));assert.equal(await scanner.getByRole('alert').count(),0);
});

test('a running camera stops explicitly, on leaving the page and after the one-minute limit',async t=>{
 const {page,scanner}=await setup(t,'blank');
 await page.clock.install();await scanner.getByRole('button',{name:'Scan barcode',exact:true}).click();
 await scanner.getByRole('status').filter({hasText:'Hold the barcode'}).waitFor();
 await scanner.getByRole('button',{name:'Stop camera',exact:true}).click();await stopped(page);
 await scanner.getByRole('button',{name:'Start camera',exact:true}).click();await scanner.getByRole('status').filter({hasText:'Hold the barcode'}).waitFor();
 await page.clock.fastForward(60_001);await scanner.getByRole('alert').filter({hasText:'one minute'}).waitFor();await stopped(page);
 await scanner.getByRole('button',{name:'Start camera',exact:true}).click();await scanner.getByRole('status').filter({hasText:'Hold the barcode'}).waitFor();
 await page.evaluate(()=>window.dispatchEvent(new Event('pagehide')));await stopped(page);
 assert.equal(await scanner.getByRole('button',{name:'Start camera',exact:true}).isEnabled(),true);
});

test('unsupported camera context remains stoppable and retryable without a request',async t=>{
 const {page,scanner}=await setup(t);
 await page.evaluate(()=>Object.defineProperty(window,'isSecureContext',{value:false,configurable:true}));
 await scanner.getByRole('button',{name:'Scan barcode',exact:true}).click();await scanner.getByRole('alert').filter({hasText:'private HTTPS'}).waitFor();
 await scanner.getByRole('button',{name:'Start camera',exact:true}).click();await scanner.getByRole('alert').filter({hasText:'private HTTPS'}).waitFor();
 assert.equal(await page.evaluate(()=>window.__cameraRequests.length),0);await scanner.getByRole('button',{name:'Close scanner',exact:true}).click();await scanner.getByRole('button',{name:'Scan barcode',exact:true}).waitFor();
});

test('closing the scanner and hiding the page release active camera tracks',async t=>{
 const {page,scanner}=await setup(t,'blank');
 await scanner.getByRole('button',{name:'Scan barcode',exact:true}).click();await scanner.getByRole('status').filter({hasText:'Hold the barcode'}).waitFor();
 if(process.env.RELICRAT_SCREENSHOTS){await page.screenshot({path:process.env.RELICRAT_SCREENSHOTS+'/barcode-active-mobile.png',fullPage:true});await page.setViewportSize({width:1440,height:1050});await page.screenshot({path:process.env.RELICRAT_SCREENSHOTS+'/barcode-active-desktop.png',fullPage:true});}
 await scanner.getByRole('button',{name:'Close scanner',exact:true}).click();await stopped(page);
 await scanner.getByRole('button',{name:'Scan barcode',exact:true}).click();await scanner.getByRole('status').filter({hasText:'Hold the barcode'}).waitFor();
 await page.evaluate(()=>{Object.defineProperty(document,'hidden',{value:true,configurable:true});document.dispatchEvent(new Event('visibilitychange'));});await stopped(page);
});

test('use a scan explicitly, save one copy, find it by barcode and retain removal history',async t=>{
 const {page,scanner,writes,external}=await setup(t);
 const title='Synthetic barcode intake '+Date.now();
 await page.locator('#find-title').fill(title);
 await scanner.getByRole('button',{name:'Scan barcode',exact:true}).click();
 await scanner.getByRole('heading',{name:'Barcode read',exact:true}).waitFor();await stopped(page);
 assert.deepEqual(writes,[]);
 await scanner.getByRole('button',{name:'Use barcode',exact:true}).click();
 await page.getByText('Barcode in this draft',{exact:true}).waitFor();assert.deepEqual(writes,[]);
 assert.equal(await page.locator('#find-title').inputValue(),title);
 assert.equal(await page.locator('#find-title').evaluate(e=>e===document.activeElement),true);
 if(process.env.RELICRAT_INTAKE_SCREENSHOTS){const dir=process.env.RELICRAT_INTAKE_SCREENSHOTS;await mkdir(dir,{recursive:true});await page.screenshot({path:dir+'/intake-mobile.png',fullPage:true});await page.setViewportSize({width:1440,height:1050});await page.screenshot({path:dir+'/intake-desktop.png',fullPage:true});await page.setViewportSize({width:390,height:844});}
 await page.getByRole('form',{name:'Add a find',exact:true}).getByRole('button',{name:'Save copy',exact:true}).click();
 await page.getByText('Copy saved. You can add more details whenever you like.',{exact:true}).waitFor();
 const copies=await (await page.request.get(base+'/api/v1/inventory?q='+encodeURIComponent(title))).json();
 assert.equal(copies.length,1);const copy=copies[0];assert.equal(copy.barcode.value,'012345678905');
 assert.equal(await page.getByText('Barcode in this draft',{exact:true}).count(),0);
 await page.selectOption('#collection-browse-view','copies');await page.locator('#query').fill(copy.barcode.value);
 await page.getByRole('form',{name:'Search inventory'}).getByRole('button',{name:'Search',exact:true}).click();
 await page.locator('.inventory-list').getByRole('button').filter({hasText:title}).waitFor();
 await page.reload();
 await page.selectOption('#collection-browse-view','copies');
 await page.locator('.inventory-list').getByRole('button').filter({hasText:title}).click();
 const edit=page.getByRole('form',{name:'Edit copy details'}),disclosure=edit.locator('summary').filter({hasText:'Barcode (optional)'});
 await disclosure.click();await edit.getByText('Saved barcode',{exact:true}).waitFor();
 if(process.env.RELICRAT_INTAKE_SCREENSHOTS){const dir=process.env.RELICRAT_INTAKE_SCREENSHOTS;await page.screenshot({path:dir+'/saved-mobile.png',fullPage:true});await page.setViewportSize({width:1440,height:1050});await page.screenshot({path:dir+'/saved-desktop.png',fullPage:true});await page.setViewportSize({width:390,height:844});}
 await page.evaluate(()=>{window.__cameraMode='blank';});
 const savedScanner=edit.getByRole('region',{name:'Barcode scanning trial',exact:true});
 await savedScanner.getByRole('button',{name:'Scan barcode',exact:true}).click();
 await savedScanner.getByRole('status').filter({hasText:'Hold the barcode'}).waitFor();
 await disclosure.click();await stopped(page);await disclosure.click();
 await edit.getByText('Saved barcode',{exact:true}).waitFor();
 await edit.getByRole('button',{name:'Remove barcode from draft',exact:true}).click();
 assert.equal((await (await page.request.get(base+'/api/v1/inventory/'+copy.id)).json()).barcode.value,'012345678905');
 await edit.getByRole('button',{name:'Save details',exact:true}).click();
 await page.getByText('Copy details saved.',{exact:true}).waitFor();
 const cleared=await (await page.request.get(base+'/api/v1/inventory/'+copy.id)).json();assert.deepEqual(cleared.barcode,{});assert.equal(cleared.id,copy.id);
 const history=await (await page.request.get(base+'/api/v1/inventory/'+copy.id+'/detail-history')).json();
 assert.equal(history.at(-1).before_barcode.value,'012345678905');assert.deepEqual(history.at(-1).after_barcode,{});
 assert.deepEqual(external,[]);assert.equal(writes.filter(p=>p==='/api/v1/inventory').length,1);
});

test('a failed copy save retains the attached reading and a confirmed type change clears it',async t=>{
 const {page,scanner,writes}=await setup(t);
 await page.locator('#find-title').fill('Synthetic failed barcode draft');
 await scanner.getByRole('button',{name:'Scan barcode',exact:true}).click();await scanner.getByRole('heading',{name:'Barcode read',exact:true}).waitFor();
 await scanner.getByRole('button',{name:'Use barcode',exact:true}).click();
 await page.route('**/api/v1/inventory',async route=>{
  if(route.request().method()==='POST')await route.fulfill({status:503,contentType:'application/json',body:'{"detail":"Synthetic save unavailable"}'});else await route.continue();
 });
 await page.getByRole('form',{name:'Add a find',exact:true}).getByRole('button',{name:'Save copy',exact:true}).click();
 await page.getByRole('alert').filter({hasText:'Synthetic save unavailable'}).waitFor();
 await page.getByText('Barcode in this draft',{exact:true}).waitFor();assert.equal(await page.locator('#find-title').inputValue(),'Synthetic failed barcode draft');
 await page.getByRole('button',{name:'Reload inventory',exact:true}).last().click();
 await page.waitForFunction(()=>!!document.querySelector('#find-type') && !document.querySelector('#find-type').closest('fieldset').disabled);
 const original=await page.locator('#find-type').inputValue(),next=original==='record'?'comic':'record';
 page.once('dialog',d=>d.dismiss());await page.selectOption('#find-type',next);
 assert.equal(await page.locator('#find-type').inputValue(),original);await page.getByText('Barcode in this draft',{exact:true}).waitFor();
 page.once('dialog',d=>d.accept());await page.selectOption('#find-type',next);
 assert.equal(await page.getByText('Barcode in this draft',{exact:true}).count(),0);assert.equal(await page.locator('#find-title').inputValue(),'');
 assert.equal(writes.filter(p=>p==='/api/v1/inventory').length,1);
});

test('type configuration can disable new scans or reject a format without changing inventory',async t=>{
 const {page,scanner,writes}=await setup(t);
 let formats=[];
 const definitions=await (await page.request.get(base+'/api/v1/collection-settings/types')).json();
 await page.route('**/api/v1/collection-settings/types',async route=>{
  const types=structuredClone(definitions);
  for(const type of Object.values(types))type.barcode_formats=formats;
  await route.fulfill({json:types});
 });
 await page.reload();await page.getByRole('form',{name:'Add a find',exact:true}).getByRole('button',{name:'Save copy',exact:true}).waitFor();
 await page.waitForFunction(()=>!!document.querySelector('#find-type') && !document.querySelector('#find-type').closest('fieldset').disabled);
 assert.equal(await scanner.getByRole('button',{name:'Scan barcode',exact:true}).isDisabled(),true);
 assert.equal(await page.evaluate(()=>window.__cameraRequests.length),0);
 formats=['EAN_13'];await page.reload();await page.selectOption('#find-type','record');
 await scanner.getByRole('button',{name:'Scan barcode',exact:true}).click();
 await scanner.getByRole('alert').filter({hasText:'not supported for this collection type'}).waitFor();await stopped(page);
 assert.equal(await scanner.getByRole('button',{name:'Use barcode',exact:true}).count(),0);assert.deepEqual(writes,[]);
});

const lookupId='11111111-1111-4111-8111-111111111111';
async function lookupFixture(page,title='Synthetic Moon Album'){
 let calls=0;
 await page.route('**/api/v1/barcode-lookups/record',async route=>{
  calls++;assert.equal(route.request().method(),'POST');assert.equal(route.request().postDataJSON().value,'012345678905');
  await route.fulfill({json:{provider:'musicbrainz',provider_label:'MusicBrainz',candidates:[{id:lookupId,title,description:'Synthetic artist · Vinyl · 2020 · GB · Synthetic label',source_url:'https://musicbrainz.org/release/'+lookupId,fields:{title,artist:'Synthetic artist',format:'Vinyl'},cover_url:'/api/v1/barcode-lookups/record/'+lookupId+'/cover'}]}});
 });
 const cover=await page.evaluate(()=>{const canvas=document.createElement('canvas');canvas.width=250;canvas.height=250;const c=canvas.getContext('2d');c.fillStyle='#203a4a';c.fillRect(0,0,250,250);c.fillStyle='#ffffff';c.font='bold 24px sans-serif';c.fillText('SYNTHETIC',25,90);c.fillText('ALBUM COVER',25,125);c.font='16px sans-serif';c.fillText('Generated test fixture',25,170);return canvas.toDataURL('image/png').split(',')[1];});
 await page.route('**/api/v1/barcode-lookups/record/*/cover',route=>route.fulfill({contentType:'image/png',body:Buffer.from(cover,'base64')}));
 return ()=>calls;
}
async function scanForAlbum(page,scanner){
 await page.selectOption('#find-type','record');
 await scanner.getByRole('button',{name:'Scan barcode',exact:true}).click();await stopped(page);
 assert.equal(await scanner.getByRole('heading',{name:'Barcode read',exact:true}).count(),0);
 assert.equal(await scanner.getByRole('button',{name:'Use barcode',exact:true}).count(),0);
 const lookup=page.getByRole('region',{name:'Barcode lookup',exact:true}).first();
 await lookup.getByRole('heading',{name:'Possible matches from MusicBrainz',exact:true}).waitFor();return lookup;
}

test('review an album match, preserve existing artist, fill a draft and explicitly save one copy',async t=>{
 const {page,scanner,writes,external}=await setup(t);const title='Synthetic Moon Album '+Date.now();const calls=await lookupFixture(page,title);
 await page.selectOption('#find-type','record');await page.locator('#find-artist').fill('Keep my manual artist');
 const lookup=await scanForAlbum(page,scanner);
 if(process.env.RELICRAT_LOOKUP_SCREENSHOTS){const dir=process.env.RELICRAT_LOOKUP_SCREENSHOTS;await mkdir(dir,{recursive:true});await page.screenshot({path:dir+'/automatic-mobile.png',fullPage:true});await page.setViewportSize({width:1440,height:1050});await page.screenshot({path:dir+'/automatic-desktop.png',fullPage:true});await page.setViewportSize({width:390,height:844});}
 assert.equal(await page.locator('#find-title').inputValue(),'');assert.equal(await page.locator('#find-artist').inputValue(),'Keep my manual artist');
 assert.equal(writes.filter(path=>path==='/api/v1/inventory').length,0);assert.equal(calls(),1);
 await lookup.locator('.barcode-matches button').click();await lookup.getByRole('heading',{name:'Review details to fill'}).waitFor();await page.waitForFunction(()=>Array.from(document.querySelectorAll('.lookup-cover')).every(image=>image.complete&&image.naturalWidth>0));
 assert.equal(await lookup.getByRole('checkbox',{name:/Artist or band/}).isChecked(),false);
 assert.equal(await lookup.getByRole('checkbox',{name:/Album title/}).isChecked(),true);
 if(process.env.RELICRAT_LOOKUP_SCREENSHOTS){const dir=process.env.RELICRAT_LOOKUP_SCREENSHOTS;await mkdir(dir,{recursive:true});await page.screenshot({path:dir+'/review-mobile.png',fullPage:true});await page.setViewportSize({width:1440,height:1050});await page.screenshot({path:dir+'/review-desktop.png',fullPage:true});await page.setViewportSize({width:390,height:844});}
 await lookup.getByRole('button',{name:'Use these details',exact:true}).click();
 assert.equal(await page.locator('#find-title').inputValue(),title);assert.equal(await page.locator('#find-artist').inputValue(),'Keep my manual artist');assert.equal(await page.locator('#find-format').inputValue(),'Vinyl');
 assert.equal(writes.filter(path=>path==='/api/v1/inventory').length,0);
 if(process.env.RELICRAT_LOOKUP_SCREENSHOTS){const dir=process.env.RELICRAT_LOOKUP_SCREENSHOTS;await page.screenshot({path:dir+'/filled-mobile.png',fullPage:true});await page.setViewportSize({width:1440,height:1050});await page.screenshot({path:dir+'/filled-desktop.png',fullPage:true});await page.setViewportSize({width:390,height:844});}
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await page.getByRole('form',{name:'Add a find',exact:true}).getByRole('button',{name:'Save copy',exact:true}).click();await page.getByText('Copy saved. You can add more details whenever you like.',{exact:true}).waitFor();
 const rows=await (await page.request.get(base+'/api/v1/inventory?q='+encodeURIComponent(title))).json();assert.equal(rows.length,1);assert.equal(rows[0].record_details.artist,'Keep my manual artist');assert.equal(rows[0].barcode.value,'012345678905');assert.equal(rows[0].catalog_item_id,null);
 assert.equal(writes.filter(path=>path==='/api/v1/inventory').length,1);assert.deepEqual(external,[]);
});

test('lookup failure and no matches keep a manually editable draft without ownership writes',async t=>{
 const {page,scanner,writes}=await setup(t);let fail=true;
 await page.route('**/api/v1/barcode-lookups/record',route=>route.fulfill(fail?{status:503,json:{detail:'Synthetic unavailable'}}:{json:{provider:'musicbrainz',provider_label:'MusicBrainz',candidates:[]}}));
 await page.selectOption('#find-type','record');await page.locator('#find-title').fill('Synthetic fallback draft');
 await scanner.getByRole('button',{name:'Scan barcode',exact:true}).click();await stopped(page);
 const lookup=page.getByRole('region',{name:'Barcode lookup',exact:true}).first();await lookup.getByRole('alert').filter({hasText:'Lookup is unavailable'}).waitFor();assert.equal(await page.locator('#find-title').inputValue(),'Synthetic fallback draft');
 fail=false;await lookup.getByRole('button',{name:'Find album details',exact:true}).click();await lookup.getByRole('status').filter({hasText:'No matching releases'}).waitFor();
 assert.equal(await page.getByRole('form',{name:'Add a find',exact:true}).getByRole('button',{name:'Save copy',exact:true}).isEnabled(),true);assert.equal(writes.filter(path=>path==='/api/v1/inventory').length,0);
});

test('a changed draft requires another review before a suggestion can replace it',async t=>{
 const {page,scanner,writes}=await setup(t);await lookupFixture(page);
 const lookup=await scanForAlbum(page,scanner);await lookup.locator('.barcode-matches button').click();
 await page.locator('#find-title').fill('New manual title after review');
 await lookup.getByRole('button',{name:'Review this match again',exact:true}).waitFor();assert.equal(await lookup.getByRole('button',{name:'Use these details',exact:true}).isDisabled(),true);
 await lookup.getByRole('button',{name:'Review this match again',exact:true}).click();
 assert.equal(await lookup.getByRole('checkbox',{name:/Album title/}).isChecked(),false);
 await lookup.getByRole('button',{name:'Use these details',exact:true}).click();assert.equal(await page.locator('#find-title').inputValue(),'New manual title after review');assert.equal(await page.locator('#find-artist').inputValue(),'Synthetic artist');assert.equal(writes.filter(path=>path==='/api/v1/inventory').length,0);
});

test('late lookup responses cannot populate a changed collection type',async t=>{
 const {page,scanner,writes}=await setup(t);let release;const pending=new Promise(resolve=>{release=resolve;});let started=false;
 await page.route('**/api/v1/barcode-lookups/record',async route=>{started=true;await pending;try{await route.fulfill({json:{provider:'musicbrainz',provider_label:'MusicBrainz',candidates:[]}});}catch{/* The aborted owner request may already be gone. */}});
 await page.selectOption('#find-type','record');await scanner.getByRole('button',{name:'Scan barcode',exact:true}).click();await stopped(page);
 await page.getByRole('status').filter({hasText:'Looking for possible matches'}).waitFor();assert.equal(started,true);
 page.once('dialog',dialog=>dialog.accept());await page.selectOption('#find-type','comic');release();
 await page.locator('#find-title').fill('Synthetic comic draft');assert.equal(await page.getByRole('region',{name:'Barcode lookup',exact:true}).count(),0);assert.equal(await page.locator('#find-title').inputValue(),'Synthetic comic draft');assert.equal(writes.filter(path=>path==='/api/v1/inventory').length,0);
});

test('existing-copy lookup changes only reviewed details and saves with retained history',async t=>{
 const {page,writes}=await setup(t);const title='Original lookup copy '+Date.now();await lookupFixture(page);
 const response=await page.request.post(base+'/api/v1/inventory',{headers:{Origin:base},data:{title,collection_type:'record',barcode:{value:'012345678905',format:'UPC_A'}}});assert.equal(response.status(),201);const original=await response.json();
 await page.reload();await page.selectOption('#collection-browse-view','copies');await page.locator('.inventory-list button').filter({hasText:title}).click();
 const form=page.getByRole('form',{name:'Edit copy details'});await form.locator('summary').filter({hasText:'Barcode (optional)'}).click();const lookup=form.getByRole('region',{name:'Barcode lookup',exact:true});
 await form.getByRole('region',{name:'Barcode scanning trial',exact:true}).getByRole('button',{name:'Scan barcode',exact:true}).click();await stopped(page);
 await lookup.getByRole('heading',{name:'Possible matches from MusicBrainz',exact:true}).waitFor();await lookup.locator('.barcode-matches button').click();
 assert.equal(await lookup.getByRole('checkbox',{name:/Album title/}).isChecked(),false);
 await lookup.getByRole('button',{name:'Use these details',exact:true}).click();assert.equal((await (await page.request.get(base+'/api/v1/inventory/'+original.id)).json()).record_details.artist,undefined);
 assert.equal(await form.locator('#copy-title').evaluate(element=>element===document.activeElement),true);
 if(process.env.RELICRAT_LOOKUP_SCREENSHOTS){const dir=process.env.RELICRAT_LOOKUP_SCREENSHOTS;await page.screenshot({path:dir+'/existing-filled-mobile.png',fullPage:true});await page.setViewportSize({width:1440,height:1050});await page.screenshot({path:dir+'/existing-filled-desktop.png',fullPage:true});await page.setViewportSize({width:390,height:844});}
 await form.getByRole('button',{name:'Save details',exact:true}).click();await page.getByText('Copy details saved.',{exact:true}).waitFor();
 const saved=await (await page.request.get(base+'/api/v1/inventory/'+original.id)).json();assert.equal(saved.id,original.id);assert.equal(saved.title,title);assert.equal(saved.record_details.artist,'Synthetic artist');assert.equal(saved.catalog_item_id,null);
 const history=await (await page.request.get(base+'/api/v1/inventory/'+original.id+'/detail-history')).json();assert.equal(history.length,1);assert.equal(history[0].after_record_details.artist,'Synthetic artist');assert.equal(writes.filter(path=>path==='/api/v1/inventory').length,0);
});

test('closing a rescan does not repeat a previous external lookup',async t=>{
 const {page,scanner}=await setup(t);const calls=await lookupFixture(page);await scanForAlbum(page,scanner);assert.equal(calls(),1);
 await page.evaluate(()=>{window.__cameraMode='blank';});
 await scanner.getByRole('button',{name:'Scan barcode',exact:true}).click();await scanner.getByRole('status').filter({hasText:'Hold the barcode'}).waitFor();
 await scanner.getByRole('button',{name:'Close scanner',exact:true}).click();await stopped(page);
 const lookup=page.getByRole('region',{name:'Barcode lookup',exact:true}).first();await lookup.getByRole('button',{name:'Find album details',exact:true}).waitFor();
 assert.equal(await lookup.getByRole('heading',{name:'Possible matches from MusicBrainz',exact:true}).count(),0);assert.equal(calls(),1);
});


test('each deliberate album scan starts exactly one lookup without a barcode confirmation',async t=>{
 const {page,scanner,writes}=await setup(t);const calls=await lookupFixture(page);
 await scanForAlbum(page,scanner);assert.equal(calls(),1);
 await scanner.getByRole('button',{name:'Scan barcode',exact:true}).click();await stopped(page);
 await page.getByRole('heading',{name:'Possible matches from MusicBrainz',exact:true}).waitFor();
 assert.equal(calls(),2);assert.equal(await page.locator('#find-title').inputValue(),'');
 assert.equal(writes.filter(path=>path==='/api/v1/inventory').length,0);
});

async function coverCapture(page,name){
 if(!process.env.RELICRAT_COVER_SCREENSHOTS)return;
 const dir=process.env.RELICRAT_COVER_SCREENSHOTS;await mkdir(dir,{recursive:true});
 await page.screenshot({path:dir+'/'+name+'-mobile.png',fullPage:true});await page.setViewportSize({width:1440,height:1050});await page.screenshot({path:dir+'/'+name+'-desktop.png',fullPage:true});await page.setViewportSize({width:390,height:844});
}

test('optional catalog cover is unchecked, staged for review, and stored only with final intake save',async t=>{
 const {page,scanner,writes}=await setup(t);const title='Synthetic chosen cover '+Date.now();await lookupFixture(page,title);
 const lookup=await scanForAlbum(page,scanner);await lookup.locator('.barcode-matches button').click();
 const cover=lookup.getByRole('checkbox',{name:/Include catalog cover/});await page.waitForFunction(()=>!!document.querySelector('.lookup-cover')?.naturalWidth);
 assert.equal(await cover.isChecked(),false);await cover.check();await coverCapture(page,'cover-review');
 await lookup.getByRole('button',{name:'Use these details',exact:true}).click();await page.getByText('Catalog cover selected. Save the form to keep it.',{exact:true}).waitFor();
 assert.equal(writes.filter(p=>p==='/api/v1/inventory').length,0);assert.equal((await (await page.request.get(base+'/api/v1/inventory?q='+encodeURIComponent(title))).json()).length,0);
 await coverCapture(page,'cover-pending');
 await page.getByRole('form',{name:'Add a find',exact:true}).getByRole('button',{name:'Save copy',exact:true}).click();await page.getByRole('region',{name:'Catalog artwork',exact:true}).waitFor();
 const copies=await (await page.request.get(base+'/api/v1/inventory?q='+encodeURIComponent(title))).json();assert.equal(copies.length,1);
 const art=await (await page.request.get(base+'/api/v1/inventory/'+copies[0].id+'/photos')).json();assert.equal(art.length,1);assert.equal(art[0].role,'catalog_cover');assert.equal(art[0].source_id,lookupId);
 assert.equal(await page.getByRole('region',{name:'Catalog artwork'}).getByRole('link',{name:'Source: musicbrainz'}).getAttribute('href'),'https://musicbrainz.org/release/'+lookupId);
 await page.getByText('No photos yet. Add a clear view of this physical copy.',{exact:true}).waitFor();await coverCapture(page,'cover-saved');
});

test('cover-only existing-copy save preserves physical photos and does not create another copy',async t=>{
 const {page,writes}=await setup(t);const title='Synthetic existing cover '+Date.now();await lookupFixture(page);
 const response=await page.request.post(base+'/api/v1/inventory',{headers:{Origin:base},data:{title,collection_type:'record',barcode:{value:'012345678905',format:'UPC_A'}}});const original=await response.json();
 const png=await page.evaluate(()=>{const c=document.createElement('canvas');c.width=4;c.height=4;return c.toDataURL('image/png').split(',')[1];});assert.equal((await page.request.post(base+'/api/v1/inventory/'+original.id+'/photos',{headers:{Origin:base},multipart:{file:{name:'synthetic.png',mimeType:'image/png',buffer:Buffer.from(png,'base64')}}})).status(),201);
 await page.reload();await page.selectOption('#collection-browse-view','copies');await page.locator('.inventory-list button').filter({hasText:title}).click();
 const form=page.getByRole('form',{name:'Edit copy details'});await form.locator('summary').filter({hasText:'Barcode (optional)'}).click();const lookup=form.getByRole('region',{name:'Barcode lookup',exact:true});
 await lookup.getByRole('button',{name:'Find album details',exact:true}).click();await lookup.locator('.barcode-matches button').click();await page.waitForFunction(()=>!!document.querySelector('.lookup-cover')?.naturalWidth);
 for(const checkbox of await lookup.getByRole('checkbox').all())await checkbox.uncheck();await lookup.getByRole('checkbox',{name:/Include catalog cover/}).check();
 await lookup.getByRole('button',{name:'Use these details',exact:true}).click();assert.equal(await form.getByRole('button',{name:'Save details',exact:true}).isEnabled(),true);
 assert.equal((await (await page.request.get(base+'/api/v1/inventory/'+original.id+'/photos')).json()).length,1);
 await form.getByRole('button',{name:'Save details',exact:true}).click();await page.getByRole('region',{name:'Catalog artwork',exact:true}).waitFor();await page.getByText('View photo 1',{exact:true}).waitFor();
 const images=await (await page.request.get(base+'/api/v1/inventory/'+original.id+'/photos')).json();assert.equal(images.length,2);assert.equal(images.filter(image=>image.role==='photo').length,1);assert.equal(images.filter(image=>image.role==='catalog_cover').length,1);
 assert.equal(writes.filter(p=>p==='/api/v1/inventory').length,0);assert.equal((await (await page.request.get(base+'/api/v1/inventory/'+original.id)).json()).title,title);
});

test('unavailable selected cover retains the draft and removing it permits one ordinary save',async t=>{
 const {page,scanner}=await setup(t);const title='Synthetic unavailable cover '+Date.now();await lookupFixture(page,title);
 await page.route('**/api/v1/barcode-lookups/record',route=>route.fulfill({json:{provider:'musicbrainz',provider_label:'MusicBrainz',candidates:[{id:'22222222-2222-4222-8222-222222222222',title,description:'Synthetic unavailable saved cover',source_url:'https://musicbrainz.org/release/22222222-2222-4222-8222-222222222222',fields:{title},cover_url:'/api/v1/barcode-lookups/record/'+lookupId+'/cover'}]}}));
 const lookup=await scanForAlbum(page,scanner);await lookup.locator('.barcode-matches button').click();await page.waitForFunction(()=>!!document.querySelector('.lookup-cover')?.naturalWidth);await lookup.getByRole('checkbox',{name:/Include catalog cover/}).check();await lookup.getByRole('button',{name:'Use these details',exact:true}).click();
 const form=page.getByRole('form',{name:'Add a find',exact:true});await form.getByRole('button',{name:'Save copy',exact:true}).click();await page.getByRole('alert').filter({hasText:'selected cover is unavailable'}).waitFor();
 assert.equal((await (await page.request.get(base+'/api/v1/inventory?q='+encodeURIComponent(title))).json()).length,0);assert.equal(await page.locator('#find-title').inputValue(),title);
 await page.getByRole('button',{name:'Remove selected cover',exact:true}).click();await form.getByRole('button',{name:'Save copy',exact:true}).click();await page.getByText('Copy saved. You can add more details whenever you like.',{exact:true}).waitFor();
 const rows=await (await page.request.get(base+'/api/v1/inventory?q='+encodeURIComponent(title))).json();assert.equal(rows.length,1);assert.deepEqual(await (await page.request.get(base+'/api/v1/inventory/'+rows[0].id+'/photos')).json(),[]);
});

test('missing cover preview leaves field review available without a cover option',async t=>{
 const {page,scanner}=await setup(t);await lookupFixture(page);await page.route('**/api/v1/barcode-lookups/record/*/cover',route=>route.fulfill({status:404}));
 const lookup=await scanForAlbum(page,scanner);await lookup.locator('.barcode-matches button').click();await lookup.getByText('Cover preview unavailable.',{exact:true}).waitFor();
 assert.equal(await lookup.getByRole('checkbox',{name:/Include catalog cover/}).count(),0);assert.equal(await lookup.getByRole('button',{name:'Use these details',exact:true}).isEnabled(),true);
});
