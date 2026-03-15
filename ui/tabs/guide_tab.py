"""Get Started guide tab - workflow overview and documentation chat."""

import streamlit as st

from ui.components.guide_chat import render_guide_chat

# Step metadata for expander summary (estimated time, prerequisites)
STEPS = [
    {
        "title": "1. Design Generation",
        "body": "Describe your idea (e.g. forest animals for adults with mandala patterns). The AI researches an artistic style, generates a marketable title and description (~200 words), 50 MidJourney prompts for coloring pages, and 10 SEO keywords. Each component is evaluated for quality and refined up to 5 times. You can download the full report as JSON. Go to the Design Generation tab, enter your idea, and run the agent.",
        "estimated": "~2–5 min",
        "prerequisites": "None",
    },
    {
        "title": "2. Image Generation",
        "body": "Use the MidJourney prompts in the Design tab to generate images (e.g. in MidJourney or another tool). Set the folder path in this tab to where your images are saved. Select which images to include in the workflow. Empty selection means all images are used. Click checkboxes on images to select or deselect.",
        "estimated": "Depends on your workflow",
        "prerequisites": "Design package",
    },
    {
        "title": "3. Canva Design",
        "body": "The app creates a multi-page Canva layout: one page per image with margins. Requires a browser started with remote debugging (port set in Config tab). Log into Canva first, then run the workflow. The app will create the design and upload images.",
        "estimated": "~5–15 min",
        "prerequisites": "Design package, images folder, browser",
    },
    {
        "title": "4. Pinterest Publishing",
        "body": "Publishes one pin per image to Pinterest with title, description, and keywords from the design package. Requires a browser with remote debugging. Log into Pinterest first, then run the workflow.",
        "estimated": "~2–10 min",
        "prerequisites": "Design package, images folder, browser",
    },
]


def _render_guide_content():
    """Render the Guide sub-tab content."""
    # Quick start block
    st.markdown("### Quick start")
    st.markdown("""
    1. **Design Generation** — Enter your idea, run.  
    2. **Image Generation** — Set folder, run.  
    3. **Canva Design** — Check browser, run.  
    4. **Pinterest Publishing** — Set board, run.
    """)
    st.caption("Follow these steps in order. Each tab corresponds to a stage.")

    st.markdown("### What this app does")
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("""
            - **Design package** – Generates a marketable title, description, 50 MidJourney prompts, 
              and 10 SEO keywords for your coloring book idea
            - **Image folder** – Monitors a folder for your generated artwork (from MidJourney or other tools)
            """)
    with col2:
        with st.container(border=True):
            st.markdown("""
            - **Canva layout** – Builds a multi-page layout from your images (browser automation)
            - **Pinterest publishing** – Publishes pins with metadata (browser automation)
            """)

    st.markdown("### Recommended workflow")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("**1. Design Generation**")
        st.caption("Theme, Title, Prompts, Keywords")
    with col2:
        st.markdown("**2. Image Generation**")
        st.caption("Folder with images")
    with col3:
        st.markdown("**3. Canva Design**")
        st.caption("PDF / Layout")
    with col4:
        st.markdown("**4. Pinterest Publishing**")
        st.caption("Published pins")
    # Workflow sequence indicator (instructional)
    st.progress(1.0, text="1 → 2 → 3 → 4")
    st.caption("Workflow flows left to right. Complete each step before moving to the next.")

    st.markdown("### Detailed steps")
    for step in STEPS:
        with st.expander(f"{step['title']}", expanded=False):
            st.caption(f"**Estimated time:** {step['estimated']} · **Prerequisites:** {step['prerequisites']}")
            st.markdown(step["body"])


def _render_ask_content():
    """Render the Ask sub-tab content (chat)."""
    st.caption("Ask about the app. Answers are based on the documentation.")
    render_guide_chat()


def render_guide_tab():
    """Render the Get Started tab with workflow guide and chat."""
    st.markdown("## Get Started")

    tab_guide, tab_ask = st.tabs(["Guide", "Ask"])
    with tab_guide:
        _render_guide_content()
    with tab_ask:
        _render_ask_content()
