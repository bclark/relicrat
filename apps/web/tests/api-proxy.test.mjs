import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { after, before, test } from 'node:test';
import { forwardApi } from '../lib/api-proxy.mjs';

const id = '00000000-0000-0000-0000-000000000001';
const origin = 'https://relicrat.test:3000';
const token = 'a'.repeat(43);
const observed = [];
let apiOrigin;
const server = createServer(async (request, response) => {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  observed.push({ method: request.method, url: request.url, headers: request.headers, body: Buffer.concat(chunks) });
  response.setHeader('Set-Cookie', 'upstream-secret=not-for-the-browser');
  response.setHeader('X-Internal-Detail', 'not-forwarded');
  if (request.url.includes('redirect')) {
    response.writeHead(307, { Location: '/should-not-follow' });
    response.end();
  } else if (request.url.includes('validation')) {
    response.writeHead(422, { 'Content-Type': 'application/json' });
    response.end(JSON.stringify({ detail: 'Invalid synthetic input' }));
  } else if (request.url.includes(`/photos/${id}`)) {
    response.writeHead(200, { 'Content-Type': 'image/png' });
    response.end(Buffer.from([0, 1, 255, 4]));
  } else {
    response.writeHead(request.method === 'POST' ? 201 : 200, { 'Content-Type': 'application/json' });
    response.end(JSON.stringify({ synthetic: true }));
  }
});
before(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  apiOrigin = `http://127.0.0.1:${server.address().port}`;
  process.env.RELICRAT_API_URL = apiOrigin;
  process.env.RELICRAT_WEB_ORIGIN = origin;
});
after(async () => {
  await new Promise(resolve => server.close(resolve));
  delete process.env.RELICRAT_API_URL;
  delete process.env.RELICRAT_WEB_ORIGIN;
});
function request(path = 'inventory', options = {}) {
  const headers = new Headers(options.headers);
  headers.set('host', new URL(origin).host);
  headers.append('cookie', `__Host-relicrat_session=${token}`);
  return new Request(`${origin}/api/v1/${path}`, { ...options, headers });
}
function post(body = '{}', headers = {}) {
  return { method: 'POST', headers: { origin, 'content-type': 'application/json', ...headers }, body };
}

test('forwards literal query and strips credentials and internal response headers', async () => {
  const response = await forwardApi(request('inventory?q=50%25_%5C&limit=2', {
    headers: { cookie: 'private=secret', authorization: 'Bearer secret', 'x-forwarded-host': 'evil.test' },
  }), ['inventory']);
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { synthetic: true });
  const upstream = observed.at(-1);
  assert.equal(upstream.url, '/api/v1/inventory?q=50%25_%5C&limit=2');
  assert.equal(upstream.headers.authorization, `Bearer ${token}`);
  for (const name of ['cookie', 'x-forwarded-host']) assert.equal(upstream.headers[name], undefined);
  assert.equal(response.headers.get('set-cookie'), null);
  assert.equal(response.headers.get('x-internal-detail'), null);
  assert.equal(response.headers.get('cache-control'), 'no-store');
  assert.equal(response.headers.get('x-content-type-options'), 'nosniff');
});

test('only fixed inventory/storage routes and their methods can reach the API', async () => {
  const count = observed.length;
  for (const path of ['health', 'admin', '../inventory', 'inventory/http://evil.test', `inventory/${id}/delete`]) {
    assert.equal((await forwardApi(request(path), path.split('/'))).status, 404);
  }
  assert.equal((await forwardApi(request('inventory', { method: 'DELETE' }), ['inventory'])).status, 405);
  assert.equal((await forwardApi(request(`inventory/${id}`, post()), ['inventory', id])).status, 405);
  assert.equal(observed.length, count);
  for (const path of [`inventory/${id}`, `inventory/${id}/photos`, `inventory/${id}/reconciliations`,
    `inventory/${id}/locations`, 'storage-locations', `storage-locations/${id}`]) {
    assert.equal((await forwardApi(request(path), path.split('/'))).status, 200);
  }
});

test('same-origin JSON saves preserve body and upstream validation failures', async () => {
  const body = JSON.stringify({ title: 'Synthetic find' });
  assert.equal((await forwardApi(request('inventory', post(body)), ['inventory'])).status, 201);
  assert.equal(observed.at(-1).body.toString(), body);
  const response = await forwardApi(request('inventory?q=validation', post(body)), ['inventory']);
  assert.equal(response.status, 422);
  assert.deepEqual(await response.json(), { detail: 'Invalid synthetic input' });
  for (const path of [`inventory/${id}/reconcile`, `inventory/${id}/location`, 'storage-locations']) {
    assert.equal((await forwardApi(request(path, post()), path.split('/'))).status, 201);
  }
});

test('rejects missing, null and mismatched origins, including multipart', async () => {
  const count = observed.length;
  for (const supplied of [undefined, 'null', 'https://evil.test', 'http://relicrat.test:3001', 'http://relicrat.test:3000']) {
    const options = post();
    if (supplied === undefined) delete options.headers.origin;
    else options.headers.origin = supplied;
    assert.equal((await forwardApi(request('inventory', options), ['inventory'])).status, 403);
    options.headers['content-type'] = 'multipart/form-data; boundary=test';
    assert.equal((await forwardApi(request(`inventory/${id}/photos`, options), ['inventory', id, 'photos'])).status, 403);
  }
  assert.equal(observed.length, count);
});

test('bounds actual JSON and chunked multipart bytes, and rejects wrong media types', async () => {
  const count = observed.length;
  assert.equal((await forwardApi(request('inventory', post('x'.repeat(64 * 1024 + 1), { 'content-length': '1' })), ['inventory'])).status, 413);
  assert.equal((await forwardApi(request('inventory', post('{}', { 'content-type': 'text/plain' })), ['inventory'])).status, 415);
  const path = `inventory/${id}/photos`;
  assert.equal((await forwardApi(request(path, post()), ['inventory', id, 'photos'])).status, 415);
  const stream = new ReadableStream({ start(controller) { controller.enqueue(new Uint8Array(16 * 1024 * 1024 + 1)); controller.close(); } });
  assert.equal((await forwardApi(request(path, { ...post(stream, { 'content-type': 'multipart/form-data; boundary=test' }), duplex: 'half' }), ['inventory', id, 'photos'])).status, 413);
  assert.equal(observed.length, count);
});

test('multipart upload and binary download preserve exact bytes', async () => {
  const form = new FormData();
  form.set('file', new Blob([new Uint8Array([0, 1, 255, 4])], { type: 'image/png' }), 'synthetic.png');
  const upload = request(`inventory/${id}/photos`, { method: 'POST', headers: { origin }, body: form });
  const expected = Buffer.from(await upload.clone().arrayBuffer());
  assert.equal((await forwardApi(upload, ['inventory', id, 'photos'])).status, 201);
  assert.deepEqual(observed.at(-1).body, expected);
  const response = await forwardApi(request(`inventory/${id}/photos/${id}`), ['inventory', id, 'photos', id]);
  assert.equal(response.headers.get('content-type'), 'image/png');
  assert.deepEqual(Buffer.from(await response.arrayBuffer()), Buffer.from([0, 1, 255, 4]));
});

test('does not follow upstream redirects', async () => {
  const count = observed.length;
  assert.equal((await forwardApi(request('inventory?q=redirect'), ['inventory'])).status, 502);
  assert.equal(observed.length, count + 1);
});

test('invalid configuration and unavailable API yield safe errors without retrying saves', async () => {
  const count = observed.length;
  try {
    for (const value of ['file:///etc/passwd', 'http://user:secret@127.0.0.1', `${apiOrigin}/other`, `${apiOrigin}?secret=bad`]) {
      process.env.RELICRAT_API_URL = value;
      assert.equal((await forwardApi(request(), ['inventory'])).status, 503);
    }
    process.env.RELICRAT_API_URL = 'http://127.0.0.1:1';
    assert.equal((await forwardApi(request(), ['inventory'])).status, 502);
    const saved = await forwardApi(request('inventory', post()), ['inventory']);
    assert.equal(saved.status, 502);
    assert.match((await saved.json()).detail, /Refresh the inventory before retrying/);
    assert.equal(observed.length, count);
  } finally { process.env.RELICRAT_API_URL = apiOrigin; }
});

test('interrupted request body is rejected before the API receives a save', async () => {
  const count = observed.length;
  const body = new ReadableStream({ start(controller) { controller.error(new Error('synthetic interruption')); } });
  const response = await forwardApi(request('inventory', { ...post(body), duplex: 'half' }), ['inventory']);
  assert.equal(response.status, 400);
  assert.equal(observed.length, count);
});


test('matches actual browser Host when Next.js normalizes the internal request URL', async () => {
  const direct = new Request('https://localhost:3000/api/v1/inventory', post('{}', {
    origin, host: new URL(origin).host, cookie: `__Host-relicrat_session=${token}`,
  }));
  assert.equal((await forwardApi(direct, ['inventory'])).status, 201);
  const count = observed.length;
  const spoofed = request('inventory', post('{}', { origin: 'http://evil.test', 'x-forwarded-host': 'evil.test' }));
  assert.equal((await forwardApi(spoofed, ['inventory'])).status, 403);
  const missingHost = new Request(`${origin}/api/v1/inventory`, post());
  assert.equal((await forwardApi(missingHost, ['inventory'])).status, 403);
  assert.equal(observed.length, count);
});

test('catalog paths preserve the same write boundary and reject arbitrary extensions', async () => {
  for (const path of ['catalog/categories', 'catalog/items', `catalog/items/${id}/releases`]) {
    assert.equal((await forwardApi(request(path), path.split('/'))).status, 200);
    assert.equal((await forwardApi(request(path, post()), path.split('/'))).status, 201);
    assert.equal((await forwardApi(request(path, post('{}', { origin: 'https://untrusted.test' })), path.split('/'))).status, 403);
  }
  for (const path of [`catalog/items/${id}`, `catalog/items/${id}/releases/${id}`]) {
    assert.equal((await forwardApi(request(path), path.split('/'))).status, 200);
    assert.equal((await forwardApi(request(path, post()), path.split('/'))).status, 405);
  }
  for (const path of ['catalog', 'catalog/items/bad', `catalog/items/${id}/delete`, `catalog/categories/${id}`, `catalog/items/${id}/releases/bad`]) {
    assert.equal((await forwardApi(request(path), path.split('/'))).status, 404);
  }
});


test('anonymous and forged browser bearer headers cannot reach protected upstream data', async () => {
  const count = observed.length;
  for (const path of ['inventory', `inventory/${id}/photos/${id}`, 'catalog/items', 'storage-locations']) {
    const guest = new Request(`${origin}/api/v1/${path}`, { headers: { host: new URL(origin).host, Authorization: `Bearer ${token}` } });
    assert.equal((await forwardApi(guest, path.split('/'))).status, 401);
  }
  assert.equal(observed.length, count);
});

test('copy label edits and history retain the same allowlist, method and origin boundaries', async () => {
  const action = `inventory/${id}/details`, history = `inventory/${id}/detail-history`;
  const body = JSON.stringify({ title: 'Harbor Lights', edition_label: 'Blue vinyl', expected_details_revision: 0, expected_identification_revision: 0 });
  assert.equal((await forwardApi(request(action, post(body)), action.split('/'))).status, 201);
  assert.equal(observed.at(-1).body.toString(), body);
  assert.equal((await forwardApi(request(history + '?limit=20&offset=0'), history.split('/'))).status, 200);
  const count = observed.length;
  assert.equal((await forwardApi(request(action), action.split('/'))).status, 405);
  assert.equal((await forwardApi(request(history, post(body)), history.split('/'))).status, 405);
  assert.equal((await forwardApi(request(action, post(body, { origin: 'https://evil.test' })), action.split('/'))).status, 403);
  assert.equal((await forwardApi(request(action + '/unsafe', post(body)), [...action.split('/'), 'unsafe'])).status, 404);
  assert.equal(observed.length, count);
});

test('collection preferences use the protected fixed endpoint and same-origin JSON writes',async()=>{
  const path='collection-settings',body=JSON.stringify({status:'configured',records_enabled:true,default_type:'record',record_fields:['artist'],expected_revision:0});
  assert.equal((await forwardApi(request(path),[path])).status,200);
  assert.equal((await forwardApi(request(path,post(body)),[path])).status,201);
  assert.equal(observed.at(-1).body.toString(),body);
  const count=observed.length;
  assert.equal((await forwardApi(request(path,{method:'DELETE'}),[path])).status,405);
  assert.equal((await forwardApi(request(path,post(body,{origin:'https://evil.test'})),[path])).status,403);
  assert.equal((await forwardApi(request(path+'/unsafe'),[path,'unsafe'])).status,404);
  assert.equal(observed.length,count);
});


test('type definitions use a fixed read-only owner endpoint',async()=>{
  const path='collection-settings/types';
  assert.equal((await forwardApi(request(path),path.split('/'))).status,200);
  const count=observed.length;
  assert.equal((await forwardApi(request(path,post()),path.split('/'))).status,405);
  assert.equal((await forwardApi(request(path+'/record'),[...path.split('/'),'record'])).status,404);
  assert.equal(observed.length,count);
});
