"""Bulk-run helpers for Canva and Pinterest tabs.

These helpers keep the Streamlit UI code small and reduce the risk of
duplicating widgets/keys when iterating on the UI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from core.notifications import notify_completed


def build_design_package_options(packages: list[dict]) -> dict[str, str]:
    """Return a stable, collision-resistant label->path map for multiselects."""
    options: dict[str, str] = {}
    for p in packages:
        title = (p.get("title") or "Untitled").strip() or "Untitled"
        imgs = int(p.get("image_count") or 0)
        name = (p.get("name") or Path(p.get("path") or "").name or "pkg").strip()
        label = f"{title} ({imgs} imgs) — {name}"
        # Ensure uniqueness even if two packages share title/name
        if label in options:
            label = f"{label} — {Path(p.get('path') or '').name}"
        options[label] = str(p.get("path") or "")
    return options


def run_bulk_canva(
    *,
    st,  # streamlit module
    workflow,
    selected_paths: list[str],
    page_size: str,
    margin_percent: float,
    outline_height_percent: float,
    blank_between: bool,
    get_images_in_folder: Callable[[str], list[str]],
    debug_mode: bool = False,
) -> None:
    """Run Canva sequentially for selected design package folders."""
    st.info("Starting bulk Canva run. This tab will stay busy until all designs are processed.")
    progress_area = st.empty()
    for idx, folder in enumerate(selected_paths, start=1):
        images_folder = folder
        image_files = get_images_in_folder(images_folder)
        label = Path(folder).name
        if not image_files:
            with progress_area.container():
                st.warning(f"[{idx}/{len(selected_paths)}] Skipping `{label}` — no images found in:\n`{images_folder}`")
            continue

        with progress_area.container():
            st.caption(f"[{idx}/{len(selected_paths)}] Running Canva for **{label}**")

        try:
            def bulk_progress_callback(progress_update: dict) -> None:
                with progress_area.container():
                    msg = progress_update.get("message") or progress_update.get("status", "")
                    st.caption(f"[{idx}/{len(selected_paths)}] {msg or 'In progress...'}")

            workflow.create_design(
                images_folder=images_folder,
                page_size=page_size,
                margin_percent=margin_percent,
                outline_height_percent=outline_height_percent,
                blank_between=blank_between,
                progress_callback=bulk_progress_callback,
                selected_images=None,
                debug_mode=debug_mode,
            )
            notify_completed(
                "task.completed",
                task_id=f"{folder}:{idx}",
                task_name="Canva Design",
                task_index=idx,
                task_total=len(selected_paths),
                result_summary=label,
            )
        except Exception as e:
            import traceback

            with progress_area.container():
                st.error(f"[{idx}/{len(selected_paths)}] Error while processing `{label}`: {e}")
                st.code(traceback.format_exc())

    with progress_area.container():
        st.success("Bulk Canva run completed.")
    notify_completed(
        "workflow.completed",
        task_id=f"bulk_canva:{id(selected_paths)}",
        task_name="Bulk Canva",
        result_summary=f"{len(selected_paths)} design(s)",
    )


def run_bulk_pinterest(
    *,
    st,  # streamlit module
    workflow,
    selected_design_paths: list[str],
    load_design_package: Callable[[str], dict | None],
    get_images_in_folder: Callable[[str], list[str]],
    board_name: str,
    max_pins_per_design: int,
) -> None:
    """Run Pinterest sequentially for selected design packages."""
    st.info("Starting bulk Pinterest run. This tab will stay busy until all designs are processed.")
    progress_area = st.empty()

    for idx, design_path in enumerate(selected_design_paths, start=1):
        design_state = load_design_package(design_path) or {}
        images_folder = design_state.get("images_folder_path") or design_path
        image_files = get_images_in_folder(images_folder)
        label = Path(design_path).name

        if not image_files:
            with progress_area.container():
                st.warning(f"[{idx}/{len(selected_design_paths)}] Skipping `{label}` — no images found in:\n`{images_folder}`")
            continue

        image_files.sort()
        effective_images = image_files
        total_before_limit = len(image_files)
        if max_pins_per_design > 0:
            effective_images = image_files[:max_pins_per_design]

        with progress_area.container():
            if max_pins_per_design > 0 and total_before_limit > max_pins_per_design:
                st.caption(
                    f"[{idx}/{len(selected_design_paths)}] Publishing {len(effective_images)} image(s) "
                    f"(first {max_pins_per_design} of {total_before_limit}) for **{label}**"
                )
            else:
                st.caption(f"[{idx}/{len(selected_design_paths)}] Publishing {len(effective_images)} image(s) for **{label}**")

        try:
            # Always copy subset for bulk to avoid mixing sessions.
            folder_path = workflow.prepare_publishing_folder(
                design_state=design_state,
                images_folder=images_folder,
                selected_images=effective_images,
                use_folder_directly=False,
            )

            def bulk_progress_callback(progress_update: dict) -> None:
                with progress_area.container():
                    cur = progress_update.get("current", 0)
                    tot = progress_update.get("total", 0)
                    msg = progress_update.get("message", "")
                    if tot > 0:
                        st.caption(f"[{idx}/{len(selected_design_paths)}] {msg or 'Publishing pins...'} ({cur}/{tot})")
                    else:
                        st.caption(f"[{idx}/{len(selected_design_paths)}] {msg or 'Publishing pins...'}")

            workflow.publish_to_pinterest(
                folder_path=folder_path,
                board_name=board_name,
                progress_callback=bulk_progress_callback,
            )
            notify_completed(
                "task.completed",
                task_id=f"{design_path}:{idx}",
                task_name="Pinterest Publish",
                task_index=idx,
                task_total=len(selected_design_paths),
                result_summary=label,
            )
        except Exception as e:
            import traceback

            with progress_area.container():
                st.error(f"[{idx}/{len(selected_design_paths)}] Error while publishing `{label}`: {e}")
                st.code(traceback.format_exc())

    with progress_area.container():
        st.success("Bulk Pinterest run completed.")
    notify_completed(
        "workflow.completed",
        task_id=f"bulk_pinterest:{id(selected_design_paths)}",
        task_name="Bulk Pinterest",
        result_summary=f"{len(selected_design_paths)} design(s)",
    )

