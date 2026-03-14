# Coloring Book Prompts: Best Practices vs Current Approach — Analysis & Recommendations

This document summarizes **best practices** for creating Midjourney prompts for coloring book **inside pages** and **covers** (from web research and project docs), compares them to the **current implementation**, and lists **recommendations** for improvement. **No code changes are implemented here.**

---

## 1. Best Practices (from research)

### 1.1 Inside pages (coloring book pages)

**Essential terminology and intent:**

| Requirement | Purpose |
|-------------|--------|
| **Black and white only** | Force colorless line art for user coloring; Midjourney defaults to full color. |
| **Thick outlines / bold lines** | Thin lines disappear under crayon or marker; thick black outlines stay clear. |
| **No shading / no gradient / no shadow** | Shadows and tonal variation fill areas meant for coloring and confuse print. |
| **Simple outlines** | Keeps designs approachable; too much detail frustrates colorers. |
| **White background** | Clean printing; grey or textured backgrounds waste ink and look messy. |
| **No background** (alternative) | Focus on subject only; avoids busy backgrounds. |

**Recommended Midjourney parameters:**

- **`--no shading, color, gradient, shadow, depth`** — Removes problematic elements in one go. Many sources stress that **`--no color`** alone is not enough; shading and gradients still appear and ruin coloring pages.
- **Aspect ratio** — **`--ar 1:1`** (square) or **`--ar 3:4`** (portrait) are both used; project choice is **1:1 for inside pages** (configurable if desired).
- **`--style raw`** — Produces cleaner line work with less unwanted artistic interpretation and complexity.
- **`--q 1`** — Optional; balances quality and speed for simple line art.

**Prompt structure (common formula):**

```text
[subject], [2–4 style/context keywords], coloring book page, black and white line art, thick outlines, simple details --no shading color gradient --ar 1:1
```
(Project choice: **inside pages use --ar 1:1**; cover uses **--ar 2:3**.)

**Audience-specific guidance:**

- **Kids:** Simpler designs, larger coloring spaces, fewer tiny details, “kid-friendly” or “children’s illustration style”.
- **Adults:** Can handle more intricate patterns (mandala, zentangle, detailed borders).

**Consistency across pages (“same feel”):**

- **`--seed [number]`** — The seed is a number (0–4,294,967,295) that fixes the **starting noise pattern** Midjourney uses. Using the **same seed** for all pages in a book can give more consistent line weight and detail level across generations (same “starting point”), which helps achieve a **coherent feel** even when subjects differ. Note: the seed does **not** store or copy “a style from a picture you like”; it only makes the random starting point repeatable. For **reusing the style of a specific image**, Midjourney recommends **style reference** (`--sref`) or character reference (`--cref`) instead. So: use **seed** for “same feel across my set of prompts”; use **sref** (when supported in your flow) if you want to match the look of an existing image.
- **Style reference (`--sref`)** — If you have a generated image whose style you like, `--sref <url>` can push later images toward that style. This is the right tool for “different pictures, same style from this one image.”

---

### 1.2 Covers

**Intent:**

- Full-color illustrated **background**; title/text added later in Canva or similar (Midjourney is unreliable for legible text).
- Visually aligned with inside pages (same theme and style).

**Recommended parameters and wording:**

- **Aspect ratio:** **`--ar 2:3`** (portrait) is standard for book covers and matches many print/KDP expectations. Some references mention **1:1.6** for Amazon KDP print. **Landscape** (e.g. 2:1) is non-standard for a book cover.
- **No text in image:** Explicit “no text”, “no letters”, “no words” (or “no typography”) to avoid AI-generated titles.
- **Space for title:** Optional but useful: “upper third uncluttered”, “space for title”, “empty banner at top”, “decorative frame with space for text” so the final cover has a clear area for the title overlay.
- **Low stylization:** Keep stylization low so the cover doesn’t become overly detailed or inconsistent with the book.
- **Theme and style:** Same main theme and artistic style as the inside pages.

**Prompt structure (example):**

```text
[theme/subject], [style keywords], book cover, rich colors, illustrated, no text --ar 2:3
```

With optional title-space variant:

```text
[theme], [style] style, book cover design, upper third softly blended or uncluttered for title placement, ornate frame below, rich colors, no text --ar 2:3
```

---

## 2. Current implementation (summary)

### 2.1 Inside pages

**Where:** `features/design_generation/tools/content_tools.py` — `_generate_prompts_internal()`.

**Current fixed suffix and parameters:**

- Wording: **`coloring book page, clean and simple line art, black and white`**
- Parameters: **`--no color --ar 1:1`**

**What the LLM is instructed to produce (concise):**

- ~50 prompts; subject + 2–4 style/context keywords + the fixed suffix above.
- No color-related keywords (enforced via `BANNED_COLOR_WORDS` in the evaluator).
- Main-theme consistency and artistic style from `theme_context`.

**Evaluation:** `features/design_generation/agents/evaluator.py` — `evaluate_prompts()` checks for “coloring book page”, “clean and simple line art”, “black and white”, and “--no color --ar 1:1”; rejects color words.

---

### 2.2 Covers

**Where:** `features/design_generation/tools/content_tools.py` — `_generate_cover_prompts_internal()`.

**Current fixed suffix and parameters:**

- Wording: **`book cover, rich colors, illustrated, no text`** (or “cover art” / “cover design”).
- Parameters: **`--ar 2:1`** (landscape).

**What the LLM is instructed to produce:**

- Exactly `COVER_PROMPTS_COUNT` (15) prompts; theme + 2–3 style keywords + full color, no text.
- No inside-page wording (e.g. “coloring book page”, “black and white”).

**Evaluation:** `evaluate_cover_prompts()` checks for “--ar 2:1”, “no text” (or similar), cover-specific wording, and forbids inside-page phrasing.

**Docs vs code:**

- `docs/COVER_PROMPTS_IMPLEMENTATION_PLAN.md` and `docs/COVER_GENERATION_ANALYSIS.md` recommend **`--ar 2:3`** (portrait) and optionally “space for title”.
- Implemented code uses **`--ar 2:1`** (landscape), which conflicts with typical book-cover proportions and with the project’s own design docs.

---

## 3. Gap analysis

### 3.1 Inside pages

| Best practice | Current implementation | Gap |
|---------------|-------------------------|-----|
| **--no shading, gradient, shadow, depth** | Only `--no color` | Shading/gradient/shadow/depth can still appear; often cited as the main cause of “non-colorable” AI pages. |
| **Thick / bold outlines** | “clean and simple line art” only | No explicit “thick outlines” or “bold black lines”; lines may come out too thin for coloring. |
| **White background** | Not specified | Background not explicitly constrained; grey or textured backgrounds possible. |
| **Aspect ratio** | `--ar 1:1` | **Accepted:** keep **1:1 for inside** (user preference). No change. |
| **--style raw** | Not used | No guidance for cleaner, less over-stylized line work. |
| **Target audience (kids vs adults)** | `target_audience` in theme_context, used in description/keywords | Not clearly fed into the **page prompt** template (e.g. “simple shapes, large spaces, kid-friendly” vs “intricate, detailed”). |
| **Optional --q 1** | Not used | Minor; could be added for consistency/speed. |

### 3.2 Covers

| Best practice | Current implementation | Gap |
|---------------|-------------------------|-----|
| **Portrait aspect ratio (e.g. 2:3)** | `--ar 2:1` (landscape) | Mismatch with standard book cover and with project docs; 2:1 is landscape, not portrait. |
| **“Space for title” / uncluttered area** | Not in template | No explicit instruction for a clear zone (e.g. top third) for title overlay. |
| **--no text** (or equivalent) | “no text” in wording | Already present; OK. |
| **Match inside theme/style** | Theme and style from theme_context | Already present; OK. |

---

## 4. Recommendations (no implementation)

### 4.1 Inside pages

1. **Extend `--no` parameters**  
   Change the required suffix from `--no color --ar 1:1` to include at least:  
   `--no shading, color, gradient, shadow, depth`  
   (or similar, depending on Midjourney’s current syntax). Update the generator template and the evaluator so that prompts are required to use this form (or a single canonical form you define).

2. **Add explicit line and background wording**  
   In the fixed part of the prompt, add:
   - “thick outlines” or “bold black lines” (or one canonical phrase), and  
   - “white background” (or “no background”)  
   so that the model and Midjourney consistently aim for colorable, print-friendly pages.

3. **Aspect ratios (decided)**  
   - **Inside pages:** keep **`--ar 1:1`** (no change).  
   - **Cover:** use **`--ar 2:3`** (portrait), and make it **configurable from the UI** (e.g. dropdown or field so users can choose 2:3 or another ratio if needed).

4. **Consider `--style raw`**  
   Add `--style raw` to the required suffix for inside pages and validate it in the evaluator. If Midjourney version or product constraints don’t support it, document that and keep the rest of the improvements.

5. **Use target audience in the page prompt**  
   Pass `target_audience` (and optionally age range or “kids” vs “adults”) into the **inside-page** prompt template and add short rules, e.g.:
   - Kids: “simple shapes, large coloring areas, kid-friendly, minimal small detail”.
   - Adults: “intricate details, detailed patterns, adult coloring” (where appropriate).  
   Keep the same 2–4 keyword rule; only the style/context part is audience-aware.

6. **Seed for “same feel” across images**  
   - **What seed does:** Same `--seed <number>` across prompts gives the same **starting noise**, which can yield more consistent line weight and detail level across a book (“different pictures, same feel”). It does **not** copy “the style of a picture I like”; for that, use **style reference (`--sref`)** when supported.  
   - **Recommendation:** Support an optional **book-level seed** (e.g. user can set a seed in design or image-generation UI; that seed is appended to every inside-page prompt when publishing to Midjourney). If no seed is set, omit it (Midjourney will randomize). This supports “same feel” without changing prompt text generation.  
   - **Optional later:** Allow **style reference** (e.g. URL of a generated image) so users can push new images toward a chosen style.

### 4.2 Covers

7. **Cover aspect ratio: 2:3 and configurable from UI**  
   Change cover prompts from **`--ar 2:1`** to **`--ar 2:3`** (portrait). Update generator and evaluator. In addition, make the **cover aspect ratio configurable from the UI** (e.g. in design or image-generation: dropdown or text field for 2:3, 1:1, or custom), and use that value when generating/validating cover prompts and when sending to Midjourney.

8. **Add optional “space for title” variant**  
   In the cover prompt template, add one of:
   - A rule: “At least N of the prompts should mention an uncluttered area (e.g. top third) or space for title,” or  
   - A fixed phrase in the suffix, e.g. “upper third uncluttered for title, no text”.  
   So that some cover options are explicitly composed for title overlay (Option C in `COVER_GENERATION_ANALYSIS.md`).

9. **Reconcile cover prompt count with docs**  
   `COVER_PROMPTS_IMPLEMENTATION_PLAN.md` suggests 3–5 cover prompts; code uses `COVER_PROMPTS_COUNT = 15`. Decide the desired count (e.g. 5 vs 15) and align constant, template, and evaluator.

### 4.3 Cross-cutting

10. **Centralize “canonical” suffixes**  
    Define constants (e.g. in `features/design_generation/constants.py`) for:
    - Inside: e.g.  
      `INSIDE_PAGE_SUFFIX = "coloring book page, black and white line art, thick outlines, white background --no shading color gradient shadow depth --ar 1:1"`  
      (and optionally `--style raw`), and  
    - Cover: e.g.  
      `COVER_SUFFIX = "book cover, rich colors, illustrated, no text --ar 2:3"` (with AR value configurable from UI).  
    Use these in both the generator and the evaluator so that any future change (e.g. adding `--style raw`) happens in one place.

11. **Document Midjourney version and parameter support**  
    In a short design or config note, record which Midjourney version and parameters the prompts are designed for (e.g. `--style raw`, `--no …`, `--ar`), so that when Midjourney changes, the team can adjust the canonical suffixes and docs in one place.

12. **Keep evaluation in sync**  
    For every change to the required suffix or parameters (inside or cover), update the evaluator’s pre-checks and, if present, the LLM evaluation criteria (so that “correct” prompts are not marked as failing).

---

## 5. Accepted decisions (from discussion)

- **Inside pages:** keep **`--ar 1:1`** (square). No change to aspect ratio.
- **Cover:** use **`--ar 2:3`** (portrait), and make the cover aspect ratio **configurable from the UI**.
- **Seed:** support optional **book-level seed** so users can get “different pictures, same feel”; document that seed = same starting noise (coherent feel), while **style from a picture** = use `--sref` when available.
- **Rest of recommendations:** accepted as-is (extend --no, thick outlines, white background, target_audience in prompts, space for title on cover, centralize suffixes, etc.).

---

## 6. Priority overview

| Priority | Item | Impact |
|----------|------|--------|
| High | Extend `--no` to include shading, gradient, shadow, depth (inside) | Directly improves colorability of generated pages. |
| High | Add thick outlines + white background (inside) | Improves line clarity and print suitability. |
| High | Cover aspect ratio 2:1 → 2:3; configurable from UI | Aligns with print; user can override if needed. |
| Medium | Add “space for title” for covers | Better usability when adding title in Canva. |
| Medium | Use target_audience in inside-page template | Better fit for kids vs adults. |
| Medium | Optional seed (book-level) for inside prompts | “Same feel” across all pages when publishing to Midjourney. |
| Lower | Add --style raw (and document) | Cleaner line work; depends on Midjourney support. |
| Lower | Centralize suffixes and reconcile cover count | Maintainability and consistency. |

---

## 7. References (in-repo and web)

- **In-repo:**  
  - `features/design_generation/tools/content_tools.py` — `_generate_prompts_internal`, `_generate_cover_prompts_internal`.  
  - `features/design_generation/agents/evaluator.py` — `evaluate_prompts`, `evaluate_cover_prompts`, `BANNED_COLOR_WORDS`.  
  - `features/design_generation/constants.py` — `COVER_PROMPTS_COUNT`.  
  - `docs/COVER_GENERATION_ANALYSIS.md`, `docs/COVER_PROMPTS_IMPLEMENTATION_PLAN.md`.
- **Web (concepts used in this doc):**  
  - General best practices: “black and white only”, “thick outlines”, “no shading/gradient”, “white background”, “--no shading, color, gradient, shadow, depth”, “--ar 3:4”, “--style raw”; audience-specific guidance; cover “no text” and “space for title”; portrait 2:3 for covers.  
  - Ai Creative Blog: “50+ Ready Templates”, formula with `--no shading color gradient --ar 3:4`, use of `--style raw` and seed for consistency.  
  - Multiple references to Amazon KDP and portrait aspect ratios for book covers.
