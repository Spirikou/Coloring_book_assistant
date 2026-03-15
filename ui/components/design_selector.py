"""Shared design package selector component for loading designs from any tab.

When to use which:
- render_tab_design_selector: Use at the top of a tab (Design Gen, Image Gen, Canva, Pinterest)
  when you want a single row: [Design package ▼] [Load for this tab]. Loads into workflow_state
  and optionally into tab-specific state. Returns True if a design is loaded.
- render_design_package_selector: Use in the sidebar (compact=True) or in Design Gen for the
  full package list with Load/Delete per package (compact=False). Does not return a value.
"""

import streamlit as st

from core.persistence import (
    list_design_packages,
    load_design_package,
    delete_design_package,
)


def render_tab_design_selector(
    key_prefix: str,
    *,
    persist_to_workflow: bool = True,
    tab_state_key: str | None = None,
) -> bool:
    """
    Render design package selector row at top of a tab: [Design package ▼] [Load for this tab].
    Always visible so user can switch design from any tab. Loads into workflow_state and optionally
    into tab-specific state (e.g. canva_tab_state).

    Returns True if a design is currently loaded (workflow_state or tab_state_key has state with title).
    """
    packages = list_design_packages()
    workflow_state = st.session_state.get("workflow_state")
    tab_state = st.session_state.get(tab_state_key) if tab_state_key else None
    has_design = bool((workflow_state or tab_state) and (workflow_state or tab_state).get("title"))

    # Left-aligned: label above, then dropdown and button on same horizontal line (collapsed label so they align)
    st.caption("**Design package**")
    if not packages:
        st.caption("No design packages yet. Go to the **Design Generation** tab to create one.")
        return has_design
    options = [f"{p['title']} ({p['image_count']} imgs)" for p in packages]
    col_sel, col_btn = st.columns([4, 1])
    with col_sel:
        idx = st.selectbox(
            "Design package",
            range(len(options)),
            format_func=lambda i: options[i],
            key=f"{key_prefix}_tab_design_select",
            label_visibility="collapsed",
        )
    with col_btn:
        if st.button("Load for this tab", key=f"{key_prefix}_tab_design_load", use_container_width=True):
            loaded = load_design_package(packages[idx]["path"])
            if loaded:
                if persist_to_workflow:
                    st.session_state.workflow_state = loaded
                if tab_state_key:
                    st.session_state[tab_state_key] = loaded
                st.rerun()
            else:
                st.error("Failed to load")
    return has_design


def render_design_package_selector(
    compact: bool = False,
    key_prefix: str = "design_sel",
) -> None:
    """
    Render design package selector UI.

    Args:
        compact: If True, show compact sidebar UI (selectbox + Load). If False, show full
            expanders with Load/Delete per package.
        key_prefix: Prefix for Streamlit widget keys to avoid collisions when rendered
            in multiple places.
    """
    packages = list_design_packages()
    workflow_state = st.session_state.get("workflow_state")
    current_path = (workflow_state or {}).get("design_package_path", "")

    if compact:
        _render_compact(packages, current_path, key_prefix)
    else:
        _render_full(packages, key_prefix)


def _render_compact(
    packages: list,
    current_path: str,
    key_prefix: str,
) -> None:
    """Compact sidebar UI: selectbox + Load button."""
    if current_path:
        # Find current package title for display
        current_title = "Unknown"
        for p in packages:
            if p["path"] == current_path:
                current_title = p["title"]
                break
        st.caption(f"Current: {current_title}")

    if not packages:
        st.caption("No packages. Go to the **Design Generation** tab to create one.")
        return

    options = ["— None —", "— Clear —"] + [
        f"{p['title']} ({p['image_count']} imgs)" for p in packages
    ]
    # Map display string back to action: index 0 = None, 1 = Clear, 2+ = load package
    selected = st.selectbox(
        "Design package",
        options=options,
        key=f"{key_prefix}_select",
        label_visibility="collapsed",
    )
    if st.button("Load", key=f"{key_prefix}_load"):
        idx = options.index(selected)
        if idx == 0:
            # — None —: no-op
            pass
        elif idx == 1:
            # — Clear —
            st.session_state.workflow_state = None
            st.rerun()
        else:
            pkg = packages[idx - 2]
            loaded = load_design_package(pkg["path"])
            if loaded:
                st.session_state.workflow_state = loaded
                st.rerun()
            else:
                st.error("Failed to load")


def _render_full(packages: list, key_prefix: str) -> None:
    """Full per-tab UI: expanders with Load/Delete per package."""
    if not packages:
        st.caption("No design packages yet. Go to the **Design Generation** tab to create one.")
        return

    for pkg in packages[:10]:
        with st.expander(
            f"{pkg['title']} ({pkg['image_count']} images)",
            expanded=False,
        ):
            st.caption(f"Saved: {pkg['saved_at']}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Load", key=f"{key_prefix}_load_{pkg['name']}"):
                    loaded = load_design_package(pkg["path"])
                    if loaded:
                        st.session_state.workflow_state = loaded
                        st.success("Design package loaded!")
                        st.rerun()
                    else:
                        st.error("Failed to load")
            with col2:
                if st.button("Delete", key=f"{key_prefix}_del_{pkg['name']}"):
                    if delete_design_package(pkg["path"]):
                        st.success("Deleted!")
                        st.rerun()
                    else:
                        st.error("Failed to delete")
