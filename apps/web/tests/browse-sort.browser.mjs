import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdir } from 'node:fs/promises';
import { test } from 'node:test';
import { chromium } from 'playwright';

const base = process.env.RELICRAT_TEST_WEB_URL;
assert.ok(base && new URL(base).hostname === '127.0.0.1' && new URL(base).port !== '56742',
  'Use a disposable loopback stack');

test('phone sorting, filters and Covers preserve an ordered page across Back', async t => {
  const browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE });
  t.after(() => browser.close());
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true });
  const post = async (path, data, contentType='application/json') => {
    const response = await context.request.post(base+'/api/v1/'+path, {
      data, headers: { Origin: base, 'Content-Type': contentType },
    });
    assert.ok(response.ok(), await response.text());
    return response.json();
  };
  await post('auth/login', { password: 'synthetic-only-owner-password' });
  const prefix = 'Synthetic sort '+Date.now();
  const records = Array.from({length: 25}, (_,i) =>
    [24-i, prefix+' '+String(24-i).padStart(2,'0')]);
  const csv = ['Title,Artist,Format,release_id', ...records.map(([n,title]) =>
    `${title},${n<13?'North Window':'Mira Vale'},Vinyl,${n}`)].join('\n');
  const hash = createHash('sha256').update(csv).digest('hex');
  const batch = await post('imports/commit?source=discogs&reviewed_sha256='+hash, csv, 'text/csv');
  assert.equal(batch.batch.copy_count, 25);

  const longTitle = prefix+' 19 '+('long-title-without-breaks'.repeat(6));
  const variants = await Promise.all(['Blue pressing','Copper pressing'].map(edition_label =>
    post('inventory',{title:longTitle,collection_type:'record',record_details:{artist:'Mira Vale'},edition_label})));
  const shelf = await post('storage-locations',{name:'Synthetic archive shelf'});
  await post('inventory/'+variants[0].id+'/location',{storage_location_id:shelf.id,expected_storage_revision:0});

  const page = await context.newPage();
  page.setDefaultTimeout(12000);
  const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto(base);
  await page.getByRole('navigation',{name:'Collections'}).getByRole('button',{name:'Albums',exact:true}).tap();
  await page.getByRole('searchbox',{name:'Find a copy'}).fill(prefix);
  await page.getByRole('button',{name:'Search',exact:true}).tap();
  await page.getByRole('button',{name:'Filters',exact:true}).tap();
  await page.getByLabel('Sort copies').selectOption('title');
  await page.getByRole('button',{name:'Filters (1)',exact:true}).tap();
  const rows=page.locator('.collection .copy-row');
  await rows.first().filter({hasText:prefix+' 00'}).waitFor();
  assert.equal(await rows.count(),20);
  await page.getByRole('button',{name:'Next',exact:true}).tap();
  await rows.first().filter({hasText:longTitle}).waitFor();
  const blue=page.getByRole('button',{name:'Open Mira Vale — '+longTitle+' · Blue pressing',exact:true});
  await blue.waitFor();
  await page.getByRole('button',{name:'Filters (1)',exact:true}).tap();
  await page.getByRole('button',{name:'Covers',exact:true}).tap();
  await page.getByRole('button',{name:'Filters (2)',exact:true}).tap();
  await page.setViewportSize({width:320,height:844});
  assert.equal(await blue.getByText('Blue pressing',{exact:true}).isVisible(),true);
  assert.equal(await blue.locator('.phone-copy-meta').isVisible(),false);
  assert.equal(await blue.getByLabel('No artwork',{exact:true}).isVisible(),true);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  if(process.env.RELICRAT_SCREENSHOTS){
    await mkdir(process.env.RELICRAT_SCREENSHOTS,{recursive:true});
    await page.screenshot({path:process.env.RELICRAT_SCREENSHOTS+'/sorted-covers-phone.png'});
  }

  await blue.tap();
  await page.getByRole('heading',{name:longTitle,exact:true}).waitFor();
  await page.getByRole('button',{name:'Back to collection',exact:true}).tap();
  await page.getByText('Page 2',{exact:true}).waitFor();
  await page.waitForFunction(id=>document.activeElement?.id===id,'copy-row-'+variants[0].id);
  assert.equal(await page.getByRole('searchbox').inputValue(),prefix);
  await page.getByText('Title A–Z',{exact:true}).filter({visible:true}).first().waitFor();

  await page.getByRole('button',{name:'Filters (2)',exact:true}).tap();
  await page.getByLabel('Storage location',{exact:true}).selectOption(shelf.id);
  await page.getByRole('button',{name:'Filters (3)',exact:true}).tap();
  await page.getByRole('status').filter({hasText:'1 copy on this page'}).waitFor();
  await page.getByText(shelf.name,{exact:true}).filter({visible:true}).first().waitFor();
  await page.getByRole('searchbox').fill('No synthetic match');
  await page.getByRole('button',{name:'Search',exact:true}).tap();
  await page.getByRole('heading',{name:'No matching copies'}).waitFor();
  await page.getByRole('button',{name:'Clear search',exact:true}).tap();
  await blue.waitFor();
  await page.getByRole('button',{name:'Clear storage filter',exact:true}).tap();

  await page.setViewportSize({width:1440,height:1050});
  await page.getByLabel('Browse view').selectOption('groups');
  await page.getByLabel('Sort copies').selectOption('artist');
  assert.equal(await page.getByLabel('Browse view').inputValue(),'copies');
  await rows.first().filter({hasText:'Mira Vale'}).waitFor();
  await page.getByRole('button',{name:'List',exact:true}).click();
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  if(process.env.RELICRAT_SCREENSHOTS)
    await page.screenshot({path:process.env.RELICRAT_SCREENSHOTS+'/sorted-list-desktop.png'});
  assert.deepEqual(errors,[]);
});
