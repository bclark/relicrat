---
name: RelicRat inventory application
description: Current inventory workbench with the approved RelicRat factory appearance
colors:
  page: "#F7F3E9"
  paper: "#FFFFFF"
  ink: "#302B28"
  muted: "#595650"
  rule: "#C6C9C3"
  accent: "#823B3D"
  hover: "#823B3D"
  accent-text: "#FFFFFF"
  soft: "#E8EEE9"
  error: "#8d2433"
  error-bg: "#fff1f2"
  success: "#302B28"
  focus: "#823B3D"
  control-border: "#595650"
  pressed: "#E8EEE9"
  selected-border: "#823B3D"
  error-border: "#8d2433"
  loading: "#E8EEE9"
  photo-bg: "#E8EEE9"
typography:
  headline:
    fontFamily: 'system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'
    fontSize: "1.75rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-.025em"
  title:
    fontFamily: 'system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "-.015em"
  body:
    fontFamily: 'system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'
    fontSize: "16px"
    lineHeight: 1.5
  label:
    fontFamily: 'system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'
    fontSize: ".9rem"
    fontWeight: 650
    lineHeight: 1.5
rounded:
  input: "6px"
  button: "6px"
  empty: "12px"
  panel: "12px"
spacing:
  small: "12px"
  control: "16px"
  compact-panel: "20px"
  panel-block: "28px"
  section: "32px"
  mobile-column: "36px"
  desktop-column: "48px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.accent-text}"
    rounded: "{rounded.button}"
    padding: "10px 24px"
  button-primary-hover:
    backgroundColor: "{colors.hover}"
    textColor: "{colors.accent-text}"
  button-secondary:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.button}"
    padding: "10px 16px"
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.input}"
    padding: "10px 12px"
  intake-panel:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.panel}"
    padding: "28px"
  inventory-row-selected:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.ink}"
    padding: "18px 16px"
---

# Design System: RelicRat inventory application

## Overview

**Creative North Star: "The new-arrivals workbench"**

This is a record of the current inventory implementation, extracted from apps/web/app/globals.css, its React components and the bounded theme styles in apps/api/relicrat/theme_values.py. The new-arrivals workbench uses warm ivory, white surfaces, charcoal ink and restrained burgundy actions to make physical copies easy to record and find. Plain labeled controls and text-led records keep collection information prominent, without paper texture or faux-vintage controls.

The owner approved these factory theme values on 2026-10-31, including sans body/headings, balanced spacing, soft corners and comfortable density. The forest and light-gold After hours preset is the dark companion. Approval covers application theme values; brand-wide master specifications, proposed logos, mascot extensions and navigation layouts remain separate decisions. Owners can explicitly preview and apply their own supported theme. This record describes the implementation for review, not deployment or production readiness.

The separate frozen progress report through PR #14 retains its own [historical design record](docs/design/project-dashboard.md) and [preserved sidecar](.impeccable/project-dashboard-design.json); it is not current application guidance. The original add-first and direct-build choices do not establish a standing build-path preference.

**Key Characteristics:**
- System UI sans for an Operate workflow.
- Approved ivory, charcoal and burgundy factory palette with a forest/gold dark companion.
- Flat paper and ruled rows with one explicit selection.
- Visible save, loading, conflict and recovery states.
- Responsive reading order and keyboard focus.

## Colors

The factory light theme pairs warm neutral surfaces with one burgundy action accent. Frontmatter records its default primitives and role aliases. The portable [default theme](packages/themes/relicrat-default.json) and API preset source own the supported light/dark palettes; owner-selected themes can replace the eight bounded color roles.

### Primary
- **Burgundy action:** accent identifies primary saves, links and the caret; hover and focus alias the same accent. The primary hover adds an underline in the authenticated application. Accent-text supplies primary-button text and selection text.
- **Soft sage wash:** soft supports selected/hover surfaces, secondary pressed states, static loading skeletons and photo frames. Pressed, loading and photo-bg describe these uses of the same soft value; selected-border aliases accent for the selected-row inset rule.

### Secondary
- **Fixed error red:** error and error-bg retain the application's alert treatment; error-border aliases error. These values remain fixed across owner themes.
- **Confirmation ink:** success aliases ink. Save notices use ordinary readable text plus explicit status wording.

### Neutral
- **Warm ivory and white surfaces:** page holds the workspace; paper holds intake, fields and secondary buttons.
- **Charcoal and quiet warm-gray ink:** ink carries authoritative copy; muted carries hints, metadata, placeholders and editable-field borders. Control-border aliases muted.
- **Subtle neutral rule:** rule separates sections and outlines secondary buttons and panels.

### Dark companion

After hours uses forest page/paper/soft surfaces with ivory primary text, pale secondary text and light-gold actions with forest button text. It uses the same sans fonts, balanced spacing, soft corners and comfortable density as the default. The runtime maps hover/focus to its accent and confirmation text to its ink, retaining the fixed error treatment. Login and initial loading/failure fallback retain the light factory appearance; the saved owner theme loads after authentication and may briefly follow that fallback. Mode controls native browser surfaces and does not automatically follow the device.

**The Explicit State Rule.** Pair state colors with readable text and programmatic status; color alone does not establish a saved record.

## Typography

The factory theme uses the operating-system sans stack for both headings and body in this Operate surface. Appearance offers bounded installed sans, serif and mono stacks for each role independently. No external font or decorative display face ships. Headline and title values are in frontmatter; heading weights are browser-default bold. The brand uses 1.5rem, weight 750 and -.025em tracking. Labels and row titles use weight 650; buttons use 600. Row descriptions are .875rem; status and pagination are .8rem and .85rem respectively; record metadata reaches .75rem. Notes use .95rem with preserved whitespace. Intro and notes cap at 65ch. Pagination and copy metadata use tabular numerals.

## Layout

A centered 1320px maximum shell uses 36px desktop gutters. The workspace begins with a 32px top margin after the appearance and collection setup controls, with minmax columns in a 1:1.1 ratio and a 48px gap at balanced spacing. Intake occupies a bordered paper panel with 28px padding; its selected working record follows below a rule. Search and the collection register occupy the other column. These are the current first surface's composition, not a required template for every future page.

At 850px and below, columns become equal, the gap is 28px, gutters are 24px, panel padding is 24px 20px, section headings may wrap, and the development notice stacks. At 650px and below, content stacks in DOM order: intake, selected record, collection. Gutters become 20px, the workspace gap is 36px, and the header tagline hides. Photo grids change from three columns to two. Long titles, identifiers and errors wrap; row descriptions clamp to two lines. Collection pagination shows 20 copies per page with explicit Previous/Next controls.

## Elevation & Depth

The surface is flat. Paper fills and one-pixel rules group content. The selected inventory row alone uses an inset one-pixel accent shadow; there are no ambient card shadows or overlays. Reduced-motion preferences remove the 150ms button color transitions and the 180ms record opacity entrance (from .7 to 1).

## Shapes

The approved soft setting gives panels and empty-state blocks a gentle 12px radius; fields, buttons, error boxes and photos use 6px. These values follow the owner-selected corner setting when applied. Inventory rows are square and full-width. Buttons and editable controls have a minimum 44px height. Textareas resize vertically with a 100px minimum. Photos preserve the whole image inside square frames using object-fit:contain.

## Components

### Forms and saves

Persistent labels precede fields; helper text explains required information and photo constraints. The burgundy primary button saves the copy. White secondary buttons distinguish supporting actions. Authenticated comfortable-density controls use 10px vertical padding, with 24px horizontal padding on primary actions and 16px on secondary actions; the 44px minimum remains in force. Disabled controls use .55 opacity. The quiet variant reduces text to .875rem with 7px 12px padding; underlined text actions retain a 44px minimum height. Native file controls, selects and details/summary remain recognizable. Uploads accept JPEG, PNG or WebP up to 15 MiB, subject to API validation.

Saving locks conflicting actions and changes the primary label to Saving…. Drafts remain page-local and can be lost on reload. A new location becomes available after creation without moving the copy. Choosing it saves the move immediately; a nearby status announces progress and the confirmed destination. No POST is retried automatically. Unconfirmed writes and revision conflicts display explicit review/reload guidance and block subsequent saves until review.

### Register and selected record

Each ruled list row is a real button with aria-pressed. It carries a title, short description and identification/location text; the selected wash indicates the open copy. Opening a record focuses its heading. Native disclosures reveal location creation, movement history and copy details. Movement/location lists load additional bounded pages explicitly. Photos link to the stored image; their content is collection data, not decorative artwork.

### Focus, feedback and loading

Interactive controls use a three-pixel focus outline offset by three pixels; the focused record heading uses a five-pixel offset. A focus-revealed skip link leads to intake. Confirmation text uses the theme ink and role=status; errors use role=alert with a bordered red-tinted box. Inventory loading combines announced text with aria-hidden static skeletons. Empty and failed search states give explicit next actions. Read failures offer reload; no fabricated records appear as placeholders.

**The Separate Save Rule.** Make confirmed copy, photo and location saves distinguishable; choosing a location immediately saves a revision-checked move and confirms its destination beside the selector. Creating a location remains a separate save.

### Appearance and login

Appearance expands inline. Desktop keeps controls beside a labeled isolated preview; at 800px and below the sample follows the controls. Manual or imported edits invalidate the preview; explicit Apply persists appearance with its own revision. The theme changes supported presentation values, leaving inventory, layout and navigation intact. Error styling stays fixed. The login uses the factory light palette and existing centered form; it does not load the saved owner theme.

### Navigation

The brand links home; the screen has no tab or sidebar navigation. Search has a visible label, explicit submit and conditional clear action. Pagination is a named navigation region with disabled end controls. Mobile keeps the same semantic order.

## Do's and Don'ts

### Do:
- **Do** preserve visible labels, focus outlines and textual status alongside color.
- **Do** use contained photos of the physical copy as user data.
- **Do** keep copy/photo/catalog/location creation separate, save location choices immediately, and require explicit review after uncertain writes.

### Don't:
- **Don't** turn the historical progress report into app design guidance.
- **Don't** imply saved data, identity or production readiness through visual state alone.
- **Don't** treat factory-theme approval as approval for proposed logos, mascot extensions, layouts or brand-wide master specifications.
- **Don't** apply paper texture or faux-vintage controls across the product interface.
