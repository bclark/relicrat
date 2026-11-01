import { apiOrigin, checkRequest, jsonError as error, sessionToken } from './server-security.mjs';
/** Browser access to the fixed internal API; no client-selected upstreams. */
const uuid = '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}';
const copyPath = new RegExp(`^inventory/${uuid}$`);
const historyPath = new RegExp(`^inventory/${uuid}/(reconciliations|locations|detail-history)$`);
const photoPath = new RegExp(`^inventory/${uuid}/photos$`);
const downloadPath = new RegExp(`^inventory/${uuid}/photos/${uuid}$`);
const actionPath = new RegExp(`^inventory/${uuid}/(reconcile|location|details)$`);
const catalogCollection = /^(catalog\/categories|catalog\/items)$/;
const catalogItem = new RegExp(`^catalog/items/${uuid}$`);
const releases = new RegExp(`^catalog/items/${uuid}/releases$`);
const release = new RegExp(`^catalog/items/${uuid}/releases/${uuid}$`);
const importRows = new RegExp(`^imports/${uuid}/rows$`);
const storageLabels = new RegExp(`^imports/${uuid}/storage-labels$`);
const storageMapping = new RegExp(`^imports/${uuid}/storage-(preview|apply)$`);
const importUpload = /^imports\/(preview|commit)$/;
const barcodeLookup = /^barcode-lookups\/(record|comic|other)$/;
const barcodeCover = /^barcode-lookups\/(record|comic|other)\/[A-Za-z0-9_-]{1,128}\/cover$/;
const locationPath = new RegExp(`^storage-locations/${uuid}$`);

/** @param {Request} request @param {string[]} segments */
export async function forwardApi(request, segments) {
  const rejected = checkRequest(request);
  if (rejected) return rejected;
  const token = sessionToken(request.headers);
  if (!token) return error(401, 'Sign in to continue');
  const path = segments.join('/');
  const methods = path === 'appearance' || path === 'collection-settings' || path === 'inventory' || path === 'storage-locations' || photoPath.test(path) || catalogCollection.test(path) || releases.test(path)
    ? ['GET', 'POST']
    : barcodeCover.test(path) || storageLabels.test(path) || path === 'collection-groups' || path === 'imports' || importRows.test(path) || path === 'collection-settings/publisher-suggestions' || path === 'collection-settings/artist-suggestions' || path === 'collection-settings/types' || copyPath.test(path) || historyPath.test(path) || downloadPath.test(path) || locationPath.test(path) || catalogItem.test(path) || release.test(path)
      ? ['GET'] : barcodeLookup.test(path) || storageMapping.test(path) || importUpload.test(path) || path === 'appearance/preview' || actionPath.test(path) ? ['POST'] : [];
  if (!methods.length) return error(404, 'API route not found');
  if (!methods.includes(request.method)) return error(405, 'Method not allowed');
  let upstream;
  try {
    upstream = apiOrigin();
  } catch {
    return error(503, 'The internal API connection is not configured correctly');
  }
  upstream.pathname = `/api/v1/${path}`;
  upstream.search = new URL(request.url).search;
  const headers = new Headers({ Authorization: `Bearer ${token}` });
  let body;
  if (request.method === 'POST') {
    const contentType = request.headers.get('content-type') || '';
    const photo = photoPath.test(path);
    const csv = importUpload.test(path);
    if (!(csv ? /^text\/csv(?:;|$)/i : photo ? /^multipart\/form-data;\s*boundary=/i : /^application\/json(?:;|$)/i).test(contentType)) {
      return error(415, csv ? 'Choose a CSV file' : photo ? 'Choose a photo file to upload' : 'Expected a JSON request');
    }
    // Bound actual bytes, including chunked requests with no Content-Length.
    // Photo envelope allows 15 MiB image bytes plus multipart metadata.
    const maximum = csv ? 4 * 1024 * 1024 : photo ? 16 * 1024 * 1024 : 64 * 1024;
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
            return error(413, csv ? 'CSV must be at most 4 MiB' : photo ? 'Upload is too large; photos must be at most 15 MiB' : 'Request is too large');
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
