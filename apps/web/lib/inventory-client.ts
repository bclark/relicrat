export type InventoryCopy = {
  id: string; title: string | null; description: string | null;
  edition_label: string | null; details_revision: number;
  catalog_item_id: string | null; release_id: string | null;
  identification_status: string; identification_revision: number;
  storage_location_id: string | null; storage_revision: number;
  ownership_status: string; created_at: string; updated_at: string;
};
export type Location = { id: string; name: string; parent_id: string | null };
export type Photo = { id: string; owned_copy_id: string; content_type: string; byte_size: number };
export type Movement = { id: string; before_location_id: string | null; after_location_id: string | null; after_revision: number; created_at: string };
export type RunSave = <T>(action: () => Promise<T>) => Promise<T | undefined>;
export const copyName = (copy: InventoryCopy) => copy.title || copy.description || 'Untitled copy';

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
  get uncertain() { return this.status === 0 || this.status >= 500; }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/v1/${path}`, { ...options, cache: 'no-store', signal: options.signal || AbortSignal.timeout(35_000) });
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new ApiError(options.method === 'POST'
      ? 'Save could not be confirmed. Reload and inspect the record before trying again.'
      : 'Cannot reach the inventory. Check the service, then reload.', 0);
  }
  if (response.status === 401) { window.location.replace('/login'); throw new ApiError('Session ended. Sign in again.', 401); }
  let body;
  try { body = await response.json(); }
  catch { throw new ApiError('The service returned an unreadable response. Reload before trying again.', response.ok ? 502 : response.status); }
  if (!response.ok) {
    const detail = typeof body?.detail === 'string' ? body.detail : `The request was rejected (${response.status}). Check the fields and try again.`;
    throw new ApiError(detail, response.status);
  }
  return body as T;
}
export const jsonSave = (body: unknown): RequestInit => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
export const errorText = (error: unknown) => error instanceof Error ? error.message : 'The request failed. Reload and try again.';
