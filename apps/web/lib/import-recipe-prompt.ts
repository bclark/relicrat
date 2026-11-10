export const IMPORT_RECIPE_PROMPT = `Help me make a RelicRat video game CSV import recipe. Ask for the header row and a few anonymized rows, then ask me to clarify ambiguous fields and whether every row represents a game I own. Keep my actual inventory out of your output.

Return two separate files:
1. import-recipe.json. Return only a JSON object using this exact structure:
{"schema_version":1,"name":"Export name","collection":"game","columns":{"title":"Exact title column header"}}

Allowed optional keys in columns are platform, region, edition, notes, quantity, media, packaging, manual, and inserts. Each value is an exact CSV header, used once. Only map fields supported by the data. Title is required. Platform, region and edition describe the release. Notes and contents describe the physical copy. A blank quantity means one; other quantities must be whole numbers from 1 to 10000. The four contents fields accept present, missing, not_applicable, or a blank for unknown. If your export uses other values, omit those mappings and explain why. Keep the recipe under 2 KiB and use no code, URLs, extra keys, or transformation rules.

2. fixture.csv. Use the same headers with a few invented rows that demonstrate the mapping, including a blank optional value if applicable. Include only owned games in this fixture.

Explain any unmapped columns and the expected number of physical copies in the fixture. Ask me to verify ownership, the field mapping and the copy count in RelicRat before confirming. For official support, I can share the recipe and invented fixture with the maintainers.`;
