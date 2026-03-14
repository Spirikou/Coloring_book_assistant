# Saving Assets to Google Drive – Design & Options

This doc maps where assets are created today and how you can (or could) use Google Drive with the project.

---

## Current approach: one output folder → Drive sync

**No code changes needed.** Set **`CB_OUTPUT_DIR`** to a folder that is synced by Google Drive for Desktop (e.g. `G:\My Drive\ColoringBookOutput` on Windows, or a path under your Drive mount). All workflow outputs (saved_designs, saved_design_packages, pinterest_publish, generated_images, config) live under that single root and sync to the cloud. The app writes to local paths; Drive for Desktop syncs the folder.

The sections below describe the exact paths used today and, if you later want **Drive API** as primary storage (e.g. open from another device without a local sync folder), a design for that.

---

## 1. What Gets Saved Today (and Where)

| Asset type | Location (config) | Written by | Contents |
|------------|-------------------|------------|----------|
| **Workflow state** | `SAVED_DESIGNS_DIR` / `saved_designs/` | `core/persistence.py` | JSON: title, description, prompts, messages, paths |
| **Design packages** | `SAVED_DESIGN_PACKAGES_DIR` / `saved_design_packages/` | `core/persistence.py` | Folder per design: `design.json`, `book_config.json`, images, `image_evaluations.json` |
| **Generated images** | `GENERATED_IMAGES_DIR` / `generated_images/` | Midjourney integration | Downloaded Midjourney images (by prompt/attempt) |
| **Pinterest publish** | `PINTEREST_PUBLISH_DIR` / `pinterest_publish/` | `workflows/pinterest/publisher.py`, persistence | `publish_YYYYMMDD_HHMMSS/`: images, `book_config.json`, `published_pins.json` |
| **Pinterest config** | `PINTEREST_PUBLISH_DIR/pinterest_config.json` | `core/persistence.py` | Board name, images folder path |
| **Pipeline templates** | `SAVED_DESIGNS_DIR/pipeline_templates/` | `core/pipeline_persistence.py` | Custom pipeline step JSONs |
| **Image evaluations** | Inside any images folder | `features/image_generation/agents/evaluator.py` | `image_evaluations.json` |
| **Design report (CLI)** | `output_dir` from tools | `features/design_generation/tools/user_tools.py` | `coloring_book_*.json` |

All of these currently use **local paths** derived from `OUTPUT_DIR` (or `CB_OUTPUT_DIR`). Reading/writing is via `open()`, `Path`, `shutil.copy2`, and directory listing.

---

## 2. High-Level Options

### Option A: Google Drive for Desktop (sync only)

- **Idea:** Keep the app unchanged. Set `CB_OUTPUT_DIR` to a folder inside your Google Drive mount (e.g. `G:\My Drive\ColoringBookOutput` on Windows).
- **Pros:** No code changes; Drive syncs files automatically.
- **Cons:** Requires Drive for Desktop installed and that folder always in sync; paths are still “local”; no multi-device “open from Drive” unless you open the same mount.

### Option B: Drive API as primary storage

- **Idea:** Replace local file I/O with Google Drive API: create folders, upload files, list children, download file bytes when the app needs to read.
- **Pros:** True cloud storage; same assets available from any machine with credentials; no local sync needed.
- **Cons:** More code; need to handle auth (OAuth), rate limits, and offline/errors; listing and “folder” semantics are different (Drive has no real folders, only parent IDs).

### Option C: Hybrid (local + optional mirror to Drive)

- **Idea:** Keep writing to local (or a temp) path for speed and simplicity; after each “save” (workflow state, design package, publish folder, etc.), optionally upload that path (or a zip) to a Drive folder.
- **Pros:** Fast local UX; backup/mirror on Drive; can evolve toward “open from Drive” later.
- **Cons:** Two sources of truth unless you treat Drive as read-only backup; need clear rules for “which is canonical.”

---

## 3. Recommended Direction: Storage abstraction + Drive backend

A clean way to support Drive without rewriting every caller is to introduce a **small storage abstraction** and then add a **Google Drive backend** (while keeping a **local backend** for current behavior).

### 3.1 Storage abstraction (new module)

Introduce a thin interface that the rest of the app uses instead of raw `open()` / `Path` / `shutil` for “asset” operations:

- **Write:** “Save this file (bytes or path) under key/path in the current output root.”
- **Read:** “Return bytes or a local temp path for this key.”
- **List:** “List keys/paths under a prefix (e.g. `saved_designs/`, `saved_design_packages/DesignName/`).”
- **Delete:** “Remove a file or a tree.”

Optional: **Sync from local to Drive** (e.g. after each save) so you can start with “local primary + Drive mirror” and later flip to “Drive primary” by switching the backend.

### 3.2 Where to plug it in

- **config.py**  
  - Keep `OUTPUT_DIR` and existing dir constants.  
  - Add something like `STORAGE_BACKEND = "local" | "gdrive"` (e.g. from env `CB_STORAGE_BACKEND`) and, for Drive, `GDRIVE_ROOT_FOLDER_ID` or a well-known folder name under which you create `saved_designs`, `generated_images`, etc.

- **core/persistence.py**  
  - Replace direct `open(...)/Path` usage with the storage abstraction for:
    - workflow state save/load/list/delete,
    - Pinterest config,
    - `book_config.json` in images folders,
    - publish sessions (list/load config/delete session/image),
    - design packages (create/save/list/load/delete).
  - For “save design package” you’d: write `design.json` and `book_config.json` via the abstraction, and upload image files (and optional `image_evaluations.json`) under the same logical folder in Drive.

- **core/pipeline_persistence.py**  
  - Use the abstraction for pipeline template save/list/load/delete (paths under `saved_designs/pipeline_templates/`).

- **workflows/pinterest/publisher.py**  
  - When “preparing publish folder,” either write to the abstraction (Drive) or keep writing to a local path and then “sync this folder” to Drive (hybrid).

- **integrations/midjourney**  
  - Midjourney downloads go to a **local** directory (browser/Playwright need a real path). So:
    - Keep downloads in a local dir (e.g. `GENERATED_IMAGES_DIR` or a temp dir).
    - After a batch completes, **upload** that directory (or its new files) to Drive under e.g. `generated_images/<run_id>/` so “generated images” are also in Drive.

- **features/image_generation/agents/evaluator.py**  
  - `image_evaluations.json` lives “in the images folder.” If that folder is represented in Drive, the evaluator should write via the storage abstraction (or write locally and then sync that folder to Drive).

- **features/design_generation/tools/user_tools.py**  
  - The report save path should go through the same abstraction (e.g. under `saved_designs/` or a dedicated `reports/` prefix) so reports also land on Drive when using the Drive backend.

### 3.3 Google Drive backend (new module)

- **Auth:** Use a service account (for a “bot” user) or OAuth (for “my personal Drive”).  
  - Service account: JSON key, then share the target Drive folder with the service account email.  
  - OAuth: `google-auth-oauthlib` + `google-api-python-client`; store refresh token in a known location (or env).
- **Layout:** One root folder (by ID or name). Under it create the same logical tree: e.g. `saved_designs/`, `saved_design_packages/<slug>/`, `generated_images/`, `pinterest_publish/publish_*/`, `pinterest_config.json`, etc.
- **Operations:**  
  - Create folder by path (e.g. `saved_design_packages/MyBook_20250108/`).  
  - Upload file: path → Drive file in the right parent.  
  - List: list children of a folder ID; filter by name/prefix if needed.  
  - Download: get file bytes and return to caller (or write to a temp file and return temp path so existing code that expects a path keeps working).  
  - Delete: move to trash or delete permanently.
- **Rate limits / retries:** Use exponential backoff and respect Drive API quotas.

### 3.4 Environment and credentials

- `CB_STORAGE_BACKEND=local` (default) or `gdrive`.
- For Drive:
  - `GDRIVE_CREDENTIALS_JSON` path to service account JSON, **or** use OAuth and store refresh token (e.g. `GDRIVE_TOKEN_JSON`).
  - `GDRIVE_ROOT_FOLDER_ID` (preferred) or `GDRIVE_ROOT_FOLDER_NAME` to create/find the root folder.

Do **not** commit credentials; add `*credentials*.json`, `*token*.json` to `.gitignore` and document in README.

---

## 4. Implementation order (if you adopt this)

1. **Add storage abstraction**  
   - New module, e.g. `core/storage.py`: interface + `LocalStorageBackend` that uses `OUTPUT_DIR` and current path layout.  
   - No new dependencies yet.

2. **Switch persistence to the abstraction**  
   - Refactor `core/persistence.py` and `core/pipeline_persistence.py` to use it; keep behavior identical with `STORAGE_BACKEND=local`.  
   - Tests should still pass (mock or temp dir for storage).

3. **Add Google Drive backend**  
   - New module, e.g. `core/gdrive_storage.py`, using `google-api-python-client` and `google-auth`.  
   - Implement same interface: create folder by path, upload, list, download, delete.  
   - Map “path” to Drive folder hierarchy and file names.

4. **Wire config and Midjourney**  
   - In config, set backend from env; in persistence, instantiate the right backend.  
   - For Midjourney: keep local download dir; add a “sync this folder to Drive” step after generation (or a background job).

5. **Pinterest and evaluator**  
   - Publisher and evaluator use the abstraction for any path they write/read under the output tree so publish sessions and image_evaluations live on Drive when backend is Drive.

6. **Docs and env example**  
   - Document `CB_STORAGE_BACKEND`, `GDRIVE_*`, and how to get credentials in README or `docs/SETUP.md`; add `.env.example` with placeholder vars.

---

## 5. Summary

- **Minimal change:** Use **Option A** (point `CB_OUTPUT_DIR` at a Drive-for-Desktop folder).  
- **Proper cloud integration:** Use **Option B/C** via a **storage abstraction** and a **Google Drive backend**, so all assets (images, descriptions, prompts, configs, templates, reports) are stored under a single Drive root and the app stays agnostic of where bytes actually live.

If you tell me whether you prefer “local primary + Drive mirror” (C) or “Drive primary” (B), I can outline the exact function signatures for the storage interface and the Drive backend next (or draft the `core/storage.py` skeleton).
