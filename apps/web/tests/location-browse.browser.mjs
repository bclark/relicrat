import assert from 'node:assert/strict';
import {after,before,test} from 'node:test';
import {chromium} from 'playwright';
import {BinaryBitmap,DecodeHintType,HybridBinarizer,QRCodeReader,RGBLuminanceSource} from '@zxing/library';

const base=process.env.RELICRAT_TEST_WEB_URL;
assert.ok(base&&new URL(base).hostname==='127.0.0.1'&&new URL(base).port!=='56742','Use only a disposable loopback test stack');
let browser;
before(async()=>{browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE});});
after(async()=>{await browser?.close();});

for(const [layout,viewport] of [
  ['desktop',{width:1440,height:1050}],
  ['mobile',{width:320,height:840}],
]){
  test(`browse nested locations and move a copy on ${layout}`,async t=>{
    const context=await browser.newContext({viewport});
    t.after(()=>context.close());
    const api=base+'/api/v1/';
    const post=async(path,data)=>{
      const response=await context.request.post(api+path,{headers:{Origin:base},data});
      assert.ok(response.ok(),await response.text());
      return response.json();
    };
    await post('auth/login',{password:'synthetic-only-owner-password'});
    const shelf=await post('storage-locations',{name:`Synthetic location-browser ${layout} shelf`});
    const boxA=await post('storage-locations',{name:`Box A ${layout}`,parent_id:shelf.id});
    const boxB=await post('storage-locations',{name:`Box B ${layout}`,parent_id:shelf.id});
    const prefix=`Synthetic ${layout} copy`;
    const unassigned=await post('inventory',{title:`${prefix} unassigned`,collection_type:'other'});
    for(let i=0;i<22;i++){
      const copy=await post('inventory',{title:`${prefix} ${i}`,collection_type:i%2?'record':'comic'});
      await post(`inventory/${copy.id}/location`,{storage_location_id:boxA.id,expected_storage_revision:0});
    }

    const page=await context.newPage();
    const errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    t.after(()=>assert.deepEqual(errors,[]));
    await page.goto(base);
    await page.getByRole('button',{name:'Browse locations',exact:true}).click();
    const roots=page.getByRole('region',{name:'Top-level locations',exact:true});
    await roots.getByRole('button',{name:shelf.name,exact:true}).waitFor();
    assert.equal(await roots.getByRole('button',{name:boxA.name,exact:true}).count(),0);

    await page.getByRole('button',{name:'Unassigned copies',exact:true}).click();
    const unassignedView=page.getByRole('region',{name:'Unassigned copies',exact:true});
    await unassignedView.getByLabel('Find a copy').fill(`${prefix} unassigned`);
    await unassignedView.getByRole('button',{name:'Search',exact:true}).click();
    await unassignedView.locator(`#copy-row-${unassigned.id}`).waitFor();
    await unassignedView.getByRole('button',{name:'All locations',exact:true}).click();

    await roots.getByRole('button',{name:shelf.name,exact:true}).click();
    const nested=page.getByRole('region',{name:'Nested locations',exact:true});
    await nested.getByRole('button',{name:boxA.name,exact:true}).click();
    const contents=page.getByRole('region',{name:boxA.name,exact:true});
    const pages=contents.getByRole('navigation',{name:'Inventory pages'});
    await contents.getByLabel('Find a copy').fill(prefix);
    await contents.getByRole('button',{name:'Search',exact:true}).click();
    await contents.getByRole('status').filter({hasText:'20 copies on this page'}).waitFor();
    await contents.getByRole('heading',{name:'Comics',exact:true}).waitFor();
    await contents.getByRole('heading',{name:'Albums',exact:true}).waitFor();
    await pages.getByRole('button',{name:'Next',exact:true}).click();
    await contents.getByRole('status').filter({hasText:'2 copies on this page'}).waitFor();
    const row=contents.locator('.copy-row').first();
    const rowId=await row.getAttribute('id');
    const rowName=await row.getAttribute('aria-label');
    await row.click();
    await page.getByLabel('Location',{exact:true}).selectOption(boxB.id);
    await page.getByRole('status').filter({hasText:`Added to ${boxB.name}.`}).waitFor();
    await page.getByRole('button',{name:'Back to collection',exact:true}).click();
    await pages.getByText('Page 2',{exact:true}).waitFor();
    await contents.getByRole('status').filter({hasText:'1 copy on this page'}).waitFor();
    assert.equal(await contents.getByLabel('Find a copy').inputValue(),prefix);
    assert.equal(await contents.locator(`#${rowId}`).count(),0);
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));

    await contents.getByRole('button',{name:`Back to ${shelf.name}`,exact:true}).click();
    await nested.getByRole('button',{name:boxB.name,exact:true}).click();
    const destination=page.getByRole('region',{name:boxB.name,exact:true});
    await destination.getByRole('button',{name:rowName,exact:true}).waitFor();
    const response=await context.request.get(api+`inventory/${rowId.slice('copy-row-'.length)}`);
    assert.ok(response.ok(),await response.text());
    const moved=await response.json();
    assert.equal(moved.storage_location_id,boxB.id);
    assert.equal(moved.storage_revision,2);
  });
}

for(const [layout,viewport] of [
  ['desktop',{width:1440,height:1050}],
  ['mobile',{width:320,height:840}],
]){
  test(`create, rename and move a populated box on ${layout}`,async t=>{
    const context=await browser.newContext({viewport});
    t.after(()=>context.close());
    const api=base+'/api/v1/';
    const post=(path,data)=>context.request.post(api+path,{headers:{Origin:base},data});
    const login=await post('auth/login',{password:'synthetic-only-owner-password'});
    assert.ok(login.ok(),await login.text());
    const page=await context.newPage();
    const errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    t.after(()=>assert.deepEqual(errors,[]));
    await page.goto(base);
    await page.getByRole('button',{name:'Browse locations',exact:true}).click();

    const create=async(name,nested=false)=>{
      await page.getByRole('button',{name:nested?'Add nested location':'Add location',exact:true}).click();
      const form=page.getByRole('form',{name:'Create location',exact:true});
      await form.getByLabel('Location name').fill(name);
      const saved=page.waitForResponse(response=>response.url()===api+'storage-locations'&&response.request().method()==='POST');
      await form.getByRole('button',{name:'Create location',exact:true}).click();
      const response=await saved;
      assert.equal(response.status(),201,await response.text());
      await page.getByRole('heading',{name,exact:true,level:1}).waitFor();
      return response.json();
    };
    const source=await create(`Manage ${layout} source shelf`);
    await page.getByRole('button',{name:'All locations',exact:true}).click();
    const destination=await create(`Manage ${layout} destination shelf`);
    await page.getByRole('button',{name:'All locations',exact:true}).click();
    const roots=page.getByRole('region',{name:'Top-level locations',exact:true});
    await roots.getByRole('button',{name:source.name,exact:true}).click();
    const box=await create(`Manage ${layout} box`,true);
    assert.equal(box.parent_id,source.id);

    const seeded=await post('inventory',{title:`Synthetic managed copy ${layout}`,collection_type:'other'});
    assert.ok(seeded.ok(),await seeded.text());
    const copy=await seeded.json();
    const assigned=await post(`inventory/${copy.id}/location`,{storage_location_id:box.id,expected_storage_revision:0});
    assert.ok(assigned.ok(),await assigned.text());

    const edit=page.getByRole('form',{name:'Edit location',exact:true});
    const openEditor=()=>page.getByRole('button',{name:'Rename or move location',exact:true}).click();
    const renamed=`Renamed ${layout} box`;
    await openEditor();
    await edit.getByLabel('Location name').fill(renamed);
    await edit.getByRole('button',{name:'Save location',exact:true}).click();
    await page.getByRole('heading',{name:renamed,exact:true,level:1}).waitFor();
    await openEditor();
    await edit.getByRole('button',{name:'Choose a different parent',exact:true}).click();
    const picker=edit.getByRole('region',{name:'Choose parent location',exact:true});
    await picker.getByRole('button',{name:destination.name,exact:true}).click();
    await picker.getByRole('button',{name:'Use this destination',exact:true}).click();
    await edit.getByText(`${destination.name} / ${renamed}`,{exact:true}).waitFor();
    await edit.getByRole('button',{name:'Save location',exact:true}).click();
    await page.getByRole('button',{name:`Back to ${destination.name}`,exact:true}).waitFor();
    await page.locator(`#copy-row-${copy.id}`).waitFor();

    await page.getByRole('button',{name:`Back to ${destination.name}`,exact:true}).click();
    const nested=page.getByRole('region',{name:'Nested locations',exact:true});
    await nested.getByRole('button',{name:renamed,exact:true}).waitFor();
    await openEditor();
    await edit.getByRole('button',{name:'Choose a different parent',exact:true}).click();
    const self=picker.getByRole('button',{name:destination.name,exact:true});
    await self.waitFor();
    assert.equal(await self.isDisabled(),true);
    assert.equal(await picker.getByRole('button',{name:renamed,exact:true}).count(),0);

    const cycle=await post(`storage-locations/${destination.id}`,{
      name:destination.name,parent_id:box.id,expected_name:destination.name,expected_parent_id:null,
    });
    assert.equal(cycle.status(),409,await cycle.text());
    assert.match((await cycle.json()).detail,/nested locations/);
    const stale=await post(`storage-locations/${box.id}`,{
      name:'Stale edit',parent_id:source.id,expected_name:box.name,expected_parent_id:source.id,
    });
    assert.equal(stale.status(),409,await stale.text());

    const read=async path=>{
      const response=await context.request.get(api+path);
      assert.ok(response.ok(),await response.text());
      return response.json();
    };
    assert.equal((await read(`storage-locations/${destination.id}`)).parent_id,null);
    const moved=await read(`storage-locations/${box.id}`);
    assert.equal(moved.parent_id,destination.id);
    assert.equal(moved.name,renamed);
    const retained=await read(`inventory/${copy.id}`);
    assert.equal(retained.storage_location_id,box.id);
    assert.equal(retained.storage_revision,1);

    await edit.getByRole('button',{name:'Cancel',exact:true}).click();
    await page.getByRole('button',{name:'All locations',exact:true}).click();
    await roots.getByRole('button',{name:source.name,exact:true}).click();
    await nested.getByText('No nested locations.',{exact:true}).waitFor();
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  });
}

test('a printed QR opens the moved box and resumes and resolves mobile audits after sign-in',async t=>{
  const owner=await browser.newContext();
  const phone=await browser.newContext({viewport:{width:320,height:840},isMobile:true,hasTouch:true});
  t.after(()=>Promise.all([owner.close(),phone.close()]));
  const post=async(path,data)=>{
    const response=await owner.request.post(base+'/api/v1/'+path,{headers:{Origin:base},data});
    assert.ok(response.ok(),await response.text());
    return response.json();
  };
  await post('auth/login',{password:'synthetic-only-owner-password'});
  const source=await post('storage-locations',{name:'Synthetic QR source shelf'});
  const destination=await post('storage-locations',{name:'Synthetic QR destination shelf'});
  const box=await post('storage-locations',{name:'Synthetic QR box',parent_id:source.id});
  const otherBox=await post('storage-locations',{name:'Synthetic other box',parent_id:source.id});
  const extra=await post('inventory',{title:'Synthetic extra found in box',collection_type:'comic'});
  await post(`inventory/${extra.id}/location`,{storage_location_id:otherBox.id,expected_storage_revision:0});
  const copy=await post('inventory',{title:'Synthetic QR copy',collection_type:'comic'});
  await post(`inventory/${copy.id}/location`,{storage_location_id:box.id,expected_storage_revision:0});
  const missing=await post('inventory',{title:'Synthetic missing QR copy',collection_type:'comic'});
  await post(`inventory/${missing.id}/location`,{storage_location_id:box.id,expected_storage_revision:0});

  const movedDuringDraft=await post('inventory',{title:'Synthetic copy moved during draft',collection_type:'comic'});
  await post(`inventory/${movedDuringDraft.id}/location`,{storage_location_id:box.id,expected_storage_revision:0});

  const desktop=await owner.newPage();
  await desktop.goto(base);
  await desktop.getByRole('button',{name:'Browse locations',exact:true}).click();
  await desktop.getByRole('button',{name:source.name,exact:true}).click();
  await desktop.getByRole('button',{name:box.name,exact:true}).click();
  await desktop.getByRole('link',{name:'Print QR label',exact:true}).click();
  await desktop.getByRole('heading',{name:box.name,exact:true}).waitFor();
  assert.equal(await desktop.getByRole('button',{name:'Print label',exact:true}).isEnabled(),true);
  await desktop.emulateMedia({media:'print'});
  assert.equal(await desktop.getByRole('button',{name:'Print label',exact:true}).count(),0);
  const qr=desktop.getByRole('img',{name:'Location QR code',exact:true});
  await qr.waitFor();
  const {size,luminance}=await qr.evaluate(async svg=>{
    const size=svg.viewBox.baseVal.width*8;
    const image=new Image();
    image.src='data:image/svg+xml,'+encodeURIComponent(new XMLSerializer().serializeToString(svg));
    await image.decode();
    const canvas=document.createElement('canvas');
    canvas.width=canvas.height=size;
    const context=canvas.getContext('2d');
    context.imageSmoothingEnabled=false;
    context.drawImage(image,0,0,size,size);
    const pixels=context.getImageData(0,0,size,size).data;
    return {size,luminance:Array.from({length:size*size},(_,i)=>pixels[4*i])};
  });
  const bitmap=new BinaryBitmap(new HybridBinarizer(new RGBLuminanceSource(Uint8ClampedArray.from(luminance),size,size)));
  const scanned=new QRCodeReader().decode(bitmap,new Map([[DecodeHintType.PURE_BARCODE,true]])).getText();
  assert.equal(scanned,`${base}/?location=${box.id}`);

  const renamed='Synthetic QR box after move';
  await post(`storage-locations/${box.id}`,{
    name:renamed,parent_id:destination.id,expected_name:box.name,expected_parent_id:source.id,
  });
  let scanPage=await phone.newPage();
  const pageErrors=[];
  scanPage.on('pageerror',error=>pageErrors.push(error.message));
  await scanPage.goto(scanned);
  await scanPage.waitForURL(`**/login?location=${box.id}`);
  assert.equal(await scanPage.getByText(copy.title,{exact:true}).count(),0);
  await scanPage.getByLabel('Owner password').fill('synthetic-only-owner-password');
  await scanPage.getByRole('button',{name:'Sign in',exact:true}).click();
  await scanPage.waitForURL(scanned);
  await scanPage.getByRole('heading',{name:renamed,exact:true}).waitFor();
  await scanPage.locator(`#copy-row-${copy.id}`).waitFor();
  await scanPage.getByRole('button',{name:`Back to ${destination.name}`,exact:true}).waitFor();

  await scanPage.getByRole('button',{name:'Check contents',exact:true}).click();
  let audit=scanPage.getByRole('region',{name:'Check location contents',exact:true});
  await audit.getByRole('checkbox',{name:/^Synthetic QR copy/}).check();
  assert.equal(await audit.getByRole('checkbox',{name:/Synthetic missing QR copy/}).isChecked(),false);
  await audit.getByLabel('Extra item',{exact:true}).fill('Synthetic extra found in box');
  await audit.getByRole('button',{name:'Add extra item',exact:true}).click();
  await audit.getByRole('checkbox',{name:/Synthetic copy moved during draft/}).check();
  await scanPage.close();
  scanPage=await phone.newPage();
  scanPage.on('pageerror',error=>pageErrors.push(error.message));
  await scanPage.goto(scanned);
  await scanPage.getByRole('button',{name:'Check contents',exact:true}).click();
  audit=scanPage.getByRole('region',{name:'Check location contents',exact:true});
  await audit.getByRole('button',{name:'Resume audit',exact:true}).click();
  assert.equal(await audit.getByRole('checkbox',{name:/^Synthetic QR copy/}).isChecked(),true);
  assert.equal(await audit.getByRole('checkbox',{name:/Synthetic copy moved during draft/}).isChecked(),true);
  await audit.getByRole('list',{name:'Recorded extra items'}).getByText('Synthetic extra found in box',{exact:false}).waitFor();

  await post(`inventory/${movedDuringDraft.id}/location`,{storage_location_id:otherBox.id,expected_storage_revision:1});
  await audit.getByRole('button',{name:'Review audit',exact:true}).click();
  const changes=audit.getByRole('region',{name:'Review box changes',exact:true});
  await changes.getByText(/Synthetic copy moved during draft/).waitFor();
  assert.equal(await audit.getByRole('button',{name:'Save audit',exact:true}).count(),0);
  await changes.getByRole('button',{name:'Review current checklist',exact:true}).click();
  assert.equal(await audit.getByRole('checkbox',{name:/^Synthetic QR copy/}).isChecked(),true);
  assert.equal(await audit.getByRole('checkbox',{name:/Synthetic copy moved during draft/}).count(),0);

  await audit.getByRole('button',{name:'Review audit',exact:true}).click();
  await audit.getByRole('heading',{name:'Missing copies (1)',exact:true}).waitFor();
  await audit.getByRole('heading',{name:'Extra items (1)',exact:true}).waitFor();
  const auditUrl=`${base}/api/v1/storage-locations/${box.id}/audits`;
  const saveResponse=scanPage.waitForResponse(response=>response.url()===auditUrl&&response.request().method()==='POST');
  await audit.getByRole('button',{name:'Save audit',exact:true}).click();
  const saved=await saveResponse;
  assert.ok(saved.ok(),await saved.text());
  const firstResult=await saved.json();
  assert.deepEqual(firstResult.copies.filter(row=>row.found).map(row=>row.id),[copy.id]);
  assert.deepEqual(firstResult.extras,['Synthetic extra found in box']);
  await audit.getByRole('status').filter({hasText:'Audit saved.'}).waitFor();
  assert.deepEqual(pageErrors,[]);
  const replay=await phone.request.post(auditUrl,{headers:{Origin:base},data:saved.request().postDataJSON()});
  assert.ok(replay.ok(),await replay.text());
  assert.deepEqual(await replay.json(),firstResult);
  await audit.getByRole('button',{name:'Start a fresh check',exact:true}).click();
  await audit.getByRole('checkbox',{name:/^Synthetic QR copy/}).check();
  await audit.getByRole('checkbox',{name:/Synthetic missing QR copy/}).check();
  await audit.getByRole('button',{name:'Review audit',exact:true}).click();
  const secondSave=scanPage.waitForResponse(response=>response.url()===auditUrl&&response.request().method()==='POST');
  await audit.getByRole('button',{name:'Save audit',exact:true}).click();
  const second=await secondSave;
  assert.ok(second.ok(),await second.text());
  const secondResult=await second.json();
  await audit.getByText(/Last checked.*2 found.*0 missing.*0 extra/).waitFor();
  assert.notEqual(secondResult.id,firstResult.id);

  const openUrl=`${base}/api/v1/storage-locations/audits/open`;
  const openBefore=await phone.request.get(openUrl);
  assert.ok(openBefore.ok(),await openBefore.text());
  assert.deepEqual((await openBefore.json()).find(row=>row.id===box.id),{id:box.id,name:renamed,unresolved:2});

  await scanPage.getByRole('button',{name:`Back to ${destination.name}`,exact:true}).click();
  await scanPage.getByRole('button',{name:'All locations',exact:true}).click();
  await scanPage.getByText('Unresolved audit findings',{exact:true}).click();
  const openList=scanPage.getByRole('region',{name:'Locations with unresolved findings',exact:true});
  const listedBox=openList.getByRole('link',{name:renamed,exact:true});
  assert.equal(await listedBox.getAttribute('href'),`/?location=${box.id}`);
  await listedBox.locator('..').getByText('2 unresolved',{exact:false}).waitFor();
  await scanPage.goto(scanned);
  await scanPage.getByRole('button',{name:'Check contents',exact:true}).click();
  const history=audit.getByText('Audit history',{exact:true});
  await history.click();
  const past=audit.getByRole('button',{name:/^Past audit.*1 found.*1 missing.*1 extra/});
  const current=audit.getByRole('button',{name:/^Latest audit.*2 found.*0 missing.*0 extra.*0 unresolved/});
  await current.waitFor();
  await past.filter({hasText:'2 unresolved'}).click();
  const summary=audit.getByText(/Selected audit.*1 found.*1 missing.*1 extra/);
  const savedAudit=summary.locator('..');
  await savedAudit.getByText(/Synthetic missing QR copy/).waitFor();
  await savedAudit.getByText('Synthetic extra found in box',{exact:true}).waitFor();
  const resolve=savedAudit.getByRole('region',{name:'Resolve discrepancy',exact:true});
  await savedAudit.getByRole('button',{name:'Resolve Synthetic missing QR copy',exact:true}).click();
  await resolve.getByRole('button',{name:'Found elsewhere',exact:true}).click();
  await resolve.getByRole('button',{name:source.name,exact:true}).click();
  await resolve.getByRole('button',{name:otherBox.name,exact:true}).click();
  await resolve.getByRole('button',{name:`Confirm move to ${otherBox.name}`,exact:true}).click();
  await savedAudit.getByText(`Resolved · Located in ${otherBox.name}`,{exact:true}).waitFor();

  await savedAudit.getByRole('button',{name:`Resolve ${extra.title}`,exact:true}).click();
  await resolve.getByRole('button',{name:'Search inventory',exact:true}).click();
  await resolve.getByRole('button',{name:new RegExp(`^${extra.title}.*${otherBox.name}`)}).click();
  const resolutionUrl=`${auditUrl}/${firstResult.id}/resolutions`;
  const matchResponse=scanPage.waitForResponse(response=>response.url()===resolutionUrl&&response.request().method()==='POST');
  await resolve.getByRole('button',{name:'Confirm match and assignment',exact:true}).click();
  const matched=await matchResponse;
  assert.ok(matched.ok(),await matched.text());
  const matchedResult=await matched.json();
  const extraStatus=`Resolved · Matched ${extra.title} and assigned it to ${renamed}`;
  await savedAudit.getByText(extraStatus,{exact:true}).waitFor();
  await scanPage.locator(`#copy-row-${extra.id}`).waitFor();
  assert.equal(await scanPage.locator(`#copy-row-${missing.id}`).count(),0);
  const matchRetry=await phone.request.post(resolutionUrl,{headers:{Origin:base},data:matched.request().postDataJSON()});
  assert.ok(matchRetry.ok(),await matchRetry.text());
  assert.deepEqual(await matchRetry.json(),matchedResult);

  await scanPage.reload();
  await scanPage.getByRole('button',{name:'Check contents',exact:true}).click();
  await history.click();
  await current.waitFor();
  await past.filter({hasText:'0 unresolved'}).click();
  await savedAudit.getByRole('heading',{name:'Original findings',exact:true}).waitFor();
  await savedAudit.getByText(/Synthetic missing QR copy/).waitFor();
  await savedAudit.getByText(extra.title,{exact:true}).waitFor();
  await savedAudit.getByText(`Resolved · Located in ${otherBox.name}`,{exact:true}).waitFor();
  await savedAudit.getByText(extraStatus,{exact:true}).waitFor();
  assert.deepEqual(pageErrors,[]);

  const persisted=await phone.request.get(`${base}/api/v1/storage-locations/${box.id}/audits`);
  assert.ok(persisted.ok(),await persisted.text());
  const {latest:currentAudit}=await persisted.json();
  assert.deepEqual(currentAudit,secondResult);
  const old=await phone.request.get(`${auditUrl}/${firstResult.id}`);
  assert.ok(old.ok(),await old.text());
  const latest=await old.json();
  assert.equal(latest.id,firstResult.id);
  assert.deepEqual(latest.copies.filter(copy=>!copy.found).map(copy=>copy.id),[missing.id]);
  assert.deepEqual(latest.copies,firstResult.copies);
  assert.deepEqual(latest.extras,firstResult.extras);
  assert.equal(latest.resolutions[`missing:${missing.id}`].location_id,otherBox.id);
  assert.equal(latest.resolutions['extra:0'].copy_id,extra.id);
  assert.equal(latest.resolutions['extra:0'].location_id,box.id);
  const conflictingResolution=await phone.request.post(resolutionUrl,{headers:{Origin:base},data:{
    action:'create_extra',extra_index:0,title:extra.title,
  }});
  assert.equal(conflictingResolution.status(),409);
  const copyResponse=await phone.request.get(`${base}/api/v1/inventory/${missing.id}`);
  assert.ok(copyResponse.ok(),await copyResponse.text());
  const movedMissing=await copyResponse.json();
  assert.equal(movedMissing.storage_location_id,otherBox.id);
  assert.equal(movedMissing.storage_revision,2);
  const assignedExtra=await phone.request.get(`${base}/api/v1/inventory/${extra.id}`);
  assert.ok(assignedExtra.ok(),await assignedExtra.text());
  const movedExtra=await assignedExtra.json();
  assert.equal(movedExtra.storage_location_id,box.id);
  assert.equal(movedExtra.storage_revision,2);

  const openAfter=await phone.request.get(openUrl);
  assert.ok(openAfter.ok(),await openAfter.text());
  assert.equal((await openAfter.json()).some(row=>row.id===box.id),false);
  await scanPage.getByRole('button',{name:`Back to ${destination.name}`,exact:true}).click();
  await scanPage.getByRole('button',{name:'All locations',exact:true}).click();
  await scanPage.getByText('Unresolved audit findings',{exact:true}).click();
  await scanPage.getByText('No locations with unresolved findings on this page.',{exact:true}).waitFor();

  await scanPage.goto(base+'/login?location='+encodeURIComponent('https://example.invalid'));
  assert.equal(scanPage.url(),base+'/');
});

test('audit resolutions validate the observed copies and replay new copy creation safely',async t=>{
  const context=await browser.newContext();
  t.after(()=>context.close());
  const request=(path,data)=>context.request.post(`${base}/api/v1/${path}`,{headers:{Origin:base},data});
  const post=async(path,data)=>{
    const response=await request(path,data);
    assert.ok(response.ok(),await response.text());
    return response.json();
  };
  await post('auth/login',{password:'synthetic-only-owner-password'});
  const box=await post('storage-locations',{name:'Synthetic resolution validation box'});
  const missing=await post('inventory',{title:'Synthetic found-in-place copy'});
  await post(`inventory/${missing.id}/location`,{storage_location_id:box.id,expected_storage_revision:0});
  const auditPath=`storage-locations/${box.id}/audits`;
  const preview=await context.request.get(`${base}/api/v1/${auditPath}`);
  assert.ok(preview.ok(),await preview.text());
  const {snapshot}=await preview.json();
  const audit=await post(auditPath,{
    request_id:crypto.randomUUID(),snapshot,found_ids:[],extras:['Synthetic new extra'],
  });
  const resolutionPath=`${auditPath}/${audit.id}/resolutions`;
  const stale=await request(resolutionPath,{
    action:'match_extra',extra_index:0,copy_id:missing.id,expected_storage_revision:0,
  });
  assert.equal(stale.status(),409);
  const expected=await request(resolutionPath,{
    action:'match_extra',extra_index:0,copy_id:missing.id,expected_storage_revision:1,
  });
  assert.equal(expected.status(),422);
  const found=await post(resolutionPath,{action:'found',copy_id:missing.id});
  assert.equal(found.resolutions[`missing:${missing.id}`].action,'found');
  const payload={action:'create_extra',extra_index:0,title:'Synthetic new extra',collection_type:'comic'};
  const created=await post(resolutionPath,payload);
  assert.deepEqual(await post(resolutionPath,payload),created);
  const newId=created.resolutions['extra:0'].copy_id;
  const contents=await context.request.get(`${base}/api/v1/inventory?storage_location_id=${box.id}`);
  assert.ok(contents.ok(),await contents.text());
  const copies=await contents.json();
  assert.equal(copies.length,2);
  assert.equal(copies.find(copy=>copy.id===missing.id).storage_revision,1);
  assert.equal(copies.find(copy=>copy.id===newId).collection_type,'comic');
});
