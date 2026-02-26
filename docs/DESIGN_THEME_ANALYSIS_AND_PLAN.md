# Design Generation: Theme Consistency Analysis & Improvement Plan

## 1. Current Implementation Analysis

### 1.1 How Prompts Are Generated

**Entry point:** `generate_and_refine_prompts` in `tools/content_tools.py` (line 735) is invoked from the workflow with `description` and `theme_context`.

**Theme context structure** (from `workflow._build_theme_context_from_concept` and theme expansion):

- `original_input`: e.g. `"Highland cows in Celtic art style"`
- `expanded_theme`: full concept description
- `artistic_style`: e.g. `"Celtic art"` (the **secondary** / style dimension)
- `style_keywords`, `visual_elements`, `page_ideas`, `signature_artist`, etc.

**What the generator actually receives** (`_generate_prompts_internal`, content_tools.py ~448–524):

- **Book description** (from title/description step) — may mention the main theme but is generic.
- **Style section** built only from:
  - `artistic_style`
  - `signature_artist`
  - `style_keywords`
  - `visual_elements`
  - `page_ideas`
- **No explicit “main theme”** (e.g. “Highland cows”, “Easter”, “dogs”) is passed as a **primary, mandatory** constraint.

So the model is strongly steered by **style** (Celtic, Art Nouveau, etc.) and **page_ideas**, but the **main subject/theme** is not clearly stated as “this must be the focus of every prompt.” The instructions say “EVERY prompt should reflect this artistic style” and “Include style-specific keywords,” but there is no equivalent “EVERY prompt must center on [main theme].”

**Result:** The generator can drift toward the secondary theme (e.g. “Celtic patterns” or “Art Nouveau”) and produce prompts that are only loosely related—or unrelated—to the main theme (e.g. Highland cows, Easter, dogs). That matches the “secondary theme takes over” behavior you described.

---

### 1.2 Where the Main Theme Exists but Is Underused

- **Concept:** `theme` / `theme_concept` (e.g. “Highland cows”, “Easter”) and `style` / `art_style` (e.g. “Celtic art”) are separate in the concept and in `_build_theme_context_from_concept`.
- **Theme context:** `original_input` and `expanded_theme` both encode “main theme + style,” but:
  - **Prompt generator** does not pull out a dedicated “main theme” or “primary subject” and does not instruct “every prompt must be about this.”
  - So the **main theme** is only implicit in the description and in blended strings like `expanded_theme`, and is easily outweighed by style and page_ideas.

---

### 1.3 Evaluator: How Prompts Are Evaluated

**Location:** `agents/evaluator.py` — `evaluate_prompts(prompts: list)` (line 404).

**Current behavior:**

1. **Signature:** `evaluate_prompts(prompts)` — it receives **only** the list of prompts. It does **not** receive `theme_context` or any explicit “main theme” or “primary subject.”
2. **Criteria in `PROMPTS_EVALUATOR_PROMPT`:**
   - **Technical (30 pts):**
     - **Count:** “Must have EXACTLY 50 prompts” — so count is treated as a strict technical requirement and can contribute to fail (e.g. if the evaluator gives 0/30 for “not exactly 50”).
     - Format, required elements, no color keywords.
   - **Creative variety (40 pts):** subject diversity, style diversity, creative combinations, **artistic coherence** (“unifying theme while maintaining variety” — but no explicit “main theme” to check against).
   - **MidJourney effectiveness (30 pts):** keyword quality, coloring appropriateness.

So:

- **Theme consistency** is only implied via “artistic coherence” and “unifying theme.” The evaluator has **no** notion of “main theme = X”; it cannot detect “this set is all Celtic but not about Highland cows.”
- **Count** is stated as “EXACTLY 50” and is part of a critical-looking technical block, so it can effectively act as a **critical fail** (e.g. failing the whole prompt set for having 48 or 52 prompts). That conflicts with your preference that “50ish, preferably more” should not be a critical fail.

**Pre-checks** (lines 406–416): format, required phrases, color words. No check against a main theme.

---

### 1.4 Summary of Why Theme Drifts

| Cause | Where |
|-------|--------|
| Main theme not explicitly passed to the prompt generator as the primary constraint | `_generate_prompts_internal`: only style + page_ideas + description; no “main_theme” / “primary subject” section |
| Generator is told “reflect artistic style” but not “every prompt must be about [main theme]” | Same prompt template |
| Evaluator cannot enforce “all prompts align with main theme X” | `evaluate_prompts(prompts)` has no `theme_context` or `main_theme`; only generic “unifying theme” |
| Count (50) can act as a hard fail | Evaluator prompt: “Must have EXACTLY 50” under Technical (30 pts) |

---

## 2. Improvement Plan

### 2.1 Goal

- **Main theme** (e.g. Highland cows, Easter, dogs) stays **primary** across all prompts; **secondary** theme (e.g. Celtic art, Art Nouveau) is the style applied to that main theme.
- Evaluator treats **theme consistency** as a first-class, critical criterion and **count** as “50ish, preferably more” but **not** a critical fail.

---

### 2.2 Changes to Prompt Generation (`content_tools.py`)

1. **Define and pass “main theme” into the generator**
   - Derive a single **main theme** (primary subject) from `theme_context`:
     - e.g. from `original_input` or `expanded_theme` (e.g. first part before “ in … style”), or add a dedicated `main_theme` / `primary_subject` on the concept and in `_build_theme_context_from_concept` if needed.
   - Ensure `theme_context` consistently exposes something like:
     - `main_theme` or `primary_subject`: e.g. “Highland cows”, “Easter”, “dogs”  
     - Keep `artistic_style` as the secondary (style) dimension.

2. **Add a “MAIN THEME” block to the prompt template**
   - In `_generate_prompts_internal`, add a section, e.g.:
     - “## MAIN THEME (PRIMARY – MUST APPLY TO EVERY PROMPT): [main_theme]. Every prompt must be clearly about this subject; the artistic style is how it is drawn, not what it is.”
   - Keep the existing “ARTISTIC STYLE DIRECTION” as secondary (how it looks).

3. **Tighten the rules in the template**
   - Add an explicit rule: “Every prompt must center on the MAIN THEME above. Do not create prompts that are only about the artistic style (e.g. generic Celtic patterns) without the main theme subject.”
   - Optionally add 1–2 examples: good = “Highland cow, Celtic knot border, …”; bad = “Celtic knot, mandala, …” (no main theme).

4. **Optional: target count wording**
   - In the generator, you can soften “EXACTLY 50” to “approximately 50 (e.g. 48–55)” so the model doesn’t over-prioritize count and under-prioritize theme. This is optional if the evaluator no longer fails on count.

---

### 2.3 Changes to Evaluator (`evaluator.py`)

1. **Pass theme context into evaluate_prompts**
   - Change signature to something like:  
     `evaluate_prompts(prompts: list, theme_context: dict = None)`  
   - Caller: `generate_and_refine_prompts` (and any other callers) must pass the same `theme_context` they use for generation.

2. **Derive main theme for evaluation**
   - From `theme_context` compute:
     - `main_theme` / `primary_subject` (e.g. from `original_input`, `expanded_theme`, or new field).
   - If `theme_context` is missing, keep current behavior (no theme-consistency check).

3. **Add “Main theme consistency” as a first-class criterion**
   - In `PROMPTS_EVALUATOR_PROMPT`:
     - New criterion (e.g. 25–30 points): “**Main theme consistency**: The main theme for this book is: [main_theme]. Every prompt must be clearly about this theme (subject). Prompts that are only about the artistic style or unrelated subjects (e.g. generic patterns with no link to the main theme) must fail this criterion. Deduct heavily if a significant portion of prompts do not reflect the main theme.”
   - Include in the JSON: e.g. `main_theme_consistency_score`, `prompts_off_theme` (count or indices), and/or `theme_consistency_issues`.

4. **Reduce count from critical to soft**
   - Replace “Must have EXACTLY 50 prompts” with:
     - “Target: around 50 prompts (e.g. 45–55). Slightly under or over is acceptable; do not fail the entire set solely for being 48 or 52. Prefer ‘approximately 50’.”
   - Move count into a “minor” or “soft” requirement: e.g. small deduction for “far from 50” (e.g. &lt;40 or &gt;60), but **never** the sole reason for `passed: false` if theme consistency, diversity, and format are good.

5. **Re-balance weights**
   - Ensure theme consistency has a high weight (e.g. 25–30 pts); keep diversity and format; make count a small share (e.g. 5 pts) so that “in theme + diverse + good format” can still pass with 48 or 52 prompts.

6. **Pre-check (optional)**
   - Optionally add a simple heuristic: e.g. check that a keyword for the main theme (or a stem) appears in a large fraction of prompts (e.g. 80%+). If not, add an issue to the evaluation result. This is a supplement to the LLM criterion, not a replacement.

---

### 2.4 Call Site Updates

- **content_tools.py:** In `generate_and_refine_prompts`, when calling `evaluate_prompts`, pass `theme_context`:  
  `evaluate_prompts(prompts, theme_context=theme_context)`.
- **content_tools.py:** When building feedback for the next attempt, include evaluator output about theme consistency (e.g. “prompts_off_theme” or “main_theme_consistency_score”) so the generator can be explicitly asked to fix those prompts.

---

### 2.5 Optional: State and UI

- **State:** You can add `main_theme` (or `primary_subject`) to the concept and to `theme_context` in `workflow._build_theme_context_from_concept` so it’s explicit everywhere.
- **UI:** If the evaluator returns `prompts_off_theme` (indices), the UI could highlight “these prompts may be off-theme” for the user.

---

### 2.6 Implementation Order

1. **Theme context:** Add or derive `main_theme` in workflow/concept and ensure it’s in `theme_context` passed to both generator and evaluator.
2. **Generator:** Add MAIN THEME section and explicit “every prompt must center on main theme” rule (and examples) in `_generate_prompts_internal`.
3. **Evaluator:** Add `theme_context`/`main_theme` to `evaluate_prompts`, add main-theme-consistency criterion and JSON fields, and soften count to “~50, not a critical fail.”
4. **Call sites:** Pass `theme_context` into `evaluate_prompts` and use theme-consistency feedback in the refinement loop.
5. **Tests:** Run a few concepts (e.g. “Highland cows + Celtic”, “Easter + Art Nouveau”) and confirm prompts stay on-theme and evaluator no longer fails solely for count.

---

This gives you a clear picture of **how it’s implemented today** and a **concrete plan** so the main theme stays primary across all prompts and the evaluator enforces that while treating count as “50ish, preferably more” and not a critical fail.
