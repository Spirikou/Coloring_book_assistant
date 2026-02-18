"""Image generation tab UI."""

import streamlit as st
import os
from pathlib import Path

from features.image_generation.monitor import get_images_in_folder
from features.image_generation.image_utils import create_thumbnail


def render_image_generation_tab(state: dict):
    """Render Image Generation tab with folder monitoring and click-to-select image grid."""
    st.markdown("## Image Generation")
    default_folder = state.get("images_folder_path", "./generated_images/")
    folder_path = st.text_input(
        "Image Folder Path",
        value=default_folder,
        help="Path to the folder containing your generated images",
        key="image_folder_input"
    )
    images = get_images_in_folder(folder_path) if folder_path and os.path.exists(folder_path) else []
    found_count = len(images)
    state["images_folder_path"] = folder_path
    btn1, btn2, btn3, _ = st.columns([1, 1, 1, 5])
    with btn1:
        if st.button("Refresh", key="refresh_images"):
            st.rerun()
    with btn2:
        if st.button("Select All", key="select_all_images", disabled=found_count == 0):
            if found_count > 0:
                state["selected_images"] = images
                st.session_state.workflow_state = state
                st.rerun()
    with btn3:
        if st.button("Clear", key="clear_image_selection"):
            state["selected_images"] = []
            st.session_state.workflow_state = state
            st.rerun()

    if not folder_path:
        st.info("Enter a folder path.")
        return

    if not os.path.exists(folder_path):
        st.info("Folder not found.")
        return

    if found_count == 0:
        st.info("Folder empty.")
        state["uploaded_images"] = []
        state["images_ready"] = False
        state["selected_images"] = []
        st.session_state.workflow_state = state
        return

    current_selected = set(state.get("selected_images", []))
    if not current_selected:
        current_selected = set(images)

    sel_count = len(current_selected)
    sel_text = f"{sel_count} selected" if sel_count < found_count else "all"
    st.caption(f"Found {found_count} images. {sel_text} (empty = use all). Click checkboxes to select.")

    cols_per_row = 5
    thumbnail_size = (140, 140)
    new_selected = []
    for i in range(0, len(images), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, img_path in enumerate(images[i:i + cols_per_row]):
            with cols[j]:
                try:
                    thumbnail = create_thumbnail(img_path, thumbnail_size)
                    if thumbnail:
                        st.image(thumbnail, use_container_width=True)
                    fname = Path(img_path).name
                    short_name = fname[:20] + "..." if len(fname) > 20 else fname
                    key = f"img_sel_{i + j}_{hash(img_path) % 100000}"
                    is_checked = st.checkbox(short_name, value=img_path in current_selected, key=key)
                    if is_checked:
                        new_selected.append(img_path)
                except Exception as e:
                    st.caption(Path(img_path).name)
                    st.error(str(e)[:30])

    state["selected_images"] = new_selected
    state["uploaded_images"] = images
    state["images_ready"] = len(images) > 0
    st.session_state.workflow_state = state
