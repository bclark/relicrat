RELICRAT — BRAND & UI REVIEW KIT, REVISION 2
October 31, 2026 | PROPOSED assets and specifications

OPEN THE REVIEW
Run python3 build-review.py, then open RelicRat Review.html for the standalone, offline review. The generated HTML is intentionally not versioned.
For reliable browser-local demo persistence, run this folder on localhost:
python3 -m http.server 58129 --bind 127.0.0.1
Then open http://127.0.0.1:58129/prototype/#brand

WHAT CHANGED
- Curved slab wordmark with distinctive R bowls/legs and a subtle rising rhythm.
- Rat-head silhouette with two rounded ears, swept fur, round nose and neck.
- Dedicated small silhouette without interior detail for 16–24 CSS px.
- Standalone transparent mascot front study and revised vinyl-handling pose.
- Six varied fictional collectible illustrations in collection and detail views.
- Corrected reference-recovery status and unambiguous clear-space measurement.
Revision 1 remains preserved in the original external design folder; see ../../README.md for provenance.

CANONICAL REFERENCES
../../../brand/RELICRAT_BRAND.md remains the canonical v1 creative-direction source.
All three original reference PNGs are preserved unchanged in ../../../brand/references/:
a_clean_character_concept_illustration_on_a_cream.png — primary character anatomy.
a_clean_character_design_and_iconography_presentat.png — icon/silhouette exploration.
a_clean_stylized_brand_identity_board_illustratio.png — modern collecting direction.
../../../brand/references/wordmark-exploration.png is earlier exploration, not canonical anatomy.
Generated boards do not establish exact fonts, vector geometry or measured colors.

STATUS AND USE
User acceptance of the review recommendations authorizes this revision. It does
not make each newly drawn asset canonical. All new marks and character extensions
remain PROPOSED. Fictional collectible imagery remains EXPLORATORY and is not
production catalog artwork, an actual collection photo, or evidence of condition.
The canonical primary mascot reference always takes precedence over extensions.

WORDMARK AND ICON
Use uppercase RELICRAT in the proposed mark and RelicRat in running text.
The wordmark is original SVG paths; no font dependency. UI text uses system sans.
Minimum wordmark width: 144 CSS px. Below that, use the head mark.
Clear space: at least 8 SVG units on each side of the VISIBLE letter contours.
Nominal capital height: 52 units. Minimum clearance is approximately 15% of it.
Prefer 26 units (half the nominal capital height) when space permits.
Charcoal on white/ivory; reversed ivory on forest/charcoal.
Do not stretch, outline, rotate, distress or recolor individual letters.
Head mark viewBox: 64 x 64. At 16–24 px use rat-head-small-PROPOSED.svg;
at 32 px and above use rat-head-PROPOSED.svg. Reversed variants are supplied.
App icon: 80 x 80 viewBox, 16-unit corner radius.
Provenance emblem identifies a record; it does not certify authenticity.
All optical sizes remain proposals requiring owner review.

MASCOT EXTENSIONS
assets/mascot-front-v2-PROPOSED.png — straight-on front-facing anatomy study.
assets/mascot-vinyl-v2-PROPOSED.png — revised collector interaction pose.
Both are standalone PNGs with genuine alpha transparency, not sheet crops.
The previous mascot-reference-sheet-PROPOSED.png is superseded exploration;
its turned front view and fingers on record grooves remain known defects.
The new studies do not constitute a full orthographic turnaround or complete
expression library. Additional poses need the same anatomy/outfit comparison.

PALETTE
Retained prototype values: ivory #F7F3E9, charcoal #302B28, forest #29483E,
burgundy #823B3D, gold #B78B43. These remain proposed exact specifications.
Gold #B78B43 is decorative on light surfaces, not normal text on ivory/white.
The dark theme uses a lighter gold #E9C590 for its action accent; that distinct
semantic token is contrast-checked and is not the decorative gold above.
The prototype uses forest navigation and burgundy primary actions.
Theme imports support one action accent and do not install the screen layout.
No existing application theme or production assets have been changed.

UI REVIEW
prototype/ contains the local demo. It preserves physical-copy IDs and history,
separates provisional identification from catalog/release linking, and labels
owner-entered history. No authentication, real uploads, API saves, backup,
verified provenance, multi-user conflict handling or production integration.
The revision uses its own browser storage key; revision-1 demo data is untouched.
Six generated illustrative objects share one contact-sheet asset. SVG viewports display
one cell per category at its original proportions. They are demonstrations, not physical-copy photographs.
No-photo states remain for newly entered records.

VALIDATION AND REBUILD
python3 check.py checks specified theme text contrast and SVG well-formedness.
node --check prototype/app.js checks JavaScript syntax.
python3 build-review.py rebuilds the self-contained HTML from source files.
review/verification.txt records original design-package checks; it does not establish production implementation or deployment status.
Design screenshots are review evidence, not accessibility certification.

REMAINING APPROVALS
Owner review of letterforms, icon recognition at small sizes, character fidelity,
exact palette values and application layout. Production rollout and a complete
mascot turnaround/expression library remain separate work.
