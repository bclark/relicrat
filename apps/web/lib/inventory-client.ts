export type BarcodeReading = {value:string;format:string;supplement?:string|null};
export type CollectionTypeId = 'other'|'record'|'comic'|'movie';
export type ComicField = 'issue_number'|'publisher'|'edition'|'notes';
export type MovieField = 'media_format'|'studio'|'edition'|'notes';
export type EntryField = 'title'|RecordField|ComicField|MovieField;
export type InventoryCopy = {
  barcode: Partial<BarcodeReading>;
  id: string; title: string | null; description: string | null;
  collection_type: CollectionTypeId; record_details: { artist?: string; format?: string }; comic_details: {issue_number?:string;publisher?:string}; movie_details?: {media_format?:string;studio?:string};
  edition_label: string | null; details_revision: number;
  catalog_item_id: string | null; release_id: string | null;
  identification_status: string; identification_revision: number;
  storage_location_id: string | null; storage_revision: number;
  ownership_status: string; created_at: string; updated_at: string;
};
export type Location = { id: string; name: string; parent_id: string | null };
export type CatalogCover = {provider:string;candidate_id:string;title:string;cover_url:string;source_url:string;provider_label:string};
export type Photo = { role?:string;source_provider?:string|null;source_id?:string|null;source_url?:string|null; id: string; owned_copy_id: string; content_type: string; byte_size: number };
export type Movement = { id: string; before_location_id: string | null; after_location_id: string | null; after_revision: number; created_at: string };
export type RunSave = <T>(action: () => Promise<T>) => Promise<T | undefined>;
const titleName = (copy:InventoryCopy) => copy.title || copy.description || 'Untitled copy';
export const copyName = (copy: InventoryCopy) => copy.collection_type==='comic' && copy.comic_details?.issue_number
  ? `${titleName(copy)} ${copy.comic_details.issue_number.startsWith('#') ? '' : '#'}${copy.comic_details.issue_number}`
  : copy.collection_type==='record' && copy.record_details?.artist ? `${copy.record_details.artist} — ${titleName(copy)}` : titleName(copy);
export type RecordField = 'artist' | 'format' | 'edition' | 'notes';
export type CollectionSettings = { status: 'not_started'|'skipped'|'configured'; records_enabled: boolean; default_type: CollectionTypeId; record_fields: RecordField[]; movies_enabled?: boolean; movie_fields?: MovieField[]; comics_enabled?: boolean; comic_fields?: ComicField[]; revision: number };
export type TypeField = { key: EntryField; label: string; max_length: number; placeholder: string; suggested: boolean; input?: 'text'|'autocomplete'|'select'; options?: string[] };
export type BrowseGrouping = {field:'artist'|'title';plural_label:string;unknown_label:string;order:'title'|'issue_number'};
export type BarcodeLookupConfig={provider:string;action_label:string;max_results:number;field_mappings:Record<string,string>;value_maps:Record<string,Record<string,string>>;cover_art:boolean};
export type CollectionType = { lookup?:BarcodeLookupConfig|null; barcode_formats?: string[]; grouping: BrowseGrouping|null; schema_version: 1; id: CollectionTypeId; label: string; plural_label: string; title: TypeField; fields: TypeField[]; entry_order: EntryField[] };
export type CollectionTypes = Record<CollectionTypeId, CollectionType>;

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
