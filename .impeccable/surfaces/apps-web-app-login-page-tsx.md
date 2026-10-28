---
version: 1
slug: "apps-web-app-login-page-tsx"
primary_target: "apps/web/app/login/page.tsx"
related_targets: ["apps/web/app/login/login-form.tsx","apps/web/app/sign-out.tsx","apps/web/app/page.tsx","apps/web/app/globals.css"]
---

# Owner access

Mode: Operate. Ordinary extension of the existing inventory world. User chose
one owner password with SSH setup. Inherit DESIGN.md and design.json unchanged:
cool page, white work surface, navy text, cobalt actions, system type and native
labeled controls. No new visual world, decorative assets, or approved comp.

Job: enter the owner password and reach the same collection; sign out clearly.
One compact form with password-manager autocomplete and visible error/status.
Single-column layout preserves the incumbent 44px controls at desktop/mobile.
No signup/account/avatar controls or unsupported recovery claims. SSH reset is
operator work, not a browser workflow. Sign out belongs in the inventory header.

Thesis: access is a brief gate to the existing collecting workbench. First view:
RelicRat wordmark, sign-in heading, plain instruction, labeled password and primary
action. Distinguish wrong password, lockout, unavailable configuration and failed
logout; do not clear a session until revocation is confirmed. No token rendered
in the UI. Authentication does not remove the synthetic-only notice.

Required evidence: login desktop 1440/mobile 390 and protected inventory at both
widths, real browser guest/login/reload/logout/replay checks, Node gateway tests
and PostgreSQL session tests. No image/icon asset work is warranted.
