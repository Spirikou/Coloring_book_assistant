# Architecture

## Entry Points

- **app.py** – Streamlit multi-tab workflow (run: `uv run streamlit run app.py`)
- **main.py** – CLI for design generation only (run: `uv run python main.py "theme description"`)

## Module Layout

| Module | Purpose |
|--------|---------|
| core/ | Shared infrastructure: state schema, persistence |
| features/design_generation/ | Design generation: agents, tools, workflow, UI |
| features/image_generation/ | Image generation: Midjourney workflow (Publish/Upscale/Download), folder monitor, image selection grid |
| workflows/canva/ | Canva design creation workflow |
| workflows/pinterest/ | Pinterest publishing workflow |
| integrations/canva/ | Canva browser automation |
| integrations/pinterest/ | Pinterest browser automation |
| integrations/midjourney/ | Midjourney web automation (Playwright), config, CLI (setup, record-coords) |
| ui/ | Streamlit tabs and components (guide, canva, pinterest) |
| utils/ | Compatibility shim (folder_monitor re-exports from features.image_generation.monitor) |

## Data Flow

```
Design Generation (main.py or app) --> workflow state (midjourney_prompts, title, etc.)
       |
       v
Image Generation tab --> Midjourney (Publish/Upscale/Download) --> images folder --> selected_images
       |
       v
Canva Design tab --> multi-page layout (browser)
       |
       v
Pinterest Publishing tab --> published pins (browser)
```

## State and Config

**State ownership**

- **core/state.py** – `ColoringBookState` TypedDict: design package, images, Pinterest, etc. Used as the app’s workflow state.
- **st.session_state.workflow_state** – Streamlit UI holds the current workflow state; tabs read/write it. No separate global state module; session state is the UI state.
- **integrations/midjourney/graph/state.py** – `AgentState` / `PromptTask` for the Midjourney LangGraph agent only.
- **integrations/pinterest/state_manager.py** – Pinterest-specific publishing state.

**Browser config**

- **core/browser_config.py** – Single source for **browser slots**: up to four slots (midjourney, pinterest, canva, unused), each with a CDP port. Provides `get_port_for_role(role)`, `load_slots()`, `save_slots()`, `test_connection(port)`, and `check_browser_connection(port)` (dict with `connected`, `port`, `error`). All UI and pipeline code should use these to decide which port to check or connect to.
- **integrations/midjourney/automation/browser_config.py** – Midjourney-specific browser paths and launch (reads port from root config or slot). **integrations/pinterest/config.py** and **integrations/canva/config.py** – Same pattern: browser type/paths/launch per integration; port for the app should come from `get_port_for_role(role)`.

**Pipeline runner**

- **core/pipeline_runner.py** – Runs pipeline steps (design, image, evaluate, canva, pinterest) in a subprocess. Uses `get_port_for_role("midjourney"|"canva"|"pinterest")` for browser pre-checks and passes that port into the integration. Step dependencies are loaded inside each step branch to avoid heavy imports at startup.

## Config and Output

- **config.py** – Centralized paths: `OUTPUT_DIR`, `SAVED_DESIGNS_DIR`, `SAVED_DESIGN_PACKAGES_DIR`, `PINTEREST_PUBLISH_DIR`, `GENERATED_IMAGES_DIR`
- **CB_OUTPUT_DIR** – Optional env var for the single output root. Default: project root. Set to e.g. `output` or a Google Drive folder path so all workflow outputs live in one place (and can sync to the cloud).
- Output structure (all under `OUTPUT_DIR`):
  - `saved_designs/` – Workflow state JSON files and `pipeline_templates/`
  - `saved_design_packages/` – Design packages (design.json, book_config, images, evaluations)
  - `generated_images/` – Midjourney default output folder
  - `pinterest_publish/` – Pinterest config and `publish_YYYYMMDD_HHMMSS/` session folders
  - `config/` – Browser slots, jobs (from core/browser_config, core/jobs)

## Path handling

Use `pathlib.Path` for folder and file paths inside application logic (iterating, joining, checking existence). Convert to `str` at persistence boundaries (e.g. JSON, DB) and when passing paths to UI or external APIs that expect strings. This keeps behaviour consistent across platforms and avoids mixing Path/str in the same flow.

## Migration from Previous Layout

If you had `saved_designs/` or `pinterest_publish/` at project root and want to use a dedicated output folder, set `CB_OUTPUT_DIR=output` (or your path) and move existing data into that folder.
