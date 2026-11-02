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
  intake:
    fontFamily: 'system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "-.015em"
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
  panel: "12px"
spacing:
  small: "12px"
  control: "16px"
  compact-panel: "20px"
  panel-block: "28px"
  section: "32px"
  workspace-gap: "28px"
  compact-workspace-gap: "26px"
  row-inline: "8px"
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
  quick-intake:
    backgroundColor: "transparent"
    padding: "0"
  inventory-row-selected:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.accent-text}"
    rounded: "{rounded.input}"
    padding: "4px 8px"
  inventory-brick:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    padding: "14px 8px 22px"
---

# Design System: RelicRat inventory application

## Overview

**Creative North Star: "The new-arrivals workbench"**

This is a record of the current inventory implementation, extracted from apps/web/app/globals.css, its React components and the bounded theme styles in apps/api/relicrat/theme_values.py. The new-arrivals workbench uses warm ivory, white surfaces, charcoal ink and restrained burgundy actions to make physical copies easy to record and find. Plain labeled controls and text-led records keep collection information prominent, without paper texture or faux-vintage controls.

The owner approved these factory theme values on 2026-10-31, including sans body/headings, balanced spacing, soft corners and comfortable density. The forest and light-gold After hours preset is the dark companion. Approval covers application theme values; brand-wide master specifications, proposed logos and mascot extensions remain separate decisions. The owner separately approved the three-column workspace refinement on 2026-11-02; it is integrated on current main for review; validation is recorded in docs/harness.md. Owners can explicitly preview and apply their own supported theme. This record describes the implementation for review, not deployment or production readiness.

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
- **Soft sage wash:** soft supports alternating list rows, hover surfaces, category selection, secondary pressed states, static loading skeletons and photo frames. Pressed, loading and photo-bg describe these uses of the same soft value. The selected copy uses accent fill and accent-text; the selected-border alias is retained as historical token metadata and is not a current row shadow.

### Secondary
- **Fixed error red:** error and error-bg retain the application's alert treatment; error-border aliases error. These values remain fixed across owner themes.
- **Confirmation ink:** success aliases ink. Save notices use ordinary readable text plus explicit status wording.

### Neutral
- **Warm ivory and white surfaces:** page holds the workspace; paper holds fields and secondary buttons.
- **Charcoal and quiet warm-gray ink:** ink carries authoritative copy; muted carries hints, metadata, placeholders and editable-field borders. Control-border aliases muted.
- **Subtle neutral rule:** rule separates sections and outlines secondary buttons and panels.

### Dark companion

After hours uses forest page/paper/soft surfaces with ivory primary text, pale secondary text and light-gold actions with forest button text. It uses the same sans fonts, balanced spacing, soft corners and comfortable density as the default. The runtime maps hover/focus to its accent and confirmation text to its ink, retaining the fixed error treatment. Login and initial loading/failure fallback retain the light factory appearance; the saved owner theme loads after authentication and may briefly follow that fallback. Mode controls native browser surfaces and does not automatically follow the device.

**The Explicit State Rule.** Pair state colors with readable text and programmatic status; color alone does not establish a saved record.

## Typography

The factory theme uses the operating-system sans stack for both headings and body in this Operate surface. Appearance offers bounded installed sans, serif and mono stacks for each role independently. No external font or decorative display face ships. Frontmatter records the current collection headline and intake heading; heading weights are browser-default bold. The collection headline becomes 1.5rem below 760px. The brand uses 1.75rem, weight 750 and -.025em tracking. Labels use .9rem and weight 650. Dense list titles use .875rem, weight 500 and 22px row line-height; edition and location use .875rem. Group headings use .875rem and weight 600, while column labels use .75rem. Bricks titles use 1rem and weight 650. Buttons use 600. Status and pagination are .8rem and .85rem respectively; record metadata reaches .75rem. Notes use .95rem with preserved whitespace and a 65ch maximum. Pagination, category counts and copy metadata use tabular numerals.

## Layout

The inventory header and main workspace have a 1700px maximum width. Main uses 32px desktop gutters; the header retains 36px gutters. Three columns place quick intake, early item type and page-local categories in a 232px left rail, the searchable List/Bricks register in a flexible middle column, and the full selected-copy inspector in a 340px right pane. The workspace has a theme-space top margin (32px balanced), a 28px gap, and one-pixel left rules with 28px inset padding on middle and right panes. Intake itself is unboxed. Inline settings precede the workspace; the synthetic-trial notice follows it. This is the current inventory composition, not a mandatory template for future screens.

Below 1180px (max-width:1179px), the workspace uses a 220px rail and flexible content with a 26px gap. Opening a copy switches the middle content from collection to inspector; Back to collection restores the list and focus to the selected row, falling back to the collection heading. Below 760px (max-width:759px), the workspace stacks with 18px main gutters and a 24px top margin; the intake/category rail also hides while details are open. Returning reveals the rail and collection. Quick intake remains visible when browsing; only the full Review item form starts collapsed and stays mounted when hidden. Categories become wrapping controls. Header utilities retain their separate 650px Menu breakpoint; the tagline hides at 850px. Appearance keeps its own 800px stacking breakpoint.

List rows use title, edition and assigned/unassigned-location columns in minmax(0,1.2fr), minmax(0,.95fr), minmax(0,.9fr), with 12px gaps. Fine-pointer desktop rows have a 30px minimum, 4px 8px padding and single-line ellipsis. Coarse-pointer rows have a 44px minimum. Below 760px, 44px rows show title/edition in the flexible first column and location in a 100px second column; column headers hide. Bricks uses two unboxed columns with 20px gaps (12px below 760px), a 130px minimum per item, top rules and 14px 8px 22px padding. Titles and edition wrap; longer notes remain in the full selected-copy editor. Individual-copy type groups and category counts describe the current 20-copy page. Existing server groups retain whole-collection counts and paging. Location labels say Location assigned or Unassigned; they do not invent a location name.

## Elevation & Depth

The surface is flat. Paper fills and one-pixel rules group content. Selected inventory rows use solid accent fill and contrasting text; there are no row or ambient card shadows. The mobile utility dropdown sits above content as a paper surface with a one-pixel rule and panel corners. Dense inventory rows change selection immediately without a color transition. Reduced-motion preferences remove the other 150ms button color transitions and the 180ms record opacity entrance (from .7 to 1).

## Shapes

The approved soft setting gives panels a gentle 12px radius; fields, buttons, error boxes and photos use 6px. These values follow the owner-selected corner setting when applied. List rows are full-width and use the theme control radius; unboxed Bricks have square corners. Buttons and editable controls have a minimum 44px height, except dense list rows with the pointer/width rules described above. Textareas resize vertically with a 100px minimum. Photos preserve the whole image inside square frames using object-fit:contain.

## Components

### Forms and saves

Persistent labels precede fields. Quick intake starts with Title or barcode, early collection type and the existing Scan barcode control. Review item or Enter expands the mounted form; 12-digit UPC-A and 13-digit EAN-13 typing also opens it after a 500ms pause. Eight-digit codes require scanning or an expanded code to avoid guessing UPC-E versus EAN-8. Hiding and reopening the same draft does not repeat provider lookup. Barcode observations retain their structured format and history separately from notes. Configured provider suggestions and optional covers require review; Save copy alone creates ownership. No scanner or provider implementation is replaced. Camera frames stay on the device, and tracks stop when phone details hide the rail as well as on existing close, read, timeout and visibility boundaries. Type changes with a draft require confirmation. Controls retain current theme density/corners and 44px minimum targets; dense desktop pointer rows are the documented exception. Native file controls, selects and details remain recognizable. Uploads accept JPEG, PNG or WebP up to 15 MiB, subject to API validation.

Saving locks conflicting actions and changes the primary label to Saving…. Drafts remain page-local and can be lost on reload. A new location becomes available after creation without moving the copy. Choosing it saves the move immediately; a nearby status announces progress and the confirmed destination. No POST is retried automatically. Unconfirmed writes and revision conflicts display explicit review/reload guidance and block subsequent saves until review.

### Register and selected record

Each list row or unboxed brick is a real button with aria-pressed. List presents compact title, edition and location state with alternating soft fills; selected copies use accent fill and accent-text. Bricks wraps the same title, edition and location facts. There are no repetitive Saved copy labels. Albums, Comics, Movies and Other group the visible page; collection-type configuration supplies labels where available. Category filters and List/Bricks choice remain page-local and do not create or change inventory. Opening a record focuses its heading and exposes the full working copy in the right pane or responsive detail view. Native disclosures reveal location creation, movement history and copy details. Movement/location lists load additional bounded pages explicitly. Photos link to the stored image; their content is collection data, not decorative artwork.

### Focus, feedback and loading

Interactive controls use a three-pixel focus outline offset by three pixels; the focused record heading uses a five-pixel offset. A focus-revealed skip link returns from detail view to intake and targets its focusable heading. There is no separate Add a find jump link. Confirmation text uses the theme ink and role=status; errors use role=alert with a bordered red-tinted box. Inventory loading combines announced text with aria-hidden static skeletons. Empty and failed search states give explicit next actions. Empty collection/search messages sit openly on the workspace with generous vertical space and no filled card. Read failures offer reload; no fabricated records appear as placeholders.

**The Separate Save Rule.** Make confirmed copy, photo and location saves distinguishable; choosing a location immediately saves a revision-checked move and confirms its destination beside the selector. Creating a location remains a separate save.

### Appearance and login

Header controls select one inline settings editor before the workspace. The Appearance and collection setup components remain mounted when their editors close; entry drafts remain intact. Collection setup initializes its choices when opened, and Skip for now appears inside setup. Closing settings restores focus to the desktop trigger or mobile Menu button. Appearance expands inline. Desktop keeps controls beside a labeled isolated preview; at 800px and below the sample follows the controls. Manual or imported edits invalidate the preview; explicit Apply persists appearance with its own revision. The theme changes supported presentation values, leaving inventory, layout and navigation intact. Error styling stays fixed. The login uses the factory light palette and existing centered form; it does not load the saved owner theme.

### Navigation

The brand links home; the inventory rail provides page-local category filters rather than application navigation. Desktop exposes Appearance, collection settings and Sign out in the header. At 650px and below, Menu reveals those same controls in a right-aligned dropdown with an expanded state. Escape dismisses it and returns focus to Menu; outside pointer interaction and focus leaving the utility group also dismiss it. Choosing settings closes the dropdown and focuses the editor heading. Search has a visible label, explicit submit and conditional clear action. Pagination is a named navigation region with disabled end controls. Mobile keeps the same semantic order.

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
