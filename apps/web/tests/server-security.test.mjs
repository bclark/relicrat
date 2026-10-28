import assert from 'node:assert/strict';
import { afterEach, beforeEach, test } from 'node:test';
import { checkRequest, sessionCookie, sessionToken, webConfig } from '../lib/server-security.mjs';
beforeEach(() => { delete process.env.RELICRAT_WEB_ORIGIN; delete process.env.RELICRAT_ALLOW_LOOPBACK_HTTP; });
afterEach(() => { delete process.env.RELICRAT_WEB_ORIGIN; delete process.env.RELICRAT_ALLOW_LOOPBACK_HTTP; });
const request = (origin, host, headers = {}) => new Request(origin + '/', { headers: { host, ...headers } });
test('missing configuration, remote HTTP and credential/path origins fail closed', () => {
  assert.equal(checkRequest(request('https://private.test', 'private.test')).status, 503);
  for (const value of ['http://private.test', 'https://user:secret@private.test', 'https://private.test/path', 'https://private.test?q=x']) {
    process.env.RELICRAT_WEB_ORIGIN = value;
    assert.throws(webConfig);
  }
  process.env.RELICRAT_WEB_ORIGIN = 'http://127.0.0.1:3000';
  assert.throws(webConfig);
  process.env.RELICRAT_ALLOW_LOOPBACK_HTTP = '1';
  assert.equal(webConfig().secure, false);
});
test('host/protocol pinning ignores spoofed forwarding headers and blocks cross-origin writes', () => {
  process.env.RELICRAT_WEB_ORIGIN = 'https://private.test';
  assert.equal(checkRequest(request('https://localhost', 'private.test')), null);
  assert.equal(checkRequest(request('https://localhost', 'evil.test', { 'x-forwarded-host': 'private.test' })).status, 403);
  assert.equal(checkRequest(request('http://localhost', 'private.test', { 'x-forwarded-proto': 'https' })).status, 403);
  assert.equal(checkRequest(request('https://localhost', 'private.test'), true).status, 403);
  assert.equal(checkRequest(request('https://localhost', 'private.test', { origin: 'https://evil.test' }), true).status, 403);
  assert.equal(checkRequest(request('https://localhost', 'private.test', { origin: 'https://private.test' }), true), null);
});
test('session cookies are host-only and opaque, strict/http-only, with secure HTTPS and explicit loopback exception', () => {
  process.env.RELICRAT_WEB_ORIGIN = 'https://private.test';
  const token = 'a'.repeat(43);
  assert.equal(sessionCookie(token, 43200), `__Host-relicrat_session=${token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=43200; Secure`);
  assert.equal(sessionToken(new Headers({ cookie: `ignored=other; __Host-relicrat_session=${token}` })), token);
  for (const value of ['', '__Host-relicrat_session=bad', `__Host-relicrat_session=${token}; __Host-relicrat_session=${token}`]) assert.equal(sessionToken(new Headers({ cookie: value })), null);
  process.env.RELICRAT_WEB_ORIGIN = 'http://127.0.0.1:3000'; process.env.RELICRAT_ALLOW_LOOPBACK_HTTP = '1';
  assert.ok(!sessionCookie(token, 43200).includes('; Secure'));
});
