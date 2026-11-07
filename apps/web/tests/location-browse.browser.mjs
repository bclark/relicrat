import assert from 'node:assert/strict';
import {after,before,test} from 'node:test';
import {chromium} from 'playwright';
import {BinaryBitmap,HybridBinarizer,QRCodeReader,RGBLuminanceSource} from '@zxing/library';

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

test('a printed QR opens the renamed and moved box after phone sign-in',async t=>{
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
  const copy=await post('inventory',{title:'Synthetic QR copy',collection_type:'comic'});
  await post(`inventory/${copy.id}/location`,{storage_location_id:box.id,expected_storage_revision:0});

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
  const size=320;
  const luminance=await qr.evaluate(async (svg,size)=>{
    const image=new Image();
    image.src='data:image/svg+xml,'+encodeURIComponent(new XMLSerializer().serializeToString(svg));
    await image.decode();
    const canvas=document.createElement('canvas');
    canvas.width=canvas.height=size;
    const context=canvas.getContext('2d');
    context.imageSmoothingEnabled=false;
    context.drawImage(image,0,0,size,size);
    const pixels=context.getImageData(0,0,size,size).data;
    return Array.from({length:size*size},(_,i)=>pixels[4*i]);
  },size);
  const bitmap=new BinaryBitmap(new HybridBinarizer(new RGBLuminanceSource(Uint8ClampedArray.from(luminance),size,size)));
  const scanned=new QRCodeReader().decode(bitmap).getText();
  assert.equal(scanned,`${base}/?location=${box.id}`);

  const renamed='Synthetic QR box after move';
  await post(`storage-locations/${box.id}`,{
    name:renamed,parent_id:destination.id,expected_name:box.name,expected_parent_id:source.id,
  });
  const scanPage=await phone.newPage();
  await scanPage.goto(scanned);
  await scanPage.waitForURL(`**/login?location=${box.id}`);
  assert.equal(await scanPage.getByText(copy.title,{exact:true}).count(),0);
  await scanPage.getByLabel('Owner password').fill('synthetic-only-owner-password');
  await scanPage.getByRole('button',{name:'Sign in',exact:true}).click();
  await scanPage.waitForURL(scanned);
  await scanPage.getByRole('heading',{name:renamed,exact:true}).waitFor();
  await scanPage.locator(`#copy-row-${copy.id}`).waitFor();
  await scanPage.getByRole('button',{name:`Back to ${destination.name}`,exact:true}).waitFor();

  await scanPage.goto(base+'/login?location='+encodeURIComponent('https://example.invalid'));
  assert.equal(scanPage.url(),base+'/');
});
