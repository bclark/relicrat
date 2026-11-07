import assert from 'node:assert/strict';
import {after,before,test} from 'node:test';
import {chromium} from 'playwright';

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
