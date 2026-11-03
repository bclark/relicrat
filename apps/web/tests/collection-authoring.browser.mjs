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
  await page.getByText('Start a new collection — preview',{exact:true}).click();
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
   if(artifacts)await page.locator('.collection-authoring').screenshot({path:`${artifacts}/authoring-${width}.png`});
  }
  await page.getByLabel('Or paste collection JSON').fill('{}');
  assert.equal(await page.getByRole('heading',{name:'TMNT — Original 1988 figures',exact:true}).count(),0);
  await page.getByRole('button',{name:'Validate and preview'}).click();
  await page.getByRole('alert').filter({hasText:'draft_format'}).waitFor();
  assert.ok(posts.every(path=>path==='/api/v1/collection-proposals/preview'));
  await context.close();
 } finally {await browser.close();}
});
