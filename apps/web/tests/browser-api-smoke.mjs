/** Run only inside the disposable web-test container, never a collection app. */
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';

assert.equal(process.env.RELICRAT_SYNTHETIC_SMOKE, '1', 'Use scripts/test-web.sh on the dedicated worker');
const origin = 'http://127.0.0.1:3000';
let cookie = '';
const webFetch = (url, options = {}) => fetch(url, { ...options, headers: { ...options.headers, ...(cookie ? { cookie } : {}) }, signal: AbortSignal.timeout(15000) });
const photoBytes = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGPgl1QGAACGAEwFRbXWAAAAAElFTkSuQmCC', 'base64');
const fixture = '/tmp/relicrat-browser-smoke.json';
async function get(path) {
  const response = await webFetch(`${origin}/api/v1/${path}`);
  assert.equal(response.status, 200, await response.clone().text());
  return response.json();
}
async function save(path, body, status = 201) {
  const response = await webFetch(`${origin}/api/v1/${path}`, {
    method: 'POST', headers: { origin, 'content-type': 'application/json' }, body: JSON.stringify(body),
  });
  assert.equal(response.status, status, await response.clone().text());
  return response.json();
}
// Wait only for the disposable container's production Next.js/API startup.
let ready = false;
for (let attempt = 0; attempt < 60; attempt++) {
  try {
    if ((await fetch(`${process.env.RELICRAT_API_URL}/health`, { signal: AbortSignal.timeout(1000) })).ok &&
        (await webFetch(`${origin}/api/v1/inventory`)).status === 401) { ready = true; break; }
  } catch {}
  await new Promise(resolve => setTimeout(resolve, 500));
}
assert.ok(ready, 'Disposable web/API stack did not become ready');
const access = await webFetch(`${origin}/api/v1/auth/login`, { method: 'POST', headers: { origin, 'Content-Type': 'application/json' }, body: JSON.stringify({ password: process.env.RELICRAT_TEST_OWNER_PASSWORD }) });
assert.equal(access.status, 200, await access.clone().text());
cookie = access.headers.get('set-cookie').split(';')[0];
assert.equal(JSON.stringify(await access.json()).includes('token'), false);
if (process.argv[2] === 'seed') {
  assert.deepEqual(await get('inventory'), [], 'Refusing to seed a nonempty inventory');
  assert.deepEqual(await get('storage-locations'), [], 'Refusing to seed nonempty storage');
  const title = `Synthetic 50%_ find ${randomUUID()}`;
  const copy = await save('inventory', { title, description: 'Disposable browser/API fixture only.' });
  const form = new FormData();
  form.set('file', new Blob([photoBytes], { type: 'image/png' }), 'synthetic.png');
  const uploaded = await webFetch(`${origin}/api/v1/inventory/${copy.id}/photos`, { method: 'POST', headers: { origin }, body: form });
  assert.equal(uploaded.status, 201, await uploaded.clone().text());
  const photo = await uploaded.json();
  const room = await save('storage-locations', { name: 'Synthetic workroom' });
  const box = await save('storage-locations', { name: 'Synthetic box', parent_id: room.id });
  const assigned = await save(`inventory/${copy.id}/location`, { storage_location_id: box.id, expected_storage_revision: 0 }, 200);
  assert.equal(assigned.storage_revision, 1);
  await save(`inventory/${copy.id}/location`, { storage_location_id: null, expected_storage_revision: 0 }, 409);
  const blocked = await webFetch(`${origin}/api/v1/inventory`, {
    method: 'POST', headers: { origin: 'https://untrusted.example', 'content-type': 'application/json' }, body: JSON.stringify({ title: 'Must not exist' }),
  });
  assert.equal(blocked.status, 403);
  const oversized = await webFetch(`${origin}/api/v1/inventory`, {
    method: 'POST', headers: { origin, 'content-type': 'application/json' }, body: 'x'.repeat(65537),
  });
  assert.equal(oversized.status, 413);
  assert.equal((await webFetch(`${origin}/api/v1/admin`)).status, 404);
  const state = { copy: assigned, photo, box };
  writeFileSync(fixture, JSON.stringify(state));
} else {
  assert.equal(process.argv[2], 'verify');
}
const { copy, photo, box } = JSON.parse(readFileSync(fixture, 'utf8'));
assert.deepEqual(await get('inventory'), [copy]);
assert.deepEqual(await get(`inventory?q=${encodeURIComponent('50%_')}`), [copy]);
assert.deepEqual(await get('inventory?q=absent-synthetic-match'), []);
assert.deepEqual(await get(`inventory/${copy.id}`), copy);
assert.deepEqual(await get(`inventory/${copy.id}/photos`), [photo]);
assert.deepEqual(await get(`storage-locations/${box.id}`), box);
const movements = await get(`inventory/${copy.id}/locations`);
assert.equal(movements.length, 1);
assert.equal(movements[0].after_location_id, box.id);
assert.equal(movements[0].after_revision, 1);
const downloaded = await webFetch(`${origin}/api/v1/inventory/${copy.id}/photos/${photo.id}`);
assert.equal(downloaded.status, 200);
assert.equal(downloaded.headers.get('content-type'), 'image/png');
assert.deepEqual(Buffer.from(await downloaded.arrayBuffer()), photoBytes);
console.log(`Verified ${process.argv[2]}: production Next route → FastAPI → PostgreSQL/media, copy ${copy.id}, exact photo bytes and retained storage history.`);
