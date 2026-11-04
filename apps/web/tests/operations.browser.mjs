/** Standalone synthetic report; no app, owner login or inventory used. */
import assert from 'node:assert/strict';
import {test} from 'node:test';
import {spawn} from 'node:child_process';
import {mkdtemp,writeFile,chmod,mkdir,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';

test('operations report shows fresh evidence, wraps on phones and drops green states on failure',async()=>{
 const root=await mkdtemp(join(tmpdir(),'relicrat-operations-')),repo=fileURLToPath(new URL('../../../',import.meta.url));let server,browser;
 try{
  const identity={source_commit:'a'.repeat(40),sha256:'b'.repeat(64),completed_at_utc:new Date().toISOString()};
  const mac={...identity,status:'verified-offhost-copy-and-disposable-restore',restore_verified:true,member_checksums_verified:true,saved_image_ids_verified:true};
  const cloud={...identity,status:'verified-offsite-parts',all_downloaded_parts_verified:true,downloaded_manifest_verified:true,full_archive_sha256_verified:true,owner_only_metadata_verified:true,cms_authenticated_decryption_verified:true};
  await writeFile(join(root,'mac.json'),JSON.stringify(mac));await writeFile(join(root,'cloud.json'),JSON.stringify(cloud));
  const config={receipts:{'mac-backup':{label:'Mac verified backup',path:join(root,'mac.json')},'cloud-backup':{label:'Google Drive verified copy',path:join(root,'cloud.json')}},capacity_path:root,capacity_id:'storage',capacity_label:'NAS storage',minimum_free_bytes:1};
  await writeFile(join(root,'config.json'),JSON.stringify(config));await chmod(join(root,'config.json'),0o600);
  server=spawn('python3',[join(repo,'scripts/operations.py'),'serve','--config',join(root,'config.json'),'--output',join(root,'status.json'),'--report',join(repo,'docs/project-dashboard.html')]);
  const url=await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(new Error('Report startup timed out')),10000);server.once('error',reject);server.stdout.once('data',data=>{clearTimeout(timer);resolve(data.toString().trim());});});
  assert.equal(new URL(url).hostname,'127.0.0.1');assert.notEqual(new URL(url).port,'56742');
  browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE||undefined});const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(url);await page.getByText('All reported checks are current.',{exact:true}).waitFor();assert.equal(await page.locator('#operations-checks tr').count(),3);
  const artifacts=process.env.RELICRAT_TEST_ARTIFACTS;if(artifacts)await mkdir(artifacts,{recursive:true});
  for(const width of [1440,390,320]){await page.setViewportSize({width,height:950});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));if(artifacts)await page.screenshot({path:join(artifacts,`operations-${width}.png`),fullPage:true});}
  await page.getByRole('link',{name:'Historical overview',exact:true}).click();assert.equal(await page.locator('#operations').isVisible(),false);await page.getByRole('link',{name:'Operations',exact:true}).click();await page.getByText('All reported checks are current.',{exact:true}).waitFor();
  const injected='<img src=x onerror="window.bad=true">';await page.route('**/operations.json',route=>route.fulfill({json:{format:1,checked_at_utc:new Date().toISOString(),checks:[{id:'safe',label:injected,detail:'Synthetic literal evidence',state:'ok'}]}}));
  await page.getByRole('button',{name:'Refresh checks',exact:true}).click();await page.getByText(injected,{exact:true}).waitFor();assert.equal(await page.locator('#operations-checks img').count(),0);
  await page.unroute('**/operations.json');await writeFile(join(root,'status.json'),JSON.stringify({format:1,checked_at_utc:'2000-01-01T00:00:00Z',checks:[]}));
  const refresh=page.getByRole('button',{name:'Refresh checks',exact:true});await page.waitForFunction(()=>!document.querySelector('#refresh-operations').disabled);await refresh.focus();const unavailable=page.waitForResponse(r=>new URL(r.url()).pathname==='/operations.json');await page.keyboard.press('Enter');assert.equal((await unavailable).status(),503);await page.getByRole('status').filter({hasText:'Current checks are unavailable'}).waitFor();assert.equal(await page.locator('#operations-table').isVisible(),false);assert.equal(await page.locator('#operations-checks tr').count(),0);assert.equal(await refresh.isEnabled(),true);
  if(artifacts)await page.screenshot({path:join(artifacts,'operations-unavailable-320.png'),fullPage:true});assert.deepEqual(errors,[]);
 }finally{await browser?.close();if(server&&server.exitCode===null){server.kill();await new Promise(resolve=>server.once('exit',resolve));}await rm(root,{recursive:true,force:true});}
});
