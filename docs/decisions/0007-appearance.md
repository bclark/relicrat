# 0007 — Portable visual themes with AI authoring guidelines

Status: Implemented for review in the synthetic trial; rollout requires migration
0008 and a matching API/web release. Not deployed by this change.

The collector chose colors, body/heading fonts, spacing, corners and density,
with preview and manual controls. AI assistance uses a prompt or Markdown file
describing supported values. There is no embedded model, provider configuration,
API key, or automatic external request.

Use a versioned, closed JSON object. Color roles are six-digit hex values; fonts,
spacing, corners and density are bounded choices. Reject arbitrary CSS, markup,
URLs, external fonts and unknown properties. The API validates both imported and
manually edited themes with the same parser. Require text/link contrast of 4.5:1
against supported surfaces and button text against accent. This palette check
does not certify whole-interface accessibility. Error styling remains fixed.
Compact controls retain 44 px minimum touch targets and the base font size.

Preview is an authenticated, read-only POST that returns validated values and
allowlisted style properties for an isolated sample. Editing invalidates that
preview. Applying requires an explicit action and the appearance revision.
Persist one active owner theme in a separate singleton PostgreSQL row, with a
row lock and independent revision so collection setup and inventory remain
unchanged. No timestamps are stored: the revision is the conflict token, and
there is no theme history or time-based behavior. A no-op does not increment it.
Uncertain writes are never retried automatically; reload and review are required.

The app loads the theme after authentication; login retains its default styling.
Loading/failure uses the default appearance and exposes reload. Browser loading
can briefly show the default before saved appearance arrives. Local exports are
portable JSON drafts, not an installation format for code. The Markdown download
contains the owner's description, theme, and JSON Schema; users choose what to
share with their AI tool. RelicRat never includes inventory or credentials.

Migration 0008 adds only `appearance_settings`, with a singleton constraint,
nonnegative revision, bounded document, required keys and supported-value checks.
Contrast is enforced by the API on reads/previews/saves; direct SQL is trusted
operator work, and an unreadable stored theme causes a 503. Existing full database
backups include the row. Downgrade locks the table and refuses a customized theme;
export it and deliberately restore the default before a reviewed rollback.
Default-theme revision history is discarded by downgrade. Never roll back the
live trial without verified recovery and an explicit release plan.

Multiple saved themes, automatic device mode, custom fonts, images, layout and
navigation customization, theme history, and an integrated AI provider are outside
this increment. The reusable authoring contract is
[the Markdown guidelines](../../packages/themes/AUTHORING-PROMPT.md).
