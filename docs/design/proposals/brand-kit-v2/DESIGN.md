---
name: RelicRat brand and UI proposal
description: Proposed extension of approved modern collecting direction
colors:
  page: "#F7F3E9"
  paper: "#FFFFFF"
  ink: "#302B28"
  muted: "#595650"
  forest: "#29483E"
  burgundy: "#823B3D"
  rule: "#C6C9C3"
  soft: "#E8EEE9"
typography:
  body:
    fontFamily: system-ui, -apple-system, sans-serif
    fontSize: 16px
    lineHeight: 1.5
  headline:
    fontFamily: system-ui, -apple-system, sans-serif
    fontSize: 36px
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: -.025em
rounded:
  control: 6px
  field: 5px
  cover: 3px
  form: 10px
spacing:
  gutter: 44px
  mobile: 20px
components:
  button-primary:
    backgroundColor: "{colors.burgundy}"
    textColor: "{colors.paper}"
    rounded: "{rounded.control}"
    padding: 10px 16px
---

## Overview

Review proposal, not a canonical brand update. Inherits the canonical v1 character and modern collectibles direction. Collection imagery and metadata lead. All three original reference PNGs are preserved unchanged in references/. Standalone mascot extensions remain proposed and require comparison against the primary reference. The recovered wordmark exploration board does not replace them. Existing application is untouched.

## Colors

Forest navigation, ivory canvas, white controls, charcoal ink, burgundy intake actions. Gold stays decorative. Light/dark theme imports target the existing Appearance schema and use a single accent; they do not apply the prototype layout.

## Typography

System sans for operating text. The revision-2 wordmark uses original curved slab SVG paths, a shallow rising rhythm, and distinctive curved R bowls and legs, independently of the text font. No new font package or licensing claim.

## Layout

224px desktop navigation, 88px header, 44px content gutters. Four-column collection grid at 1200px; five at 1400px; three below 1050px; two below 700px. Mobile navigation moves to the top. Detail pages reflow from two columns to one. Add/edit forms use a separate screen and native controls.

## Elevation & Depth

Flat surfaces and one-pixel rules. No ornamental card shadows. Collection covers are explicitly fictional typographic studies; they are not collectible photos.

## Shapes

Six-pixel buttons and navigation corners, five-pixel fields, three-pixel cover corners, and ten-pixel form corners. Buttons have 44px minimum height; fields have 46px minimum height. Mobile navigation links have 44px minimum height. Rat-head and slab-letter wordmark proposals are purpose-drawn vectors, not traced generated text.

## Components

Real button cards, labeled search and filters, aria-pressed grid/list state, keyboard focus, skip link, form validation and live notices. Demo saves browser-local data explicitly, catches storage errors, and retains copy identity/history on edits. This self-hosted inventory proposal treats each demo record as a physical copy with provisional identification. Catalog items and releases remain separate concepts; neither is linked or modeled by this local review. No production-save or provenance verification claims.

## Do's and Don'ts

Preserve the canonical mascot anatomy, physical-copy identity and source uncertainty. Keep all proposals marked until approval. Do not treat a theme import as navigation/layout implementation. Do not use this demo for real collection data. Create character extensions using the recovered primary reference and retain proposed status until review.
