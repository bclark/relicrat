---
name: RelicRat inventory application
description: Descriptive visual record of the first working inventory screen
colors:
  page: "#f1f4f8"
  paper: "#fff"
  ink: "#1b2a3d"
  muted: "#53647a"
  rule: "#cdd6e2"
  accent: "#214fbd"
  hover: "#173d99"
  soft: "#e9effc"
  error: "#8d2433"
  error-bg: "#fff1f2"
  success: "#1b6549"
  focus: "#1647b0"
  control-border: "#9baabd"
  pressed: "#d9e4fa"
  selected-border: "#b1c4ed"
  error-border: "#e8b8bf"
  loading: "#e1e7f0"
  photo-bg: "#e4e9f0"
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
  input: "5px"
  button: "6px"
  empty: "8px"
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
    textColor: "{colors.paper}"
    rounded: "{rounded.button}"
    padding: "11px 24px"
  button-primary-hover:
    backgroundColor: "{colors.hover}"
    textColor: "{colors.paper}"
  button-secondary:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.button}"
    padding: "9px 16px"
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.input}"
    padding: "10px 12px"
  intake-panel:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.panel}"
    padding: "28px 30px"
  inventory-row-selected:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.ink}"
    padding: "18px 16px"
---

# Design System: RelicRat inventory application

## Overview

**Creative North Star: "The new-arrivals workbench"**

This is a descriptive record of the current inventory implementation, extracted from apps/web/app/globals.css and its React components. The new-arrivals workbench uses white paper, cool blue-gray support, restrained navy ink and cobalt actions to make provisional physical copies easy to record and find. The surface operates as a working register, with plain labeled controls and text-led records.

The owner chose an add-first screen and a direct working-interface build for this task. This record does not infer a permanent brand, palette preference or global build-path preference. The separate frozen progress report through PR #14 retains its own [historical design record](docs/design/project-dashboard.md) and [preserved sidecar](.impeccable/project-dashboard-design.json); it is not current application guidance.

**Key Characteristics:**
- System UI sans for an Operate workflow.
- Flat paper and ruled rows with one explicit selection.
- Visible save, loading, conflict and recovery states.
- Responsive reading order and keyboard focus.

## Colors

The current light-only theme pairs cool neutrals with a single cobalt action family. Exact source values are in frontmatter; names describe observed roles.

### Primary
- **Cobalt action:** accent and hover identify primary saves and links; focus supplies the visible keyboard ring. The caret uses accent; text selection uses paper on accent.
- **Selection wash:** soft and selected-border mark the open collection row; pressed records the button's active wash.

### Secondary
- **Confirmed green:** success colors save notices.
- **Error red:** error, error-bg and error-border form the visible alert treatment.

### Neutral
- **Cool page and white paper:** page holds the workspace; paper holds intake, fields and buttons.
- **Navy and blue-gray ink:** ink carries authoritative copy; muted carries hints and metadata, including placeholders.
- **Rules and surfaces:** rule separates sections, control-border outlines editable fields, loading fills static skeletons, and photo-bg sits behind contained photos.

**The Explicit State Rule.** Pair state colors with readable text and programmatic status; color alone does not establish a saved record.

## Typography

The operating-system sans stack serves both headings and body in this Operate surface. No external font or decorative display face ships. Headline and title values are in frontmatter; heading weights are browser-default bold. The brand uses 1.5rem, weight 750 and -.025em tracking. Labels and row titles use weight 650; buttons use 600. Row descriptions are .875rem; status and pagination are .8rem and .85rem respectively; record metadata reaches .75rem. Notes use .95rem with preserved whitespace. Intro and notes cap at 65ch. Pagination and copy metadata use tabular numerals.

## Layout

A centered 1320px maximum shell uses 36px desktop gutters. The workspace begins 32px below the development notice, with minmax columns in a 1:1.1 ratio and a 48px gap. Intake occupies a bordered paper panel; its selected working record follows below a rule. Search and the collection register occupy the other column. These are the current first surface's composition, not a required template for every future page.

At 850px and below, columns become equal, the gap is 28px, gutters are 24px, panel padding is 24px 20px, section headings may wrap, and the development notice stacks. At 650px and below, content stacks in DOM order: intake, selected record, collection. Gutters become 20px, the workspace gap is 36px, and the header tagline hides. Photo grids change from three columns to two. Long titles, identifiers and errors wrap; row descriptions clamp to two lines. Collection pagination shows 20 copies per page with explicit Previous/Next controls.

## Elevation & Depth

The surface is flat. Paper fills and one-pixel rules group content. The selected inventory row alone uses an inset one-pixel selected-border shadow; there are no ambient card shadows or overlays. Reduced-motion preferences remove the 150ms button color transitions and the 180ms record opacity entrance (from .7 to 1).

## Shapes

Panels have a gentle 12px radius; fields use 5px, buttons/error boxes/photos 6px, and empty-state blocks 8px. Inventory rows are square and full-width. Buttons and editable controls have a minimum 44px height. Textareas resize vertically with a 100px minimum. Photos preserve the whole image inside square frames using object-fit:contain.

## Components

### Forms and saves

Persistent labels precede fields; helper text explains required information and photo constraints. The cobalt primary button saves the copy. Paper secondary buttons save photos and storage separately. Disabled controls use .55 opacity. The quiet variant reduces text to .875rem with 7px 12px padding; underlined text actions retain a 44px minimum height. Native file controls, selects and details/summary remain recognizable. Uploads accept JPEG, PNG or WebP up to 15 MiB, subject to API validation.

Saving locks conflicting actions and changes the primary label to Saving…. Drafts remain page-local and can be lost on reload. A new location becomes available after creation without moving the copy. Choosing it saves the move immediately; a nearby status announces progress and the confirmed destination. No POST is retried automatically. Unconfirmed writes and revision conflicts display explicit review/reload guidance and block subsequent saves until review.

### Register and selected record

Each ruled list row is a real button with aria-pressed. It carries a title, short description and identification/location text; the selected wash indicates the open copy. Opening a record focuses its heading. Native disclosures reveal location creation, movement history and copy details. Movement/location lists load additional bounded pages explicitly. Photos link to the stored image; their content is collection data, not decorative artwork.

### Focus, feedback and loading

Interactive controls use a three-pixel focus outline offset by three pixels; the focused record heading uses a five-pixel offset. A focus-revealed skip link leads to intake. Success text uses role=status; errors use role=alert with a bordered red-tinted box. Inventory loading combines announced text with aria-hidden static skeletons. Empty and failed search states give explicit next actions. Read failures offer reload; no fabricated records appear as placeholders.

**The Separate Save Rule.** Make confirmed copy, photo and location saves distinguishable; choosing a location immediately saves a revision-checked move and confirms its destination beside the selector. Creating a location remains a separate save.

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
- **Don't** treat this implementation record as a permanent user brand preference.
