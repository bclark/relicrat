import { apiOrigin, boundedBody, checkRequest, jsonError, sessionCookie, sessionToken, tokenPattern, webConfig } from './server-security.mjs';

/** Server-only cookie -> bearer translation. Browser tokens never enter JSON. */
export async function ownerSession(headers) {
  let token, origin;
  try {
    if (headers.get('host') !== webConfig().host) return { status: 403 };
    token = sessionToken(headers); origin = apiOrigin();
  } catch { return { status: 503 }; }
  if (!token) return { status: 401 };
  try {
    const response = await fetch(new URL('/api/v1/auth/session', origin), { headers: { Authorization: `Bearer ${token}` }, cache: 'no-store', redirect: 'manual', signal: AbortSignal.timeout(5000) });
    if (response.status === 401) return { status: 401 };
    if (!response.ok) return { status: 503 };
    const body = await response.json();
    return body.authenticated === true ? { status: 200 } : { status: 503 };
  } catch { return { status: 503 }; }
}

export async function ownerAction(request, action) {
  const rejected = checkRequest(request, true);
  if (rejected) return rejected;
  if (request.method !== 'POST') return jsonError(405, 'Method not allowed');
  if (!['login', 'logout'].includes(action)) return jsonError(404, 'Route not found');
  let upstream;
  try { upstream = new URL(`/api/v1/auth/${action}`, apiOrigin()); } catch { return jsonError(503, 'Owner access is unavailable'); }
  let body, token;
  const headers = new Headers();
  if (action === 'login') {
    if (!/^application\/json(?:;|$)/i.test(request.headers.get('content-type') || '')) return jsonError(415, 'Expected a JSON request');
    body = await boundedBody(request, 2048);
    if (body instanceof Response) return body;
    headers.set('Content-Type', 'application/json');
  } else {
    token = sessionToken(request.headers);
    if (token) headers.set('Authorization', `Bearer ${token}`);
  }
  try {
    const response = token || action === 'login' ? await fetch(upstream, {
      method: 'POST', headers, body, cache: 'no-store', redirect: 'manual', signal: AbortSignal.timeout(15_000),
    }) : null;
    if (action === 'logout' && (!response || response.ok || response.status === 401)) {
      return Response.json({ authenticated: false }, { headers: { 'Cache-Control': 'no-store', 'Set-Cookie': sessionCookie('', 0) } });
    }
    if (action === 'login' && response?.ok) {
      const result = await response.json();
      if (!tokenPattern.test(result.token || '') || result.max_age !== 43200 || !Number.isFinite(Date.parse(result.expires_at))) return jsonError(502, 'Sign in could not be confirmed');
      return Response.json({ authenticated: true, expires_at: result.expires_at }, {
        headers: { 'Cache-Control': 'no-store', 'Set-Cookie': sessionCookie(result.token, result.max_age), 'X-Content-Type-Options': 'nosniff' },
      });
    }
    if (response?.status === 429) {
      const error = jsonError(429, 'Too many failed attempts. Try again later');
      const retry = response.headers.get('retry-after');
      if (retry && /^\d{1,5}$/.test(retry)) error.headers.set('Retry-After', retry);
      return error;
    }
    if (response?.status === 401) return jsonError(401, 'Password not recognized');
    if (response?.status === 422) return jsonError(422, 'Enter your owner password (up to 256 characters)');
    return jsonError(503, action === 'login' ? 'Owner access is unavailable. Try again later' : 'Sign out could not be confirmed. Try again');
  } catch { return jsonError(503, action === 'login' ? 'Sign in could not be confirmed. Try again' : 'Sign out could not be confirmed. Try again'); }
}
