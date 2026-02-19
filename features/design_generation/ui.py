"""Design generation tab UI."""

import streamlit as st
import json
from pathlib import Path

from core.persistence import save_workflow_state, load_workflow_state, list_saved_states, delete_saved_state
from features.design_generation.workflow import (
    run_coloring_book_agent,
    run_design_for_concept,
    run_design_step_for_concept,
    create_coloring_book_graph,
    rerun_design_with_modifications,
    DESIGN_STEPS,
)
from features.design_generation.tools.content_tools import generate_concept_variations
from features.design_generation.constants import (
    MAX_SELECTED_CONCEPTS,
    MIN_CONCEPT_VARIATIONS,
    MAX_CONCEPT_VARIATIONS,
)

STEP_DISPLAY_NAMES = [
    "Building theme context from concept",
    "Generating title and description",
    "Generating MidJourney prompts",
    "Generating SEO keywords",
]


def render_attempt(attempt: dict, attempt_num: int, component_type: str):
    """Render a single attempt with content and evaluation."""
    evaluation = attempt.get("evaluation", {})
    content = attempt.get("content", {})
    feedback = attempt.get("feedback", "")
    score = evaluation.get("score", 0)
    passed = evaluation.get("passed", False) or score >= 80

    if score >= 80:
        icon = "✓"
    elif score >= 60:
        icon = "~"
    else:
        icon = "✗"

    with st.expander(f"Attempt {attempt_num} - {icon} Score: {score}/100", expanded=(not passed)):
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("### Generated Content")

            if component_type == "title":
                title = content.get("title", "") if isinstance(content, dict) else ""
                desc = content.get("description", "") if isinstance(content, dict) else ""

                st.markdown("**Title:**")
                st.info(f"{title} ({len(title)} chars)")

                st.markdown("**Description:**")
                word_count = len(desc.split()) if desc else 0
                st.text_area("Description text", desc, height=150, disabled=True, label_visibility="collapsed", key=f"desc_{component_type}_{attempt_num}")
                st.caption(f"Word count: {word_count}")

            elif component_type == "prompts":
                prompts = content if isinstance(content, list) else []
                st.markdown(f"**Prompts Generated:** {len(prompts)}")

                if prompts:
                    for i, p in enumerate(prompts[:3], 1):
                        st.code(p, language="text")
                    if len(prompts) > 3:
                        st.caption(f"... and {len(prompts) - 3} more prompts")

            elif component_type == "keywords":
                keywords = content if isinstance(content, list) else []
                st.markdown(f"**Keywords Generated:** {len(keywords)}")

                if keywords:
                    keyword_str = " | ".join(keywords)
                    st.write(keyword_str)

        with col2:
            st.markdown("### Evaluator Assessment")

            st.metric("Quality Score", f"{score}/100",
                     delta="PASSED" if passed else "NEEDS IMPROVEMENT",
                     delta_color="normal" if passed else "inverse")

            if component_type == "title":
                title_issues = evaluation.get("title_issues", [])
                desc_issues = evaluation.get("description_issues", [])
                all_issues = title_issues + desc_issues
            else:
                all_issues = evaluation.get("issues", [])

            if all_issues:
                st.markdown("**Issues Found:**")
                for issue in all_issues:
                    severity = issue.get("severity", "unknown").upper()
                    issue_text = issue.get("issue", "No description")
                    suggestion = issue.get("suggestion", "")

                    severity_marker = {"CRITICAL": "●", "MAJOR": "●", "MINOR": "○"}.get(severity, "○")

                    st.markdown(f"{severity_marker} **[{severity}]** {issue_text}")
                    if suggestion:
                        st.markdown(f"   → *Fix: {suggestion}*")
            else:
                st.success("No issues found!")

            summary = evaluation.get("summary", "")
            if summary:
                st.markdown(f"**Summary:** {summary}")

        if feedback and not passed:
            st.markdown("**Feedback sent to Executor for next attempt:**")
            st.text_area("Feedback content", feedback, height=100, disabled=True, label_visibility="collapsed", key=f"feedback_{component_type}_{attempt_num}")


def render_theme_attempt(attempt: dict, attempt_num: int):
    """Render a theme expansion attempt."""
    evaluation = attempt.get("evaluation", {})
    content = attempt.get("content", {})
    feedback = attempt.get("feedback", "")
    score = evaluation.get("score", 0)
    passed = evaluation.get("passed", False) or score >= 80

    if score >= 80:
        icon = "✓"
    elif score >= 60:
        icon = "~"
    else:
        icon = "✗"

    with st.expander(f"Attempt {attempt_num} - {icon} Creativity Score: {score}/100", expanded=(not passed)):
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("### Theme & Style Development")

            if isinstance(content, dict):
                st.markdown(f"**Expanded Theme:** {content.get('expanded_theme', 'N/A')}")
                st.markdown(f"**Artistic Style:** {content.get('artistic_style', 'N/A')}")
                st.markdown(f"**Signature Artist:** {content.get('signature_artist', 'N/A')}")

        with col2:
            st.markdown("### Creativity Assessment")
            st.metric("Creativity Score", f"{score}/100",
                     delta="PASSED" if passed else "NEEDS IMPROVEMENT",
                     delta_color="normal" if passed else "inverse")

        if feedback and not passed:
            st.markdown("**Feedback for refinement:**")
            st.text_area("Feedback for refinement", feedback[:500], height=80, disabled=True, label_visibility="collapsed", key=f"feedback_theme_{attempt_num}")


def render_component_section(title: str, attempts: list, component_type: str, final_score: int, passed: bool):
    """Render a complete component section with all attempts."""
    status_icon = "✓" if passed else "✗"

    st.markdown(f"## {title} {status_icon}")
    st.markdown(f"**Final Score:** {final_score}/100 | **Attempts:** {len(attempts)} | **Status:** {'PASSED' if passed else 'FAILED'}")

    if not attempts:
        st.warning("No attempts recorded for this component.")
        return

    for i, attempt in enumerate(attempts, 1):
        if component_type == "theme":
            render_theme_attempt(attempt, i)
        else:
            render_attempt(attempt, i, component_type)


def _render_generation_log(state: dict):
    """Render generation log if present (for concept-based designs)."""
    gen_log = state.get("generation_log", [])
    if gen_log:
        with st.expander("Generation log", expanded=False):
            for entry in gen_log:
                st.write(f"✓ {entry.get('message', '')}")


def render_progress_overview(state: dict):
    """Render high-level progress overview with real-time status."""
    st.markdown("### Workflow Progress")

    theme_status = state.get("theme_status", "pending")
    title_status = state.get("title_status", "pending")
    prompts_status = state.get("prompts_status", "pending")
    keywords_status = state.get("keywords_status", "pending")

    def get_status_display(status: str, score: int = 0, passed: bool = False):
        if status == "completed":
            if passed or score >= 80:
                return "✓", "Completed", "normal"
            else:
                return "!", "Completed (Low Score)", "off"
        elif status == "in_progress":
            return "...", "In Progress", "normal"
        elif status == "failed":
            return "✗", "Failed", "inverse"
        else:
            return "○", "Pending", "off"

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        theme_icon, theme_label, theme_color = get_status_display(
            theme_status,
            state.get("theme_score", 0),
            state.get("theme_passed", False)
        )
        st.metric(
            "Theme Expansion",
            f"{state.get('theme_score', 0)}/100",
            delta=theme_label,
            delta_color=theme_color
        )
        if theme_status == "in_progress":
            st.progress(0.5)

    with col2:
        title_icon, title_label, title_color = get_status_display(
            title_status,
            state.get("title_score", 0),
            state.get("title_passed", False)
        )
        st.metric(
            "Title & Description",
            f"{state.get('title_score', 0)}/100",
            delta=title_label,
            delta_color=title_color
        )
        if title_status == "in_progress":
            st.progress(0.5)

    with col3:
        prompts_icon, prompts_label, prompts_color = get_status_display(
            prompts_status,
            state.get("prompts_score", 0),
            state.get("prompts_passed", False)
        )
        st.metric(
            "MidJourney Prompts",
            f"{state.get('prompts_score', 0)}/100",
            delta=prompts_label,
            delta_color=prompts_color
        )
        if prompts_status == "in_progress":
            st.progress(0.5)

    with col4:
        keywords_icon, keywords_label, keywords_color = get_status_display(
            keywords_status,
            state.get("keywords_score", 0),
            state.get("keywords_passed", False)
        )
        st.metric(
            "SEO Keywords",
            f"{state.get('keywords_score', 0)}/100",
            delta=keywords_label,
            delta_color=keywords_color
        )
        if keywords_status == "in_progress":
            st.progress(0.5)


def render_final_results_compact(state: dict, key_prefix: str = ""):
    """Render compact final results display with editable fields and rerun controls."""
    st.markdown("### Generated Design Package")
    with st.expander("Regenerate", expanded=False):
        st.caption("Modify and regenerate parts of this design.")
        
        # Examples shown above the text field
        st.markdown("""**Example instructions:**
- *"Make the title more playful and fun"*
- *"Change art style to Pop manga"* or *"Switch to watercolor style"*
- *"Add more fantasy/whimsical elements"*
- *"Focus on relaxation and stress-relief"*
- *"Target younger adults / beginners"*
- *"Make keywords more specific to Amazon searches"*
""")
        
        # Single instruction field
        custom_instructions = st.text_area(
            "Your instructions:",
            placeholder="Type what you want to change...",
            key=f"{key_prefix}custom_instructions",
            height=80
        )
        
        # All buttons on the same line
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            if st.button("Title", key=f"{key_prefix}rerun_title_btn"):
                with st.spinner("Regenerating title & description..."):
                    try:
                        mods = {"regenerate": ["title"]}
                        if custom_instructions.strip():
                            mods["custom_instructions"] = custom_instructions.strip()
                        updated = rerun_design_with_modifications(state, mods)
                        st.session_state.workflow_state = updated
                        save_workflow_state(updated)
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
        with col2:
            if st.button("Prompts", key=f"{key_prefix}rerun_prompts_btn"):
                with st.spinner("Regenerating prompts..."):
                    try:
                        mods = {"regenerate": ["prompts"]}
                        if custom_instructions.strip():
                            mods["custom_instructions"] = custom_instructions.strip()
                        updated = rerun_design_with_modifications(state, mods)
                        st.session_state.workflow_state = updated
                        save_workflow_state(updated)
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
        with col3:
            if st.button("Keywords", key=f"{key_prefix}rerun_keywords_btn"):
                with st.spinner("Regenerating keywords..."):
                    try:
                        mods = {"regenerate": ["keywords"]}
                        if custom_instructions.strip():
                            mods["custom_instructions"] = custom_instructions.strip()
                        updated = rerun_design_with_modifications(state, mods)
                        st.session_state.workflow_state = updated
                        save_workflow_state(updated)
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
        with col4:
            if st.button("All", key=f"{key_prefix}rerun_all_btn"):
                with st.spinner("Regenerating all..."):
                    try:
                        mods = {"regenerate": ["title", "prompts", "keywords"]}
                        if custom_instructions.strip():
                            mods["custom_instructions"] = custom_instructions.strip()
                        updated = rerun_design_with_modifications(state, mods)
                        st.session_state.workflow_state = updated
                        save_workflow_state(updated)
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
        with col5:
            if st.button("Full Rerun", key=f"{key_prefix}rerun_full_btn"):
                with st.spinner("Full rerun from concept..."):
                    try:
                        concept = state.get("concept_source") or state.get("concept")
                        if concept:
                            updated = run_design_for_concept(concept)
                            st.session_state.workflow_state = updated
                            save_workflow_state(updated)
                            st.rerun()
                        else:
                            updated = run_coloring_book_agent(state.get("user_request", ""))
                            st.session_state.workflow_state = updated
                            save_workflow_state(updated)
                            st.rerun()
                    except Exception as e:
                        st.error(str(e))
    with st.expander("Edit and Save", expanded=False):
        st.caption("Modify the design below and click Save to persist changes.")
        edited_title = st.text_input("Title", value=state.get("title", ""), key="edit_title", max_chars=100)
        edited_desc = st.text_area("Description", value=state.get("description", ""), key="edit_desc", height=150)
        keywords_list = state.get("seo_keywords", [])
        edited_keywords = st.text_area("Keywords (one per line)", value="\n".join(keywords_list) if isinstance(keywords_list, list) else str(keywords_list), key="edit_keywords", height=100)
        with st.expander("MidJourney Prompts (advanced)", expanded=False):
            prompts_list = state.get("midjourney_prompts", [])
            edited_prompts = st.text_area("Prompts (one per line)", value="\n".join(prompts_list) if isinstance(prompts_list, list) else "", key="edit_prompts", height=200)
            state["midjourney_prompts"] = [p.strip() for p in edited_prompts.split("\n") if p.strip()]
        state["title"] = edited_title
        state["description"] = edited_desc
        state["seo_keywords"] = [k.strip() for k in edited_keywords.split("\n") if k.strip()]
        st.session_state.workflow_state = state
        if st.button("Save changes", key="save_edits_btn"):
            if not edited_title.strip():
                st.warning("Please enter a title before saving.")
            elif not edited_desc.strip():
                st.warning("Please enter a description before saving.")
            else:
                try:
                    filepath = save_workflow_state(state)
                    st.success(f"Design saved as `{Path(filepath).name}`")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving: {e}")
    title = state.get("title", "")
    description = state.get("description", "")
    if title:
        st.markdown(f"### {title}")
    
    # Theme & Artistic Style section (editable, before description)
    expanded_theme = state.get("expanded_theme", {})
    if expanded_theme:
        with st.expander("Theme & Artistic Style", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                edited_style = st.text_input(
                    "Artistic Style",
                    value=expanded_theme.get('artistic_style', ''),
                    key=f"{key_prefix}edit_artistic_style"
                )
                edited_artist = st.text_input(
                    "Signature Artist",
                    value=expanded_theme.get('signature_artist', ''),
                    key=f"{key_prefix}edit_signature_artist"
                )
            with col2:
                edited_angle = st.text_input(
                    "Unique Angle",
                    value=expanded_theme.get('unique_angle', ''),
                    key=f"{key_prefix}edit_unique_angle",
                    disabled=True
                )
                edited_audience = st.text_input(
                    "Target Audience",
                    value=expanded_theme.get('target_audience', ''),
                    key=f"{key_prefix}edit_target_audience",
                    disabled=True
                )
            # Update state with edited values (unique_angle and target_audience stay from expanded_theme)
            if "expanded_theme" not in state:
                state["expanded_theme"] = {}
            state["expanded_theme"]["artistic_style"] = edited_style
            state["expanded_theme"]["signature_artist"] = edited_artist
            state["expanded_theme"]["unique_angle"] = expanded_theme.get('unique_angle', '')
            state["expanded_theme"]["target_audience"] = expanded_theme.get('target_audience', '')
    
    # Description section (after theme)
    if description:
        with st.expander("Description", expanded=False):
            st.write(description)

    st.markdown("### Content Details")

    if expanded_theme:
        tab1, tab2, tab3, tab4 = st.tabs(["Title & Description", "Prompts", "Keywords", "Download"])
    else:
        tab1, tab2, tab3 = st.tabs(["Prompts", "Keywords", "Download"])

    if expanded_theme:
        with tab1:
            st.markdown(f"**Title:** {title}")
            st.markdown("**Description:**")
            st.write(description)

    prompts_tab = tab2 if expanded_theme else tab1
    with prompts_tab:
        prompts = state.get("midjourney_prompts", [])
        st.markdown(f"**{len(prompts)} MidJourney Prompts**")
        st.caption("Read-only. Use Edit and Save above to modify prompts.")

        search = st.text_input("Filter prompts", key="prompt_filter")
        filtered = [p for p in prompts if search.lower() in p.lower()] if search else prompts

        for i, p in enumerate(filtered, 1):
            st.markdown(f"**Prompt {i}**")
            st.code(p, language="text")

    keywords_tab = tab3 if expanded_theme else tab2
    with keywords_tab:
        keywords = state.get("seo_keywords", [])
        st.markdown(f"**{len(keywords)} SEO Keywords:**")
        for i, kw in enumerate(keywords, 1):
            st.markdown(f"{i}. {kw}")

    download_tab = tab4 if expanded_theme else tab3
    with download_tab:
        report = {
            "title": state.get("title", ""),
            "description": state.get("description", ""),
            "midjourney_prompts": state.get("midjourney_prompts", []),
            "seo_keywords": state.get("seo_keywords", []),
            "quality_scores": {
                "theme": state.get("theme_score", 0),
                "title_description": state.get("title_score", 0),
                "prompts": state.get("prompts_score", 0),
                "keywords": state.get("keywords_score", 0)
            },
            "attempts_needed": {
                "theme": len(state.get("theme_attempts", [])),
                "title_description": len(state.get("title_attempts", [])),
                "prompts": len(state.get("prompts_attempts", [])),
                "keywords": len(state.get("keywords_attempts", []))
            }
        }

        st.download_button(
            "Download Full Report (JSON)",
            data=json.dumps(report, indent=2),
            file_name="coloring_book_report.json",
            mime="application/json"
        )

        st.json(report)


def render_attempt_history_collapsed(state: dict):
    """Render collapsed attempt history at bottom."""
    with st.expander("View Detailed Attempt History", expanded=False):
        st.markdown("### Per-Component Attempt History")
        st.markdown("*Review each attempt to verify evaluator quality*")

        theme_attempts = state.get("theme_attempts", [])
        if theme_attempts:
            render_component_section(
                "Theme Expansion & Research",
                theme_attempts,
                "theme",
                state.get("theme_score", 0),
                state.get("theme_passed", False)
            )

        render_component_section(
            "Title & Description",
            state.get("title_attempts", []),
            "title",
            state.get("title_score", 0),
            state.get("title_passed", False)
        )

        render_component_section(
            "MidJourney Prompts",
            state.get("prompts_attempts", []),
            "prompts",
            state.get("prompts_score", 0),
            state.get("prompts_passed", False)
        )

        render_component_section(
            "SEO Keywords",
            state.get("keywords_attempts", []),
            "keywords",
            state.get("keywords_score", 0),
            state.get("keywords_passed", False)
        )


def _normalize_concept(theme: str, style: str, variations: list = None) -> dict:
    """Build a concept dict from theme + style, optionally enriching from variations."""
    concept = {
        "theme": theme,
        "style": style,
        "theme_concept": theme,
        "art_style": style,
        "mixable_components": {"theme": theme, "style": style},
    }
    if variations:
        for v in variations:
            if (v.get("theme_concept") or v.get("mixable_components", {}).get("theme")) == theme:
                concept["style_description"] = v.get("style_description", "")
                concept["unique_angle"] = v.get("unique_angle", "")
                break
            if (v.get("art_style") or v.get("mixable_components", {}).get("style")) == style:
                concept["style_description"] = concept.get("style_description") or v.get("style_description", "")
                concept["unique_angle"] = concept.get("unique_angle") or v.get("unique_angle", "")
    return concept


def render_concept_research_section():
    """Render the preliminary concept research section with variations and mix-and-match."""
    st.markdown("### 1. Concept Research")
    st.caption(
        f"Enter an idea to get creative variations. Select concepts for design generation (up to {MAX_SELECTED_CONCEPTS})."
    )

    if "concept_variations" not in st.session_state:
        st.session_state.concept_variations = []
    if "selected_concepts" not in st.session_state:
        st.session_state.selected_concepts = []
    if "generated_designs" not in st.session_state:
        st.session_state.generated_designs = []

    idea_input = st.text_input(
        "Your idea (e.g., dog, forest animals, ocean life):",
        placeholder="Enter a theme or subject...",
        key="concept_idea_input",
    )

    num_variations = st.selectbox(
        "Number of variations to generate:",
        options=list(range(MIN_CONCEPT_VARIATIONS, MAX_CONCEPT_VARIATIONS + 1)),
        index=0,
        key="num_variations_select",
    )

    if st.button(
        f"Generate {num_variations} Concept Variations",
        key="gen_variations_btn",
        disabled=st.session_state.get("is_running", False),
    ):
        if idea_input.strip():
            with st.spinner(f"Generating {num_variations} creative variations..."):
                try:
                    variations = generate_concept_variations(idea_input.strip(), num_variations=num_variations)
                    st.session_state.concept_variations = variations
                    st.rerun()
                except Exception as e:
                    st.error(f"Error generating variations: {e}")
        else:
            st.warning("Please enter an idea first.")

    variations = st.session_state.concept_variations
    selected = st.session_state.selected_concepts

    if variations:
        st.markdown("#### Concept Variations")
        st.caption("Click **Add to concepts** on any variation, or use **Add all** to select everything.")

        if st.button(
            "Add all variations",
            key="add_all_btn",
            disabled=st.session_state.get("is_running", False) or len(selected) >= MAX_SELECTED_CONCEPTS,
        ):
            existing_keys = {(c.get("theme", ""), c.get("style", "")) for c in st.session_state.selected_concepts}
            for v in variations:
                if len(st.session_state.selected_concepts) >= MAX_SELECTED_CONCEPTS:
                    break
                theme = v.get("theme_concept") or v.get("mixable_components", {}).get("theme", "")
                style = v.get("art_style") or v.get("mixable_components", {}).get("style", "")
                if (theme, style) not in existing_keys:
                    concept = _normalize_concept(theme, style, variations)
                    st.session_state.selected_concepts = st.session_state.selected_concepts + [concept]
                    existing_keys.add((theme, style))
            st.rerun()

        cards_per_row = 3
        for row_start in range(0, len(variations), cards_per_row):
            cols = st.columns(cards_per_row)
            for col_idx, col in enumerate(cols):
                i = row_start + col_idx
                if i >= len(variations):
                    break
                v = variations[i]
                with col:
                    theme = v.get("theme_concept") or v.get("mixable_components", {}).get("theme", "?")
                    style = v.get("art_style") or v.get("mixable_components", {}).get("style", "?")
                    with st.container(border=True):
                        st.markdown(f"**{theme}**")
                        st.caption(style)
                        angle = v.get("unique_angle", "")
                        st.caption(angle[:100] + "..." if len(angle) > 100 else angle)
                        if st.button(
                            "Add to concepts",
                            key=f"add_variation_{i}",
                            disabled=len(selected) >= MAX_SELECTED_CONCEPTS or st.session_state.get("is_running", False),
                        ):
                            existing_keys = {(c.get("theme", ""), c.get("style", "")) for c in st.session_state.selected_concepts}
                            if (theme, style) not in existing_keys:
                                concept = _normalize_concept(theme, style, variations)
                                st.session_state.selected_concepts = st.session_state.selected_concepts + [concept]
                            st.rerun()

        with st.expander("Create custom concept (mix and match)", expanded=False):
            themes = list(
                {(v.get("theme_concept") or v.get("mixable_components", {}).get("theme") or "").strip() for v in variations}
            )
            themes = [t for t in themes if t] or [""]
            styles = list(
                {(v.get("art_style") or v.get("mixable_components", {}).get("style") or "").strip() for v in variations}
            )
            styles = [s for s in styles if s] or [""]
            col1, col2 = st.columns(2)
            with col1:
                sel_theme = st.selectbox("Theme", options=themes, key="mix_theme")
            with col2:
                sel_style = st.selectbox("Art Style", options=styles, key="mix_style")
            if st.button("Add Custom Concept", key="add_concept_btn"):
                if sel_theme and sel_style:
                    concept = _normalize_concept(sel_theme, sel_style, variations)
                    if len(st.session_state.selected_concepts) < MAX_SELECTED_CONCEPTS:
                        st.session_state.selected_concepts = st.session_state.selected_concepts + [concept]
                        st.rerun()
                    else:
                        st.warning(f"Maximum {MAX_SELECTED_CONCEPTS} concepts. Remove one to add another.")
                else:
                    st.warning("Select both theme and style.")

    st.markdown("#### Selected Concepts")
    st.caption(f"{len(selected)} / {MAX_SELECTED_CONCEPTS} concepts selected")
    if selected:
        st.progress(min(1.0, len(selected) / MAX_SELECTED_CONCEPTS))
        for idx, c in enumerate(selected):
            theme = c.get("theme", "")
            style = c.get("style", "")
            chip_col1, chip_col2 = st.columns([6, 1])
            with chip_col1:
                st.markdown(f"**{idx + 1}.** {theme} | {style}")
            with chip_col2:
                if st.button("Remove", key=f"remove_concept_{idx}"):
                    st.session_state.selected_concepts = [x for i, x in enumerate(selected) if i != idx]
                    st.rerun()

    return variations, st.session_state.selected_concepts


def render_design_generation_tab():
    """Render the Design Generation tab with all three sections."""
    st.markdown("## Design Generation")

    if "concept_variations" not in st.session_state:
        st.session_state.concept_variations = []
    if "selected_concepts" not in st.session_state:
        st.session_state.selected_concepts = []
    if "generated_designs" not in st.session_state:
        st.session_state.generated_designs = []

    variations, selected_concepts = render_concept_research_section()

    workflow_state = st.session_state.get("workflow_state")
    generated_designs = st.session_state.get("generated_designs", [])

    if selected_concepts:
        st.markdown("---")
        st.markdown("### 2. Generate Designs for Selected Concepts")
        st.caption(
            "Generate a full design package (title, description, prompts, keywords) for each concept. "
            "~2–3 min per design."
        )

        if "generation_queue" not in st.session_state:
            st.session_state.generation_queue = []
        if "generation_results" not in st.session_state:
            st.session_state.generation_results = []
        if "generation_current_index" not in st.session_state:
            st.session_state.generation_current_index = 0
        if "generation_in_progress" not in st.session_state:
            st.session_state.generation_in_progress = False
        if "generation_step_state" not in st.session_state:
            st.session_state.generation_step_state = None
        if "generation_current_step" not in st.session_state:
            st.session_state.generation_current_step = 0
        if "generation_single_insert_idx" not in st.session_state:
            st.session_state.generation_single_insert_idx = None

        n_concepts = len(selected_concepts)
        if st.button(
            f"Generate All {n_concepts} Designs",
            type="primary",
            key="gen_all_btn",
            disabled=st.session_state.get("is_running", False) or st.session_state.get("generation_in_progress", False),
        ):
            st.session_state.generation_queue = list(selected_concepts)
            st.session_state.generation_results = []
            st.session_state.generation_current_index = 0
            st.session_state.generation_in_progress = True
            st.session_state.generation_step_state = None
            st.session_state.generation_current_step = 0
            st.session_state.generation_single_insert_idx = None
            st.session_state.is_running = True
            st.rerun()

        if st.session_state.get("generation_in_progress") and st.session_state.generation_queue:
            queue = st.session_state.generation_queue
            results = st.session_state.generation_results
            current_idx = st.session_state.generation_current_index
            step_state = st.session_state.generation_step_state
            step_idx = st.session_state.generation_current_step

            if current_idx < len(queue):
                concept = queue[current_idx]
                theme = concept.get("theme", "")
                style = concept.get("style", "")

                if step_idx < len(DESIGN_STEPS):
                    step_name = DESIGN_STEPS[step_idx]
                    completed_count = step_idx

                    with st.status(
                        f"Design {current_idx + 1} of {len(queue)}: {theme} | {style}",
                        state="running",
                        expanded=True,
                    ) as status:
                        for i, name in enumerate(STEP_DISPLAY_NAMES):
                            if i < completed_count:
                                st.write(f"✓ {name}")
                            elif i == completed_count:
                                st.write(f"⟳ {name}")
                            else:
                                st.write(f"○ {name}")

                        try:
                            new_state = run_design_step_for_concept(concept, step_name, step_state)
                            st.session_state.generation_step_state = new_state

                            if step_name == "keywords":
                                new_results = results + [new_state]
                                st.session_state.generation_results = new_results
                                try:
                                    save_workflow_state(new_state)
                                except Exception:
                                    pass
                                st.session_state.generation_step_state = None
                                st.session_state.generation_current_step = 0
                                st.session_state.generation_current_index = current_idx + 1
                                if st.session_state.generation_current_index >= len(queue):
                                    st.session_state.generation_in_progress = False
                                    st.session_state.is_running = False
                                    single_idx = st.session_state.generation_single_insert_idx
                                    if single_idx is not None:
                                        designs = list(st.session_state.generated_designs)
                                        while len(designs) <= single_idx:
                                            designs.append({})
                                        designs[single_idx] = new_results[0]
                                        st.session_state.generated_designs = designs
                                        st.session_state.generation_single_insert_idx = None
                                    else:
                                        st.session_state.generated_designs = new_results
                                    status.update(label="All designs complete!", state="complete")
                            else:
                                st.session_state.generation_current_step = step_idx + 1
                        except Exception as e:
                            st.error(f"Error generating design {current_idx + 1}: {e}")
                            st.session_state.generation_in_progress = False
                            st.session_state.is_running = False

                st.rerun()
            else:
                st.session_state.generation_in_progress = False
                st.session_state.is_running = False
                single_idx = st.session_state.generation_single_insert_idx
                results = st.session_state.generation_results
                if single_idx is not None and results:
                    designs = list(st.session_state.generated_designs)
                    while len(designs) <= single_idx:
                        designs.append({})
                    designs[single_idx] = results[0]
                    st.session_state.generated_designs = designs
                    st.session_state.generation_single_insert_idx = None
                else:
                    st.session_state.generated_designs = results
                st.rerun()

        generated_designs = st.session_state.get("generated_designs", [])

        for idx, concept in enumerate(selected_concepts):
            with st.expander(f"Concept {idx + 1}: {concept.get('theme', '')} | {concept.get('style', '')}", expanded=(idx < len(generated_designs))):
                if idx < len(generated_designs):
                    design = generated_designs[idx]
                    st.markdown(f"**{design.get('title', 'Untitled')}**")
                    st.caption(f"{len(design.get('midjourney_prompts', []))} prompts | {len(design.get('seo_keywords', []))} keywords")
                    gen_log = design.get("generation_log", [])
                    if gen_log:
                        with st.expander("Generation log", expanded=False):
                            for entry in gen_log:
                                st.write(f"✓ {entry.get('message', '')}")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("Use this design", key=f"use_design_{idx}"):
                            design_copy = dict(design)
                            design_images_folders = st.session_state.get("mj_design_images_folders", {})
                            if idx in design_images_folders:
                                design_copy["images_folder_path"] = design_images_folders[idx]
                            st.session_state.workflow_state = design_copy
                            st.rerun()
                    with col_b:
                        if st.button("Regenerate", key=f"regen_concept_{idx}"):
                            st.session_state.generation_queue = [concept]
                            st.session_state.generation_results = []
                            st.session_state.generation_current_index = 0
                            st.session_state.generation_in_progress = True
                            st.session_state.generation_step_state = None
                            st.session_state.generation_current_step = 0
                            st.session_state.generation_single_insert_idx = idx
                            st.session_state.is_running = True
                            st.rerun()
                else:
                    if st.button(f"Generate design {idx + 1}", key=f"gen_single_{idx}", disabled=st.session_state.get("is_running", False)):
                        st.session_state.generation_queue = [concept]
                        st.session_state.generation_results = []
                        st.session_state.generation_current_index = 0
                        st.session_state.generation_in_progress = True
                        st.session_state.generation_step_state = None
                        st.session_state.generation_current_step = 0
                        st.session_state.generation_single_insert_idx = idx
                        st.session_state.is_running = True
                        st.rerun()

    st.markdown("---")
    st.markdown("### 3. Or Describe Your Coloring Book (Direct)")
    user_request = st.text_area(
        "What kind of coloring book would you like to create?",
        placeholder="Example: A forest animals coloring book for adults with intricate mandala patterns...",
        height=100,
        key="design_user_request"
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        generate_btn = st.button("Generate", type="primary", disabled=st.session_state.get("is_running", False))
    with col2:
        if st.button("Clear", disabled=st.session_state.get("is_running", False)):
            st.session_state.workflow_state = None
            st.rerun()

    st.markdown("**Saved Designs**")
    if workflow_state and workflow_state.get("title"):
        save_name = st.text_input("Save as:", value=workflow_state.get("title", ""), key="save_name_input")
        if st.button("Save Current Design", key="save_design_btn"):
            try:
                filepath = save_workflow_state(workflow_state, name=save_name if save_name else None)
                st.success("Design saved!")
                st.rerun()
            except Exception as e:
                st.error(f"Error saving: {e}")

    st.markdown("**Load Previous Design**")
    saved_states = list_saved_states()
    if saved_states:
        for state_info in saved_states[:10]:
            with st.expander(f"{state_info['title']}", expanded=False):
                st.caption(f"Saved: {state_info['saved_at']}")
                if state_info['description']:
                    st.text(state_info['description'][:150])
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Load", key=f"load_{state_info['name']}"):
                        loaded_state = load_workflow_state(state_info['filepath'])
                        if loaded_state:
                            st.session_state.workflow_state = loaded_state
                            st.success("Design loaded!")
                            st.rerun()
                        else:
                            st.error("Failed to load design")
                with col2:
                    if st.button("Delete", key=f"delete_{state_info['name']}"):
                        if delete_saved_state(state_info['filepath']):
                            st.success("Deleted!")
                            st.rerun()
                        else:
                            st.error("Failed to delete")
    else:
        st.caption("No saved designs yet. Generate a design and save it.")

    if workflow_state:
        pending_question = workflow_state.get("pending_question", "")
        if pending_question and not st.session_state.get("is_running", False):
            st.info("**Agent Question**")
            st.markdown(f"**{pending_question}**")

            user_answer = st.text_input(
                "Your answer:",
                key="user_answer_input",
                placeholder="Type your answer here..."
            )

            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("Submit Answer", type="primary"):
                    if user_answer.strip():
                        workflow_state["user_answer"] = user_answer.strip()
                        workflow_state["pending_question"] = ""
                        workflow_state["status"] = "generating"
                        st.session_state.workflow_state = workflow_state
                        st.session_state.is_running = True
                        st.rerun()
                    else:
                        st.warning("Please provide an answer.")
            with col2:
                if st.button("Skip Question"):
                    workflow_state["user_answer"] = "No response provided"
                    workflow_state["pending_question"] = ""
                    workflow_state["status"] = "generating"
                    st.session_state.workflow_state = workflow_state
                    st.session_state.is_running = True
                    st.rerun()

    if generate_btn and user_request.strip():
        st.session_state.is_running = True
        with st.spinner("Running multi-agent workflow with per-component evaluation..."):
            try:
                final_state = run_coloring_book_agent(user_request)
                st.session_state.workflow_state = final_state
                st.session_state.is_running = False
                if final_state.get("status") == "complete" and final_state.get("title"):
                    try:
                        save_workflow_state(final_state)
                    except Exception:
                        pass
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
                st.session_state.is_running = False

    elif generate_btn and not user_request.strip():
        st.warning("Please enter a description.")

    if workflow_state and workflow_state.get("status") == "waiting_for_user" and workflow_state.get("user_answer"):
        st.session_state.is_running = True
        with st.spinner("Continuing workflow with your answer..."):
            try:
                app = create_coloring_book_graph()
                current_state = workflow_state.copy()
                updated_state = app.invoke(current_state)
                st.session_state.workflow_state = updated_state
                st.session_state.is_running = False
                st.rerun()
            except Exception as e:
                st.error(f"Error continuing workflow: {e}")
                import traceback
                st.code(traceback.format_exc())
                st.session_state.is_running = False

    if workflow_state and workflow_state.get("status") == "complete":
        render_progress_overview(workflow_state)
        _render_generation_log(workflow_state)
        render_final_results_compact(workflow_state)
        render_attempt_history_collapsed(workflow_state)
