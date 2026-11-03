# Custom collections in shared browsing

Implemented for review, 2026-11-03; not deployed. No migration or dependency change.

The main **Show collection** filter lists built-in collection types and custom
collections in separate native option groups. Custom choices page in batches of
50, retain a selected collection from another page, and retry failed pages
without skipping them. Empty custom collections are available through the
selector even though the inventory group overview only contains saved copies.

The grouped overview can show each custom collection alongside built-in types.
Selecting one opens its individual copies with ordinary search, storage filters,
pagination and copy inspection. Progress is for the whole collection and retains
its owner-reviewed checklist rules; search/storage restrict only the copies.
The Add a figure to this collection shortcut opens existing custom intake. It
preserves another unfinished custom draft instead of silently retargeting it.
Built-in intake and selected-copy edit drafts remain independent of browsing.
Saving from generic intake while viewing a custom collection clearly explains
that the new copy was saved outside that custom goal.

## Identity and read contracts

A custom goal remains identified by its UUID, not its label or built-in type.
Same-name custom collections and a built-in type with the same name are not
merged. Physical copies retain `collection_type=other` and their existing
`custom_collection_id`; browsing never changes membership, catalog/release
identity, ownership, history, storage or personal observations.

Inventory adds optional read-only `custom_collection_name`. A SQLAlchemy computed
property resolves the immutable collection label in the same database query;
there is no new column, per-copy HTTP request or persisted display-name cache.
Row grouping uses the collection UUID and labels custom copies separately from
Other finds. `exclude_custom=true` lets that built-in filter show generic finds;
its default remains false for existing API clients. It cannot be combined with
an explicit custom_collection_id. Search/storage/pagination continue through the
shared validated query. Names and identifiers never become executable SQL/HTML.

The main group overview requests `split_custom=true` on the existing fixed,
authenticated collection-groups route. Its default remains false, preserving the
old response grouping for older tabs/clients. Split rows add custom_collection_id
only for custom groups and use deterministic label/UUID ordering. Existing
Album/Comic/Movie group behavior remains unchanged. No new provider/network
access, ownership writes or schema change is involved.

API/web should roll out together after review. The schema remains0016 and the
unchanged backup helper captures all existing tables. Matching source/images and
a fresh copied recovery verification precede rollout. This increment unifies
browsing; it does not replace the existing custom authoring/configuration/intake
forms or turn checklist goals into catalog types.
