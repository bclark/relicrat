/** Server-only access boundary. Forwarded host/protocol headers are never trusted. */
export function webConfig() {
  const value = process.env.RELICRAT_WEB_ORIGIN;
  if (!value) throw new Error('Owner access is not configured');
  const url = new URL(value);
  const loopback = ['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname);
  const secure = url.protocol === 'https:';
  if ((!secure && !(url.protocol === 'http:' && loopback && process.env.RELICRAT_ALLOW_LOOPBACK_HTTP === '1')) ||
      url.username || url.password || url.pathname !== '/' || url.search || url.hash) throw new Error('Invalid owner origin');
  return { origin: url.origin, host: url.host, protocol: url.protocol, secure,
    cookieName: secure ? '__Host-relicrat_session' : 'relicrat_loopback_session' };
}
export function apiOrigin() {
  const url = new URL(process.env.RELICRAT_API_URL || 'http://127.0.0.1:8000');
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password ||
      url.pathname !== '/' || url.search || url.hash) throw new Error('Invalid API origin');
  return url;
}
export function jsonError(status, detail) {
  return Response.json({ detail }, { status, headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' } });
}
export function checkRequest(request, write = request.method === 'POST') {
  let config;
  try { config = webConfig(); } catch { return jsonError(503, 'Owner access is not configured correctly'); }
  if (request.headers.get('host') !== config.host || new URL(request.url).protocol !== config.protocol ||
      (write && request.headers.get('origin') !== config.origin)) return jsonError(403, 'Open RelicRat at its configured address');
  return null;
}
export const tokenPattern = /^[A-Za-z0-9_-]{43}$/;
export function sessionToken(headers) {
  const name = webConfig().cookieName;
  const matches = (headers.get('cookie') || '').split(';').map(value => value.trim()).filter(value => value.startsWith(name + '='));
  if (matches.length !== 1) return null;
  const token = matches[0].slice(name.length + 1);
  return tokenPattern.test(token) ? token : null;
}
export function sessionCookie(token, maxAge) {
  const config = webConfig();
  if (token && !tokenPattern.test(token)) throw new Error('Invalid session token');
  return `${config.cookieName}=${token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${maxAge}${config.secure ? '; Secure' : ''}`;
}
export async function boundedBody(request, maximum) {
  const reader = request.body?.getReader();
  const chunks = []; let size = 0;
  try {
    if (reader) while (true) {
      const part = await reader.read();
      if (part.done) break;
      size += part.value.byteLength;
      if (size > maximum) { await reader.cancel(); return jsonError(413, 'Request is too large'); }
      chunks.push(part.value);
    }
  } catch { return jsonError(400, 'The request was interrupted before it could be sent'); }
  return Buffer.concat(chunks);
}
