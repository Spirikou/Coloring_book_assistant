# Cover Prompts & Cover Image Generation — Implementation Plan

This document is a **proposal only**. It describes how to add **cover prompt generation** (design) and a **parallel cover image workflow** (image generation) so that cover prompts are generated and evaluated like inside prompts, and cover images go through the same Publish → Upscale/Vary → Download flow in a dedicated section. **No code is implemented yet.**

---

## 1. Goals

- **Design generation:** Generate a small set of **cover background prompts** (no title text). They are **evaluated** with a dedicated evaluator and stored **separately** from inside-page prompts.
- **Image generation:** Keep the existing **inside** workflow unchanged. Add a **second section** below it that **mirrors** the inside workflow (prompts → Publish → Upscale/Vary → Download → gallery) but for **cover** prompts and cover images, with separate state and (optionally) a dedicated output subfolder for cover images.

---

## 2. Design Generation

### 2.1 State and Data Model

Extend `ColoringBookState` (and any initial state dicts) with:

| Field | Type | Purpose |
|-------|------|--------|
| `cover_prompts` | `list[str]` | Generated cover background prompts (e.g. 3–5). |
| `cover_prompts_attempts` | `list` | Attempt history for cover prompts (same shape as `prompts_attempts`). |
| `cover_prompts_score` | `int` | Final evaluation score for cover prompts. |
| `cover_prompts_passed` | `bool` | Whether evaluation passed. |
| `cover_prompts_status` | `str` | `"pending"` \| `"in_progress"` \| `"completed"` \| `"failed"`. |

**Files to touch:** `core/state.py`, and every place that builds initial state (e.g. `workflow.py` for concept-based flow, `run_design_step_for_concept`, agent extraction; design_generation UI when creating new state).

### 2.2 Cover Prompt Generator

Add in `features/design_generation/tools/content_tools.py`:

- **`_generate_cover_prompts_internal(description, theme_context, feedback="", custom_instructions="")`**  
  - Uses same LLM/style pattern as `_generate_prompts_internal` but with a **different prompt template**.
  - **Template rules:**
    - Output: **3–5** prompts (configurable constant, e.g. `COVER_PROMPTS_COUNT = 5`).
    - Each prompt must describe a **full-color book cover background**, **no text/title** in the image.
    - Include theme + artistic style from `theme_context` (same style as inside pages).
    - Require: `no text`, `no letters`, `no words` (or similar) so the image is title-free.
    - Require: `book cover`, `illustrated`, `rich colors` (or equivalent).
    - Aspect ratio: **`--ar 2:3`** (portrait cover).
    - **Do not** include: `coloring book page`, `clean and simple line art`, `black and white`, `--no color`.
  - Returns a list of strings (one per prompt).

- **`generate_and_refine_cover_prompts(description, theme_context, custom_instructions="")`** (as a `@tool` for agent use, and callable directly for concept flow):
  - Same pattern as `generate_and_refine_prompts`: loop up to `MAX_ATTEMPTS`, call `_generate_cover_prompts_internal`, then **evaluate** with `evaluate_cover_prompts`, use feedback to refine until pass or max attempts.
  - Returns `{"final_content": list[str], "attempts": [...], "passed": bool, "final_score": int}`.

**Constants:** In `features/design_generation/constants.py` (or next to other prompt counts), add e.g. `COVER_PROMPTS_COUNT = 5` (or 3–5 range).

### 2.3 Cover Prompts Evaluator

Add in `features/design_generation/agents/evaluator.py`:

- **`evaluate_cover_prompts(prompts: list, theme_context: dict = None) -> dict`**
  - **Criteria (different from inside prompts):**
    - **Count:** Target 3–5 prompts (or whatever `COVER_PROMPTS_COUNT` is); soft fail if way off.
    - **Format:** Comma-separated keywords; must end with `--ar 2:3` (or similar); no sentences.
    - **Cover-specific:** Must suggest a **book cover background** (e.g. contain “book cover”, “cover art”, or similar). Must **exclude title/text** (e.g. “no text” or “no words” in prompt).
    - **No inside-page wording:** Must **not** contain “coloring book page”, “clean and simple line art”, “black and white”, “--no color”. If present, deduct heavily.
    - **Theme/style consistency:** Same main theme and artistic style as the book (use `theme_context`).
    - **Color:** Prompts should imply **full color** (no “black and white”).
  - **Pre-checks (like `evaluate_prompts`):** Validate each prompt for required suffixes (`--ar 2:3`), forbidden phrases (inside-page boilerplate), and optionally “no text” presence.
  - Return shape similar to `evaluate_prompts`: `passed`, `score`, `issues`, `summary`, etc., so the refine loop can consume it.

**Scoring weights:** Either reuse a small block in `SCORING_WEIGHTS` for `"cover_prompts"` or keep logic inline (e.g. 25 format, 25 cover-specific, 25 theme consistency, 25 variety/quality).

### 2.4 Workflow Integration

**Concept-based path** (no agent), in `workflow.py`:

- After **keywords** step, add a **cover prompts** step:
  1. `generation_log.append({"step": "cover_prompts", "message": "Generating cover prompts..."})`
  2. Call `generate_and_refine_cover_prompts.invoke({"description": ..., "theme_context": theme_context})`
  3. Set `new_state["cover_prompts"]`, `cover_prompts_attempts`, `cover_prompts_score`, `cover_prompts_passed`, `cover_prompts_status = "completed"`.

**Executor/agent path** (if you still use it):

- Register **`generate_and_refine_cover_prompts`** in `get_executor_tools()` and in `EXECUTOR_SYSTEM_PROMPT`: after generating inside prompts and keywords, the agent should call `generate_and_refine_cover_prompts(description, theme_context=...)` and then summarize cover prompts count and score.
- In the **tool-result extraction** loop in `executor_node`, handle `generate_and_refine_cover_prompts` and set `new_state["cover_prompts"]`, `cover_prompts_attempts`, `cover_prompts_score`, `cover_prompts_passed`, `cover_prompts_status`.

**Step-by-step (e.g. `run_design_step_for_concept`):**

- Add step **`"cover_prompts"`** to `DESIGN_STEPS` (e.g. `["theme_context", "title", "prompts", "keywords", "cover_prompts"]`).
- In `run_design_step_for_concept`, when `step_name == "cover_prompts"`, call `generate_and_refine_cover_prompts` and fill the same state fields; append to `generation_log`.

**Regenerate / rerun:**

- If you have “Regenerate prompts” or “Regenerate all”, add “Regenerate cover prompts” that calls `regenerate_cover_prompts(theme_context, description, ...)` (implement similarly to `regenerate_prompts`), and optionally a “Regenerate all” that also regenerates cover prompts.

### 2.5 Design Generation UI

In `features/design_generation/ui.py`:

- **Checklist / progress:** Add a row for **Cover prompts** with status (pending/completed/failed) and score, same pattern as “MidJourney Prompts”.
- **Results / edit:** In the same tab or expander where inside prompts are shown, add a **“Cover prompts”** block:
  - Show count and score.
  - Read-only list of `state.get("cover_prompts", [])` with optional filter.
  - **Edit & save:** A text area (one prompt per line) and a button to write back to `state["cover_prompts"]`, and optionally call `_update_design_package_metadata` if a package is loaded.
- **Download / export:** Include `cover_prompts` in the exported design JSON (and in any “Download design” payload).

### 2.6 Persistence

- **`create_design_package` / `save_design_package` / `_update_design_package_metadata`:** Already persist full `state` to `design.json`. Once `cover_prompts` and related fields are in state, they will be saved and loaded automatically.
- **`load_design_package`:** No change needed; loaded state will include `cover_prompts` if present.
- **Backward compatibility:** When loading old design packages without `cover_prompts`, treat `cover_prompts` as `[]` and `cover_prompts_status` as `"pending"` (or hidden) so the UI doesn’t break.

---

## 3. Image Generation

### 3.1 Layout and Sections

Keep the existing **inside** workflow as the first section. Add a **second section** below it that **mirrors** the same flow for **cover** only:

1. **Section: Inside (book pages)**  
   - Midjourney prompts (from `state["midjourney_prompts"]`).  
   - Publish → Upscale/Vary → Download.  
   - Downloaded images gallery (from current output folder).  
   - All existing session state and processes (e.g. `mj_status`, `mj_publish_*`, `mj_uxd_*`, `mj_download_*`) stay as they are.

2. **Section: Cover**  
   - Cover prompts (from `state["cover_prompts"]`).  
   - Same flow: Publish → Upscale/Vary → Download.  
   - Downloaded images gallery for **cover only** (from a dedicated cover folder, e.g. `output_folder/cover`).  
   - **Separate** session state and process refs so inside and cover never mix: e.g. `mj_cover_status`, `mj_cover_publish_process`, `mj_cover_uxd_*`, `mj_cover_download_*`, and a dedicated **cover output folder**.

### 3.2 Cover Output Folder

- **Recommendation:** Use a **subfolder** of the same design output folder: e.g. `cover_folder = Path(output_folder) / "cover"`.  
- When the user is in the Cover section, “Output folder” for cover can be **read-only** or pre-filled as `{current output folder}/cover` so that:
  - Inside images: `output_folder/*.png` (etc.)
  - Cover images: `output_folder/cover/*.png`
- This keeps one “design output root” and separates inside vs cover by subfolder, which also simplifies “Save design package” (see below).

### 3.3 Session State for Cover

Duplicate the **inside** Midjourney session state with a **cover** prefix so the two flows are independent:

- `mj_cover_status` — same shape as `mj_status`: `publish_status`, `publish_error`, `uxd_action_status`, `uxd_action_error`, `download_status`, `download_error`, `downloaded_paths`.
- `mj_cover_publish_progress`, `mj_cover_uxd_progress`, `mj_cover_download_progress`.
- `mj_cover_publish_stop_flag`, `mj_cover_uxd_stop_flag`, `mj_cover_download_stop_flag`.
- `mj_cover_publish_process`, `mj_cover_uxd_process`, `mj_cover_download_process` (and any manager/status refs used for sync).
- Optional: “Run full automated” for cover: `mj_cover_automated_process`, `mj_cover_automated_shared`, etc.

In `_init_mj_session_state()` (or equivalent), initialize all `mj_cover_*` defaults the same way as the inside ones.

### 3.4 Reuse Existing Runners

**Do not duplicate** `run_publish_process`, `run_uxd_action_process`, `run_download_process`, or the automated runner. They already take:

- A list of prompts
- Button coordinates, browser port, output folder, stop flag, progress dicts, status dict

For the **Cover** section, call the **same** functions with:

- **Prompts:** `state.get("cover_prompts", [])` (or the edited list from the cover text area).
- **Output folder:** `Path(output_folder) / "cover"` (create the directory if needed).
- **Status/progress:** the `mj_cover_*` dicts.

So the only difference is **which** prompts and **which** folder and **which** session state keys are passed in. No new runner logic.

### 3.5 Image Generation UI Structure (Concrete)

In `features/image_generation/ui.py`, inside `render_image_generation_tab`:

1. **Shared:** System & Prerequisites, output folder (root) — unchanged. Batch mode (if any) can stay for **inside** only for now; cover can be single-design only.

2. **Block A — Inside (book pages)**  
   - Step indicator: 1. Publish → 2. Upscale/Vary → 3. Download (current behavior).  
   - “Midjourney Workflow” / “Midjourney Prompts” text area: `state.get("midjourney_prompts", [])`.  
   - Publish (and optional “Run full automated”) using `mj_status`, `mj_publish_*`, etc., and **output_folder** as the target.  
   - Upscale/Vary: same as today, using the same output_folder and `mj_uxd_*`, `mj_download_*`.  
   - Download: same, into `output_folder`.  
   - “Downloaded Images” gallery: `list_images_in_folder(output_folder)` and existing selection/evaluate/delete logic.

3. **Block B — Cover**  
   - Subheader, e.g. “Cover (background images)”.  
   - Step indicator for cover: same three steps, but driven by `mj_cover_status`.  
   - “Cover Prompts” text area: `state.get("cover_prompts", [])`; pre-filled from design, editable.  
   - Publish: same flow as inside but with `cover_prompts`, `output_folder_cover = output_folder / "cover"`, and `mj_cover_*` state.  
   - Upscale/Vary: same as inside but for cover (count, checkboxes, Run/Stop) using `mj_cover_*` and `output_folder_cover`.  
   - Download: same, into `output_folder_cover`.  
   - “Downloaded Cover Images” gallery: `list_images_in_folder(output_folder_cover)` with the same gallery/selection/delete pattern as inside (reuse or factor a shared gallery component if helpful).

4. **Save design package**  
   - When the user clicks “Save design” (from either section or a single shared button):
     - If the implementation currently copies from one folder: extend to **two sources** — e.g. copy `output_folder` → package root (inside images) and `output_folder/cover` → `package/cover` (cover images).  
   - So: **one** design package folder; **inside** images at package root; **cover** images in `package/cover`.  
   - Persisted state (design.json) already includes `cover_prompts`; no extra persistence for “which images are cover” beyond folder layout.

### 3.6 Batch Mode (Optional)

- Current batch mode runs **inside** prompts for multiple designs, each in its own subfolder.  
- **Recommendation for v1:** Do **not** add batch for cover; cover workflow is **single-design** only. The user selects one design and runs Publish → Upscale/Vary → Download for cover prompts in that design’s (cover) subfolder.  
- Later, you could add “Run cover for all selected designs” that, for each design, sets output to `design_subfolder/cover` and runs the same publish/uxd/download flow for that design’s `cover_prompts`.

---

## 4. Summary of Files to Touch

| Area | Files |
|------|--------|
| **State** | `core/state.py` — add cover_prompts, cover_prompts_attempts, cover_prompts_score, cover_prompts_passed, cover_prompts_status. |
| **Constants** | `features/design_generation/constants.py` — e.g. COVER_PROMPTS_COUNT. |
| **Content tools** | `features/design_generation/tools/content_tools.py` — _generate_cover_prompts_internal, generate_and_refine_cover_prompts; optional regenerate_cover_prompts. |
| **Evaluator** | `features/design_generation/agents/evaluator.py` — evaluate_cover_prompts + cover-specific prompt/criteria. |
| **Workflow** | `features/design_generation/workflow.py` — concept path: add cover step; agent path: add tool + result extraction; run_design_step_for_concept: add cover_prompts step; initial state: add cover_* keys. |
| **Executor** | `features/design_generation/agents/executor.py` — add generate_and_refine_cover_prompts to tools and system prompt (if agent path is used). |
| **Design UI** | `features/design_generation/ui.py` — checklist + cover prompts block (display, edit, save); include in download/export. |
| **Image Gen UI** | `features/image_generation/ui.py` — init mj_cover_* state; add Block B (Cover) with prompts, Publish, Upscale/Vary, Download, gallery; wire Save design to copy both root and cover subfolder. |
| **Persistence** | `core/persistence.py` — save_design_package (and create if needed) to copy both inside folder and cover subfolder into package; load already gets full state. |

---

## 5. Recommendation and Order of Work

1. **State + constants** — Add cover fields and COVER_PROMPTS_COUNT so nothing breaks when missing.  
2. **Evaluator** — Implement `evaluate_cover_prompts` and cover-specific criteria so the generator has a target.  
3. **Content tools** — Implement `_generate_cover_prompts_internal` and `generate_and_refine_cover_prompts`.  
4. **Workflow** — Integrate cover step in concept path (and agent/step-wise if used).  
5. **Design UI** — Show and edit cover prompts, show score/status.  
6. **Image Gen UI** — Add cover section and mj_cover_* state; wire same runners with cover prompts and cover folder; add cover gallery; extend Save design to include cover subfolder.  
7. **Persistence** — Ensure design package save/load handles cover folder and state.  
8. **Tests** — Unit tests for evaluate_cover_prompts and for cover prompt generation; optional E2E for “generate design → see cover prompts → publish cover → download to cover folder”.

This keeps **inside** behavior unchanged, adds **cover** as a parallel track with the same capabilities (generate → evaluate → publish → upscale → download → select), and keeps the codebase consistent and maintainable.
