"""Get Started guide tab - workflow overview and documentation chat."""

import streamlit as st

from ui.components.guide_chat import render_guide_chat


def render_guide_tab():
    """Render the Get Started tab with workflow guide and chat."""
    st.markdown("## Get Started")
    st.markdown("### What this app does")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        - **Design package** – Generates a marketable title, description, 50 MidJourney prompts, 
          and 10 SEO keywords for your coloring book idea
        - **Image folder** – Monitors a folder for your generated artwork (from MidJourney or other tools)
        """)
    with col2:
        st.markdown("""
        - **Canva layout** – Builds a multi-page layout from your images (browser automation)
        - **Pinterest publishing** – Publishes pins with metadata (browser automation)
        """)
    st.markdown("### Recommended workflow")
    st.caption("Follow these steps in order. Each tab corresponds to a stage.")
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
    st.caption("→ Workflow flows left to right. Complete each step before moving to the next.")

    steps = [
        {
            "title": "1. Design Generation",
            "icon": "🎨",
            "body": "Describe your idea (e.g. forest animals for adults with mandala patterns). The AI researches an artistic style, generates a marketable title and description (~200 words), 50 MidJourney prompts for coloring pages, and 10 SEO keywords. Each component is evaluated for quality and refined up to 5 times. You can download the full report as JSON. Go to the Design Generation tab, enter your idea, and run the agent.",
        },
        {
            "title": "2. Image Generation",
            "icon": "🖼️",
            "body": "Use the MidJourney prompts in the Design tab to generate images (e.g. in MidJourney or another tool). Set the folder path in this tab to where your images are saved. Select which images to include in the workflow. Empty selection means all images are used. Click checkboxes on images to select or deselect.",
        },
        {
            "title": "3. Canva Design",
            "icon": "🎨",
            "body": "The app creates a multi-page Canva layout: one page per image with margins. Requires a browser started with --remote-debugging-port=9222. Log into Canva first, then run the workflow. The app will create the design and upload images.",
        },
        {
            "title": "4. Pinterest Publishing",
            "icon": "📌",
            "body": "Publishes one pin per image to Pinterest with title, description, and keywords from the design package. Requires a browser with remote debugging. Log into Pinterest first, then run the workflow.",
        },
    ]

    for step in steps:
        with st.expander(f"{step['icon']} {step['title']}", expanded=False):
            st.markdown(step["body"])

    with st.expander("💬 Have questions? Ask about this app", expanded=False):
        render_guide_chat()
