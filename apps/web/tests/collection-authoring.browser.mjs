import assert from 'node:assert/strict';
import {readFile, mkdir} from 'node:fs/promises';
import {test} from 'node:test';
import {chromium} from 'playwright';
const base=process.env.RELICRAT_TEST_WEB_URL || 'http://127.0.0.1:63112';
assert.ok(['127.0.0.1','localhost'].includes(new URL(base).hostname));
const example=await readFile(new URL('../../../packages/collection-packs/proposals/tmnt-original-1988/collection.draft.json',import.meta.url),'utf8');

// Use only a disposable test stack with the standard synthetic owner.
test('collection prompt, raw JSON validation and read-only previews preserve drafts on desktop and phone',async()=>{
 const browser=await chromium.launch({headless:true, executablePath:process.env.RELICRAT_TEST_CHROME || undefined});
 try {
  const context=await browser.newContext();
  const login=await context.request.post(base+'/api/v1/auth/login',{data:{password:'synthetic-only-owner-password'},headers:{Origin:new URL(base).origin}});
  assert.equal(login.status(),200);
  const page=await context.newPage();
  const posts=[];
  page.on('request',request=>{if(request.method()==='POST')posts.push(new URL(request.url()).pathname);});
  await page.goto(base);
  await page.getByText('Start a new collection',{exact:true}).click();
  await page.getByLabel('What would you like to collect?').fill('The first 10 TMNT figures');
  const downloaded=page.waitForEvent('download');
  await page.getByRole('button',{name:'Download agent prompt'}).click();
  const prompt=await readFile(await (await downloaded).path(),'utf8');
  assert.ok(prompt.includes('The first 10 TMNT figures') && prompt.includes('"additionalProperties": false'));
  await page.getByLabel('Or paste collection JSON').fill('{"status":1,"status":2}');
  await page.getByRole('button',{name:'Validate and preview'}).click();
  await page.getByRole('alert').filter({hasText:'unique keys'}).waitFor();
  assert.equal(await page.getByLabel('Or paste collection JSON').inputValue(),'{"status":1,"status":2}');
  await page.getByLabel('Upload collection JSON').setInputFiles({name:'tmnt.json',mimeType:'application/json',buffer:Buffer.from(example)});
  await page.getByRole('button',{name:'Validate and preview'}).click();
  await page.getByRole('heading',{name:'TMNT — Original 1988 figures',exact:true}).waitFor();
  await page.getByText('Ownership and completion have not been evaluated.',{exact:false}).waitFor();
  assert.equal(await page.locator('.collection-authoring fieldset input').count(),5);
  assert.equal(await page.locator('.collection-authoring fieldset input:disabled').count(),5);
  assert.equal(await page.locator('.collection-authoring a').count(),0);
  const artifacts=process.env.RELICRAT_TEST_ARTIFACTS;
  if(artifacts) await mkdir(artifacts,{recursive:true});
  for(const width of [1440,390]) {
   await page.setViewportSize({width,height:1000});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   if(artifacts)await page.locator('details').filter({has:page.getByText('Start a new collection',{exact:true})}).screenshot({path:`${artifacts}/authoring-${width}.png`});
  }
  await page.getByLabel('Or paste collection JSON').fill('{}');
  assert.equal(await page.getByRole('heading',{name:'TMNT — Original 1988 figures',exact:true}).count(),0);
  await page.getByRole('button',{name:'Validate and preview'}).click();
  await page.getByRole('alert').filter({hasText:'draft_format'}).waitFor();
  assert.ok(posts.every(path=>path==='/api/v1/collection-proposals/preview'));
  await context.close();
 } finally {await browser.close();}
});

test('explicit activation remains empty; figure retry, custom observations and history persist',async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.RELICRAT_TEST_CHROME||undefined});
 try{
  const context=await browser.newContext();
  assert.equal((await context.request.post(base+'/api/v1/auth/login',{data:{password:'synthetic-only-owner-password'},headers:{Origin:new URL(base).origin}})).status(),200);
  const page=await context.newPage();await page.goto(base);
  await page.getByText('Start a new collection',{exact:true}).click();
  const draft=JSON.parse(example),suffix=Date.now().toString(36);draft.type_definition.id='figure-ui-'+suffix;draft.collection.type_id=draft.type_definition.id;draft.collection.id='tmnt-ui-'+suffix;
  await page.getByLabel('Or paste collection JSON').fill(JSON.stringify(draft));await page.getByRole('button',{name:'Validate and preview'}).click();
  await page.getByRole('heading',{name:draft.collection.name,exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Create collection',exact:true}).isDisabled(),true);
  await page.getByRole('checkbox',{name:'I reviewed the fields, scope and checklist.',exact:false}).check();
  await page.getByRole('button',{name:'Create collection',exact:true}).click();
  await page.getByRole('button',{name:'Collection created',exact:true}).waitFor();
  const list=await (await context.request.get(base+'/api/v1/custom-collections')).json();const collection=list.find(c=>c.name===draft.collection.name&&c.id);
  // Find this exact new ID through its stable slug, without guessing among older trials.
  const created=(await Promise.all(list.map(c=>context.request.get(base+'/api/v1/custom-collections/'+c.id).then(r=>r.json())))).find(c=>c.proposal.collection.id===draft.collection.id);
  assert.ok(created);
  assert.equal((await (await context.request.get(base+'/api/v1/inventory?custom_collection_id='+created.id)).json()).length,0);
  const form=page.getByRole('region',{name:'Saved collection: '+draft.collection.name,exact:true});
  await form.getByLabel('Figure name (required)',{exact:true}).fill('Synthetic Leonardo');
  await form.getByLabel('Accessories (optional)',{exact:true}).fill('Two synthetic swords');
  let interrupted=false;
  await page.route('**/api/v1/custom-collections/*/copies',async route=>{if(!interrupted){interrupted=true;await route.fetch();await route.abort('failed');}else await route.continue();});
  await form.getByRole('button',{name:'Add figure',exact:true}).click();
  const another=structuredClone(draft);another.collection.id+='-second';another.collection.name+=' — second goal';
  await page.getByLabel('Or paste collection JSON').fill(JSON.stringify(another));await page.getByRole('button',{name:'Validate and preview'}).click();
  await page.getByRole('heading',{name:another.collection.name,exact:true}).waitFor();
  await page.getByRole('checkbox',{name:'I reviewed the fields, scope and checklist.',exact:false}).check();await page.getByRole('button',{name:'Create collection',exact:true}).click();
  await page.getByText('Your figure draft is still in its original collection',{exact:false}).waitFor();
  assert.equal(await page.getByLabel('Collection',{exact:true}).inputValue(),created.id);
  await form.getByRole('button',{name:'Retry same save',exact:true}).click();
  await form.getByRole('button',{name:'Synthetic Leonardo',exact:true}).waitFor();
  const copies=await (await context.request.get(base+'/api/v1/inventory?custom_collection_id='+created.id)).json();assert.equal(copies.length,1);assert.equal(copies[0].custom_details.accessories,'Two synthetic swords');
  await form.getByRole('button',{name:'Synthetic Leonardo',exact:true}).click();
  const edit=page.getByRole('form',{name:'Edit copy details'});await edit.getByLabel('Condition (optional)',{exact:true}).fill('Synthetic paint wear');
  await edit.getByRole('button',{name:'Save details',exact:true}).click();
  await page.getByText('Copy details saved.',{exact:true}).waitFor();
  await page.getByText('Copy edit history',{exact:true}).click();await page.getByText('Condition: Not recorded to Synthetic paint wear',{exact:true}).waitFor();
  const location=await context.request.post(base+'/api/v1/storage-locations',{data:{name:'Synthetic figure box'},headers:{Origin:new URL(base).origin}});assert.equal(location.status(),201);
  const moved=await context.request.post(base+'/api/v1/inventory/'+copies[0].id+'/location',{data:{storage_location_id:(await location.json()).id,expected_storage_revision:0},headers:{Origin:new URL(base).origin}});assert.equal(moved.status(),200,await moved.text());
  const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGPgl1QGAACGAEwFRbXWAAAAAElFTkSuQmCC','base64');
  const photo=await context.request.post(base+'/api/v1/inventory/'+copies[0].id+'/photos',{multipart:{file:{name:'synthetic.png',mimeType:'image/png',buffer:png}},headers:{Origin:new URL(base).origin}});assert.equal(photo.status(),201,await photo.text());
  const image=await context.request.get(base+'/api/v1/inventory/'+copies[0].id+'/photos/'+(await photo.json()).id);assert.equal(image.status(),200);assert.deepEqual(await image.body(),png);
  const saved=await (await context.request.get(base+'/api/v1/inventory/'+copies[0].id)).json();assert.equal(saved.custom_details.condition,'Synthetic paint wear');
  const concurrent=await page.evaluate(async id=>{
   const payload={request_id:crypto.randomUUID(),title:'Synthetic Donatello',custom_details:{}};
   const results=await Promise.all([1,2].map(()=>fetch('/api/v1/custom-collections/'+id+'/copies',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}).then(async r=>({status:r.status,copy:await r.json()}))));return results;
  },created.id);
  assert.deepEqual(concurrent.map(r=>r.status),[200,200]);assert.equal(concurrent[0].copy.id,concurrent[1].copy.id);
  await page.reload();
  await page.getByText('Your custom collections',{exact:true}).click();await page.getByLabel('Collection',{exact:true}).selectOption(created.id);await page.getByRole('button',{name:'Synthetic Leonardo',exact:true}).waitFor();
  const artifacts=process.env.RELICRAT_TEST_ARTIFACTS;if(artifacts)await mkdir(artifacts,{recursive:true});
  for(const width of [1440,390]){await page.setViewportSize({width,height:1000});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);if(artifacts)await page.locator('details').filter({has:page.getByText('Your custom collections',{exact:true})}).screenshot({path:`${artifacts}/saved-collection-${width}.png`});}
  await context.close();
 }finally{await browser.close();}
});

test('field controls revise compatible legacy values and preserve unknown, No and empty selections',async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.RELICRAT_TEST_CHROME||undefined});
 try{
  const context=await browser.newContext();assert.equal((await context.request.post(base+'/api/v1/auth/login',{data:{password:'synthetic-only-owner-password'},headers:{Origin:new URL(base).origin}})).status(),200);
  const raw=JSON.parse(example),suffix=Date.now().toString(36);raw.type_definition.id='controls-'+suffix;raw.collection.id='controls-goal-'+suffix;raw.collection.type_id=raw.type_definition.id;raw.collection.name='Synthetic Head Variant Trial';
  raw.type_definition.optional_fields=[{id:'head',label:'Head Variant',input:'text',max_length:50},{id:'packaging',label:'Packaging',input:'select',max_length:50,options:['Loose','Carded']},{id:'signed',label:'Signed',input:'checkbox',max_length:50},{id:'accessories',label:'Accessories',input:'checkboxes',max_length:50,options:['Sword','Belt']}];
  const createdResponse=await context.request.post(base+'/api/v1/custom-collections',{data:raw,headers:{Origin:new URL(base).origin}});assert.equal(createdResponse.status(),200,await createdResponse.text());const created=await createdResponse.json();
  const old=await context.request.post(base+'/api/v1/custom-collections/'+created.id+'/copies',{data:{request_id:crypto.randomUUID(),title:'Earlier synthetic figure',custom_details:{head:'Soft'}},headers:{Origin:new URL(base).origin}});assert.equal(old.status(),200);
  const page=await context.newPage();await page.goto(base);await page.getByText('Your custom collections',{exact:true}).click();await page.getByLabel('Collection',{exact:true}).selectOption(created.id);
  const region=page.getByRole('region',{name:'Saved collection: '+raw.collection.name,exact:true});
  await region.getByText('Configure field controls',{exact:true}).click();await region.getByLabel('Control for Head Variant',{exact:true}).selectOption('radio');await region.getByLabel('Choices for Head Variant (one per line)',{exact:true}).fill('Soft\nHard\n');
  await region.getByRole('button',{name:'Review field changes',exact:true}).click();await region.getByText('All saved values remain compatible.',{exact:false}).waitFor();
  await region.getByRole('checkbox',{name:'I reviewed the field changes and all affected collections.'}).check();await region.getByRole('button',{name:'Apply field controls',exact:true}).click();await page.getByText('Field controls updated. Existing figures were preserved.',{exact:true}).waitFor();
  const add=region.locator('form').filter({has:page.getByRole('button',{name:'Add figure',exact:true})});
  const head=add.getByRole('group',{name:'Head Variant (optional)',exact:true}),signed=add.getByRole('group',{name:'Signed (optional)',exact:true}),accessories=add.getByRole('group',{name:'Accessories (optional)',exact:true});
  assert.equal(await head.getByRole('radio',{name:'Not recorded',exact:true}).isChecked(),true);
  assert.equal(await signed.getByRole('checkbox',{name:'Signed',exact:true}).getAttribute('aria-checked'),'mixed');
  await add.getByLabel('Figure name (required)',{exact:true}).fill('Typed synthetic figure');await head.getByRole('radio',{name:'Hard',exact:true}).check();await add.getByLabel('Packaging (optional)',{exact:true}).selectOption('Loose');
  await signed.getByRole('checkbox',{name:'Signed',exact:true}).check();await signed.getByRole('checkbox',{name:'Signed',exact:true}).uncheck();await accessories.getByRole('checkbox',{name:'Sword',exact:true}).check();await accessories.getByRole('checkbox',{name:'Sword',exact:true}).uncheck();
  await add.getByRole('button',{name:'Add figure',exact:true}).click();await region.getByRole('button',{name:'Typed synthetic figure',exact:true}).waitFor();
  let copies=await (await context.request.get(base+'/api/v1/inventory?custom_collection_id='+created.id)).json();const figure=copies.find(c=>c.title==='Typed synthetic figure');assert.deepEqual(figure.custom_details,{head:'Hard',packaging:'Loose',signed:false,accessories:[]});
  await region.getByRole('button',{name:'Typed synthetic figure',exact:true}).click();const edit=page.getByRole('form',{name:'Edit copy details'});
  await edit.getByRole('group',{name:'Head Variant (optional)',exact:true}).getByRole('radio',{name:'Soft',exact:true}).check();await edit.getByRole('group',{name:'Signed (optional)',exact:true}).getByRole('checkbox',{name:'Signed',exact:true}).check();
  await edit.getByRole('group',{name:'Accessories (optional)',exact:true}).getByRole('checkbox',{name:'Sword',exact:true}).check();await edit.getByRole('button',{name:'Save details',exact:true}).click();await page.getByText('Copy details saved.',{exact:true}).waitFor();
  await page.getByText('Copy edit history',{exact:true}).click();await page.getByText('Signed: No to Yes',{exact:true}).waitFor();await page.getByText('Accessories: None selected to Sword',{exact:true}).waitFor();
  const current=await (await context.request.get(base+'/api/v1/custom-collections/'+created.id)).json();const definition=structuredClone(current.proposal.type_definition);definition.optional_fields.find(f=>f.id==='packaging').options.push('Boxed');
  const concurrent=await page.evaluate(async ({id,definition})=>Promise.all([1,2].map(()=>fetch('/api/v1/custom-collections/'+id+'/definition',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({expected_revision:1,definition})}).then(r=>r.status))),{id:created.id,definition});assert.deepEqual(concurrent.sort(),[200,409]);
  await edit.getByRole('group',{name:'Signed (optional)',exact:true}).getByRole('checkbox',{name:'Signed',exact:true}).uncheck();await edit.getByRole('button',{name:'Save details',exact:true}).click();await page.getByText('Reload field controls and review your preserved draft.',{exact:false}).waitFor();
  await page.locator('.copy-details-form').getByRole('button',{name:'Reload field controls',exact:true}).click();await edit.getByRole('button',{name:'Save details',exact:true}).waitFor();
  assert.equal(await edit.getByRole('checkbox',{name:'Signed',exact:true}).isChecked(),false);await edit.getByRole('button',{name:'Save details',exact:true}).click();await page.getByText('Copy details saved.',{exact:true}).waitFor();
  assert.equal((await (await context.request.get(base+'/api/v1/inventory/'+figure.id)).json()).custom_details.signed,false);
  const history=await (await context.request.get(base+'/api/v1/custom-collections/'+created.id+'/definition-history')).json();assert.deepEqual(history.map(h=>h.revision),[2,1,0]);
  await region.getByRole('button',{name:'Reload field controls',exact:true}).click();
  const artifacts=process.env.RELICRAT_TEST_ARTIFACTS;if(artifacts)await mkdir(artifacts,{recursive:true});for(const width of [1440,390]){await page.setViewportSize({width,height:1000});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);if(artifacts)await region.screenshot({path:`${artifacts}/field-controls-${width}.png`});}
  await context.close();
 }finally{await browser.close();}
});

test('owner-reviewed checklist progress counts distinct active entries and recovers uncertain saves',async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.RELICRAT_TEST_CHROME||undefined});
 try{
  const context=await browser.newContext();assert.equal((await context.request.post(base+'/api/v1/auth/login',{data:{password:'synthetic-only-owner-password'},headers:{Origin:new URL(base).origin}})).status(),200);
  const raw=JSON.parse(example),suffix=Date.now().toString(36);raw.type_definition.id='checklist-'+suffix;raw.collection.type_id=raw.type_definition.id;raw.collection.id='goal-'+suffix;raw.collection.name='Synthetic checklist progress';
  const response=await context.request.post(base+'/api/v1/custom-collections',{data:raw,headers:{Origin:new URL(base).origin}});assert.equal(response.status(),200,await response.text());const collection=await response.json();
  async function add(title){const r=await context.request.post(base+`/api/v1/custom-collections/${collection.id}/copies`,{data:{request_id:crypto.randomUUID(),title,custom_details:{}},headers:{Origin:new URL(base).origin}});assert.equal(r.status(),200);return (await r.json()).id;}
  const first=await add('Unrelated synthetic name'),second=await add('Leonardo');
  const page=await context.newPage();await page.goto(base);await page.getByText('Your custom collections',{exact:true}).click();await page.getByLabel('Collection',{exact:true}).selectOption(collection.id);
  const region=page.getByRole('region',{name:'Saved collection: '+raw.collection.name,exact:true}),progress=region.getByRole('region',{name:'Checklist progress',exact:true});
  await progress.getByText('0 of 10 collected',{exact:true}).waitFor();await region.getByRole('button',{name:'Unrelated synthetic name',exact:true}).click();
  const match=page.getByRole('region',{name:'Checklist match',exact:true}),form=match.getByRole('form',{name:'Review checklist match'}),entry=form.getByLabel('Checklist entry',{exact:true}),confirm=form.getByRole('checkbox');
  const detailsDraft=page.locator('#copy-title');await detailsDraft.fill('Unsaved synthetic details draft');
  await entry.selectOption('leonardo');assert.equal(await confirm.isChecked(),false);await form.getByRole('button',{name:'Save checklist match',exact:true}).click();await match.getByText('Checklist link saved for review. It does not count yet.',{exact:true}).waitFor();await progress.getByText('0 of 10 collected',{exact:true}).waitFor();
  await confirm.check();await form.getByRole('button',{name:'Save checklist match',exact:true}).click();await progress.getByText('1 of 10 collected',{exact:true}).waitFor();
  const duplicate=await context.request.post(base+`/api/v1/custom-collections/${collection.id}/copies/${second}/checklist-match`,{data:{entry_id:'leonardo',confirmed:true,expected_revision:0},headers:{Origin:new URL(base).origin}});assert.equal(duplicate.status(),200);
  await progress.getByRole('button',{name:'Refresh checklist progress'}).click();await progress.getByText('1 of 10 collected',{exact:true}).waitFor();await progress.getByText('View checklist and missing entries',{exact:true}).click();await progress.getByText('Collected · Qualifying figures: 2',{exact:false}).waitFor();
  await entry.selectOption('donatello');assert.equal(await confirm.isChecked(),false);await confirm.check();await form.getByRole('button',{name:'Save checklist match',exact:true}).click();await progress.getByText('2 of 10 collected',{exact:true}).waitFor();
  await entry.selectOption('');await form.getByRole('button',{name:'Save checklist match',exact:true}).click();await progress.getByText('1 of 10 collected',{exact:true}).waitFor();
  let interrupted=false;await page.route('**/checklist-match',async route=>{if(route.request().method()==='POST'&&!interrupted){interrupted=true;await route.fetch();await route.abort('failed');}else await route.continue();});
  await entry.selectOption('raphael');await confirm.check();await form.getByRole('button',{name:'Save checklist match',exact:true}).click();await match.getByText('The save needs review.',{exact:false}).waitFor();assert.equal(await form.getByRole('button',{name:'Save checklist match',exact:true}).isDisabled(),true);
  await match.getByRole('button',{name:'Reload saved checklist match',exact:true}).click();await entry.waitFor();await page.waitForFunction(()=>document.querySelector('#checklist-entry')?.value==='raphael');assert.equal(await confirm.isChecked(),true);
  const concurrent=await page.evaluate(async ({cid,id})=>Promise.all([1,2].map(()=>fetch(`/api/v1/custom-collections/${cid}/copies/${id}/checklist-match`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({entry_id:null,confirmed:false,expected_revision:5})}).then(r=>r.status))),{cid:collection.id,id:first});assert.deepEqual(concurrent.sort(),[200,409]);
  await match.getByRole('button',{name:'Reload saved checklist match',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#checklist-entry')?.value==='');
  await progress.getByRole('button',{name:'Refresh checklist progress'}).click();await progress.getByText('1 of 10 collected',{exact:true}).waitFor();await progress.getByRole('checkbox',{name:'Show only entries without a confirmed figure'}).check();assert.equal(await progress.getByText('Leonardo',{exact:true}).count(),0);assert.equal(await progress.getByText('Donatello',{exact:true}).count(),1);
  await match.getByText('Checklist match history',{exact:true}).click();await match.getByText('Revision 6',{exact:false}).waitFor();
  assert.equal(await detailsDraft.inputValue(),'Unsaved synthetic details draft');assert.equal((await (await context.request.get(base+'/api/v1/inventory/'+first)).json()).title,'Unrelated synthetic name');
  const history=await (await context.request.get(base+`/api/v1/custom-collections/${collection.id}/copies/${first}/checklist-history`)).json();assert.deepEqual(history.map(e=>e.revision),[6,5,4,3,2,1]);
  const artifacts=process.env.RELICRAT_TEST_ARTIFACTS;if(artifacts)await mkdir(artifacts,{recursive:true});for(const width of [1440,390]){await page.setViewportSize({width,height:1000});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);if(artifacts){await progress.screenshot({path:`${artifacts}/checklist-progress-${width}.png`});await match.screenshot({path:`${artifacts}/checklist-match-${width}.png`});}}
  await context.close();
 }finally{await browser.close();}
});
