"""Image generation tab UI.

Section A: Midjourney workflow (Publish → Upscale/Vary → Download)
Section B: Downloaded images gallery
"""

from __future__ import annotations

import base64
import io
import os
import platform
import subprocess
import time
from pathlib import Path

import streamlit as st
from PIL import Image

from config import GENERATED_IMAGES_DIR, IMAGE_MIN_SCORE_THRESHOLD, get_midjourney_config
from features.image_generation.midjourney_runner import (
    run_automated_process,
    run_batch_automated_process,
    run_download_process,
    run_publish_process,
    run_uxd_action_process,
)
from features.image_generation.agents.evaluator import (
    evaluate_images_in_folder,
    load_image_evaluations,
    save_image_evaluations,
)
from features.image_generation.monitor import list_images_in_folder
from integrations.midjourney.automation.browser_utils import check_browser_connection
from integrations.midjourney.automation.health_check import run_health_checks

BROWSER_STATUS_KEY = "mj_browser_status"


def _design_to_subfolder_slug(design: dict, index: int, used_slugs: set[str] | None = None) -> str:
    """Generate a safe subfolder name for a design. Avoids duplicates via used_slugs."""
    used = used_slugs or set()

    def _slugify(s: str, max_len: int = 40) -> str:
        safe = "".join(c for c in s if c.isalnum() or c in (" ", "-", "_")).strip()
        safe = safe.replace(" ", "_")[:max_len].strip("_")
        return safe or f"concept_{index}"

    # Prefer title
    title = design.get("title", "").strip()
    if title:
        slug = _slugify(title)
        if slug and slug not in used:
            used.add(slug)
            return slug

    # Fallback: concept_source theme + style
    concept = design.get("concept_source", {})
    theme = concept.get("theme") or concept.get("theme_concept", "")
    style = concept.get("style") or concept.get("art_style", "")
    if theme or style:
        parts = [p for p in [_slugify(theme, 20), _slugify(style, 20)] if p]
        slug = "_".join(parts) if parts else ""
        if slug and slug not in used:
            used.add(slug)
            return slug

    # Last resort: concept_N
    base = f"concept_{index}"
    slug = base
    n = 1
    while slug in used:
        slug = f"{base}_{n}"
        n += 1
    used.add(slug)
    return slug


UPSCALE_VARY_OPTIONS = [
    ("upscale_subtle", "Upscale Subtle"),
    ("upscale_creative", "Upscale Creative"),
    ("vary_subtle", "Vary Subtle"),
    ("vary_strong", "Vary Strong"),
]


def _init_mj_session_state() -> None:
    """Initialize Midjourney session state with mj_ prefix."""
    defaults = {
        "mj_status": {
            "publish_status": "idle",
            "publish_error": "",
            "uxd_action_status": "idle",
            "uxd_action_error": "",
            "download_status": "idle",
            "download_error": "",
            "downloaded_paths": [],
        },
        "mj_publish_progress": {"elapsed": 0, "total": 0, "phase": "submit"},
        "mj_uxd_progress": {"elapsed": 0, "total": 0, "phase": "click"},
        "mj_download_progress": {"current": 0, "total": 0},
        "mj_publish_stop_flag": {"stop": False},
        "mj_uxd_stop_flag": {"stop": False},
        "mj_download_stop_flag": {"stop": False},
        "mj_publish_process": None,
        "mj_uxd_process": None,
        "mj_download_process": None,
        "mj_automated_process": None,
        "mj_automated_stop_flag": {"stop": False},
        "mj_automated_shared": {
            "publish_status": "idle",
            "publish_error": "",
            "uxd_action_status": "idle",
            "uxd_action_error": "",
            "download_status": "idle",
            "download_error": "",
            "downloaded_paths": [],
            "batch_current_index": 0,
            "batch_total": 0,
            "batch_current_design_title": "",
            "batch_results": [],
        },
        "mj_batch_selected_indices": [],
        "mj_design_images_folders": {},
        "mj_lightbox_open": False,
        "mj_lightbox_index": 0,
        # Cover workflow (separate from inside)
        "mj_cover_status": {
            "publish_status": "idle",
            "publish_error": "",
            "uxd_action_status": "idle",
            "uxd_action_error": "",
            "download_status": "idle",
            "download_error": "",
            "downloaded_paths": [],
        },
        "mj_cover_publish_progress": {"elapsed": 0, "total": 0, "phase": "submit"},
        "mj_cover_uxd_progress": {"elapsed": 0, "total": 0, "phase": "click"},
        "mj_cover_download_progress": {"current": 0, "total": 0},
        "mj_cover_publish_stop_flag": {"stop": False},
        "mj_cover_uxd_stop_flag": {"stop": False},
        "mj_cover_download_stop_flag": {"stop": False},
        "mj_cover_publish_process": None,
        "mj_cover_uxd_process": None,
        "mj_cover_download_process": None,
        "mj_cover_automated_process": None,
        "mj_cover_automated_stop_flag": {"stop": False},
        "mj_cover_automated_shared": {
            "publish_status": "idle",
            "publish_error": "",
            "uxd_action_status": "idle",
            "uxd_action_error": "",
            "download_status": "idle",
            "download_error": "",
            "downloaded_paths": [],
        },
        "mj_lightbox_folder": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _render_system_and_prerequisites(settings: dict) -> dict:
    """Render System & Prerequisites section. Returns browser_connected, debug_show_clicks."""
    port = settings.get("browser_debug_port", 9222)
    output_folder = Path(settings.get("output_folder", str(GENERATED_IMAGES_DIR)))

    health = run_health_checks(output_folder=output_folder, browser_port=port)
    has_issues = health.has_errors()

    if BROWSER_STATUS_KEY not in st.session_state:
        st.session_state[BROWSER_STATUS_KEY] = check_browser_connection(port)

    browser_status = st.session_state[BROWSER_STATUS_KEY]
    browser_connected = browser_status.get("connected", False)

    issue_count = sum(1 for c in health.checks if c.severity == "error" and not c.status)
    if not browser_connected:
        issue_count = max(issue_count, 1)

    col1, col2 = st.columns([4, 1])
    with col1:
        if issue_count == 0 and browser_connected:
            st.success("Ready")
        elif issue_count > 0:
            st.warning(f"{issue_count} issue(s) – expand for details")
        else:
            st.info("Complete prerequisites below")
    with col2:
        if st.button("Refresh", key="mj_refresh_system_btn", help="Refresh checks"):
            st.session_state[BROWSER_STATUS_KEY] = check_browser_connection(port)
            st.rerun()

    with st.expander("System & Prerequisites", expanded=has_issues or not browser_connected):
        st.markdown("**Checks completed**")
        summary_items = []
        for c in health.checks:
            status = "✓" if c.status else "✗"
            summary_items.append(f"• **{c.name}:** {status} {c.message}")
        if browser_connected:
            summary_items.append(
                f"• **Browser:** ✓ Connected on port {browser_status.get('port', port)}"
            )
        else:
            summary_items.append("• **Browser:** Not connected (port 9222)")
        st.caption("\n".join(summary_items))

        st.markdown("**Browser connection**")
        if browser_connected:
            st.success(f"Browser connected on port {port}")
            st.caption("Log in to Midjourney.com in the browser, then click Publish above.")
        else:
            st.warning("No browser detected on port 9222.")
            st.caption(
                "Use **Launch Browser** to start a dedicated automation window (separate profile, so it works even if Brave is already open). "
                "Log in to Midjourney.com in that window. Or start manually:"
            )
            from integrations.midjourney.automation.browser_config import get_browser_startup_command
            st.code(get_browser_startup_command(), language="powershell")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Check Browser", key="mj_check_browser_btn", width="stretch"):
                    st.session_state[BROWSER_STATUS_KEY] = check_browser_connection(port)
                    st.rerun()
            with col_b:
                from integrations.midjourney.automation.browser_utils import (
                    launch_browser_with_debugging,
                )

                if st.button("Launch Browser", key="mj_launch_browser_btn", width="stretch"):
                    with st.spinner("Launching..."):
                        result = launch_browser_with_debugging()
                        if result.get("success"):
                            st.session_state[BROWSER_STATUS_KEY] = check_browser_connection(port)
                            st.success(result["message"])
                        else:
                            st.error(result["message"])
                    st.rerun()

        st.divider()
        st.markdown("**Debug options**")
        debug_show_clicks = st.checkbox(
            "Show click overlays",
            value=settings.get("debug_show_clicks", False),
            key="mj_debug_show_clicks",
            help="Show red circle at click location before each coordinate-based click.",
        )

    return {"browser_connected": browser_connected, "debug_show_clicks": debug_show_clicks}


def _workflow_step_indicator(status: dict) -> None:
    """Render step indicator: 1. Publish → 2. Upscale/Vary → 3. Download."""
    pub = status.get("publish_status", "idle")
    uxd = status.get("uxd_action_status", "idle")
    dl = status.get("download_status", "idle")

    step1_done = pub in ("completed", "stopped")
    step2_done = uxd in ("completed", "stopped")
    step3_done = dl in ("completed", "stopped")
    step1_current = pub == "running" or (not step1_done and not step2_done)
    step2_current = step1_done and (uxd == "running" or (not step2_done and not step3_done))
    step3_current = step2_done and (dl == "running" or not step3_done)

    def _badge(label: str, done: bool, current: bool) -> str:
        if done:
            return f"**{label}** ✓"
        if current:
            return f"**{label}** ←"
        return label

    s1 = _badge("1. Publish", step1_done, step1_current)
    s2 = _badge("2. Upscale/Vary", step2_done, step2_current)
    s3 = _badge("3. Download", step3_done, step3_current)
    st.caption(f"{s1} → {s2} → {s3}")


def _next_step_guidance(status: dict, section: str | None = None) -> None:
    """Render next-step guidance."""
    pub = status.get("publish_status", "idle")
    uxd = status.get("uxd_action_status", "idle")
    dl = status.get("download_status", "idle")

    if pub == "running" or uxd == "running":
        return
    if pub == "completed" and uxd in ("idle", "completed", "error", "stopped"):
        msg, target = "Select Upscale/Vary actions and Run.", "upscale"
    elif uxd in ("completed", "stopped") and dl in ("idle", "completed", "error", "stopped"):
        msg, target = "Set count and click Download.", "download"
    elif dl in ("completed", "stopped"):
        msg, target = "Done. Run more actions or Publish again.", "download"
    else:
        msg, target = "Enter prompts and click Publish.", "publish"
    if section is not None and section != target:
        return
    st.info(msg)


def _total_uxd_images(keys: list[str], count: int) -> int:
    """Compute total new images: upscale=1 per image, vary=4 per image."""
    upscale = sum(1 for k in keys if k.startswith("upscale"))
    vary = sum(1 for k in keys if k.startswith("vary"))
    return count * (upscale * 1 + vary * 4)


def _open_folder_in_explorer(folder: Path) -> bool:
    """Open the folder in the system file manager. Returns True on success."""
    folder = Path(folder)
    if not folder.exists():
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except Exception:
            return False
    path = str(folder.resolve())
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
        return True
    except Exception:
        return False


def _prune_evaluations_for_deleted(folder: Path, deleted_names: set[str]) -> None:
    """Remove evaluation entries for deleted images from image_evaluations.json."""
    if not folder or not deleted_names:
        return
    evals = load_image_evaluations(folder)
    updated = {k: v for k, v in evals.items() if k not in deleted_names}
    if len(updated) != len(evals):
        save_image_evaluations(folder, updated)


def _do_delete_all(paths: list[Path], folder: Path | None, mj_status: dict) -> None:
    """Delete all files and clear session state."""
    deleted_names = {Path(p).name for p in paths}
    for p in paths:
        try:
            Path(p).unlink(missing_ok=True)
        except Exception:
            pass
    mj_status["downloaded_paths"] = []
    if folder:
        _prune_evaluations_for_deleted(folder, deleted_names)


def _do_delete_one(p: Path, folder: Path | None, mj_status: dict) -> None:
    """Delete single file and update session state."""
    try:
        p.unlink(missing_ok=True)
        if folder:
            _prune_evaluations_for_deleted(folder, {p.name})
        if folder is None and "downloaded_paths" in mj_status:
            mj_status["downloaded_paths"] = [
                x for x in mj_status["downloaded_paths"]
                if Path(x) != p and str(x) != str(p)
            ]
    except Exception:
        pass


def _process_lightbox_action() -> bool:
    """Process lightbox_action from query params; update session state and rerun. Returns True if an action was processed (caller should rerun)."""
    action = st.query_params.get("lightbox_action")
    if not action or not st.session_state.get("mj_lightbox_open"):
        return False
    folder_str = st.session_state.get("mj_lightbox_folder", "")
    if not folder_str:
        st.session_state["mj_lightbox_open"] = False
        st.query_params["lightbox_action"] = None
        st.rerun()
        return True
    folder = Path(folder_str)
    paths = [Path(p) for p in list_images_in_folder(folder_str) if Path(p).exists()]
    idx = max(0, min(st.session_state.get("mj_lightbox_index", 0), len(paths) - 1)) if paths else 0
    mj_status = st.session_state.get("mj_status", {})

    if action == "close":
        st.session_state["mj_lightbox_open"] = False
        st.query_params["lightbox_action"] = None
        st.rerun()
        return True

    if action == "prev":
        st.session_state["mj_lightbox_index"] = max(0, idx - 1)
        st.query_params["lightbox_action"] = None
        st.rerun()
        return True

    if action == "next":
        st.session_state["mj_lightbox_index"] = min(len(paths) - 1, idx + 1) if paths else 0
        st.query_params["lightbox_action"] = None
        st.rerun()
        return True

    if action == "delete" and paths:
        p = paths[idx]
        _do_delete_one(p, folder, mj_status)
        paths = [Path(x) for x in list_images_in_folder(folder_str) if Path(x).exists()]
        if not paths:
            st.session_state["mj_lightbox_open"] = False
        else:
            st.session_state["mj_lightbox_index"] = min(idx, len(paths) - 1) if idx < len(paths) else len(paths) - 1
        st.query_params["lightbox_action"] = None
        st.rerun()
        return True

    if action == "select" and paths:
        name = paths[idx].name
        st.session_state[f"mj_sel_{name}"] = True
        if "mj_selected_images" not in st.session_state:
            st.session_state["mj_selected_images"] = {}
        sel = st.session_state["mj_selected_images"].get(folder_str, set()) or set()
        sel.add(name)
        st.session_state["mj_selected_images"][folder_str] = sel
        st.query_params["lightbox_action"] = None
        st.rerun()
        return True

    if action == "deselect" and paths:
        name = paths[idx].name
        st.session_state.pop(f"mj_sel_{name}", None)
        if "mj_selected_images" in st.session_state and folder_str in st.session_state["mj_selected_images"]:
            st.session_state["mj_selected_images"][folder_str] = {
                n for n in st.session_state["mj_selected_images"][folder_str] if n != name
            }
        st.query_params["lightbox_action"] = None
        st.rerun()
        return True

    if action == "delete_selected":
        selected_set = st.session_state.get("mj_selected_images", {}).get(folder_str, set()) or set()
        if selected_set and paths:
            deleted_names = set()
            for p in paths:
                if p.name in selected_set:
                    try:
                        p.unlink(missing_ok=True)
                        deleted_names.add(p.name)
                    except Exception:
                        pass
            if deleted_names:
                _prune_evaluations_for_deleted(folder, deleted_names)
                mj_status["downloaded_paths"] = [
                    x for x in mj_status.get("downloaded_paths", [])
                    if Path(x).name not in deleted_names
                ]
                for name in deleted_names:
                    st.session_state.pop(f"mj_sel_{name}", None)
                if folder_str in st.session_state.get("mj_selected_images", {}):
                    st.session_state["mj_selected_images"][folder_str] = set()
            paths = [Path(x) for x in list_images_in_folder(folder_str) if Path(x).exists()]
        st.session_state["mj_lightbox_open"] = False
        st.query_params["lightbox_action"] = None
        st.rerun()
        return True

    st.query_params["lightbox_action"] = None
    return False


# Max longest side for lightbox image (B1: smaller payload, faster load)
LIGHTBOX_IMAGE_MAX_LONGEST_SIDE = 1600


def _image_to_data_uri(p: Path, max_longest_side: int | None = None) -> str | None:
    """Read image file and return data URI (base64) or None. If max_longest_side is set, resize image to fit before encoding."""
    if not p.exists():
        return None
    try:
        suffix = p.suffix.lower()
        mime = "image/png" if suffix in (".png",) else "image/jpeg" if suffix in (".jpg", ".jpeg", ".webp") else "image/png"
        if max_longest_side:
            img = Image.open(p)
            img = img.convert("RGB" if mime == "image/jpeg" else "RGBA")
            w, h = img.size
            if max(w, h) > max_longest_side:
                ratio = max_longest_side / max(w, h)
                new_size = (int(w * ratio), int(h * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            fmt = "PNG" if mime == "image/png" else "JPEG"
            img.save(buf, format=fmt, quality=85)
            raw = buf.getvalue()
        else:
            raw = p.read_bytes()
        b64 = base64.standard_b64encode(raw).decode("ascii")
        return f"data:{mime};base64,{b64}"
    except Exception:
        return None


def _render_lightbox_html(
    folder: Path,
    paths: list[Path],
    idx: int,
    selected_set: set[str],
    mj_status: dict,
) -> None:
    """Render in-page lightbox overlay: dark backdrop, centered image (fit to viewport), control links."""
    if not paths or idx < 0 or idx >= len(paths):
        return
    p = paths[idx]
    data_uri = _image_to_data_uri(p, max_longest_side=LIGHTBOX_IMAGE_MAX_LONGEST_SIDE)
    if not data_uri:
        st.warning(f"Could not load: {p.name}")
        return

    caption = f"{p.name} — {idx + 1} / {len(paths)}"
    is_selected = p.name in selected_set
    folder_str = str(folder)
    selected_count = len(selected_set)

    # Build query param links (same page, so just the param)
    def link(action: str, label: str, css_class: str = "lightbox-btn") -> str:
        return f'<a href="?lightbox_action={action}" class="{css_class}">{label}</a>'

    prev_link = link("prev", "← Prev") if idx > 0 else '<span class="lightbox-btn lightbox-btn-disabled">← Prev</span>'
    next_link = link("next", "Next →") if idx < len(paths) - 1 else '<span class="lightbox-btn lightbox-btn-disabled">Next →</span>'
    select_link = link("deselect", "Deselect") if is_selected else link("select", "Select")
    delete_sel_link = (
        link("delete_selected", f"Delete selected ({selected_count})")
        if selected_count else ""
    )

    html = f"""
    <div id="mj-lightbox-overlay" style="
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.92); z-index: 9999;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        padding: 1rem; box-sizing: border-box;
    ">
        <div style="color: rgba(255,255,255,0.9); font-size: 0.9rem; margin-bottom: 0.5rem;">{caption}</div>
        <img src="{data_uri}" alt="{p.name}" style="
            max-width: 90vw; max-height: 75vh; object-fit: contain;
            border-radius: 8px; box-shadow: 0 4px 24px rgba(0,0,0,0.5);
        " />
        <div style="
            display: flex; gap: 0.75rem; margin-top: 1rem; flex-wrap: wrap;
            justify-content: center; align-items: center;
        ">
            {prev_link}
            {next_link}
            <a href="?lightbox_action=close" class="lightbox-btn">Close</a>
            <a href="?lightbox_action=delete" class="lightbox-btn lightbox-btn-danger">Delete</a>
            {select_link}
            {delete_sel_link if delete_sel_link else ""}
        </div>
    </div>
    <style>
        .lightbox-btn {{
            display: inline-block; padding: 0.5rem 1rem; background: rgba(255,255,255,0.15);
            color: #fff; text-decoration: none; border-radius: 6px;
            font-size: 0.95rem; border: 1px solid rgba(255,255,255,0.3);
        }}
        .lightbox-btn:hover {{ background: rgba(255,255,255,0.25); color: #fff; }}
        .lightbox-btn-disabled {{ opacity: 0.5; cursor: not-allowed; pointer-events: none; }}
        .lightbox-btn-danger {{ background: rgba(220,53,69,0.4); border-color: rgba(220,53,69,0.6); }}
        .lightbox-btn-danger:hover {{ background: rgba(220,53,69,0.6); }}
    </style>
    """
    st.markdown(html, unsafe_allow_html=True)


def _maybe_render_lightbox_at_top(mj_status: dict) -> None:
    """A1: When lightbox is open, render it first (before tab content) so overlay paints before grid. Handle arrow-key nav."""
    if not st.session_state.get("mj_lightbox_open", False):
        return
    folder_str = st.session_state.get("mj_lightbox_folder", "")
    if not folder_str:
        return
    folder = Path(folder_str)
    paths = [Path(x) for x in list_images_in_folder(folder_str) if Path(x).exists()]
    if not paths:
        st.session_state["mj_lightbox_open"] = False
        return
    idx = max(0, min(st.session_state.get("mj_lightbox_index", 0), len(paths) - 1))
    st.session_state["mj_lightbox_index"] = idx
    selected_set = {
        p.name for p in paths
        if st.session_state.get(f"mj_sel_{p.name}", False)
    }
    _render_lightbox_html(folder, paths, idx, selected_set, mj_status)
    try:
        import streamlit_hotkeys as hotkeys
        hotkeys.activate([
            hotkeys.hk("left", "ArrowLeft"),
            hotkeys.hk("right", "ArrowRight"),
        ])
        if hotkeys.pressed("left") and idx > 0:
            st.session_state["mj_lightbox_index"] = idx - 1
            st.rerun()
        if hotkeys.pressed("right") and idx < len(paths) - 1:
            st.session_state["mj_lightbox_index"] = idx + 1
            st.rerun()
    except Exception:
        pass


def _render_downloaded_images_gallery(
    folder: Path,
    mj_status: dict,
    state: dict | None = None,
    key_prefix: str = "",
) -> None:
    """Render a grid of downloaded images with Delete button and quality badges per image.
    key_prefix: use e.g. 'cover_' for the cover gallery to avoid duplicate widget keys; when 'cover_', Save design is disabled."""
    paths = list_images_in_folder(str(folder))
    if not paths:
        st.subheader("Downloaded Cover Images" if key_prefix == "cover_" else "Downloaded Images")
        st.info("No images yet. Publish prompts, then Download.")
        if folder and st.button("Open folder", key=f"mj_open_folder_empty_{key_prefix}", type="secondary"):
            _open_folder_in_explorer(folder)
        return
    paths = [Path(p) if not isinstance(p, Path) else p for p in paths]

    evaluations = load_image_evaluations(folder)

    if "mj_selected_images" not in st.session_state:
        st.session_state["mj_selected_images"] = {}
    # Sync selected images from checkboxes (from previous run)
    selected_set = {
        p.name for p in paths
        if st.session_state.get(f"mj_sel_{p.name}", False)
    }
    st.session_state["mj_selected_images"][str(folder)] = selected_set

    # Lightbox is rendered at top of tab (A1) when open; no duplicate here

    col_title, col_open, col_save, col_analyze, col_delete_sel, col_delete_all = st.columns([2, 1, 1, 1, 1, 1])
    with col_title:
        st.subheader("Downloaded Cover Images" if key_prefix == "cover_" else "Downloaded Images")
        st.caption("Your images appear here. Use Analyze to check quality with AI.")
        sel_all, desel_all = st.columns(2)
        with sel_all:
            if st.button("Select all", key=f"mj_sel_all_{key_prefix}", type="secondary"):
                for p in paths:
                    st.session_state[f"mj_sel_{p.name}"] = True
                st.session_state["mj_selected_images"][str(folder)] = {p.name for p in paths}
                st.rerun()
        with desel_all:
            if st.button("Deselect all", key=f"mj_desel_all_{key_prefix}", type="secondary"):
                for p in paths:
                    st.session_state.pop(f"mj_sel_{p.name}", None)
                st.session_state["mj_selected_images"][str(folder)] = set()
                st.rerun()
    with col_open:
        if folder and st.button("Open folder", key=f"mj_open_folder_btn_{key_prefix}", type="secondary"):
            _open_folder_in_explorer(folder)
    with col_save:
        from core.persistence import save_design_package
        has_images = len(paths) > 0
        is_cover_gallery = key_prefix == "cover_"
        if state and has_images and not is_cover_gallery:
            if st.button("Save design", key=f"mj_save_design_btn_{key_prefix}", type="secondary"):
                try:
                    folder_path = Path(folder) if not isinstance(folder, Path) else folder
                    cover_path = folder_path / "cover"
                    cover_source = str(cover_path) if cover_path.exists() and cover_path.is_dir() else None
                    pkg_path = state.get("design_package_path")
                    if pkg_path and Path(pkg_path).exists():
                        save_design_package(state, str(folder), package_path=pkg_path, cover_source_folder=cover_source)
                    else:
                        pkg_path = save_design_package(state, str(folder), cover_source_folder=cover_source)
                        state["design_package_path"] = pkg_path
                        state["images_folder_path"] = pkg_path
                        st.session_state.workflow_state = state
                    st.success("Design saved to package!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.button(
                "Save design",
                key=f"mj_save_design_btn_{key_prefix}",
                disabled=True,
                help="Save from the Inside images section above to include both inside and cover." if is_cover_gallery else "No images or no design metadata",
            )
    with col_analyze:
        if st.button("Analyze images", key=f"mj_analyze_btn_{key_prefix}", type="secondary", help="Run AI quality check on all images"):
            st.session_state["mj_analyze_requested"] = True
            st.rerun()
    with col_delete_sel:
        if selected_set and st.button(f"Delete selected ({len(selected_set)})", key=f"mj_del_selected_{key_prefix}", type="secondary"):
            deleted_names = set()
            for p in paths:
                if p.name in selected_set:
                    try:
                        p.unlink(missing_ok=True)
                        deleted_names.add(p.name)
                    except Exception:
                        pass
            if deleted_names:
                _prune_evaluations_for_deleted(folder, deleted_names)
                mj_status["downloaded_paths"] = [
                    x for x in mj_status.get("downloaded_paths", [])
                    if Path(x).name not in deleted_names
                ]
                for name in deleted_names:
                    st.session_state.pop(f"mj_sel_{name}", None)
                st.session_state["mj_selected_images"][str(folder)] = set()
            st.rerun()
    with col_delete_all:
        if st.button("Delete all", key=f"mj_del_all_downloaded_{key_prefix}", type="secondary"):
            _do_delete_all(paths, folder, mj_status)
            st.rerun()

    # Delete below threshold (only when evaluations exist)
    with st.expander("Image quality", expanded=False):
        threshold = st.number_input(
            "Min score to keep",
            min_value=0,
            max_value=100,
            value=IMAGE_MIN_SCORE_THRESHOLD,
            key=f"mj_score_threshold_{key_prefix}",
            help="Images with score below this will be deleted when you click 'Delete below threshold'.",
        )
        if evaluations:
            to_delete = [
                p for p in paths
                if p.name in evaluations
                and evaluations[p.name].get("score") is not None
                and evaluations[p.name]["score"] < threshold
            ]
            if to_delete and st.button("Delete below threshold", key=f"mj_del_below_threshold_{key_prefix}", type="secondary"):
                deleted_names = set()
                for p in to_delete:
                    try:
                        p.unlink(missing_ok=True)
                        deleted_names.add(p.name)
                    except Exception:
                        pass
                if deleted_names:
                    _prune_evaluations_for_deleted(folder, deleted_names)
                    mj_status["downloaded_paths"] = [
                        x for x in mj_status.get("downloaded_paths", [])
                        if Path(x).name not in deleted_names
                    ]
                    for name in deleted_names:
                        st.session_state.pop(f"mj_sel_{name}", None)
                    if str(folder) in st.session_state.get("mj_selected_images", {}):
                        st.session_state["mj_selected_images"][str(folder)] -= deleted_names
                st.rerun()

    if st.session_state.get("mj_analyze_requested"):
        st.session_state["mj_analyze_requested"] = False
        with st.spinner("Analyzing images with AI..."):
            progress_placeholder = st.empty()
            def on_progress(current: int, total: int, filename: str) -> None:
                progress_placeholder.caption(f"Analyzing {current}/{total}: {filename}")

            results = evaluate_images_in_folder(
                folder,
                on_progress=on_progress,
            )
            save_image_evaluations(folder, results)
            progress_placeholder.empty()
        st.success("Analysis complete!")
        st.rerun()

    for row_start in range(0, len(paths), 4):
        row_paths = paths[row_start : row_start + 4]
        cols = st.columns(4)
        for i, p in enumerate(row_paths):
            with cols[i]:
                if p.exists():
                    try:
                        st.image(str(p), width="stretch")
                    except (OSError, ValueError):
                        st.warning(f"Corrupted: {p.name}")
                    eval_result = evaluations.get(p.name, {})
                    passed = eval_result.get("passed", None)
                    score = eval_result.get("score")
                    summary = eval_result.get("summary", "")
                    issues = eval_result.get("issues", [])
                    if passed is True:
                        badge = "✓ Looks good"
                    elif passed is False:
                        badge = "⚠ Issues found"
                    else:
                        badge = None
                    if badge:
                        st.caption(f"**{badge}** (Score: {score}/100)")
                        if summary or issues:
                            with st.expander("Details", expanded=False):
                                if summary:
                                    st.write(summary)
                                if issues:
                                    st.markdown("**Issues:**")
                                    for iss in issues[:5]:
                                        sev = iss.get("severity", "minor").upper()
                                        st.markdown(f"- [{sev}] {iss.get('issue', '')}")
                    else:
                        st.caption(p.name)
                    st.checkbox("Select", key=f"mj_sel_{p.name}", value=(p.name in selected_set))
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        img_index = row_start + i
                        if st.button("View", key=f"mj_view_{p.name}_{row_start}_{i}", type="secondary"):
                            st.session_state["mj_lightbox_open"] = True
                            st.session_state["mj_lightbox_index"] = img_index
                            st.session_state["mj_lightbox_folder"] = str(folder)
                            st.rerun()
                    with btn_col2:
                        if st.button("Delete", key=f"mj_del_{p.name}_{row_start}_{i}", type="secondary"):
                            _do_delete_one(p, folder, mj_status)
                            st.rerun()
                else:
                    st.caption(f"{p.name} (deleted)")
                    if "downloaded_paths" in mj_status:
                        mj_status["downloaded_paths"] = [
                            x for x in mj_status["downloaded_paths"]
                            if Path(x) != p and str(x) != str(p)
                        ]
                    st.rerun()


def render_image_generation_tab(state: dict, generated_designs: list | None = None):
    """Render Image Generation tab with Midjourney workflow and folder grid.

    Args:
        state: Current workflow state (single design).
        generated_designs: List of design states from concept-based generation (for batch mode).
    """
    generated_designs = generated_designs or []

    _init_mj_session_state()
    if _process_lightbox_action():
        return  # rerun already triggered
    mj_status = st.session_state.mj_status

    # A1: Render lightbox first when open so overlay paints before grid (no flash)
    _maybe_render_lightbox_at_top(mj_status)

    st.markdown("## Image Generation")
    mj_automated_process = st.session_state.get("mj_automated_process")
    automated_running = mj_automated_process is not None and mj_automated_process.is_alive()
    # Sync from shared: when process is running OR when it just finished (so we get final status)
    if "mj_automated_shared" in st.session_state and (
        automated_running or (mj_automated_process is not None and not mj_automated_process.is_alive())
    ):
        shared = st.session_state.mj_automated_shared
        for key in ("publish_status", "publish_error", "uxd_action_status", "uxd_action_error", "download_status", "download_error"):
            if key in shared:
                mj_status[key] = shared[key]
        if "downloaded_paths" in shared:
            mj_status["downloaded_paths"] = shared["downloaded_paths"]
        for key in ("batch_current_index", "batch_total", "batch_current_design_title", "batch_results"):
            if key in shared:
                mj_status[key] = shared[key]
    # Sync from publish process when running (status; progress is already the Manager dict)
    pub_proc = st.session_state.get("mj_publish_process")
    if pub_proc is not None and pub_proc.is_alive():
        mgr_status = st.session_state.get("mj_publish_mgr_status")
        if mgr_status:
            for key in ("publish_status", "publish_error"):
                if key in mgr_status:
                    mj_status[key] = mgr_status[key]
    # Sync from uxd process when running (status; progress is already the Manager dict)
    uxd_proc = st.session_state.get("mj_uxd_process")
    if uxd_proc is not None and uxd_proc.is_alive():
        mgr_status = st.session_state.get("mj_uxd_mgr_status")
        if mgr_status:
            for key in ("uxd_action_status", "uxd_action_error"):
                if key in mgr_status:
                    mj_status[key] = mgr_status[key]
    # Sync from download process when running (status; progress is already the Manager dict)
    dl_proc = st.session_state.get("mj_download_process")
    if dl_proc is not None and dl_proc.is_alive():
        mgr_status = st.session_state.get("mj_download_mgr_status")
        if mgr_status:
            for key in ("download_status", "download_error", "downloaded_paths"):
                if key in mgr_status:
                    mj_status[key] = mgr_status[key]
    # Cover workflow: sync from cover processes
    mj_cover_status = st.session_state.mj_cover_status
    cover_pub_proc = st.session_state.get("mj_cover_publish_process")
    if cover_pub_proc is not None and cover_pub_proc.is_alive():
        mgr = st.session_state.get("mj_cover_publish_mgr_status")
        if mgr:
            for key in ("publish_status", "publish_error"):
                if key in mgr:
                    mj_cover_status[key] = mgr[key]
    cover_uxd_proc = st.session_state.get("mj_cover_uxd_process")
    if cover_uxd_proc is not None and cover_uxd_proc.is_alive():
        mgr = st.session_state.get("mj_cover_uxd_mgr_status")
        if mgr:
            for key in ("uxd_action_status", "uxd_action_error"):
                if key in mgr:
                    mj_cover_status[key] = mgr[key]
    cover_dl_proc = st.session_state.get("mj_cover_download_process")
    if cover_dl_proc is not None and cover_dl_proc.is_alive():
        mgr = st.session_state.get("mj_cover_download_mgr_status")
        if mgr:
            for key in ("download_status", "download_error", "downloaded_paths"):
                if key in mgr:
                    mj_cover_status[key] = mgr[key]
    # Sync from cover automated shared when cover automated process is running or just finished
    mj_cover_automated_process = st.session_state.get("mj_cover_automated_process")
    if "mj_cover_automated_shared" in st.session_state and (
        (mj_cover_automated_process is not None and mj_cover_automated_process.is_alive())
        or (mj_cover_automated_process is not None and not mj_cover_automated_process.is_alive())
    ):
        shared = st.session_state.mj_cover_automated_shared
        for key in ("publish_status", "publish_error", "uxd_action_status", "uxd_action_error", "download_status", "download_error"):
            if key in shared:
                mj_cover_status[key] = shared[key]
        if "downloaded_paths" in shared:
            mj_cover_status["downloaded_paths"] = shared["downloaded_paths"]
    cfg = get_midjourney_config()
    settings = {
        "browser_debug_port": cfg.get("browser_debug_port", 9222),
        "output_folder": str(cfg.get("output_folder", GENERATED_IMAGES_DIR)),
        "debug_show_clicks": cfg.get("debug_show_clicks", False),
    }

    # Output folder: default from design_package_path, images_folder_path, or GENERATED_IMAGES_DIR
    default_folder = (
        state.get("design_package_path")
        or state.get("images_folder_path")
        or str(GENERATED_IMAGES_DIR)
    )
    output_folder = st.text_input(
        "Output folder",
        value=default_folder,
        key="mj_output_folder",
        help="Where Midjourney images are saved and where we monitor for selection.",
    )
    output_folder = (output_folder or str(GENERATED_IMAGES_DIR)).strip() or str(GENERATED_IMAGES_DIR)
    settings["output_folder"] = output_folder
    state["images_folder_path"] = output_folder

    base_output = Path(output_folder)

    # System & Prerequisites (needed for batch section)
    prereqs = _render_system_and_prerequisites(settings)
    browser_connected = prereqs["browser_connected"]
    debug_show_clicks = prereqs["debug_show_clicks"]
    button_coords = cfg.get("button_coordinates") or {}
    pub_running = mj_status.get("publish_status") == "running"
    pub_process = st.session_state.mj_publish_process
    pub_process_alive = pub_process is not None and pub_process.is_alive()
    step_running = pub_running or mj_status.get("uxd_action_status") == "running" or mj_status.get("download_status") == "running"

    # Batch mode: run multiple designs sequentially (each in own subfolder)
    batch_selected: list[int] = []
    if len(generated_designs) >= 2:
        with st.expander("Run multiple designs (batch)", expanded=automated_running and mj_status.get("batch_total", 0) > 1):
            st.caption(
                "Run image generation for selected designs sequentially. Each design gets its own subfolder."
            )
            for idx, design in enumerate(generated_designs):
                title = design.get("title", "Untitled") or "Untitled"
                concept = design.get("concept_source", {})
                theme = concept.get("theme") or concept.get("theme_concept", "")
                style = concept.get("style") or concept.get("art_style", "")
                sub = f" | {theme} | {style}" if (theme or style) else ""
                n_prompts = len(design.get("midjourney_prompts", []))
                if st.checkbox(
                    f"{title}{sub} ({n_prompts} prompts)",
                    value=idx in st.session_state.get("mj_batch_selected_indices", []),
                    key=f"mj_batch_sel_{idx}",
                ):
                    batch_selected.append(idx)
            st.session_state.mj_batch_selected_indices = batch_selected

            col_sel, col_clr, _ = st.columns([1, 1, 4])
            with col_sel:
                if st.button("Select all", key="mj_batch_select_all"):
                    st.session_state.mj_batch_selected_indices = list(range(len(generated_designs)))
                    st.rerun()
            with col_clr:
                if st.button("Clear", key="mj_batch_clear"):
                    st.session_state.mj_batch_selected_indices = []
                    st.rerun()

            batch_designs = [generated_designs[i] for i in batch_selected if i < len(generated_designs)]
            batch_ready = (
                batch_designs
                and browser_connected
                and button_coords
                and not automated_running
                and not step_running
            )
            run_batch_clicked = st.button(
                "Run batch",
                type="primary",
                key="mj_run_batch_btn",
                disabled=not batch_ready,
                help=f"Run full automated pipeline for {len(batch_designs)} design(s), each in its own subfolder.",
            )
            if run_batch_clicked and batch_designs and browser_connected and button_coords:
                health = run_health_checks(
                    output_folder=base_output,
                    browser_port=settings["browser_debug_port"],
                )
                if health.has_errors():
                    st.error("Health check failed. Fix errors before starting.")
                    st.stop()
                used_slugs: set[str] = set()
                designs_with_folders: list[tuple[dict, Path, int]] = []
                for orig_idx in batch_selected:
                    design = generated_designs[orig_idx]
                    slug = _design_to_subfolder_slug(design, orig_idx, used_slugs)
                    subfolder = base_output / slug
                    designs_with_folders.append((design, subfolder, orig_idx))
                st.session_state.mj_automated_stop_flag["stop"] = False
                shared = st.session_state.mj_automated_shared
                for k in list(shared.keys()):
                    if k.startswith("batch_"):
                        del shared[k]
                shared["publish_status"] = "idle"
                shared["publish_error"] = ""
                shared["uxd_action_status"] = "idle"
                shared["uxd_action_error"] = ""
                shared["download_status"] = "idle"
                shared["download_error"] = ""
                shared["downloaded_paths"] = []
                viewport = cfg.get("viewport") or {"width": 1920, "height": 1080}
                coord_vp = cfg.get("coordinates_viewport") or {"width": 1920, "height": 1080}
                proc, manager, mgr_stop, mgr_shared, mgr_publish, mgr_uxd, mgr_download = run_batch_automated_process(
                    designs_with_folders,
                    button_coords,
                    settings["browser_debug_port"],
                    st.session_state.mj_automated_stop_flag,
                    shared,
                    st.session_state.mj_publish_progress,
                    st.session_state.mj_uxd_progress,
                    st.session_state.mj_download_progress,
                    viewport=viewport,
                    coordinates_viewport=coord_vp,
                    debug_show_clicks=debug_show_clicks,
                )
                st.session_state.mj_automated_process = proc
                st.session_state.mj_automated_manager = manager
                st.session_state.mj_automated_mgr_stop = mgr_stop
                st.session_state.mj_automated_shared = mgr_shared
                st.session_state.mj_publish_progress = mgr_publish
                st.session_state.mj_uxd_progress = mgr_uxd
                st.session_state.mj_download_progress = mgr_download
                st.rerun()

    _workflow_step_indicator(mj_status)

    # --- Section A: Prompts and Midjourney workflow ---
    st.subheader("Midjourney Workflow")

    # Pre-fill prompts from Design Generation
    default_prompts = state.get("midjourney_prompts", [])
    default_text = "\n".join(default_prompts) if default_prompts else ""

    st.caption(
        "Submit prompts to Midjourney. Each prompt generates 4 images. "
        "Prompts are sent in batches of 10."
    )
    raw = st.text_area(
        "Midjourney Prompts",
        value=default_text,
        height=120,
        key="mj_prompts_area",
        placeholder="Enter one prompt per line...",
    )
    prompts = [line.strip() for line in raw.strip().splitlines() if line.strip()]
    if prompts:
        st.caption(f"{len(prompts)} prompt(s) queued")

    _next_step_guidance(mj_status, section="publish")

    # Publish button
    if not button_coords:
        st.warning(
            "**First-time setup:** Button coordinates are not configured. Run "
            "`uv run midjourney-agent setup` to record coordinates. See README."
        )

    sec_per_prompt = cfg.get("waits", {}).get("seconds_per_prompt_estimate", 40)
    sec_per_upscale = cfg.get("waits", {}).get("seconds_per_upscale_estimate", 20)
    num_images = len(prompts) * 4 if prompts else 0
    est_min = len(prompts) * sec_per_prompt / 60 if prompts else 0
    est_min_auto = (len(prompts) * sec_per_prompt + num_images * sec_per_upscale) / 60 if prompts else 0
    est_text = f" (~{est_min:.0f} min)" if prompts and est_min >= 1 else ""
    est_text_auto = f" (~{est_min_auto:.0f} min)" if prompts and est_min_auto >= 1 else ""

    run_automated = st.checkbox(
        "Run full automated",
        value=False,
        key="mj_run_automated_checkbox",
        help=f"Publish → Upscale all → Download all{est_text_auto}",
    )

    col_pub, col_stop_pub = st.columns([4, 1])
    with col_pub:
        pub_clicked = st.button(
            "Publish",
            type="primary",
            key="mj_publish_btn",
            disabled=not (prompts and browser_connected and button_coords) or pub_process_alive or automated_running,
            help=f"Submit prompts only.{est_text}" if not run_automated else f"Full pipeline{est_text_auto}",
        )
        if pub_clicked and prompts and browser_connected and button_coords:
            health = run_health_checks(
                output_folder=Path(output_folder),
                browser_port=settings["browser_debug_port"],
            )
            if health.has_errors():
                st.error("Health check failed. Fix errors before starting.")
                st.stop()
            viewport = cfg.get("viewport") or {"width": 1920, "height": 1080}
            coord_vp = cfg.get("coordinates_viewport") or {"width": 1920, "height": 1080}

            if run_automated:
                st.session_state.mj_automated_stop_flag["stop"] = False
                shared = st.session_state.mj_automated_shared
                shared["publish_status"] = "idle"
                shared["publish_error"] = ""
                shared["uxd_action_status"] = "idle"
                shared["uxd_action_error"] = ""
                shared["download_status"] = "idle"
                shared["download_error"] = ""
                shared["downloaded_paths"] = []
                proc, manager, mgr_stop, mgr_shared, mgr_publish, mgr_uxd, mgr_download = run_automated_process(
                    prompts,
                    button_coords,
                    settings["browser_debug_port"],
                    Path(output_folder),
                    st.session_state.mj_automated_stop_flag,
                    shared,
                    st.session_state.mj_publish_progress,
                    st.session_state.mj_uxd_progress,
                    st.session_state.mj_download_progress,
                    viewport=viewport,
                    coordinates_viewport=coord_vp,
                    debug_show_clicks=debug_show_clicks,
                )
                st.session_state.mj_automated_process = proc
                st.session_state.mj_automated_manager = manager
                st.session_state.mj_automated_mgr_stop = mgr_stop
                st.session_state.mj_automated_shared = mgr_shared
                st.session_state.mj_publish_progress = mgr_publish
                st.session_state.mj_uxd_progress = mgr_uxd
                st.session_state.mj_download_progress = mgr_download
            else:
                st.session_state.mj_publish_stop_flag["stop"] = False
                mj_status["publish_status"] = "running"
                mj_status["publish_error"] = ""
                proc, manager, mgr_stop, mgr_progress, mgr_status = run_publish_process(
                    prompts,
                    button_coords,
                    settings["browser_debug_port"],
                    st.session_state.mj_publish_stop_flag,
                    st.session_state.mj_publish_progress,
                    mj_status,
                    viewport=viewport,
                    coordinates_viewport=coord_vp,
                    debug_show_clicks=debug_show_clicks,
                )
                st.session_state.mj_publish_process = proc
                st.session_state.mj_publish_manager = manager
                st.session_state.mj_publish_mgr_stop = mgr_stop
                st.session_state.mj_publish_mgr_status = mgr_status
                st.session_state.mj_publish_progress = mgr_progress
            st.rerun()
    with col_stop_pub:
        if automated_running and st.button("Stop", key="mj_automated_stop_btn"):
            mgr_stop = st.session_state.get("mj_automated_mgr_stop")
            if mgr_stop is not None:
                mgr_stop["stop"] = True
            else:
                st.session_state.mj_automated_stop_flag["stop"] = True
            st.rerun()
        elif pub_process_alive and st.button("Stop", key="mj_publish_stop_btn"):
            mgr_stop = st.session_state.get("mj_publish_mgr_stop")
            if mgr_stop is not None:
                mgr_stop["stop"] = True
            else:
                st.session_state.mj_publish_stop_flag["stop"] = True
            st.rerun()

    # Inline progress display (unified overview, publish, uxd/download)
    if automated_running:
        pub_prog = st.session_state.mj_publish_progress
        uxd_prog = st.session_state.mj_uxd_progress
        dl_prog = st.session_state.mj_download_progress
        pub_s = mj_status.get("publish_status", "idle")
        uxd_s = mj_status.get("uxd_action_status", "idle")
        dl_s = mj_status.get("download_status", "idle")
        parts = []
        if pub_s == "running":
            phase = pub_prog.get("phase", "submit")
            if phase == "submit":
                sc, stotal = pub_prog.get("submit_current", 0), pub_prog.get("submit_total", 1)
                parts.append(f"Publish: {sc}/{stotal} prompts")
            elif phase in ("wait", "wait_queue"):
                qc = pub_prog.get("queue_count")
                parts.append(f"Publish: Queue {qc} jobs" if qc is not None else "Publish: Checking...")
            else:
                parts.append("Publish: Finalizing...")
        elif pub_s in ("completed", "stopped"):
            parts.append("Publish: done")
        if uxd_s == "running":
            cur = uxd_prog.get("uxd_current_image")
            tot = uxd_prog.get("uxd_total_images")
            if cur is not None and tot:
                parts.append(f"Upscale: {cur}/{tot}")
            else:
                bc, bt = uxd_prog.get("uxd_batch_current", 1), uxd_prog.get("uxd_total_batches", 1)
                parts.append(f"Upscale: Batch {bc}/{bt}")
        elif uxd_s in ("completed", "stopped"):
            parts.append("Upscale: done")
        if dl_s == "running":
            c, t = dl_prog.get("current", 0), dl_prog.get("total", 1)
            parts.append(f"Download: {c}/{t}")
        elif dl_s in ("completed", "stopped"):
            parts.append("Download: done")
        if parts:
            st.caption(" | ".join(parts))
    # Publish progress
    pub_status = mj_status.get("publish_status", "idle")
    batch_total = mj_status.get("batch_total", 0)
    batch_cur = mj_status.get("batch_current_index", 0)
    batch_title = mj_status.get("batch_current_design_title", "")
    if automated_running and pub_status == "running":
        st.caption("**Phase 1: Publish**")
    if pub_status == "running" and batch_total > 1 and batch_title:
        st.info(f"Design {batch_cur}/{batch_total}: **{batch_title}**")
    if pub_status == "running":
        prog = st.session_state.mj_publish_progress
        phase = prog.get("phase", "submit")
        batch_cur = prog.get("batch_current", 1)
        batch_tot = prog.get("batch_total", 1)
        batch_info = f" · Batch {batch_cur}/{batch_tot}" if batch_tot > 1 else ""
        if phase == "wait":
            queue_count = prog.get("queue_count")
            estimated_min = prog.get("estimated_wait_min")
            queue_text = f"Midjourney queue: {queue_count} jobs" if queue_count is not None else "Checking..."
            est_text = f" · ~{estimated_min:.1f} min estimated" if estimated_min and estimated_min > 0 else ""
            st.info(f"{queue_text}{est_text}{batch_info}")
        elif phase == "finalize":
            elapsed = prog.get("elapsed", 0)
            total = prog.get("total", 1)
            remaining = max(0, total - elapsed)
            queue_count = prog.get("queue_count")
            estimated_min = prog.get("estimated_wait_min")
            queue_text = f"Midjourney queue: {queue_count} jobs" if queue_count is not None else "Checking..."
            est_text = f" · ~{estimated_min:.1f} min total" if estimated_min and estimated_min > 0 else ""
            st.info(f"Finalizing ({int(remaining)}s remaining) · {queue_text}{est_text}{batch_info}")
        elif phase == "wait_queue":
            queue_count = prog.get("queue_count")
            estimated_min = prog.get("estimated_wait_min")
            if queue_count == 0:
                st.info(f"Queue empty, submitting next batch{batch_info}...")
            elif queue_count is not None:
                queue_text = f"Midjourney queue: {queue_count} jobs"
                est_text = f" · ~{estimated_min:.1f} min estimated" if estimated_min and estimated_min > 0 else ""
                st.info(f"{queue_text}{est_text}{batch_info}")
            else:
                st.info(f"Checking queue status{batch_info}...")
        elif phase == "submit":
            submit_cur = prog.get("submit_current", 0)
            submit_tot = prog.get("submit_total", 1)
            progress_pct = submit_cur / submit_tot if submit_tot > 0 else 0
            st.progress(min(1.0, progress_pct), text=f"Submitting prompt {submit_cur}/{submit_tot}{batch_info}...")
        else:
            st.info("Submitting prompts...")
    elif pub_status == "completed":
        batch_total = mj_status.get("batch_total", 0)
        if batch_total > 1:
            batch_cur = mj_status.get("batch_current_index", 0)
            batch_title = mj_status.get("batch_current_design_title", "")
            if batch_title:
                st.success(f"Design {batch_cur}/{batch_total}: {batch_title} — completed.")
            else:
                st.success(f"Batch complete: {batch_total} design(s) done.")
    elif pub_status == "stopped":
        st.warning("Stopped by user.")
    elif pub_status == "error":
        st.error(mj_status.get("publish_error", "Unknown error"))
    # Unified progress for automated mode (upscale + download phases)
    if automated_running:
        uxd_status = mj_status.get("uxd_action_status", "idle")
        dl_status = mj_status.get("download_status", "idle")
        if uxd_status == "running":
            st.caption("**Phase 2: Upscale/Vary**")
            prog = st.session_state.mj_uxd_progress
            phase = prog.get("phase", "click")
            if phase == "wait":
                queue_count = prog.get("queue_count")
                estimated_min = prog.get("estimated_wait_min")
                batch_info = f" · Batch {prog.get('uxd_batch_current', 1)}/{prog.get('uxd_total_batches', 1)}"
                queue_text = f"Midjourney queue: {queue_count} jobs" if queue_count is not None else "Checking..."
                est_text = f" · ~{estimated_min:.1f} min" if estimated_min and estimated_min > 0 else ""
                st.info(f"**Upscale/Vary:** {queue_text}{est_text}{batch_info}")
            else:
                cur_img = prog.get("uxd_current_image")
                tot_img = prog.get("uxd_total_images")
                if cur_img is not None and tot_img and tot_img > 0:
                    pct = cur_img / tot_img
                    st.progress(min(1.0, pct), text=f"**Upscale/Vary:** Upscaling image {cur_img}/{tot_img}...")
                else:
                    batch_cur = prog.get("uxd_batch_current", 1)
                    batch_tot = prog.get("uxd_total_batches", 1)
                    images_est = prog.get("images_estimated", 0)
                    batch_info = f"Batch {batch_cur}/{batch_tot}" if batch_tot > 1 else ""
                    img_info = f"{images_est} images" if images_est else ""
                    label = " · ".join(filter(None, [batch_info, img_info])) or "Running upscale actions..."
                    pct = batch_cur / batch_tot if batch_tot > 0 else 0
                    st.progress(min(1.0, pct), text=f"**Upscale/Vary:** {label}")
        elif uxd_status == "completed" and dl_status != "running" and dl_status != "completed":
            st.success("Upscale done. Allow ~20s per image before download.")
        elif dl_status == "running":
            st.caption("**Phase 3: Download**")
            prog = st.session_state.mj_download_progress
            cur = prog.get("current", 0)
            tot = prog.get("total", 1)
            st.info("**Download:** Saving images to folder...")
            st.progress(min(1.0, cur / tot) if tot > 0 else 0, text=f"Downloading {cur}/{tot}...")
        elif dl_status == "completed":
            paths = mj_status.get("downloaded_paths", [])
            st.success(f"Downloaded {len(paths)} image(s).")
        elif dl_status == "stopped":
            paths = mj_status.get("downloaded_paths", [])
            st.warning(f"Stopped. Downloaded {len(paths)} file(s).")
        elif uxd_status == "error":
            st.error(mj_status.get("uxd_action_error", "Unknown error"))
        elif dl_status == "error":
            st.error(mj_status.get("download_error", "Unknown error"))

    # --- Upscale and Vary (hidden when "Run full automated" is ticked) ---
    if not (run_automated or automated_running):
        st.divider()
        _next_step_guidance(mj_status, section="upscale")

        st.subheader("Upscale and Vary")
        st.caption(
            "After images appear, select actions and count, then Run. "
            "Upscale: 1 new per original. Vary: 4 new per original."
        )

        uxd_status = mj_status.get("uxd_action_status", "idle")
        uxd_process = st.session_state.mj_uxd_process
        uxd_process_alive = uxd_process is not None and uxd_process.is_alive()

        uv_count = int(
            st.number_input(
                "Count",
                min_value=1,
                max_value=20,
                value=4,
                key="mj_uxd_count",
                help="Number of images to upscale or vary.",
            )
        )

        col1, col2, col3, col4 = st.columns(4)
        selected_keys: list[str] = []
        with col1:
            if st.checkbox("Upscale Subtle", value=False, key="mj_uxd_subtle"):
                selected_keys.append("upscale_subtle")
        with col2:
            if st.checkbox("Upscale Creative", value=False, key="mj_uxd_creative"):
                selected_keys.append("upscale_creative")
        with col3:
            if st.checkbox("Vary Subtle", value=False, key="mj_uxd_vary_subtle"):
                selected_keys.append("vary_subtle")
        with col4:
            if st.checkbox("Vary Strong", value=False, key="mj_uxd_vary_strong"):
                selected_keys.append("vary_strong")

        total_new = _total_uxd_images(selected_keys, uv_count) if selected_keys else 0
        sec_per_ux = cfg.get("waits", {}).get("seconds_per_upscale_estimate", 20)
        est_min_ux = total_new * sec_per_ux / 60 if total_new else 0
        est_help = f" (~{est_min_ux:.0f} min)" if total_new and est_min_ux >= 1 else ""

        col_run, col_stop_ux = st.columns([4, 1])
        with col_run:
            uv_run_clicked = st.button(
                "Run",
                key="mj_uxd_run_btn",
                type="secondary",
                disabled=not (button_coords and selected_keys and uxd_status != "running" and not uxd_process_alive),
                help=f"Select at least one action.{est_help}",
            )
        with col_stop_ux:
            if uxd_process_alive and st.button("Stop", key="mj_uxd_stop_btn"):
                mgr_stop = st.session_state.get("mj_uxd_mgr_stop")
                if mgr_stop is not None:
                    mgr_stop["stop"] = True
                else:
                    st.session_state.mj_uxd_stop_flag["stop"] = True
                st.rerun()

        if uv_run_clicked and browser_connected and selected_keys:
            st.session_state.mj_uxd_stop_flag["stop"] = False
            mj_status["uxd_action_status"] = "running"
            mj_status["uxd_action_error"] = ""
            total_new = _total_uxd_images(selected_keys, uv_count)
            st.session_state.mj_uxd_progress = {
                "elapsed": 0,
                "total": 0,
                "phase": "click",
                "images_estimated": total_new,
            }
            viewport = cfg.get("viewport") or {"width": 1920, "height": 1080}
            coord_vp = cfg.get("coordinates_viewport") or {"width": 1920, "height": 1080}
            proc, manager, mgr_stop, mgr_progress, mgr_status = run_uxd_action_process(
                selected_keys,
                uv_count,
                Path(output_folder),
                button_coords,
                settings["browser_debug_port"],
                st.session_state.mj_uxd_stop_flag,
                total_new,
                st.session_state.mj_uxd_progress,
                mj_status,
                viewport=viewport,
                coordinates_viewport=coord_vp,
                debug_show_clicks=debug_show_clicks,
            )
            st.session_state.mj_uxd_process = proc
            st.session_state.mj_uxd_manager = manager
            st.session_state.mj_uxd_mgr_stop = mgr_stop
            st.session_state.mj_uxd_mgr_status = mgr_status
            st.session_state.mj_uxd_progress = mgr_progress
            st.rerun()

        if uxd_status == "running":
            prog = st.session_state.mj_uxd_progress
            phase = prog.get("phase", "click")
            if phase == "wait":
                queue_count = prog.get("queue_count")
                estimated_min = prog.get("estimated_wait_min")
                batch_info = f" · Batch {prog.get('uxd_batch_current', 1)}/{prog.get('uxd_total_batches', 1)}"
                queue_text = f"Midjourney queue: {queue_count} jobs" if queue_count is not None else "Checking..."
                est_text = f" · ~{estimated_min:.1f} min" if estimated_min and estimated_min > 0 else ""
                st.info(f"{queue_text}{est_text}{batch_info}")
            else:
                cur_img = prog.get("uxd_current_image")
                tot_img = prog.get("uxd_total_images")
                if cur_img is not None and tot_img and tot_img > 0:
                    pct = cur_img / tot_img
                    st.progress(min(1.0, pct), text=f"Upscaling image {cur_img}/{tot_img}...")
                else:
                    batch_cur = prog.get("uxd_batch_current", 1)
                    batch_tot = prog.get("uxd_total_batches", 1)
                    images_est = prog.get("images_estimated", 0)
                    batch_info = f"Batch {batch_cur}/{batch_tot}" if batch_tot > 1 else ""
                    img_info = f"{images_est} images" if images_est else ""
                    label = " · ".join(filter(None, [batch_info, img_info])) or "Running upscale/vary actions..."
                    pct = batch_cur / batch_tot if batch_tot > 0 else 0
                    st.progress(min(1.0, pct), text=label)
        elif uxd_status == "completed":
            st.success("Done. Allow ~20s per new image before downloading.")
        elif uxd_status == "stopped":
            st.warning("Stopped by user.")
        elif uxd_status == "error":
            st.error(mj_status.get("uxd_action_error", "Unknown error"))

    # --- Download (hidden when "Run full automated" is ticked) ---
    if not (run_automated or automated_running):
        st.divider()
        _next_step_guidance(mj_status, section="download")

        st.subheader("Download")
        st.caption("Download images from the detail view to your output folder.")

        dl_status = mj_status.get("download_status", "idle")
        dl_process = st.session_state.mj_download_process
        dl_process_alive = dl_process is not None and dl_process.is_alive()

        dl_count = int(
            st.number_input(
                "Images to download",
                min_value=1,
                max_value=9999,
                value=4,
                key="mj_dl_count",
                help="Number of images to download.",
            )
        )

        col_dl, col_stop_dl = st.columns([4, 1])
        with col_dl:
            dl_clicked = st.button(
                "Download",
                key="mj_dl_btn",
                type="secondary",
                disabled=not button_coords or dl_process_alive,
                help="Download images to the output folder.",
            )
        with col_stop_dl:
            if dl_process_alive and st.button("Stop", key="mj_dl_stop_btn"):
                mgr_stop = st.session_state.get("mj_download_mgr_stop")
                if mgr_stop is not None:
                    mgr_stop["stop"] = True
                else:
                    st.session_state.mj_download_stop_flag["stop"] = True
                st.rerun()

        if dl_clicked and browser_connected:
            st.session_state.mj_download_stop_flag["stop"] = False
            mj_status["download_status"] = "running"
            mj_status["download_error"] = ""
            st.session_state.mj_download_progress = {"current": 0, "total": dl_count}
            viewport = cfg.get("viewport") or {"width": 1920, "height": 1080}
            coord_vp = cfg.get("coordinates_viewport") or {"width": 1920, "height": 1080}
            proc, manager, mgr_stop, mgr_progress, mgr_status = run_download_process(
                dl_count,
                Path(output_folder),
                button_coords,
                settings["browser_debug_port"],
                st.session_state.mj_download_stop_flag,
                st.session_state.mj_download_progress,
                mj_status,
                viewport=viewport,
                coordinates_viewport=coord_vp,
                debug_show_clicks=debug_show_clicks,
            )
            st.session_state.mj_download_process = proc
            st.session_state.mj_download_manager = manager
            st.session_state.mj_download_mgr_stop = mgr_stop
            st.session_state.mj_download_mgr_status = mgr_status
            st.session_state.mj_download_progress = mgr_progress
            st.rerun()

        if dl_status == "running":
            prog = st.session_state.mj_download_progress
            cur = prog.get("current", 0)
            tot = prog.get("total", 1)
            st.progress(min(1.0, cur / tot) if tot > 0 else 0, text=f"Downloading {cur}/{tot}...")
        elif dl_status == "completed":
            paths = mj_status.get("downloaded_paths", [])
            st.success(f"Downloaded {len(paths)} image(s).")
        elif dl_status == "stopped":
            paths = mj_status.get("downloaded_paths", [])
            st.warning(f"Stopped. Downloaded {len(paths)} file(s).")
        elif dl_status == "error":
            st.error(mj_status.get("download_error", "Unknown error"))

    # Downloaded images gallery: show folder selector when batch has multiple design folders
    gallery_folder = Path(output_folder)
    design_images_folders = st.session_state.get("mj_design_images_folders", {})
    if len(design_images_folders) >= 2:
        folder_options = []
        for idx, path in sorted(design_images_folders.items()):
            if generated_designs and idx < len(generated_designs):
                title = generated_designs[idx].get("title", "Untitled") or "Untitled"
                folder_options.append((path, f"{title} ({Path(path).name})"))
            else:
                folder_options.append((path, f"Design {idx + 1} ({Path(path).name})"))
        if folder_options:
            default_idx = 0
            if mj_status.get("batch_current_index") and mj_status.get("batch_total"):
                cur = mj_status.get("batch_current_index", 1) - 1
                if cur < len(folder_options):
                    default_idx = cur
            labels = [opt[1] for opt in folder_options]
            paths_list = [opt[0] for opt in folder_options]
            sel_key = "mj_gallery_folder_sel"
            selected = st.selectbox(
                "View images from",
                range(len(labels)),
                format_func=lambda i: labels[i],
                index=min(default_idx, len(labels) - 1),
                key=sel_key,
            )
            gallery_folder = Path(paths_list[selected])
    _render_downloaded_images_gallery(gallery_folder, mj_status, state)

    # --- Cover (background images) section ---
    st.divider()
    st.subheader("Cover (background images)")
    st.caption("Generate full-color cover backgrounds (no text). Add your title in Canva or another tool.")
    cover_folder = base_output / "cover"
    cover_folder.mkdir(parents=True, exist_ok=True)
    _workflow_step_indicator(mj_cover_status)

    default_cover_prompts = state.get("cover_prompts", [])
    default_cover_text = "\n".join(default_cover_prompts) if default_cover_prompts else ""
    raw_cover = st.text_area(
        "Cover Prompts",
        value=default_cover_text,
        height=80,
        key="mj_cover_prompts_area",
        placeholder="One prompt per line (e.g. book cover, no text, --ar 2:3)...",
    )
    cover_prompts_list = [line.strip() for line in raw_cover.strip().splitlines() if line.strip()]
    if cover_prompts_list:
        st.caption(f"{len(cover_prompts_list)} cover prompt(s) queued")

    mj_cover_automated_process = st.session_state.get("mj_cover_automated_process")
    cover_automated_running = mj_cover_automated_process is not None and mj_cover_automated_process.is_alive()
    cover_pub_running = mj_cover_status.get("publish_status") == "running"
    cover_pub_proc = st.session_state.get("mj_cover_publish_process")
    cover_pub_process_alive = cover_pub_proc is not None and cover_pub_proc.is_alive()
    cover_step_running = (
        cover_pub_running
        or mj_cover_status.get("uxd_action_status") == "running"
        or mj_cover_status.get("download_status") == "running"
    )

    cover_num_images = len(cover_prompts_list) * 4 if cover_prompts_list else 0
    cover_est_min_auto = (
        len(cover_prompts_list) * sec_per_prompt + cover_num_images * sec_per_upscale
    ) / 60 if cover_prompts_list else 0
    cover_est_text_auto = f" (~{cover_est_min_auto:.0f} min)" if cover_prompts_list and cover_est_min_auto >= 1 else ""

    cover_run_automated = st.checkbox(
        "Run full automated (cover)",
        value=False,
        key="mj_cover_run_automated_checkbox",
        help=f"Publish → Upscale all → Download all{cover_est_text_auto}",
    )

    col_cover_pub, col_cover_stop = st.columns([4, 1])
    with col_cover_pub:
        cover_pub_clicked = st.button(
            "Publish (cover)",
            type="primary",
            key="mj_cover_publish_btn",
            disabled=not (cover_prompts_list and browser_connected and button_coords)
            or cover_pub_process_alive
            or cover_automated_running
            or automated_running
            or step_running,
            help="Submit cover prompts only." if not cover_run_automated else f"Full pipeline (cover){cover_est_text_auto}",
        )
    if cover_pub_clicked and cover_prompts_list and browser_connected and button_coords:
        viewport = cfg.get("viewport") or {"width": 1920, "height": 1080}
        coord_vp = cfg.get("coordinates_viewport") or {"width": 1920, "height": 1080}
        if cover_run_automated:
            st.session_state.mj_cover_automated_stop_flag["stop"] = False
            shared = st.session_state.mj_cover_automated_shared
            shared["publish_status"] = "idle"
            shared["publish_error"] = ""
            shared["uxd_action_status"] = "idle"
            shared["uxd_action_error"] = ""
            shared["download_status"] = "idle"
            shared["download_error"] = ""
            shared["downloaded_paths"] = []
            proc, manager, mgr_stop, mgr_shared, mgr_publish, mgr_uxd, mgr_download = run_automated_process(
                cover_prompts_list,
                button_coords,
                settings["browser_debug_port"],
                cover_folder,
                st.session_state.mj_cover_automated_stop_flag,
                shared,
                st.session_state.mj_cover_publish_progress,
                st.session_state.mj_cover_uxd_progress,
                st.session_state.mj_cover_download_progress,
                viewport=viewport,
                coordinates_viewport=coord_vp,
                debug_show_clicks=debug_show_clicks,
            )
            st.session_state.mj_cover_automated_process = proc
            st.session_state.mj_cover_automated_manager = manager
            st.session_state.mj_cover_automated_mgr_stop = mgr_stop
            st.session_state.mj_cover_automated_shared = mgr_shared
            st.session_state.mj_cover_publish_progress = mgr_publish
            st.session_state.mj_cover_uxd_progress = mgr_uxd
            st.session_state.mj_cover_download_progress = mgr_download
        else:
            st.session_state.mj_cover_publish_stop_flag["stop"] = False
            mj_cover_status["publish_status"] = "running"
            mj_cover_status["publish_error"] = ""
            proc, manager, mgr_stop, mgr_progress, mgr_status = run_publish_process(
                cover_prompts_list,
                button_coords,
                settings["browser_debug_port"],
                st.session_state.mj_cover_publish_stop_flag,
                st.session_state.mj_cover_publish_progress,
                mj_cover_status,
                viewport=viewport,
                coordinates_viewport=coord_vp,
                debug_show_clicks=debug_show_clicks,
            )
            st.session_state.mj_cover_publish_process = proc
            st.session_state.mj_cover_publish_manager = manager
            st.session_state.mj_cover_publish_mgr_stop = mgr_stop
            st.session_state.mj_cover_publish_mgr_status = mgr_status
            st.session_state.mj_cover_publish_progress = mgr_progress
        st.rerun()
    with col_cover_stop:
        if cover_automated_running and st.button("Stop", key="mj_cover_automated_stop_btn"):
            mgr_stop = st.session_state.get("mj_cover_automated_mgr_stop")
            if mgr_stop is not None:
                mgr_stop["stop"] = True
            else:
                st.session_state.mj_cover_automated_stop_flag["stop"] = True
            st.rerun()
        elif cover_pub_process_alive and st.button("Stop", key="mj_cover_publish_stop_btn"):
            mgr_stop = st.session_state.get("mj_cover_publish_mgr_stop")
            if mgr_stop is not None:
                mgr_stop["stop"] = True
            else:
                st.session_state.mj_cover_publish_stop_flag["stop"] = True
            st.rerun()

    # Cover automated progress
    if cover_automated_running:
        pub_s = mj_cover_status.get("publish_status", "idle")
        uxd_s = mj_cover_status.get("uxd_action_status", "idle")
        dl_s = mj_cover_status.get("download_status", "idle")
        pub_prog = st.session_state.mj_cover_publish_progress
        uxd_prog = st.session_state.mj_cover_uxd_progress
        dl_prog = st.session_state.mj_cover_download_progress
        parts = []
        if pub_s == "running":
            phase = pub_prog.get("phase", "submit")
            if phase == "submit":
                sc, stotal = pub_prog.get("submit_current", 0), pub_prog.get("submit_total", 1)
                parts.append(f"Cover Publish: {sc}/{stotal} prompts")
            else:
                parts.append("Cover Publish: ...")
        elif pub_s in ("completed", "stopped"):
            parts.append("Cover Publish: done")
        if uxd_s == "running":
            cur = uxd_prog.get("uxd_current_image")
            tot = uxd_prog.get("uxd_total_images")
            if cur is not None and tot:
                parts.append(f"Cover Upscale: {cur}/{tot}")
            else:
                parts.append("Cover Upscale: ...")
        elif uxd_s in ("completed", "stopped"):
            parts.append("Cover Upscale: done")
        if dl_s == "running":
            c, t = dl_prog.get("current", 0), dl_prog.get("total", 1)
            parts.append(f"Cover Download: {c}/{t}")
        elif dl_s in ("completed", "stopped"):
            parts.append("Cover Download: done")
        if parts:
            st.caption(" | ".join(parts))

    if mj_cover_status.get("publish_status") == "running" and not cover_automated_running:
        st.info("Publishing cover prompts...")
    elif mj_cover_status.get("publish_status") == "completed" and not cover_automated_running:
        st.success("Cover prompts published. Use Upscale/Vary and Download below for cover images.")
    elif mj_cover_status.get("publish_error"):
        st.error(mj_cover_status["publish_error"])

    # Cover: Upscale and Vary (hidden when "Run full automated (cover)" is ticked)
    if not (cover_run_automated or cover_automated_running):
        st.divider()
        _next_step_guidance(mj_cover_status, section="upscale")

        st.subheader("Upscale and Vary")
        st.caption(
            "After images appear, select actions and count, then Run. "
            "Upscale: 1 new per original. Vary: 4 new per original."
        )

        cover_uxd_status = mj_cover_status.get("uxd_action_status", "idle")
        cover_uxd_process = st.session_state.mj_cover_uxd_process
        cover_uxd_alive = cover_uxd_process is not None and cover_uxd_process.is_alive()

        cover_uv_count = int(
            st.number_input(
                "Count",
                min_value=1,
                max_value=20,
                value=4,
                key="mj_cover_uxd_count",
                help="Number of images to upscale or vary.",
            )
        )

        col1, col2, col3, col4 = st.columns(4)
        cover_selected_keys = []
        with col1:
            if st.checkbox("Upscale Subtle", value=False, key="mj_cover_uxd_subtle"):
                cover_selected_keys.append("upscale_subtle")
        with col2:
            if st.checkbox("Upscale Creative", value=False, key="mj_cover_uxd_creative"):
                cover_selected_keys.append("upscale_creative")
        with col3:
            if st.checkbox("Vary Subtle", value=False, key="mj_cover_uxd_vary_subtle"):
                cover_selected_keys.append("vary_subtle")
        with col4:
            if st.checkbox("Vary Strong", value=False, key="mj_cover_uxd_vary_strong"):
                cover_selected_keys.append("vary_strong")

        total_new = _total_uxd_images(cover_selected_keys, cover_uv_count) if cover_selected_keys else 0
        sec_per_ux = cfg.get("waits", {}).get("seconds_per_upscale_estimate", 20)
        est_min_ux = total_new * sec_per_ux / 60 if total_new else 0
        est_help = f" (~{est_min_ux:.0f} min)" if total_new and est_min_ux >= 1 else ""

        col_run, col_stop_ux = st.columns([4, 1])
        with col_run:
            uv_run_clicked = st.button(
                "Run",
                key="mj_cover_uxd_run_btn",
                type="secondary",
                disabled=not (button_coords and cover_selected_keys and cover_uxd_status != "running" and not cover_uxd_alive),
                help=f"Select at least one action.{est_help}",
            )
        with col_stop_ux:
            if cover_uxd_alive and st.button("Stop", key="mj_cover_uxd_stop_btn"):
                mgr_stop = st.session_state.get("mj_cover_uxd_mgr_stop")
                if mgr_stop is not None:
                    mgr_stop["stop"] = True
                else:
                    st.session_state.mj_cover_uxd_stop_flag["stop"] = True
                st.rerun()

        if uv_run_clicked and browser_connected and cover_selected_keys:
            st.session_state.mj_cover_uxd_stop_flag["stop"] = False
            mj_cover_status["uxd_action_status"] = "running"
            mj_cover_status["uxd_action_error"] = ""
            total_new = _total_uxd_images(cover_selected_keys, cover_uv_count)
            st.session_state.mj_cover_uxd_progress = {
                "elapsed": 0,
                "total": 0,
                "phase": "click",
                "images_estimated": total_new,
            }
            viewport = cfg.get("viewport") or {"width": 1920, "height": 1080}
            coord_vp = cfg.get("coordinates_viewport") or {"width": 1920, "height": 1080}
            proc, manager, mgr_stop, mgr_progress, mgr_status = run_uxd_action_process(
                cover_selected_keys,
                cover_uv_count,
                cover_folder,
                button_coords,
                settings["browser_debug_port"],
                st.session_state.mj_cover_uxd_stop_flag,
                total_new,
                st.session_state.mj_cover_uxd_progress,
                mj_cover_status,
                viewport=viewport,
                coordinates_viewport=coord_vp,
                debug_show_clicks=debug_show_clicks,
            )
            st.session_state.mj_cover_uxd_process = proc
            st.session_state.mj_cover_uxd_manager = manager
            st.session_state.mj_cover_uxd_mgr_stop = mgr_stop
            st.session_state.mj_cover_uxd_mgr_status = mgr_status
            st.session_state.mj_cover_uxd_progress = mgr_progress
            st.rerun()

        if cover_uxd_status == "running":
            prog = st.session_state.mj_cover_uxd_progress
            cur_img = prog.get("uxd_current_image")
            tot_img = prog.get("uxd_total_images")
            if cur_img is not None and tot_img and tot_img > 0:
                pct = cur_img / tot_img
                st.progress(min(1.0, pct), text=f"Upscaling image {cur_img}/{tot_img}...")
        elif cover_uxd_status == "completed":
            st.success("Done. Allow ~20s per new image before downloading.")
        elif cover_uxd_status == "stopped":
            st.warning("Stopped by user.")
        elif cover_uxd_status == "error":
            st.error(mj_cover_status.get("uxd_action_error", "Unknown error"))

    # Cover: Download (hidden when "Run full automated (cover)" is ticked)
    if not (cover_run_automated or cover_automated_running):
        st.divider()
        _next_step_guidance(mj_cover_status, section="download")

        st.subheader("Download")
        st.caption("Download images from the detail view to your output folder.")

        cover_dl_status = mj_cover_status.get("download_status", "idle")
        cover_dl_process = st.session_state.mj_cover_download_process
        cover_dl_alive = cover_dl_process is not None and cover_dl_process.is_alive()

        cover_dl_count = int(
            st.number_input(
                "Images to download",
                min_value=1,
                max_value=9999,
                value=4,
                key="mj_cover_dl_count",
                help="Number of images to download.",
            )
        )

        col_dl, col_stop_dl = st.columns([4, 1])
        with col_dl:
            dl_clicked = st.button(
                "Download",
                key="mj_cover_dl_btn",
                type="secondary",
                disabled=not button_coords or cover_dl_alive,
                help="Download images to the output/cover folder.",
            )
        with col_stop_dl:
            if cover_dl_alive and st.button("Stop", key="mj_cover_dl_stop_btn"):
                mgr_stop = st.session_state.get("mj_cover_download_mgr_stop")
                if mgr_stop is not None:
                    mgr_stop["stop"] = True
                else:
                    st.session_state.mj_cover_download_stop_flag["stop"] = True
                st.rerun()

        if dl_clicked and browser_connected:
            st.session_state.mj_cover_download_stop_flag["stop"] = False
            mj_cover_status["download_status"] = "running"
            mj_cover_status["download_error"] = ""
            st.session_state.mj_cover_download_progress = {"current": 0, "total": cover_dl_count}
            viewport = cfg.get("viewport") or {"width": 1920, "height": 1080}
            coord_vp = cfg.get("coordinates_viewport") or {"width": 1920, "height": 1080}
            proc, manager, mgr_stop, mgr_progress, mgr_status = run_download_process(
                cover_dl_count,
                cover_folder,
                button_coords,
                settings["browser_debug_port"],
                st.session_state.mj_cover_download_stop_flag,
                st.session_state.mj_cover_download_progress,
                mj_cover_status,
                viewport=viewport,
                coordinates_viewport=coord_vp,
                debug_show_clicks=debug_show_clicks,
            )
            st.session_state.mj_cover_download_process = proc
            st.session_state.mj_cover_download_manager = manager
            st.session_state.mj_cover_download_mgr_stop = mgr_stop
            st.session_state.mj_cover_download_mgr_status = mgr_status
            st.session_state.mj_cover_download_progress = mgr_progress
            st.rerun()

        if cover_dl_status == "running":
            prog = st.session_state.mj_cover_download_progress
            cur = prog.get("current", 0)
            tot = prog.get("total", 1)
            st.progress(min(1.0, cur / tot) if tot > 0 else 0, text=f"Downloading {cur}/{tot}...")
        elif cover_dl_status == "completed":
            paths = mj_cover_status.get("downloaded_paths", [])
            st.success(f"Downloaded {len(paths)} cover image(s).")
        elif cover_dl_status == "stopped":
            paths = mj_cover_status.get("downloaded_paths", [])
            st.warning(f"Stopped. Downloaded {len(paths)} file(s).")
        elif cover_dl_status == "error":
            st.error(mj_cover_status.get("download_error", "Unknown error"))

    _render_downloaded_images_gallery(cover_folder, mj_cover_status, state, key_prefix="cover_")

    st.session_state.workflow_state = state

    # Process crash detection: if process died while "running", update status
    process_just_finished = False
    pub_proc = st.session_state.get("mj_publish_process")
    uxd_proc = st.session_state.get("mj_uxd_process")
    dl_proc = st.session_state.get("mj_download_process")
    auto_proc = st.session_state.get("mj_automated_process")
    if (
        mj_status.get("publish_status") == "running"
        and pub_proc is not None
        and not pub_proc.is_alive()
    ):
        prog = st.session_state.get("mj_publish_progress", {})
        batch_cur = prog.get("batch_current", 0)
        batch_tot = prog.get("batch_total", 1)
        phase = prog.get("phase", "")
        if batch_tot > 0 and batch_cur >= batch_tot and phase in ("wait", "finalize", "submit"):
            mj_status["publish_status"] = "completed"
        else:
            mj_status["publish_status"] = "error"
            mj_status["publish_error"] = "Publish process exited unexpectedly."
        process_just_finished = True
    if (
        mj_status.get("uxd_action_status") == "running"
        and uxd_proc is not None
        and not uxd_proc.is_alive()
    ):
        uxd_prog = st.session_state.get("mj_uxd_progress", {})
        uxd_batch_cur = uxd_prog.get("uxd_batch_current", 0)
        uxd_batch_tot = uxd_prog.get("uxd_total_batches", 1)
        uxd_phase = uxd_prog.get("phase", "")
        if uxd_batch_tot > 0 and uxd_batch_cur >= uxd_batch_tot and uxd_phase in ("wait", "finalize", "click"):
            mj_status["uxd_action_status"] = "completed"
        else:
            mj_status["uxd_action_status"] = "error"
            mj_status["uxd_action_error"] = "Upscale/Vary process exited unexpectedly."
        process_just_finished = True
    if (
        mj_status.get("download_status") == "running"
        and dl_proc is not None
        and not dl_proc.is_alive()
    ):
        mj_status["download_status"] = "error"
        mj_status["download_error"] = "Download process exited unexpectedly."
        process_just_finished = True
    # When automated process finishes: sync final status from shared, then merge batch_results
    if auto_proc is not None and not auto_proc.is_alive():
        shared = st.session_state.get("mj_automated_shared", {})
        for k in ("publish_status", "publish_error", "uxd_action_status", "uxd_action_error", "download_status", "download_error"):
            if k in shared:
                mj_status[k] = shared[k]
        batch_results = shared.get("batch_results", [])
        if batch_results:
            folders = dict(st.session_state.get("mj_design_images_folders", {}))
            for r in batch_results:
                idx = r.get("design_index")
                path = r.get("folder_path")
                if idx is not None and path:
                    folders[idx] = path
            st.session_state.mj_design_images_folders = folders

    if (
        auto_proc is not None
        and not auto_proc.is_alive()
        and (pub_proc is None or not pub_proc.is_alive())
        and (uxd_proc is None or not uxd_proc.is_alive())
        and (dl_proc is None or not dl_proc.is_alive())
        and (
            mj_status.get("publish_status") == "running"
            or mj_status.get("uxd_action_status") == "running"
            or mj_status.get("download_status") == "running"
        )
    ):
        if st.session_state.get("mj_automated_shared", {}).get("publish_status") != "error":
            mj_status["publish_status"] = "error"
            mj_status["publish_error"] = "Automated workflow process exited unexpectedly."
            if "mj_automated_shared" in st.session_state:
                st.session_state.mj_automated_shared["publish_status"] = "error"
                st.session_state.mj_automated_shared["publish_error"] = "Automated workflow process exited unexpectedly."
        process_just_finished = True
    if process_just_finished:
        st.rerun()
    # Auto-refresh while any MJ process is running (inside or cover)
    cover_auto_proc = st.session_state.get("mj_cover_automated_process")
    process_running = (
        (mj_automated_process and mj_automated_process.is_alive())
        or (mj_status.get("publish_status") == "running" and pub_proc and pub_proc.is_alive())
        or (mj_status.get("uxd_action_status") == "running" and uxd_proc and uxd_proc.is_alive())
        or (mj_status.get("download_status") == "running" and dl_proc and dl_proc.is_alive())
        or (cover_auto_proc and cover_auto_proc.is_alive())
    )
    if process_running:
        time.sleep(cfg.get("waits", {}).get("ui_refresh_sec", 5))
        st.rerun()
