# Image Lightbox (Option 2) — Implementation Plan

## Goal

Replace the current Streamlit dialog for image detail with an **in-page lightbox**: dark overlay, centered image sized to the screen, with actions (Prev/Next, Delete, Select, Close) and keyboard navigation (left/right arrows), all within Streamlit.

## Current State

- **Gallery:** `_render_downloaded_images_gallery()` shows a 4-column grid; each image has a "View" button that opens `_image_detail_dialog()`.
- **Detail:** `@st.dialog("Image Detail", width="large")` shows one image, caption, and buttons (Prev, Next, Delete, Close). No overlay, no keyboard, no Select in the dialog.
- **Selection:** Checkboxes in the grid; "Delete selected (N)" and "Delete all" in the gallery. Selection stored in `st.session_state["mj_selected_images"][folder]`.

## Target Behavior

1. **Open lightbox:** Click "View" (or the image area) → lightbox opens (no `st.dialog`).
2. **Lightbox UI:** Full-viewport dark overlay; image centered and sized to fit (e.g. max 90vw × 85vh); caption and controls visible.
3. **Actions in lightbox:** Prev, Next, Close, Delete (current image), Select/Deselect (current image), optional "Delete selected" when any are selected.
4. **Keyboard:** Left/Right arrow keys move to previous/next image when lightbox is open.
5. **Persistence:** Same session state as today; selection and delete logic reused.

## Implementation Steps

### 1. Session state for lightbox

- In `_init_mj_session_state()`, add:
  - `mj_lightbox_open` (bool, default False)
  - `mj_lightbox_index` (int, default 0)
  - `mj_lightbox_folder` (str, default "")

### 2. Handle lightbox actions via query params

- At the start of `render_image_generation_tab()` (after `_init_mj_session_state()`), read `st.query_params.get("lightbox_action")`.
- If present and lightbox was open (`mj_lightbox_folder` set), load paths for that folder and:
  - **prev** → decrement `mj_lightbox_index`, clamp to 0.
  - **next** → increment `mj_lightbox_index`, clamp to `len(paths)-1`.
  - **close** → set `mj_lightbox_open = False`.
  - **delete** → call `_do_delete_one(current_path, folder, mj_status)`; if paths become empty close lightbox, else adjust index (e.g. don’t go out of range).
  - **select** → set `st.session_state[f"mj_sel_{current_filename}"] = True` and update `mj_selected_images[folder]`.
  - **deselect** → remove `mj_sel_{filename}` and update `mj_selected_images[folder]`.
  - **delete_selected** → same logic as gallery "Delete selected" (delete all selected in folder, prune evaluations, update `downloaded_paths` and selection); then close lightbox or adjust index.
- After processing, clear the query param (e.g. `st.query_params["lightbox_action"] = None`) and `st.rerun()` so the URL is clean.

### 3. Open lightbox from gallery (no dialog)

- In `_render_downloaded_images_gallery()`, when the user clicks "View":
  - Set `st.session_state.mj_lightbox_open = True`, `mj_lightbox_index = img_index`, `mj_lightbox_folder = str(folder)`.
  - Call `st.rerun()`.
  - Do **not** call `_image_detail_dialog()`.

### 4. Render lightbox (HTML overlay + image + controls)

- In `_render_downloaded_images_gallery()`, after the gallery header/toolbar and before the grid, **if** `mj_lightbox_open` and `mj_lightbox_folder == str(folder)`:
  - Get `paths = list_images_in_folder(folder)` (already available) and `idx = st.session_state.mj_lightbox_index`; clamp `idx` to valid range.
  - Load current image file as bytes and Base64-encode (for PNG/JPEG use correct MIME type).
  - Build HTML:
    - Outer div: `position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); z-index: 9999; display: flex; flex-direction: column; align-items: center; justify-content: center;`.
    - Inner content: caption (e.g. filename and "i / N"), image `<img src="data:image/png;base64,..." style="max-width: 90vw; max-height: 85vh; object-fit: contain;">`, and a control bar with links styled as buttons.
  - Control links: `href="?lightbox_action=prev"` (only if idx > 0), `?lightbox_action=next` (only if idx < len(paths)-1), `?lightbox_action=close"`, `?lightbox_action=delete"`, `?lightbox_action=select"` or `?lightbox_action=deselect"` (depending on whether current image is in selected set), and optionally `?lightbox_action=delete_selected"` (only if `len(selected_set) > 0`). Use same query param key so one action per click.
  - Inject via `st.markdown(html, unsafe_allow_html=True)`.
- Ensure the control bar is visible (e.g. below or over the image with contrasting background).

### 5. Keyboard navigation (left/right)

- Add dependency: `streamlit-hotkeys` in `pyproject.toml`.
- When the lightbox is open, render the hotkeys component (e.g. in the same block that renders the lightbox) and bind "ArrowLeft" and "ArrowRight" (or "left"/"right" if the API uses that).
- In the same run, after rendering, if `hotkeys.pressed("left")` then set `mj_lightbox_index = max(0, idx - 1)` and `st.rerun()`; if `hotkeys.pressed("right")` then set `mj_lightbox_index = min(len(paths)-1, idx + 1)` and `st.rerun()`.
- This yields arrow-key navigation without leaving Streamlit.

### 6. Remove or repurpose old dialog

- Remove the call to `_image_detail_dialog()` from the View button path.
- Keep `_image_detail_dialog` as a fallback or remove it; if removed, delete the `@st.dialog` function and any references.

### 7. Optional: click image to open

- Streamlit does not allow making an image itself clickable without a button. Options:
  - Keep a single prominent "View" button under each thumbnail (current behavior).
  - Or use one button per card that wraps the whole card (image + caption) so the click target is larger; the button label can be "View" or empty with an icon.

## Files to Change

- `features/image_generation/ui.py`: session state init, query param handling in `render_image_generation_tab`, lightbox HTML rendering and hotkeys in `_render_downloaded_images_gallery`, View button behavior, remove dialog call.
- `pyproject.toml`: add `streamlit-hotkeys` (or equivalent) dependency.

## Testing

- Open Image Generation tab, ensure there are downloaded images.
- Click "View" on an image → lightbox appears with dark overlay and large image.
- Prev/Next (links and keyboard) → image changes.
- Close → lightbox closes.
- Delete → current image removed, lightbox shows next or closes.
- Select/Deselect → selection state matches gallery; "Delete selected" in lightbox works if implemented.
- Multiple design folders: open lightbox from one folder, close, open from another → correct folder and index.

## Risks / Fallbacks

- **Base64 image size:** Very large images may make the HTML heavy; consider resizing to max 2000px on the long side if needed.
- **streamlit-hotkeys:** If the package is problematic, fall back to link-only navigation (Prev/Next in the overlay).
- **Query param persistence:** Always clear `lightbox_action` after handling to avoid duplicate actions on refresh.
