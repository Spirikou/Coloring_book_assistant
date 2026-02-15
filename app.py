"""
Streamlit Frontend - Multi-Tab Workflow with Progress Overview

Features:
- High-level progress view at top
- Final results prominently displayed
- Collapsed attempt history at bottom
- Multi-tab structure for expanded workflow

Run with: uv run streamlit run app.py
"""

import streamlit as st
import os
from dotenv import load_dotenv

from ui.tabs.guide_tab import render_guide_tab
from ui.tabs.pinterest_tab import render_pinterest_tab
from ui.tabs.canva_tab import render_canva_tab
from features.design_generation.ui import render_design_generation_tab
from features.image_generation.ui import render_image_generation_tab

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="🎨 Coloring Book Workflow",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main Streamlit application with multi-tab interface."""
    
    st.title("🎨 Coloring Book Workflow Assistant")
    st.caption("Multi-stage workflow for coloring book creation")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # API Key check
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            st.error("⚠️ OpenAI API key not found!")
            st.info("Please set your OPENAI_API_KEY in the .env file")
        else:
            st.success("✅ API key loaded")
        
        st.markdown("---")
        st.markdown("### 📋 Workflow Stages")
        st.markdown("""
        0. **Get Started** - Guide and workflow overview
        1. **Design Generation** - Create design package
        2. **Image Generation** - Upload/generate images
        3. **Canva Design** - Create layout from images
        4. **Pinterest Publishing** - Publish to Pinterest
        
        Canva and Pinterest use the same images folder.
        """)
    
    # Initialize session state
    if "workflow_state" not in st.session_state:
        st.session_state.workflow_state = None
    
    if "is_running" not in st.session_state:
        st.session_state.is_running = False
    
    # Multi-tab interface
    tab0, tab1, tab2, tab3, tab4 = st.tabs([
        "📖 Get Started",
        "🎨 Design Generation",
        "🖼️ Image Generation",
        "🎨 Canva Design",
        "📌 Pinterest Publishing",
    ])
    
    with tab0:
        render_guide_tab()
    
    with tab1:
        render_design_generation_tab()
    
    with tab2:
        workflow_state = st.session_state.get("workflow_state")
        if workflow_state:
            render_image_generation_tab(workflow_state)
        else:
            st.info("💡 Generate a design package first in the Design Generation tab.")
    
    with tab3:
        workflow_state = st.session_state.get("workflow_state")
        if workflow_state:
            render_canva_tab(workflow_state)
        else:
            st.info("💡 Generate a design package and upload images first.")
    
    with tab4:
        workflow_state = st.session_state.get("workflow_state")
        if workflow_state:
            render_pinterest_tab(workflow_state)
        else:
            st.info("💡 Generate a design package and upload images first.")
    
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            <p>🎨 Built with Streamlit & LangGraph | Multi-Tab Workflow System</p>
        </div>
        """, 
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()

