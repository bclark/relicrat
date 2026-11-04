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
    fontSize: "1.8rem"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-.035em"
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
    backgroundColor: "{colors.paper}"
    padding: "24px"
  inventory-row-selected:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.ink}"
    rounded: "{rounded.input}"
    padding: "4px 8px"
  inventory-brick:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    padding: "12px"
---

# Design System: RelicRat inventory application

## Overview

**Creative North Star: "The new-arrivals workbench"**

This is a record of the current inventory implementation, extracted from apps/web/app/globals.css, its React components and the bounded theme styles in apps/api/relicrat/theme_values.py. The new-arrivals workbench uses warm ivory, white surfaces, charcoal ink and restrained burgundy actions to make physical copies easy to record and find. Plain labeled controls and text-led records keep collection information prominent, without paper texture or faux-vintage controls.

The owner approved these factory theme values on 2026-10-31, including sans body/headings, balanced spacing, soft corners and comfortable density. The forest and light-gold After hours preset is the dark companion. Approval covers application theme values; brand-wide master specifications, proposed logos and mascot extensions remain separate decisions. The owner separately approved the collection journey on 2026-11-04: collection navigation, browsing and a read-first inspector. It supersedes the 2026-11-02 intake-rail composition and is implemented for review; see docs/collection-journey.md and docs/harness.md. Owners can explicitly preview and apply their own supported theme. This record describes the implementation for review, not deployment or production readiness.

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
- **Soft sage wash:** soft supports alternating list rows, hover surfaces, category selection, secondary pressed states, static loading skeletons and photo frames. Pressed, loading and photo-bg describe these uses of the same soft value. The selected copy uses soft fill, ink text and an inset one-pixel accent outline; selected-border aliases accent. Accent-text remains the contrasting primary-action text.

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

The factory theme uses the operating-system sans stack for both headings and body in this Operate surface. Appearance offers bounded installed sans, serif and mono stacks for each role independently. No external font or decorative display face ships. Frontmatter records the current collection headline and intake heading; heading weights are browser-default bold. The current collection headline is 1.8rem across widths. The brand uses 1.75rem, weight 750 and -.025em tracking. Labels use .9rem and weight 650. Dense list titles use .875rem, weight 500 and 22px row line-height; edition and location use .875rem. Group headings use .875rem and weight 600, while column labels use .75rem. Bricks titles use 1rem and weight 650. Buttons use 600. Status and pagination are .8rem and .85rem respectively; record metadata reaches .75rem. Notes use .95rem with preserved whitespace and a 65ch maximum. Pagination, category counts and copy metadata use tabular numerals.

## Layout

The collection main has an 1800px maximum width; the header retains its 1700px bound and 36px gutters. Main keeps 32px desktop gutters. A 200px collection navigation rail sits beside a flexible paper browser; opening a copy adds a 380px paper inspector, with 28px gaps. The browser has 24px padding and the inspector 20px. Desktop inspection is sticky at 20px with bounded vertical scrolling. Intake is an explicit Add a find disclosure above the workspace, aligned after the rail, with a 720px maximum width and 24px padding. Inline settings and Collection tools and imports remain available. The trial notice follows the workspace. This composition is approved for the collection surface, not a mandatory future-screen template.

Below 1280px (max-width:1279px), the rail is 180px and the content gap 22px. Opening a copy replaces browsing with the inspector; Back restores the selected row and browse position, or focuses the browse heading when that row no longer exists. Below 760px, the native collection chooser replaces rail links; opening details hides the chooser and browser. Main gutters and paper padding are 16px, with a 20px workspace top margin. Header utilities retain their separate 650px Menu breakpoint; the tagline hides at 850px. Appearance keeps its own 800px stacking breakpoint.

List rows retain aligned Item, Edition and Location columns with a 64px minimum target at every width. A 44px contained thumbnail or explicit no-art fallback sits beside title and supporting artist/format/publisher information. Actual location names use the bounded display projection, with Location assigned/Unassigned fallbacks. Covers uses responsive columns with a 150px minimum and 16px gap; phone uses two columns. Cover images are contained at 140px desktop and 110px phone heights. Missing imagery never installs invented inventory. Individual-copy type headings and counts describe only the current bounded page; configured server groups retain whole-filtered-group counts and paging. Search, exact-location filtering and grouping remain server-backed. Switching List/Covers, inspecting and Back preserve the current browse state. Custom navigation choices are paged independently and retain a visible off-page selection.

## Elevation & Depth

The surface is flat. Paper fills and one-pixel rules group content. Selected inventory rows use soft fill, ink text and a one-pixel inset accent outline; there are no row or ambient card shadows. The mobile utility dropdown sits above content as a paper surface with a one-pixel rule and panel corners. Dense inventory rows change selection immediately without a color transition. Reduced-motion preferences remove the other 150ms button color transitions and the 180ms record opacity entrance (from .7 to 1).

## Shapes

The approved soft setting gives panels a gentle 12px radius; fields, buttons, error boxes and photos use 6px. These values follow the owner-selected corner setting when applied. List rows are full-width and use the theme control radius; unboxed Bricks have square corners. Buttons and editable controls have a minimum 44px height, including the current collection rows, whose minimum is 64px. Textareas resize vertically with a 100px minimum. Photos preserve the whole image inside square frames using object-fit:contain.

## Components

### Forms and saves

Persistent labels precede fields. Add a find explicitly opens intake, starting with Title or barcode, collection type and the existing Scan barcode control. Closing intake keeps its draft mounted and stops scanning. Review item or Enter expands the mounted form; 12-digit UPC-A and 13-digit EAN-13 typing also opens it after a 500ms pause. Eight-digit codes require scanning or an expanded code to avoid guessing UPC-E versus EAN-8. Hiding and reopening the same draft does not repeat provider lookup. Barcode observations retain their structured format and history separately from notes. Configured provider suggestions and optional covers require review; Save copy alone creates ownership. No scanner or provider implementation is replaced. Camera frames stay on the device, and tracks stop when phone details hide the rail as well as on existing close, read, timeout and visibility boundaries. Type changes with a draft require confirmation. Controls retain current theme density/corners and 44px minimum targets; collection rows use a 64px minimum. Native file controls, selects and details remain recognizable. Uploads accept JPEG, PNG or WebP up to 15 MiB, subject to API validation.

Saving locks conflicting actions and changes the primary label to Saving…. Drafts remain page-local and can be lost on reload. A new location becomes available after creation without moving the copy. Choosing it saves the move immediately; a nearby status announces progress and the confirmed destination. No POST is retried automatically. Unconfirmed writes and revision conflicts display explicit review/reload guidance and block subsequent saves until review.

### Register and selected record

Each list row or cover tile is a real button with aria-pressed. Selection uses soft fill, ink text and an accent outline. Albums, Comics, Movies, Other and custom collections retain configured identities and fields. List/Covers changes presentation without changing ownership, filters, group or page. Authenticated, lazy-loaded thumbnails and named locations come from the bounded API projection without per-row metadata requests. Catalog artwork is explicitly distinguished from photographs of the physical copy.

Opening a copy focuses its heading and starts with a read-only summary. Edit details reveals the existing configured editor; only a confirmed Save details returns to summary. Cancel requires explicit discard confirmation for a dirty editor. Back preserves the mounted selected record/editor; replacing it with another copy or newly saved copy checks for unsaved changes. Dirty edits lock location/catalog changes that could reset the form. Uncertain/conflicting writes require reload and review, and unsaved selected-copy changes receive a browser unload warning. Preservation is session-local; it does not imply offline synchronization. Existing notes remain read-only where the API has no editor. Photo, location, checklist and catalog operations remain independent, with secondary operations and histories behind native disclosures.

### Focus, feedback and loading

Interactive controls use a three-pixel focus outline offset by three pixels; the focused record heading uses a five-pixel offset. A focus-revealed skip link opens intake and targets its focusable heading. Add a find explicitly opens/closes intake; Back to collection restores browse focus and position. Confirmation text uses the theme ink and role=status; errors use role=alert with a bordered red-tinted box. Inventory loading combines announced text with aria-hidden static skeletons. Empty and failed search states give explicit next actions. Empty collection/search messages sit openly on the workspace with generous vertical space and no filled card. Read failures offer reload; no fabricated records appear as placeholders.

**The Separate Save Rule.** Make confirmed copy, photo and location saves distinguishable; choosing a location immediately saves a revision-checked move and confirms its destination beside the selector. Creating a location remains a separate save.

### Appearance and login

Header controls select one inline settings editor before the workspace. The Appearance and collection setup components remain mounted when their editors close; entry drafts remain intact. Collection setup initializes its choices when opened, and Skip for now appears inside setup. Closing settings restores focus to the desktop trigger or mobile Menu button. Appearance expands inline. Desktop keeps controls beside a labeled isolated preview; at 800px and below the sample follows the controls. Manual or imported edits invalidate the preview; explicit Apply persists appearance with its own revision. The theme changes supported presentation values, leaving inventory, layout and navigation intact. Error styling stays fixed. The login uses the factory light palette and existing centered form; it does not load the saved owner theme.

### Navigation

The brand links home. The collection navigation rail selects built-in or named custom collections, with bounded custom-choice paging and an off-page selection retained. Below 760px it becomes a native labeled chooser; Back returns from the focused record to browsing. Desktop exposes Appearance, collection settings and Sign out in the header. At 650px and below, Menu reveals those same controls in a right-aligned dropdown with an expanded state. Escape dismisses it and returns focus to Menu; outside pointer interaction and focus leaving the utility group also dismiss it. Choosing settings closes the dropdown and focuses the editor heading. Search has a visible label, explicit submit and conditional clear action. Pagination is a named navigation region with disabled end controls. Mobile keeps the same semantic order.

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
