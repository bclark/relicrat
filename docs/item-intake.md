# Unified item intake

Status: implemented for review; not deployed. This replaces the quick-entry/review gate and the separate custom-copy creation form with one mounted entry task.

## Destination and identity

Opening Add an item from a selected collection fixes the destination and says **Add to Movies** (or the collection name), without a repeated picker. From All items, a bounded chooser includes built-in and named custom collections. The chooser reuses collection paging, off-page selection and failure recovery. The selected destination survives Back, including an unconfirmed save. Replacing a dirty draft requires explicit discard; uncertain writes cannot change destination. Drafts remain page-local and reloads can lose them.

Back restores the mounted browse query, filters, page and scroll context. Starting intake hides rather than replaces a selected-copy editor, preserving its unsaved changes. View item after creation still uses the existing dirty-detail replacement guard. A saved custom collection definition never creates ownership; only the final Save item does.

## Configured fields and review

Built-in labels, order, maximum lengths, controls, autocomplete choices, barcode formats and provider mappings come from the current type definitions. Existing owner field preferences remain in effect. Notes and edition are under More details; their relative configured ordering is retained within that optional group. Custom title/optional fields use the saved definition and existing typed controls, preserving unknown versus false/empty values. A named custom collection has no invented barcode/provider capability.

Scanning with a configured provider starts lookup immediately. Typed barcodes include an explicit format so eight-digit observations are not guessed. With no provider, retain the observation and permit manual entry. Lookup failures and no match do not block a title-only save. Hidden intake stops camera activity through the existing scanner lifecycle and aborts pending lookup requests.

Choosing a candidate fills blank draft fields only. Per-field suggestion choices can replace explicitly chosen values or restore prior text. Editing a field clears its suggestion choice. Candidate choice and field review do not create a catalog match or ownership. Catalog cover starts unchecked, is enabled only after its preview loads, and sends the registered provider/candidate ID with the final save. A failed preview clears that artwork choice and explains that the collector can save without it. Stored catalog artwork retains provenance separately from physical-copy photos.

## Save outcomes

Save item creates one physical object using the existing endpoint. A synchronous form guard and the shared save lock prevent a double submit from replacing a pending custom request identifier. Confirmed success shows the item title and collection, with Add another item and View item. Photos, storage and checklist qualification remain separate reviewed operations.

Ordinary uncertain creation keeps fields locked until the owner inspects inventory. Check collection returns to browsing without clearing the draft; Clear inspected draft is explicit and requires confirmation. Similar titles are not treated as proof of success and saves never retry automatically.

Custom creation retains its exact request ID, payload, target and expected definition revision for safe same-save retries, including a response lost after commit. The retry button waits for any in-progress definition read. Known definition-revision rejection provides Reload field controls while retaining input; the next reviewed attempt uses the current definition. A conflicting or unconfirmed request remains blocked for inspection or the existing same-request retry rather than issuing a new identity.

When preferences cannot load, explicit generic entry uses bounded local Other fields, without overwriting saved preferences. It does not invent lookup or custom-definition capabilities. Reload settings remains available.

## Implementation scope

`apps/web/app/item-intake.tsx` owns the task and draft. Collection navigation, observation inputs, custom controls and barcode camera handling are reused. `custom-collections.tsx` remains collection administration/export/history and routes item creation to the shared task. All writes use existing API contracts, transaction boundaries and constraints. No dependency, API, migration, native client or runtime plugin framework is added.

Verification and limitations are recorded in the harness guide and PR. The synthetic visual concept remains historical approval evidence under `docs/design/proposals/item-intake-2026-11-04/`; it is not a production screenshot or API test.
