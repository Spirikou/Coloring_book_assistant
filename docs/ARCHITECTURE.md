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

## Config and Output

- **config.py** – Centralized paths: `OUTPUT_DIR`, `SAVED_DESIGNS_DIR`, `PINTEREST_PUBLISH_DIR`, `GENERATED_IMAGES_DIR`
- **CB_OUTPUT_DIR** – Optional env var to override output root (default: `./output`)
- Output structure:
  - `output/saved_designs/` – Saved design JSON files
  - `output/generated_images/` – Midjourney-generated images (default for Image Generation tab)
  - `output/pinterest_publish/` – Pinterest publish folders

## Migration from Previous Layout

If you had `saved_designs/` or `pinterest_publish/` at project root, copy them to `output/saved_designs` and `output/pinterest_publish` respectively.
