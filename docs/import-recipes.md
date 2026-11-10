# Video game CSV import recipes

Open **Import CSV → Export format → CLZ Games** for the bundled recipe. It
expects UTF-8 CSV with `Title` and `Platform` headers and imports one physical
copy per row. Check that your export contains only games you own before
confirming. Platform describes the release. Original cells such as Release
Date, Publisher, Developer, Genre, Added Date and Series remain visible in
import history.

To use another video game export, choose **Custom video game recipe**. Open
**Create an import recipe with an agent** and download the prompt. Give your
agent the prompt, the CSV header and a few anonymized rows. Load the returned
JSON with the full CSV, review the sample and copy count, then explicitly
confirm. Downloading the CLZ Games recipe gives you a starting example.

A recipe has a name, schema version `1`, collection `game`, and a `columns`
object that maps supported fields to exact headers. Title is required. Optional
release fields are `platform`, `region` and `edition`. Physical copy fields are
`notes`, `media`, `packaging`, `manual` and `inserts`. The four contents fields
accept `present`, `missing` and `not_applicable`; blanks stay unknown. Map
`quantity` to expand a row into multiple distinct copies. Blank quantity
defaults to one. Quantities must be whole numbers from 1 to 10,000.
Unmapped columns are retained as original source information.

Preview creates no records. Confirmation binds the recipe and CSV to the
reviewed preview. Rows with release fields create a new game and release for
that row, shared by its copies. Title-only rows remain provisional. The same
file reopens the existing batch across both recipe options. These recipes use
exact-file retry protection; they have no stable source IDs for matching copies
across changed exports.

To propose a bundled recipe, share the JSON and a synthetic CSV with the same
headers, plus the expected copy count and field mappings. See the bundled
[CLZ Games recipe](../apps/api/relicrat/clz-games.recipe.json) and its
[synthetic fixture](../apps/api/tests/fixtures/clz-games.synthetic.csv).

Migration `0021_game_import_recipes` allows the new batch source. A downgrade
requires a backup from before the first recipe batch because older releases
cannot read that batch source.
