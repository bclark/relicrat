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
