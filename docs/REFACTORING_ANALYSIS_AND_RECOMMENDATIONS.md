# Refactoring Analysis and Recommendations

This document summarizes a codebase review of the Coloring Book Assistant: opportunities for refactoring, cleanup options, and a recommended path.

---

## 1. Executive Summary

The project is a **Streamlit-driven coloring-book pipeline** (design → image generation → Canva → Pinterest) with a CLI for design-only runs. The main refactoring opportunities are:

| Area | Issue | Impact |
|------|--------|--------|
| **Browser config** | Browser paths, launch commands, and connection checks are duplicated across core, Midjourney, Pinterest, and Canva. | Maintenance cost, risk of drift, confusing “which port” behavior. |
| **Port/slot consistency** | Pipeline and Orchestration tab sometimes ignore the slot configuration and use a single default port. | Users who configure separate slots (e.g. MJ 9222, Pinterest 9223) get wrong or inconsistent behavior. |
| **Stale UI copy** | Orchestration tab shows an outdated message when template save fails. | Confusing for users and developers. |
| **Documentation** | ARCHITECTURE.md does not describe browser config, state ownership, or pipeline runner. | Harder onboarding and refactoring. |
| **Naming / structure** | Two `image_utils` modules; optional lazy-import pattern in pipeline_runner. | Minor confusion and maintenance overhead. |

---

## 2. Detailed Findings

### 2.1 Browser configuration and connection (high impact)

**Current state**

- **core/browser_config.py**
  - Owns **slot** model and persistence (4 slots: midjourney, pinterest, canva, unused).
  - Provides `get_port_for_role(role)`, `test_connection(port)` returning `(bool, str)`.
  - Does **not** define browser executables or launch commands.

- **integrations/midjourney/automation/browser_config.py**
  - Defines `DEBUG_PORT` (from `get_midjourney_config()`), `BROWSER_TYPE`, `BROWSER_PATHS`, `BROWSER_USER_DATA_DIRS`, `get_browser_path()`, `get_browser_startup_command()`, `get_browser_startup_command_for_port(port)`.

- **integrations/pinterest/config.py**
  - Defines its own `DEBUG_PORT` (9222), `BROWSER_TYPE`, `BROWSER_PATHS`, `BROWSER_USER_DATA_DIRS`, `get_browser_path()`, `get_browser_startup_command()`.

- **integrations/canva/config.py**
  - Same pattern: own `BROWSER_*` and port.

So: **slot assignment** lives in core; **how to launch a browser and which binary/profile** is repeated in three places.

**Connection check duplication**

- **core/browser_config.py**: `test_connection(port)` → `(bool, str)` (TCP to localhost).
- **integrations/pinterest/browser_utils.py**: `check_browser_connection(port=None)` → `dict` (connected, port, error). Uses Pinterest `DEBUG_PORT` when `port is None`.
- **integrations/midjourney/automation/browser_utils.py**: Same dict-shaped API, uses Midjourney `DEBUG_PORT` when `port is None`.

Two separate modules implement the same TCP check and similar “launch browser” logic. The UI mixes:
- `core.browser_config.get_port_for_role(...)` for Canva/Pinterest tabs.
- `integrations.pinterest.browser_utils.check_browser_connection(port)` with that port.

So Canva/Pinterest tabs are slot-aware for the **port**, but the **check** and **launch** logic are duplicated and tied to integration-specific config.

### 2.2 Port/slot usage inconsistencies (high impact)

- **Orchestration tab** (`ui/tabs/orchestration_tab.py` ~269): Calls `check_browser_connection()` with **no port**. That uses whichever integration’s `browser_utils` is imported (Pinterest), so it always checks 9222 (or Pinterest’s `DEBUG_PORT`), not the slot for “image” or “canva” or “pinterest”.
- **Pipeline runner** (`core/pipeline_runner.py`):
  - Image step: uses `get_midjourney_config()["browser_debug_port"]` for the actual automation (correct for MJ), but `check_browser_connection()` with **no port** for the pre-check, so it uses Midjourney’s default port (9222). If the user’s MJ slot is 9222, this is fine; if they ever moved it, the pre-check would be wrong.
  - Canva step: calls `check_browser_connection()` with no port → Midjourney’s port (9222), not `get_port_for_role("canva")`.
  - Pinterest step: same → not `get_port_for_role("pinterest")`.

So when the user configures different ports per role (e.g. Config tab), the pipeline and “Run pipeline” pre-check do not consistently use those slots for Canva/Pinterest (and for “image” the pre-check ignores slot).

### 2.3 Stale UI message (low effort, high clarity)

In **ui/tabs/orchestration_tab.py** (around 314–315), on `ImportError` when saving a custom template, the app shows:

```text
"Custom template saving will be available after pipeline_persistence is implemented."
```

But **core/pipeline_persistence.py** already implements `save_custom_template`. The message is outdated and misleading. On real failure (e.g. permission or path), users should see the actual error.

### 2.4 Documentation gaps

**docs/ARCHITECTURE.md** describes entry points, module layout, data flow, and output paths but does not cover:

- Where **browser** configuration lives (core slots vs integration-specific paths/ports/launch).
- Where **state** lives: `core.state.ColoringBookState` vs Midjourney graph state vs Pinterest state vs `st.session_state.workflow_state`.
- How the **pipeline runner** loads steps and which config it uses (e.g. browser port per step).

Adding a short “State and config” section would make refactoring and onboarding safer.

### 2.5 Naming and small cleanups

- **Two `image_utils` modules**: `features/image_generation/image_utils.py` (feature-level image helpers) and `integrations/midjourney/utils/image_utils.py` (e.g. `build_image_path` for MJ). Only the Midjourney controller imports the latter. Low risk of conflict but two same-named modules can confuse. Optional: rename or document clearly.
- **Pipeline runner**: Many `from ... import ...` inside step branches to avoid loading heavy deps at startup. Optional: introduce a small step registry (step_id → loader/factory) so the pattern is consistent and the file easier to maintain.

---

## 3. Options

### Option A – Minimal cleanup (low effort)

- Fix the **stale message** in the Orchestration tab: on save failure, show the real exception (e.g. `str(e)`) or a generic “Save failed: …” and remove the “pipeline_persistence is implemented” text.
- Update **ARCHITECTURE.md** with a short “State and config” subsection (browser slots vs integration config, state ownership).
- **Align pipeline and Orchestration with slot ports** without moving code:
  - In `core/pipeline_runner.py`, for the **image** step: keep using `get_midjourney_config()["browser_debug_port"]` for automation; for the pre-check, use `get_port_for_role("midjourney")` and call a single connection check with that port.
  - For **canva** and **pinterest** steps: use `get_port_for_role("canva")` and `get_port_for_role("pinterest")` for the pre-check and pass that port into whatever connection check is used (see Option B for unifying the check).
  - In **orchestration_tab**: for “Run pipeline”, if `needs_browser`, determine which roles are needed (image → midjourney, canva → canva, pinterest → pinterest) and check each required role’s port via `get_port_for_role` + one shared connection check.

**Pros:** Small, localized changes; immediate correctness for slot-aware behavior.  
**Cons:** Duplication of browser paths and connection logic remains.

---

### Option B – Unify connection check and use slots everywhere (medium effort)

- Introduce a **single** connection-check API used by all call sites:
  - Either extend **core/browser_config.py** with a small helper that returns the same dict shape as today’s `check_browser_connection` (e.g. `check_browser_connection(port) -> dict` with `connected`, `port`, `error`), or add **core/browser_utils.py** that implements it and have both Pinterest and Midjourney `browser_utils` delegate to it.
- Replace all call sites so they pass an explicit **port**:
  - UI (Orchestration, Canva tab, Pinterest tab, shared_checks, Image Gen): get port from `get_port_for_role(role)` and call the shared check with that port.
  - Pipeline runner: same for image/canva/pinterest (pre-check and, where applicable, automation).
- Deprecate or remove the “default port when `port is None`” behavior so the only source of truth for “which port for which role” is **core/browser_config** slots.

**Pros:** One place for “is something listening on this port?”; consistent slot-aware behavior everywhere.  
**Cons:** Still two sets of browser paths/launch (Midjourney vs Pinterest/Canva) unless you do Option C.

---

### Option C – Centralize browser executable and launch config (higher effort)

- Move **BROWSER_TYPE**, **BROWSER_PATHS**, **BROWSER_USER_DATA_DIRS**, **get_browser_path()**, and a generic **get_browser_startup_command(port)** (and optionally **get_browser_startup_command_for_port(port)**) into one place:
  - Either **config.py** (with a small “browser” subsection) or **core/browser_config.py** (or split into `core/browser_slots.py` + `core/browser_launch.py`).
- **integrations/midjourney/automation/browser_config.py**: keep only Midjourney-specific overrides (e.g. waits, coordinates, automation timeouts) and import shared browser path/launch from core (or config).
- **integrations/pinterest/config.py** and **integrations/canva/config.py**: keep only integration-specific options (Pinterest: selectors, timing; Canva: coordinates, etc.) and import shared browser/launch from the same central place.
- Optionally, move **launch_browser_for_port(port)** into core (or a single browser_utils in core) so only one implementation launches a browser; integrations can call it with the slot port.

**Pros:** One place to change browser type or paths; consistent behavior across MJ/Pinterest/Canva.  
**Cons:** Larger refactor; need to ensure Midjourney/Pinterest/Canva still get the right profile and port (e.g. profile per role or per port).

---

### Option D – Full browser consolidation (largest)

- One **core** module (or two: slots + launch/connection) that owns:
  - Slot definitions and persistence (already in core).
  - Browser paths, type, user data dirs, and launch command (by port or by role).
  - Connection check and optional “launch browser for port”.
- Integrations only supply overrides (e.g. Midjourney waits/coords, Pinterest selectors). No duplicate BROWSER_* or DEBUG_PORT in integrations; they use `get_port_for_role` and the shared launch/check APIs.

**Pros:** Single source of truth for everything “browser”; clear mental model.  
**Cons:** Most work; need to test all flows (CLI Midjourney, Streamlit MJ, Canva, Pinterest, pipeline runner).

---

## 4. Recommendation

**Recommended path: do Option A + Option B, then consider Option C later.**

1. **Do Option A (minimal cleanup)**
   - Fix the Orchestration tab save-failure message.
   - Document state and config in ARCHITECTURE.md.
   - Use slot ports in pipeline runner and Orchestration “Run pipeline” so that image/canva/pinterest steps and pre-checks use `get_port_for_role(...)`.

2. **Do Option B (unify connection check)**
   - Add a single “check if something is listening on this port” API (dict result) in **core** (e.g. in **core/browser_config.py** or **core/browser_utils.py**).
   - Have **integrations/pinterest/browser_utils** and **integrations/midjourney/automation/browser_utils** call that for the TCP check (or remove their duplicate and use core from all call sites).
   - Ensure every call site passes an explicit port from `get_port_for_role(role)` (or equivalent) and remove “default port when None” semantics for the shared check.

3. **Defer Option C/D** until you need to change browser type or paths in one place, or until you add more integrations. Then centralize browser executable and launch in core (Option C) or do the full consolidation (Option D).

**Optional (as time allows):**
- Rename or document the two `image_utils` modules to avoid confusion.
- Add a small step-loader registry in **core/pipeline_runner.py** for consistency and maintainability.

---

## 5. Concretes (for Option A + B)

| # | Task | Files |
|---|------|--------|
| 1 | Fix Orchestration tab save-failure message | `ui/tabs/orchestration_tab.py` |
| 2 | Add “State and config” to ARCHITECTURE.md | `docs/ARCHITECTURE.md` |
| 3 | In pipeline_runner, use `get_port_for_role("midjourney")` for image-step pre-check; use `get_port_for_role("canva")` / `get_port_for_role("pinterest")` for canva/pinterest pre-checks | `core/pipeline_runner.py` |
| 4 | In orchestration_tab “Run pipeline”, check browser for each required role (midjourney/canva/pinterest) via `get_port_for_role` + shared connection check | `ui/tabs/orchestration_tab.py` |
| 5 | Add `check_browser_connection(port) -> dict` in core (or core/browser_utils.py) and use it from pipeline_runner, orchestration_tab, shared_checks, canva_tab, pinterest_tab, image gen UI; make Midjourney/Pinterest browser_utils delegate to it | `core/browser_config.py` or new `core/browser_utils.py`, then `integrations/.../browser_utils.py`, `core/pipeline_runner.py`, `ui/...` |
| 6 | Remove “port is None → default port” behavior from shared check; all callers pass explicit port from slots | Same as above |

This gives you consistent slot-aware behavior and one place for the connection check, without yet refactoring browser paths and launch commands (Option C/D).
