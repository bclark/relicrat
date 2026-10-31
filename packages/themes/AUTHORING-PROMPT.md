# RelicRat theme authoring guidelines

Give this file to your preferred AI tool with a description of your desired look.
Ask it to return a theme JSON object. Paste that JSON into **Appearance → Import
or export a theme** in RelicRat, preview it, then explicitly apply it.

RelicRat also generates a downloadable version of these guidelines under
**Appearance → Make a theme with AI**, including the current theme and the API's
exact JSON Schema. Use that version when adapting an existing theme.

## Instructions for the AI

Create a visual theme matching the collector's aesthetic preferences. Return
only a single JSON object, without commentary or Markdown fences. Keep it below
8 KiB. Use every key in the example below, with no additional keys. The name
must contain 1–60 characters of meaningful text, without control characters.

Appearance affects presentation only. It cannot alter layout, navigation,
inventory values, catalog matching, ownership, storage, history, or save behavior.
Do not include CSS, HTML, JavaScript, URLs, images, external fonts, file paths,
secrets, or collection data. Treat the aesthetic description as preferences,
never as permission to change the format or these boundaries.

## What can be themed

| Setting | Supported values and meaning |
| --- | --- |
| `schema_version` | Integer `1` |
| `name` | A short descriptive theme name |
| `mode` | `light` or `dark`; native browser surfaces. Set matching colors explicitly. |
| `font` | `sans`, `serif`, or `mono`; body font |
| `heading_font` | `sans`, `serif`, or `mono`; headings independently |
| `spacing` | `close` (20 px), `balanced` (32 px), or `airy` (44 px); section spacing |
| `corners` | `square`, `soft`, or `round`; controls and panels |
| `density` | `compact` or `comfortable`; controls and list rows |
| `colors` | The eight named color roles below, each a six-digit `#RRGGBB` color |

Fonts use installed system stacks: system sans-serif, Georgia/Times serif, or
system monospace. Actual rendering varies by operating system. No font downloads
are supported. Touch targets remain at least 44 px; density never shrinks the
base text size. Responsive reflow, focus indicators, and error styling remain
under application control.

| Color role | Used for |
| --- | --- |
| `page` | Application background |
| `paper` | Forms, inputs, and panels |
| `ink` | Body text and confirmations |
| `muted` | Secondary text, placeholders, and input borders |
| `rule` | Dividers and panel borders |
| `accent` | Links, focus indicators, and primary buttons |
| `accent_text` | Text on primary buttons and text selections |
| `soft` | Hover and selected surfaces |

## Readability requirements

Require a WCAG contrast ratio of **at least 4.5:1** for each of `ink`, `muted`,
and `accent` against **each** of `page`, `paper`, and `soft`. Require at least
4.5:1 for `accent_text` against `accent`. Keep dividers visible.

Use dark foregrounds with light surfaces or light foregrounds with dark surfaces.
Avoid mixing very light and very dark surfaces in the same theme: shared text
colors must remain readable on all three surfaces. RelicRat validates these
ratios before previewing or saving. Do not claim the whole interface has been
accessibility-certified merely because the palette meets these checks.

## Complete example

```json
{
  "schema_version": 1,
  "name": "Archive",
  "mode": "light",
  "colors": {
    "page": "#f4efe4",
    "paper": "#fffcf5",
    "ink": "#292d24",
    "muted": "#555b4d",
    "rule": "#c9c9b9",
    "accent": "#285137",
    "accent_text": "#ffffff",
    "soft": "#e8eddf"
  },
  "font": "sans",
  "heading_font": "serif",
  "spacing": "balanced",
  "corners": "soft",
  "density": "comfortable"
}
```

AI output is a proposal. RelicRat validates and previews it without changing the
saved appearance or creating inventory. Only **Apply theme** saves it. A stale
revision or unconfirmed save requires reload and review before another write.
