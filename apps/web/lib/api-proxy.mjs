/** Browser access to the fixed internal API; no client-selected upstreams. */
const uuid = '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}';
const copyPath = new RegExp(`^inventory/${uuid}$`);
const historyPath = new RegExp(`^inventory/${uuid}/(reconciliations|locations)$`);
const photoPath = new RegExp(`^inventory/${uuid}/photos$`);
const downloadPath = new RegExp(`^inventory/${uuid}/photos/${uuid}$`);
const actionPath = new RegExp(`^inventory/${uuid}/(reconcile|location)$`);
const locationPath = new RegExp(`^storage-locations/${uuid}$`);

/** @param {number} status @param {string} detail */
function error(status, detail) {
  return Response.json({ detail }, { status, headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' } });
}

/** @param {Request} request @param {string[]} segments */
export async function forwardApi(request, segments) {
  const path = segments.join('/');
  const methods = path === 'inventory' || path === 'storage-locations' || photoPath.test(path)
    ? ['GET', 'POST']
    : copyPath.test(path) || historyPath.test(path) || downloadPath.test(path) || locationPath.test(path)
      ? ['GET'] : actionPath.test(path) ? ['POST'] : [];
  if (!methods.length) return error(404, 'API route not found');
  if (!methods.includes(request.method)) return error(405, 'Method not allowed');
  // Next.js can normalize request.url to localhost. Use the actual Host header,
  // never X-Forwarded-Host, and require an exact scheme/host/port origin.
  if (request.method === 'POST') {
    let sameOrigin = false;
    try {
      const value = request.headers.get('origin') || '';
      const origin = new URL(value);
      sameOrigin = origin.origin === value && origin.host === request.headers.get('host') &&
        origin.protocol === new URL(request.url).protocol;
    } catch { /* Missing, null, or malformed origins are rejected. */ }
    if (!sameOrigin) return error(403, 'Open RelicRat directly before saving changes');
  }
  let upstream;
  try {
    upstream = new URL(process.env.RELICRAT_API_URL || 'http://127.0.0.1:8000');
    if (!['http:', 'https:'].includes(upstream.protocol) || upstream.username || upstream.password ||
        upstream.pathname !== '/' || upstream.search || upstream.hash) throw new Error('Invalid API origin');
  } catch {
    return error(503, 'The internal API connection is not configured correctly');
  }
  upstream.pathname = `/api/v1/${path}`;
  upstream.search = new URL(request.url).search;
  const headers = new Headers();
  let body;
  if (request.method === 'POST') {
    const contentType = request.headers.get('content-type') || '';
    const photo = photoPath.test(path);
    if (!(photo ? /^multipart\/form-data;\s*boundary=/i : /^application\/json(?:;|$)/i).test(contentType)) {
      return error(415, photo ? 'Choose a photo file to upload' : 'Expected a JSON request');
    }
    // Bound actual bytes, including chunked requests with no Content-Length.
    // Photo envelope allows 15 MiB image bytes plus multipart metadata.
    const maximum = photo ? 16 * 1024 * 1024 : 64 * 1024;
    const reader = request.body?.getReader();
    const chunks = [];
    let size = 0;
    try {
      if (reader) {
        while (true) {
          const chunk = await reader.read();
          if (chunk.done) break;
          size += chunk.value.byteLength;
          if (size > maximum) {
            await reader.cancel();
            return error(413, photo ? 'Upload is too large; photos must be at most 15 MiB' : 'Request is too large');
          }
          chunks.push(chunk.value);
        }
      }
    } catch {
      return error(400, 'The request was interrupted before it could be sent');
    }
    body = Buffer.concat(chunks);
    headers.set('content-type', contentType);
  }
  try {
    const response = await fetch(upstream, {
      method: request.method, headers, body, cache: 'no-store', redirect: 'manual',
      signal: AbortSignal.timeout(30_000),
    });
    if (response.status >= 300 && response.status < 400) return error(502, 'The internal API returned an unexpected redirect');
    return new Response(response.body, { status: response.status, headers: {
      'Content-Type': response.headers.get('content-type') || 'application/octet-stream',
      'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
    } });
  } catch {
    return error(502, request.method === 'POST'
      ? 'Save could not be confirmed. Refresh the inventory before retrying.'
      : 'Cannot reach the inventory API. Check the API service and try again.');
  }
}
