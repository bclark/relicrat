---
name: RelicRat local project dashboard
description: Artifact-specific visual record for docs/project-dashboard.html
colors:
  page: "#f3f5f7"
  paper: "#fff"
  ink: "#172b3a"
  muted: "#506373"
  rule: "#d7dfe5"
  soft: "#eaf0f4"
  green: "#176148"
  green-bg: "#e6f3ec"
  amber: "#7b4c0c"
  amber-bg: "#fff0d8"
  focus: "#165baf"
  accent: "#265b71"
  selected: "#193c4e"
  on-selected: "#fff"
typography:
  headline:
    fontFamily: '-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'
    fontSize: "2.2rem"
    fontWeight: 650
    lineHeight: 1.18
    letterSpacing: "-.03em"
  title:
    fontFamily: '-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'
    fontSize: "1.35rem"
    fontWeight: 650
    lineHeight: 1.3
    letterSpacing: "-.015em"
  body:
    fontFamily: '-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'
    fontSize: "16px"
    lineHeight: 1.55
  label:
    fontFamily: '-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'
    fontSize: ".75rem"
    fontWeight: 600
rounded:
  badge: "4px"
  filter: "5px"
  button: "6px"
  callout: "8px"
  panel-mobile: "10px"
  panel: "12px"
spacing:
  compact: "6px"
  small: "12px"
  medium: "20px"
  panel: "28px"
  section: "32px"
  column: "36px"
components:
  print-button:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.button}"
    padding: "9px 15px"
  filter-selected:
    backgroundColor: "{colors.selected}"
    textColor: "{colors.on-selected}"
    rounded: "{rounded.filter}"
    padding: "7px 13px"
  state-done:
    backgroundColor: "{colors.green-bg}"
    textColor: "{colors.green}"
    typography: "{typography.label}"
    rounded: "{rounded.badge}"
    padding: "4px 9px"
  report-panel:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.panel}"
    padding: "28px"
---

# Design System: RelicRat local project dashboard

## Overview

**Creative North Star: "The conservation register"**

This record describes only [docs/project-dashboard.html](docs/project-dashboard.html), the finished local, manually updated development report. Cool paper, navy ink, ruled rows and explicit state labels give factual progress and evidence a readable hierarchy. This descriptive name comes from the existing surface contract; it is not a newly inferred user preference.

These tokens and rules apply only to this report. They establish no inventory-application identity, permanent hosting decision, preferred build path, or general RelicRat brand. Future product UI design remains open. The artifact is a dated main-448a16e snapshot through merged PR #14; its recorded 43 API tests and stopped worker state are evidence content, not live telemetry.

**Key Characteristics:**
- A compact, text-led register with no decorative imagery.
- Meaningful status text reinforced by restrained green and amber.
- Flat paper panels, ruled rows and responsive density.
- Explicit provenance and manually maintained snapshot context.

## Colors

The report uses cool neutrals with semantic status accents; the frontmatter records the actual light-theme primitives.

### Primary
- **Register ink and selection:** `ink`, `selected`, and `on-selected` establish text and active-control hierarchy.
- **Evidence link blue:** `accent` identifies source links; `focus` makes keyboard focus visible.

### Secondary
- **Verified green:** `green` on `green-bg` marks completed API behavior and recorded checks.
- **Qualified amber:** `amber` on `amber-bg` marks recommended work and partial/rehearsed status.

### Neutral
- **Cool page and white paper:** `page` and `paper` distinguish the report canvas from its principal panel.
- **Muted ink, rules and soft wash:** `muted`, `rule`, and `soft` support secondary facts, row boundaries and interaction states.

The source supplies dark equivalents under the system color-scheme media query; exact overrides are recorded in the sidecar. Print switches to white paper and restrained dark text.

**The Explicit State Rule.** Pair every status color with a readable status label; color alone cannot communicate capability or readiness.

## Typography

**Body and report-heading font:** the operating-system sans-serif stack in frontmatter. This report has no separate expressive display face or external font request.

The headline introduces the report; section titles organize evidence and work queues. Subheadings use a smaller semibold role (1.05rem, line-height 1.4). Dense descriptions range from .85rem to .95rem, with smaller metadata between .75rem and .82rem. Numbered stages and queue positions use tabular numerals. Main introductory copy is limited to 65ch; detailed stage text to 62ch.

The headline reduces to 1.85rem on narrow screens. This utilitarian report typography does not prescribe a display font for future product screens.

## Layout

The centered container has a maximum width of 1220px and desktop side padding of 36px. The masthead is at least 80px tall. Main content begins with 40px of top space. Navigation uses a horizontal rule and active underline. The overview presents five equal workflow columns above a two-column stage explanation; supporting summaries also use two columns. Completed work uses disclosure rows, remaining work uses a numbered queue, and evidence uses a table.

At 800px and below, workflow controls become stacked rows, side padding becomes 24px, the snapshot moves below the heading, and the queue badge moves under its content. At 560px and below, side padding becomes 17px, the masthead reduces to 68px, the stage detail and supporting summaries stack, disclosure metadata gets its own row, and evidence table cells become readable blocks. Panel padding reduces to 20px 17px. The navigation can scroll horizontally.

Snapshot metadata remains separate block lines on desktop. Print reveals every section and filtered entry, expands completed-work disclosures, hides screen controls and restores previous disclosure states afterward.

## Elevation & Depth

There are no shadows. Paper, soft tonal washes, thin rules and selected-control borders provide grouping and state. The report does not simulate lifted cards.

## Shapes

Small rounded badges and controls sit within gently rounded principal panels. Register rows remain straight and separated by one-pixel rules. The callout uses an intermediate radius. These shapes describe the report's existing components only.

## Components

### Report controls

The print button has a paper fill, thin rule border and soft-wash hover. Filters use the same quiet default, with selection changing to the selected/on-selected pair. Buttons and links have a visible three-pixel focus outline offset by four pixels. State transitions last .15s with ease-out only when reduced motion is not requested.

### Navigation

Section anchors use muted text and a three-pixel active underline. `aria-current` identifies the visible section. Hash navigation selects Overview, Completed work, Remaining work or Evidence & checks.

### Status badges

Badges are compact inline labels with explicit wording. Completed states use verified green, next/partial states use qualified amber, and planned states use neutral soft fill. Badges are informational; filter buttons are interactive controls.

### Workflow selector

Each stage is a real button with `aria-pressed`, a two-digit position, title and state label. The selected stage receives a soft wash and selected border; the border moves from top to left in the stacked layout. Selection updates the adjacent detail region with polite announcements. Storage is selected initially.

### Completed register and evidence

Native details/summary rows reveal explanatory text and merged-PR links. Category filters update pressed state and an announced result count. The remaining queue uses textual priorities and acceptance criteria. The evidence table uses column headers, source commands and observed results; its mobile form retains the same facts. There are no text inputs or editable project metrics.

## Do's and Don'ts

### Do:
- **Do** apply this record only when editing docs/project-dashboard.html.
- **Do** preserve explicit state labels, evidence links and dated snapshot context.
- **Do** retain keyboard focus, semantic controls, responsive stacking and complete printed evidence.

### Don't:
- **Don't** treat this local report as the inventory application's visual identity or a global build-path preference.
- **Don't** imply a live connection through decorative indicators or changing metrics.
- **Don't** derive application readiness from a status color or a test count alone.
