# Parallelisation implementation – review and alternatives

## 1. What you’re seeing

- **Config tab**: No high-level job progress. It only shows browser slots (role, port, label, test, launch) and save/reset. Job progress lives only on the **Progress** tab.
- **Canva / Pinterest “greyed out”**: The **Start** buttons (Start Design Creation, Start Publishing) are disabled because the app thinks the browser is “not connected”. That check uses a **single fixed port (9222)**. If you launched browsers from Config on 9223 (Pinterest) and 9224 (Canva), those tabs still check 9222, so they stay “not connected” and the buttons stay disabled.
- **Design generation “obscuring” Image Generation**: Design generation runs **synchronously** in the main Streamlit script under `st.spinner(...)`. The script blocks until the agent finishes, so you can’t interact with other tabs or see live Image Gen progress while design gen is running.

---

## 2. Root causes (from the code)

### 2.1 Config tab has no job progress

- **Config tab** (`ui/tabs/config_tab.py`): Renders only browser slots and save/reset. It does **not** call `core.jobs.list_jobs()` or show running/queued jobs per design.
- **Progress tab** (`ui/tabs/progress_tab.py`): This is where designs, jobs, and browser slots are shown. So “high-level progress on jobs ongoing for each design” exists, but on **Progress**, not **Config**.

### 2.2 Canva and Pinterest use a single port (9222)

- **Canva** and **Pinterest** get browser status from `ui/components/shared_checks.py` → `integrations.pinterest.browser_utils.check_browser_connection()`. When no port is passed, it uses **Pinterest’s `DEBUG_PORT` = 9222**.
- So both tabs only ever check **port 9222**. They never use the per-slot ports from the Config (e.g. 9223 for Pinterest, 9224 for Canva).
- If you only have browsers on 9223 and 9224 (launched from Config), 9222 has no browser → “not connected” → `can_create` / `can_publish` stay false → buttons disabled (“greyed out”).

Relevant call sites:

- `ui/tabs/canva_tab.py`: `check_browser_connection()` (no port).
- `ui/tabs/pinterest_tab.py`: `check_browser_connection()` (no port).
- `ui/components/shared_checks.py`: `check_browser_connection()` (no port) when refreshing/continuing.

So **no other job can run “in parallel”** from those tabs until the browser check uses the right port per tab.

### 2.3 Single “current design” (`workflow_state`)

- The app has **one** `st.session_state.workflow_state`. That is the “current design” for Image Gen, Canva, and Pinterest.
- If `workflow_state` is `None`, Image Gen / Canva / Pinterest show “Generate a design package first” or a design selector. So you must load exactly one design to use any of those tabs.
- You cannot have “Image Gen for Design A” and “Canva for Design B” at the same time in the UI: whichever design is in `workflow_state` is the one all tabs use. Parallel work on **different designs** would require either a design selector per tab or multiple “loaded” designs.

### 2.4 Design generation blocks the script

- In `features/design_generation/ui.py`, “Generate” runs `run_coloring_book_agent(user_request)` inside `with st.spinner(...)` in the **main** Streamlit run. No subprocess.
- The script blocks until the agent returns, so the rest of the app (including Image Gen tab) doesn’t update until design gen finishes. That’s why it “obscures” the view: you’re stuck on a blocking spinner.

---

## 3. Proposed alternatives (before implementing)

### 3.1 Config tab: show high-level job progress

**Options:**

- **A) Add a compact “Current jobs” section to Config**  
  At the top of the Config tab, add a small block that:
  - Calls `core.jobs.list_jobs()` and optionally `core.persistence.list_design_packages()`.
  - Shows running and recently queued jobs (e.g. “Image gen: Design X – running”, “Pinterest: Design Y – queued”).
  - Keeps Config as the place where you manage slots **and** see at a glance what’s running.

- **B) Keep Progress as the only job view and add a link**  
  Leave job details on the Progress tab only, and in Config add a short line: “See job progress in the **Progress** tab.” No duplication.

- **C) Merge Config and Progress**  
  One “Config & progress” tab: slots + launch at top, then the same designs/jobs/slots summary that Progress has. Fewer tabs, one place for “setup and status”.

**Recommendation:** **A** – add a compact “Current jobs” section at the top of Config so you see “what’s running per design” without leaving Config. Progress tab can stay as the full view.

---

### 3.2 Canva and Pinterest: use slot ports so they’re not greyed out

**Options:**

- **A) Use slot port by role in Canva/Pinterest**  
  - In `core.browser_config`, add a helper, e.g. `get_port_for_role(role: str) -> int`, that returns the port of the first slot with that role (or 9222 if none).
  - In Canva tab (and any shared checks used by Canva), call `check_browser_connection(get_port_for_role("canva"))` and store that in `state["browser_status"]`.
  - Same for Pinterest: use `get_port_for_role("pinterest")` (and handle multiple Pinterest slots if you ever support them, e.g. first one).
  - “Launch” in Config already starts a browser on the slot’s port; after this change, Canva/Pinterest would check that same port and show “connected”, so Start buttons are no longer greyed out when only 9223/9224 are in use.

- **B) Let the user pick a “browser slot” in each tab**  
  Canva/Pinterest tabs get a dropdown of slots (e.g. “Slot 1 – Midjourney (9222)”, “Slot 3 – Canva (9224)”). The chosen slot’s port is used for `check_browser_connection(port)`. More flexible, more UI.

- **C) Single port 9222 for all**  
  Don’t use Config slots for Canva/Pinterest; keep 9222 only and document that “Pinterest/Canva must use the browser on 9222”. No code change for ports; you still can’t run them in parallel with MJ on 9222 without multiple browsers on the same port (not supported).

**Recommendation:** **A** – minimal change, consistent with “one slot per role” (midjourney, pinterest, canva). Canva and Pinterest tabs then work with the browsers you launch from Config on their assigned ports.

---

### 3.3 Design generation: don’t block the whole app

**Options:**

- **A) Run design generation in a subprocess (like the pipeline)**  
  On “Generate”, start a subprocess that runs `run_coloring_book_agent`, and in the main app poll a shared state (e.g. file or `multiprocessing.Manager`) for status/progress. The UI keeps rerunning and other tabs stay usable. When design gen finishes, load the result into `workflow_state`. More work; consistent with Orchestration pipeline.

- **B) Keep blocking but improve feedback**  
  Keep the current blocking call; add a clear message under the spinner, e.g. “Design generation in progress – you can switch tabs, but other tabs won’t update until this finishes.” No parallel execution; just sets expectations.

- **C) Background thread**  
  Run the agent in a thread and poll `workflow_state` / a flag from the main script. Risk: many LLM/agent libs are not thread-safe; Streamlit reruns can be tricky with threads. Not recommended unless you’re sure of the stack.

**Recommendation:** **B** for now (simple, no new process model). If you later want true “design gen in parallel with others,” implement **A** and reuse the same pattern as the pipeline runner.

---

### 3.4 Multiple designs in parallel (optional, bigger change)

- Today, only one design is “current” (`workflow_state`). To run e.g. “Image Gen for A” and “Canva for B” from the UI, you’d need:
  - Either a **design selector per tab** (Image Gen, Canva, Pinterest each choose a design from `list_design_packages()`), and pass that design’s path/state into the tab instead of a single global `workflow_state`,
  - Or a **multi-design “workspace”** (e.g. a list of loaded designs and “which design this tab is using”).
- This was explicitly left for a later phase. Recommendation: **don’t change it in this pass.** Fix ports and job visibility first; then you can still run one design at a time per tab, but at least Canva and Pinterest will be usable (not greyed out) when their slot’s browser is running.

---

## 4. Summary of recommended next steps

1. **Config tab**: Add a compact “Current jobs” section at the top (running + recent queued jobs per design) using `core.jobs` and optionally design packages.
2. **Canva / Pinterest**: Use the port from the browser slot for their role (`get_port_for_role("canva")` / `get_port_for_role("pinterest")`) when calling `check_browser_connection(port)` and when storing/reading `browser_status`, so Start buttons are enabled when the right browser is running.
3. **Design generation**: Keep current blocking behaviour; add a short note that the app won’t update other tabs until design gen finishes (or later, move design gen to a subprocess if you want true parallelism).

No change to the single `workflow_state` model in this round: one current design, but Canva and Pinterest will no longer be greyed out solely because they were checking the wrong port.
