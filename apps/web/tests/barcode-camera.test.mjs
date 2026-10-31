import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readBarcode,cameraError} from '../lib/barcode-camera.mjs';

test('readings retain leading zeroes and only bounded UPC/EAN text and supplements',()=>{
 assert.deepEqual(readBarcode('012345678905','UPC_A','00111'),{value:'012345678905',format:'UPC_A',supplement:'00111'});
 assert.equal(readBarcode('0012345678905','EAN_13',null).value,'0012345678905');
 assert.equal(readBarcode('01234565','EAN_8','12').supplement,'12');
 for(const [value,format] of [['https://example.test','QR_CODE'],['<img src=x>','UPC_A'],['123','EAN_13'],['123456789012','toString'],[123456789012,'UPC_A'],['012345678905\n','UPC_A']])assert.equal(readBarcode(value,format),null);
 for(const supplement of ['123','123456',12,'<script>'])assert.equal(readBarcode('012345678905','UPC_A',supplement).supplement,null);
});
test('camera failures offer bounded recovery without reflecting device errors',()=>{
 assert.match(cameraError({name:'NotAllowedError'}),/browser settings/);
 assert.match(cameraError({name:'NotFoundError'}),/No camera/);
 assert.match(cameraError({name:'NotReadableError'}),/other apps/);
 assert.equal(cameraError({message:'private camera identifier'}),cameraError(null));
});
