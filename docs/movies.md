# Movies and Blu-ray.com imports

Status: implemented for review, not deployed. A physical movie release or box set
is one owned item. A title, format or source product ID does not create a shared
catalog identity or prove a particular edition. A box set is not split into films
or into one owned copy per disc.

## Collection definition and entry

`apps/api/relicrat/collection_types/movie.json` defines the Movie label, title-first
entry order, optional format/studio/edition/notes fields and grouping by title.
Only the title is required in the browser. Native format choices include Blu-ray,
4K UHD, DVD, Blu-ray + DVD, VHS and LaserDisc; Other permits a custom format and
Not specified preserves unknown. Studio suggestions reuse protected, read-only
saved-value autocomplete. No field is selected or saved automatically.

Collection setup can enable Movies, select visible optional fields and make Movie
the default for new finds. Hiding fields never deletes saved observations; old
clients omitting Movie settings preserve them. Existing records, preferences and
entry defaults are not reclassified by an import. Movies remain selectable in the
intake dropdown and collection filter independently of the setup recommendation.

Movie observations live in bounded `movie_details` JSONB (`media_format` <=100,
`studio` <=250). The ordinary copy save keeps its UUID, catalog/release links,
photos, storage and ownership, with revision-checked before/after edit history.
Changing type retains all existing Album/Comic/Movie observations. Unknown fields
are absent rather than zero-filled. Title, studio, format, barcode and notes are
searchable. Title groups summarize physical copies without merging them.

Movie config declares UPC/EAN scanning and UPCitemdb title lookup. A successful
scan searches for a retail suggestion; the owner reviews the title before filling
the draft and explicitly saving. Studio, format and edition remain manual; brand
is not studio and no artwork is fetched. This adapter needs no signup or key, but
has free-plan limits and incomplete coverage. Provider selection/mappings remain
in movie.json; see the [Movie lookup contract](barcode-lookup.md#movie-title-lookup-with-upcitemdb).
Scanning and lookup do not prove an edition or establish catalog identity.

## Reviewed Blu-ray.com collection CSV

Choose **Import CSV → Blu-ray.com Movies**, select a UTF-8 comma-separated export,
preview its mapping and notes, then explicitly confirm **Import N copies**.
Preview creates no inventory, and its digest binds confirmation to the same file.
The whole import is transactional. An exact-file retry returns the existing batch;
a modified export is a new import and can duplicate previously imported objects.
Repeated product IDs and barcodes do not deduplicate physical ownership.

The parser recognizes the export headers, including Title, Studio, UPC, EAN,
Product ID, Blu-ray discs and DVD discs. It maps:

| Export data | Result |
| --- | --- |
| Title | Movie or box-set title |
| Studio | Optional personal studio observation |
| Positive Blu-ray/DVD disc counts | Blu-ray, DVD or Blu-ray + DVD format; quantity remains one |
| Casing | Optional edition/packaging label, not verified catalog edition |
| Comment | Notes, as literal text |
| Valid, consistent UPC/EAN | One barcode observation, retaining leading zeros |
| Every original column | Private source-row evidence, unchanged |

Blank or `-1` disc counts mean unknown. Zero means no discs of that format.
Counts must otherwise be bounded nonnegative whole numbers. Disc counts never
establish a 4K resolution. Release date and Date added remain original source
text; neither is inferred to be a film's theatrical year or an acquisition date.
Slipcover, memorabilia, digital-copy, watched, retailer, price and other values
remain source evidence; no financial, grading or viewing-state subsystem is
created or populated.

Barcode values are checked for UPC-A/EAN-13 shape and check digit after removing
spacing/hyphens. Matching UPC/zero-prefixed EAN select UPC; a lone valid EAN stays
EAN. Invalid values stay in the source and produce a preview note. If two valid
codes disagree, preserve both and leave the barcode unset. These notes do not
block otherwise valid title/metadata rows. Up to 50 notes/errors are displayed;
all original cells remain retained. Invalid titles, field lengths or count values
block confirmation for the entire file. Existing byte/row/expanded-source limits
apply. CSV cells are neither executed as formulas nor rendered as HTML.

After import, choose Movies in Your collection. Import history retains the source
rows and opens each physical copy. Blu-ray.com product IDs do not trigger remote
lookups, create releases, assign storage or merge objects. The supplied private
export was inspected locally for its schema and edge cases; fixtures, browser
imports and recovery checks use independently generated data. No owner export
is committed, sent to the test worker or imported into the live collection here.

## Migration, recovery and rollout

Migration `0013_movies` adds Movie observations/history/preferences and extends
allowed type/import-source checks. Older rows get empty observations, prior
history gets NULL new fields, and Movies start disabled in setup with suggested
optional fields. Existing identifiers, source rows and owner settings remain.
No deployed migration is edited. JSON shape/length and allowed-type/source/default
rules have PostgreSQL checks in addition to API validation.

Downgrade locks affected tables and refuses any Movie copy, Movie observations,
retained Movie history, customized Movie preferences or Blu-ray import batch. It
removes only unused defaults on disposable data. Once Movie data exists, reverting
to an older application/schema requires an explicit verified recovery plan.
Never downgrade the live inventory automatically.

Before rollout, take a fresh database/media backup and rehearse migration and
row/media preservation on its offline restored copy. Deploy schema/API/web as a
reviewed release before enabling Movie entry. The existing backup helper's full
row/media fingerprints must cover nonempty Movie metadata, edit history,
preferences and import provenance, plus actual media; an empty-column check is
insufficient. Do not start or promote a verification restore's app servers.
