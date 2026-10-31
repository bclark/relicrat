# RelicRat — Brand Identity Guidelines

**Version:** 1.0 — Direction approved; production specifications in progress  
**Website:** https://relicrat.com  
**Brand concept:** **Modern collecting. Timeless stories.**  
**Document role:** Canonical creative-direction reference for design, illustration, product UI, and marketing.

> **Status convention:** **Approved** means the creative direction has been selected. **Exploratory** means an illustration or treatment is a reference, not a production-ready asset. **Proposed** means a specification needs review before becoming canonical. Do not infer exact design specifications from generated concept images.

## 1. What RelicRat is

RelicRat is a modern collectibles inventory and provenance platform. It helps collectors organize what they own, document condition and history, and preserve the stories associated with their objects.

RelicRat serves collectors of **comic books, original art, trading cards, vinyl records, toys, books, antiques, and other collectible objects**. It is not limited to antiques or museum artifacts.

**Brand personality:** curious, clever, enthusiastic, knowledgeable, approachable, trustworthy, and meticulous.

**Brand balance:** playful character storytelling + credible archival care + polished modern software.

**Messaging territories (exploratory, not mandatory taglines):**
- Modern collecting. Timeless stories. (**approved brand concept**)
- Every collectible has a story.
- Collect. Organize. Preserve.

## 2. Official mascot — Approved character direction

The official RelicRat mascot is **one consistent anthropomorphic rat**, a passionate collector, treasure hunter, and careful archivist. He is confident, friendly, and slightly mischievous, with the curiosity of an explorer and the precision of a curator.

### Canonical identifying features

- Warm **charcoal-gray fur** with a **cream muzzle and cheek accents**.
- **Oversized rounded ears** with warm pink inner ears; retain their distinctive relative scale and asymmetrical perspective.
- Expressive, intelligent eyes; curious brows; a small pink nose; and a friendly, subtly mischievous smile.
- A recognizable **swept-back, slightly tousled fur silhouette**.
- A **long, thin pink tail**.
- Expressive hands and approachable, animated proportions without baby-like exaggeration.
- **Burgundy waistcoat**, **cream rolled-sleeve shirt**, **brown trousers**, and **vintage brown leather collector's satchel**.
- Optional accessories for storytelling: magnifying glass, archival notebook, protective sleeves, or a collectible being examined.

**Do not redesign** his face, proportions, silhouette, palette, or core outfit between scenes. Match the approved primary mascot image before creating new poses.

### What he collects

Show the mascot engaging with **comics, original artwork, trading cards, vinyl records, toys, and other collectibles** as well as historical objects. Examples: carefully inspecting a trading card, flipping through a comic box, examining a record sleeve, cataloging a collectible, or researching provenance.

He should feel like **a modern collector with a vintage soul**, not exclusively an antique hunter.

### Illustration style

- Expressive hand-drawn ink lines and confident silhouettes.
- Classic 1930s–1950s animation influence, interpreted as an **original** character, not a copy of a known mascot.
- Restrained flat colors, subtle print texture, and tasteful editorial detailing.
- Natural, legible poses; warm expressions; clear visual storytelling.
- Texture is appropriate for character art and marketing, **not** as a blanket treatment over product UI.

### Avoid

- Alternate rat designs, inconsistent ears or facial geometry, changed clothing, or unrecognizable expressions.
- Overly infantile proportions, generic corporate mascot style, or excessive visual clutter.
- Pirate, steampunk, fantasy-only, or exclusively archaeological theming.
- Direct resemblance to existing copyrighted cartoon mascots.

## 3. Reference artwork — Canonical inputs, exploratory outputs

These three files are the **required visual references**. Store them alongside this document in Project files or a repository brand-assets folder.

| File | Role | Status |
| --- | --- | --- |
| `a_clean_character_concept_illustration_on_a_cream.png` | **Primary reference:** facial features, proportions, outfit, personality, full-body design | Approved character direction; generated illustration, not production master |
| `a_clean_character_design_and_iconography_presentat.png` | Silhouette and icon exploration; head shape and simplified emblem | Exploratory icon treatments |
| `a_clean_stylized_brand_identity_board_illustratio.png` | Modern collecting theme, mid-century wordmark direction, comics/cards/records applications | Approved creative direction; individual assets exploratory |

**Priority when references conflict:** primary mascot concept for anatomy and outfit; latest modern-collectibles board for subject matter and brand direction; silhouette sheet for icon research. Written constraints in this document govern all three.

**Important:** Image-generation boards may include inconsistent details, lettering artifacts, or unlicensed-looking fictional collectible covers. Do not trace these into final production artwork or treat depicted collectible covers as approved assets.

## 4. Wordmark and typography

### Wordmark direction — Approved

**Bold mid-century adventure lettering**, with sturdy, confident, distinctive shapes and a touch of handcrafted irregularity. The visual reference is the bold wordmark on the modern-collectibles board.

- Favor strong, readable, compact letterforms and recognizable capital **R** shapes.
- Explore both `RelicRat` and `RELICRAT`; final casing is **not yet locked**.
- Favor clean, flat, one-color logo construction first. Texture, outlines, and shadows are secondary applications.
- Avoid ornamental compasses and decorative flourishes in the primary logo unless specifically approved.
- Do not mistake a generated wordmark image for an editable vector logo.

**Production status:** Typeface, lettering geometry, spacing, final casing, and SVG wordmark are **not yet finalized**. Previously explored serif fonts were not selected. Do not assert a particular font is approved.

### Application typography — Direction approved, families pending

Use a contemporary, highly legible UI sans-serif for navigation, forms, tables, item metadata, and collection management. **Inter** and **DM Sans** are possible candidates, **not approved selections**. Choose based on readability, accessibility, and licensing after review.

Keep the expressive wordmark separate from ordinary product typography.

## 5. Color system

### Approved color families

- Warm ivory — brand backgrounds and paper-like illustration grounds.
- Charcoal — text, outlines, mascot fur, monochrome marks.
- Burgundy — waistcoat and selective brand accents.
- Antique gold — collector/archival accents and restrained seals.
- Deep forest green — secondary brand accent.

### Proposed starting palette — NOT YET APPROVED

The following HEX values are **working tokens for prototyping only**. They are not measured or sampled canonical values from the reference images.

| Token | Proposed HEX | Intended use |
| --- | --- | --- |
| `brand.ivory` | `#F7F3E9` | Warm brand canvas |
| `brand.charcoal` | `#302B28` | Primary ink, text, emblem |
| `brand.burgundy` | `#823B3D` | Accent and character wardrobe |
| `brand.gold` | `#B78B43` | Restrained archival accents |
| `brand.forest` | `#29483E` | Secondary accent |

**Next step:** sample and review color values against the reference artwork, then validate contrast and finalize separate light/dark UI semantic tokens. Avoid assuming the ivory color must be the background of every app screen.

## 6. Icon and provenance seal

### Icon direction — Approved

A simplified, distinctive **rat-head silhouette** that remains recognizable at small sizes. Preserve the oversized ears, swept fur, and projecting muzzle as the core outline. Reduce whiskers and interior facial marks aggressively as the icon shrinks.

### Required variants — To be produced

1. **Primary silhouette:** one-color head mark, strong positive/negative shapes.
2. **App icon:** simplified silhouette or restrained character portrait on a clear, modern background.
3. **Provenance seal:** monochrome, restrained emblem suitable for certificates, archival records, and subtle watermarks.
4. **Small-size mark:** optimized and tested at **16, 32, and 64 px**; don't merely shrink the full illustration.

**Status:** The silhouette direction is selected, but the exact vector geometry, optical corrections, and final icon are **not yet approved production assets**.

## 7. Product interface principles

The application must feel like **modern, polished, efficient collection-management software**.

- Prioritize collectible imagery, metadata clarity, navigation, search, filters, condition/provenance history, and practical workflows.
- Use neutral surfaces, accessible contrast, contemporary spacing, and restrained brand accents.
- Make the collection itself the visual hero. Mascot artwork should add character to onboarding, empty states, discovery moments, education, and celebratory moments—not compete with inventory data.
- Design for personal collection management first; maintain responsive layouts and mobile usability.
- Use restrained texture in marketing illustration, **not** across cards, tables, form fields, or dashboards.
- Support modern light and dark UI treatments without losing brand identity.

### Explicit anti-patterns

- Sepia-tinted dashboards or an antique-paper texture applied to the entire application.
- Faux-vintage controls, ornate borders everywhere, low-contrast gold text, or excessive burgundy backgrounds.
- A UI that resembles an antique shop rather than a modern inventory platform.
- Mascot art overwhelming collectible thumbnails or important record details.

## 8. Voice and copy

**Voice:** knowledgeable, warm, concise, curious, and respectful of the collector's expertise.

- Celebrate the object's history without exaggerating value or authenticity.
- Make provenance and condition statements precise, sourced, and transparent about uncertainty.
- Use playful mascot moments sparingly; avoid jokes in critical workflows such as data loss, backup restore, and irreversible deletion.
- Don't imply authentication or provenance verification has occurred unless the product actually performed it.

## 9. Brand usage by context

| Context | Preferred treatment |
| --- | --- |
| Marketing hero | Full-color mascot + bold mid-century wordmark + modern collectible subject |
| Website navigation | Clean primary wordmark or icon/wordmark lockup |
| App navigation | Minimal silhouette/icon; no oversized illustration |
| Empty states/onboarding | Expressive mascot with relevant modern collectibles |
| Provenance records | Restrained monochrome seal, not a claim of independent authentication |
| Favicon | Purpose-drawn small-size silhouette |
| Product dashboards | Contemporary UI; collectible photos and data first |

## 10. Rules for future chats, designers, and image generation

1. **Read this document and inspect the three reference images before designing.**
2. Preserve the **same character**. Create new poses and collectible interactions, not a replacement mascot.
3. Keep the **mid-century adventure** wordmark direction while avoiding overly antique styling.
4. Distinguish **illustration branding** from **modern application UI**.
5. Treat generated boards as **exploration**, not vector assets, measured palettes, or approved typefaces.
6. Mark all unapproved choices **Proposed** or **Exploratory**; request approval before promoting them to canonical status.
7. Do not introduce new logos, mascots, palettes, or typography as though they were established decisions.
8. For production, create proper SVG/vector masters and verify legibility, contrast, and sizes.

### Reusable illustration brief

> Illustrate the **established RelicRat mascot** using the primary approved character reference. Preserve his charcoal-gray fur, cream muzzle, oversized rounded pink ears, swept-back fur, expressive eyes, pink nose and tail, burgundy waistcoat, rolled-sleeve cream shirt, brown trousers, and leather satchel. He is a clever, slightly mischievous collector and careful archivist. Show him interacting naturally with [SPECIFIC COLLECTIBLE OR ACTIVITY]. Use expressive hand-drawn ink outlines, confident shapes, restrained colors, and subtle vintage print texture. Maintain the original character's facial proportions and silhouette. No redesign, no unrelated mascot, no generic corporate illustration.

### Reusable product UI brief

> Design a modern RelicRat collection-management interface. Prioritize readability, accessible contrast, clean layouts, collectible imagery, search/filter efficiency, and provenance metadata. Use the approved RelicRat brand direction with restrained charcoal, burgundy, antique-gold, and forest-green accents. The interface must not resemble a sepia-toned antique catalog. Use mascot artwork selectively and preserve the canonical mascot whenever shown.

## 11. Open decisions / production checklist

- [ ] Approve final wordmark casing, letterforms, and SVG master.
- [ ] Select and license-check open-source product typefaces.
- [ ] Finalize measured brand HEX/RGB values and semantic UI colors.
- [ ] Create canonical mascot turnaround and expression sheets.
- [ ] Create approved silhouette, favicon, app icon, and provenance seal vectors.
- [ ] Test icons at 16/32/64 px and in light/dark contexts.
- [ ] Define logo clear space, minimum size, and background usage.
- [ ] Export organized production assets with consistent filenames and versioning.

---

**Change control:** This document records the approved **v1 brand direction**, not a claim that all assets are finalized. Update the version and explicitly document approvals when production decisions are made. The reference images and this document should travel together across chats and design tools.
