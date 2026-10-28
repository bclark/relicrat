import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { before, after, test } from 'node:test';
import { ownerAction, ownerSession } from '../lib/owner-access.mjs';
const origin = 'https://private.test';
const token = 'b'.repeat(43);
let state = 200, calls = [], api;
const server = createServer(async (request, response) => {
  const chunks = []; for await (const part of request) chunks.push(part);
  calls.push({ path: request.url, authorization: request.headers.authorization, cookie: request.headers.cookie, body: Buffer.concat(chunks).toString() });
  response.writeHead(state, { 'Content-Type': 'application/json', 'Retry-After': '900', 'Set-Cookie': 'internal-secret=never-forward' });
  response.end(JSON.stringify(request.url.endsWith('/login') ? { token, max_age: 43200, expires_at: '2030-01-01T00:00:00Z' } : { authenticated: true }));
});
before(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  api = `http://127.0.0.1:${server.address().port}`;
  process.env.RELICRAT_API_URL = api; process.env.RELICRAT_WEB_ORIGIN = origin;
});
after(async () => { await new Promise(resolve => server.close(resolve)); delete process.env.RELICRAT_API_URL; delete process.env.RELICRAT_WEB_ORIGIN; });
function request(action, extra = {}) {
  return new Request(origin + '/api/v1/auth/' + action, { method: 'POST', headers: { host: 'private.test', origin, 'Content-Type': 'application/json', ...extra }, body: '{"password":"synthetic-only"}' });
}
test('login issues only an opaque HttpOnly cookie, never bearer JSON or upstream cookies', async () => {
  const response = await ownerAction(request('login'), 'login');
  assert.equal(response.status, 200);
  assert.match(response.headers.get('set-cookie'), /__Host-relicrat_session=.*HttpOnly; SameSite=Strict; Max-Age=43200; Secure/);
  assert.ok(!response.headers.get('set-cookie').includes('internal-secret'));
  const text = await response.text(); assert.ok(!text.includes(token)); assert.equal(JSON.parse(text).authenticated, true);
  assert.equal(calls.at(-1).cookie, undefined); assert.equal(calls.at(-1).authorization, undefined);
});
test('bad origins, excessive bodies and wrong content types never reach login', async () => {
  const count = calls.length;
  assert.equal((await ownerAction(request('login', { origin: 'https://evil.test' }), 'login')).status, 403);
  assert.equal((await ownerAction(request('login', { 'Content-Type': 'text/plain' }), 'login')).status, 415);
  const large = new Request(origin + '/api/v1/auth/login', { method: 'POST', headers: { host: 'private.test', origin, 'Content-Type': 'application/json' }, body: 'x'.repeat(2049) });
  assert.equal((await ownerAction(large, 'login')).status, 413);
  assert.equal(calls.length, count);
});
test('logout revokes via server bearer, clears cookie only when confirmed or already ended', async () => {
  const headers = { cookie: `__Host-relicrat_session=${token}`, authorization: 'Bearer attacker' };
  let response = await ownerAction(request('logout', headers), 'logout');
  assert.equal(response.status, 200); assert.match(response.headers.get('set-cookie'), /Max-Age=0/);
  assert.equal(calls.at(-1).authorization, `Bearer ${token}`); assert.equal(calls.at(-1).cookie, undefined);
  state = 503; response = await ownerAction(request('logout', headers), 'logout');
  assert.equal(response.status, 503); assert.equal(response.headers.get('set-cookie'), null);
  state = 401; response = await ownerAction(request('logout', headers), 'logout'); assert.equal(response.status, 200);
  state = 200;
});
test('login rejection/rate limit/outage and server-side session checks remain fail-closed', async () => {
  for (const [upstream, expected] of [[401,401], [429,429], [503,503], [307,503]]) {
    state = upstream; const response = await ownerAction(request('login'), 'login');
    assert.equal(response.status, expected); assert.equal(response.headers.get('set-cookie'), null);
  }
  state = 200;
  assert.equal((await ownerSession(new Headers({ host: 'private.test' }))).status, 401);
  assert.equal((await ownerSession(new Headers({ host: 'evil.test', cookie: `__Host-relicrat_session=${token}` }))).status, 403);
  assert.equal((await ownerSession(new Headers({ host: 'private.test', cookie: `__Host-relicrat_session=${token}` }))).status, 200);
  state = 401; assert.equal((await ownerSession(new Headers({ host: 'private.test', cookie: `__Host-relicrat_session=${token}` }))).status, 401);
  state = 200;
});
