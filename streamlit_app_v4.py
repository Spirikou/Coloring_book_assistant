"""
Streamlit Frontend v4 - Multi-Tab Workflow with Progress Overview

Features:
- High-level progress view at top
- Final results prominently displayed
- Collapsed attempt history at bottom
- Multi-tab structure for expanded workflow

Run with: uv run streamlit run streamlit_app_v4.py
"""

import streamlit as st
import os
import json
from pathlib import Path
from dotenv import load_dotenv

from workflows.design.graph import run_coloring_book_agent, create_coloring_book_graph
from utils.folder_monitor import get_images_in_folder, validate_image_count, get_image_metadata
from utils.image_utils import validate_image_file, create_thumbnail
from utils.state_persistence import save_workflow_state, load_workflow_state, list_saved_states, delete_saved_state
from ui.tabs.pinterest_tab import render_pinterest_tab

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="🎨 Coloring Book Workflow",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import render functions from v3 (reuse existing code)
# We'll copy the necessary functions inline to avoid import issues
def render_attempt(attempt: dict, attempt_num: int, component_type: str):
    """Render a single attempt with content and evaluation."""
    evaluation = attempt.get("evaluation", {})
    content = attempt.get("content", {})
    feedback = attempt.get("feedback", "")
    score = evaluation.get("score", 0)
    passed = evaluation.get("passed", False) or score >= 80
    
    # Color based on score
    if score >= 80:
        icon = "✅"
    elif score >= 60:
        icon = "🟡"
    else:
        icon = "❌"
    
    with st.expander(f"Attempt {attempt_num} - {icon} Score: {score}/100", expanded=(not passed)):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 📝 Generated Content")
            
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
            st.markdown("### 🔍 Evaluator Assessment")
            
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
                    
                    severity_icon = {"CRITICAL": "🔴", "MAJOR": "🟠", "MINOR": "🟡"}.get(severity, "⚪")
                    
                    st.markdown(f"{severity_icon} **[{severity}]** {issue_text}")
                    if suggestion:
                        st.markdown(f"   → *Fix: {suggestion}*")
            else:
                st.success("No issues found!")
            
            summary = evaluation.get("summary", "")
            if summary:
                st.markdown(f"**Summary:** {summary}")
        
        if feedback and not passed:
            st.markdown("---")
            st.markdown("**📤 Feedback sent to Executor for next attempt:**")
            st.text_area("Feedback content", feedback, height=100, disabled=True, label_visibility="collapsed", key=f"feedback_{component_type}_{attempt_num}")


def render_theme_attempt(attempt: dict, attempt_num: int):
    """Render a theme expansion attempt."""
    evaluation = attempt.get("evaluation", {})
    content = attempt.get("content", {})
    feedback = attempt.get("feedback", "")
    score = evaluation.get("score", 0)
    passed = evaluation.get("passed", False) or score >= 80
    
    if score >= 80:
        icon = "✅"
    elif score >= 60:
        icon = "🟡"
    else:
        icon = "❌"
    
    with st.expander(f"Attempt {attempt_num} - {icon} Creativity Score: {score}/100", expanded=(not passed)):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 🎨 Theme & Style Development")
            
            if isinstance(content, dict):
                st.markdown(f"**Expanded Theme:** {content.get('expanded_theme', 'N/A')}")
                st.markdown(f"**Artistic Style:** {content.get('artistic_style', 'N/A')}")
                st.markdown(f"**Signature Artist:** {content.get('signature_artist', 'N/A')}")
        
        with col2:
            st.markdown("### 🔍 Creativity Assessment")
            st.metric("Creativity Score", f"{score}/100", 
                     delta="PASSED" if passed else "NEEDS IMPROVEMENT",
                     delta_color="normal" if passed else "inverse")
        
        if feedback and not passed:
            st.markdown("---")
            st.markdown("**📤 Feedback for refinement:**")
            st.text_area("Feedback for refinement", feedback[:500], height=80, disabled=True, label_visibility="collapsed", key=f"feedback_theme_{attempt_num}")


def render_component_section(title: str, attempts: list, component_type: str, final_score: int, passed: bool):
    """Render a complete component section with all attempts."""
    status_icon = "✅" if passed else "❌"
    
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
    
    st.markdown("---")


def render_progress_overview(state: dict):
    """Render high-level progress overview with real-time status."""
    st.markdown("## 📊 Workflow Progress")
    
    # Get status for each step
    theme_status = state.get("theme_status", "pending")
    title_status = state.get("title_status", "pending")
    prompts_status = state.get("prompts_status", "pending")
    keywords_status = state.get("keywords_status", "pending")
    
    # Status icons and colors
    def get_status_display(status: str, score: int = 0, passed: bool = False):
        if status == "completed":
            if passed or score >= 80:
                return "✅", "Completed", "normal"
            else:
                return "⚠️", "Completed (Low Score)", "off"
        elif status == "in_progress":
            return "🔄", "In Progress", "normal"
        elif status == "failed":
            return "❌", "Failed", "inverse"
        else:
            return "⏳", "Pending", "off"
    
    # Create columns for each step
    col1, col2, col3, col4 = st.columns(4)
    
    # Theme Expansion
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
    
    # Title & Description
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
    
    # Prompts
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
    
    # Keywords
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
    
    st.markdown("---")


def render_final_results_compact(state: dict):
    """Render compact final results display."""
    st.markdown("## ✨ Generated Design Package")
    
    # Title and Description
    title = state.get("title", "")
    description = state.get("description", "")
    
    if title:
        st.markdown(f"### {title}")
    
    if description:
        with st.expander("📝 Description", expanded=False):
            st.write(description)
    
    # Quick stats
    col1, col2, col3 = st.columns(3)
    
    with col1:
        prompts_count = len(state.get("midjourney_prompts", []))
        st.metric("MidJourney Prompts", prompts_count)
    
    with col2:
        keywords_count = len(state.get("seo_keywords", []))
        st.metric("SEO Keywords", keywords_count)
    
    with col3:
        total_attempts = (
            len(state.get("theme_attempts", [])) +
            len(state.get("title_attempts", [])) +
            len(state.get("prompts_attempts", [])) +
            len(state.get("keywords_attempts", []))
        )
        st.metric("Total Attempts", total_attempts)
    
    # Theme info if available
    expanded_theme = state.get("expanded_theme", {})
    if expanded_theme:
        with st.expander("🎨 Theme & Artistic Style", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Artistic Style:** {expanded_theme.get('artistic_style', 'N/A')}")
                st.markdown(f"**Signature Artist:** {expanded_theme.get('signature_artist', 'N/A')}")
            with col2:
                st.markdown(f"**Unique Angle:** {expanded_theme.get('unique_angle', 'N/A')}")
                st.markdown(f"**Target Audience:** {expanded_theme.get('target_audience', 'N/A')}")
    
    # Content tabs
    st.markdown("### 📦 Content Details")
    
    if expanded_theme:
        tab1, tab2, tab3, tab4 = st.tabs(["📖 Title & Description", "🎨 Prompts", "🔍 Keywords", "📥 Download"])
    else:
        tab1, tab2, tab3 = st.tabs(["🎨 Prompts", "🔍 Keywords", "📥 Download"])
    
    # Title & Description tab
    if expanded_theme:
        with tab1:
            st.markdown(f"**Title:** {title}")
            st.markdown("**Description:**")
            st.write(description)
    
    # Prompts tab
    prompts_tab = tab2 if expanded_theme else tab1
    with prompts_tab:
        prompts = state.get("midjourney_prompts", [])
        st.markdown(f"**{len(prompts)} MidJourney Prompts:**")
        
        search = st.text_input("🔍 Filter prompts", key="prompt_filter")
        filtered = [p for p in prompts if search.lower() in p.lower()] if search else prompts
        
        for i, p in enumerate(filtered[:10], 1):  # Show first 10
            with st.expander(f"Prompt {i}"):
                st.code(p, language="text")
        if len(filtered) > 10:
            st.caption(f"... and {len(filtered) - 10} more prompts")
    
    # Keywords tab
    keywords_tab = tab3 if expanded_theme else tab2
    with keywords_tab:
        keywords = state.get("seo_keywords", [])
        st.markdown(f"**{len(keywords)} SEO Keywords:**")
        for i, kw in enumerate(keywords, 1):
            st.markdown(f"{i}. {kw}")
    
    # Download tab
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
            "📥 Download Full Report (JSON)",
            data=json.dumps(report, indent=2),
            file_name="coloring_book_report.json",
            mime="application/json"
        )
        
        st.json(report)
    
    st.markdown("---")


def render_attempt_history_collapsed(state: dict):
    """Render collapsed attempt history at bottom."""
    with st.expander("🔍 View Detailed Attempt History", expanded=False):
        st.markdown("### Per-Component Attempt History")
        st.markdown("*Review each attempt to verify evaluator quality*")
        
        # Theme Expansion attempts
        theme_attempts = state.get("theme_attempts", [])
        if theme_attempts:
            render_component_section(
                "🎨 Theme Expansion & Research",
                theme_attempts,
                "theme",
                state.get("theme_score", 0),
                state.get("theme_passed", False)
            )
        
        # Title & Description attempts
        render_component_section(
            "📖 Title & Description",
            state.get("title_attempts", []),
            "title",
            state.get("title_score", 0),
            state.get("title_passed", False)
        )
        
        # Prompts attempts
        render_component_section(
            "🎨 MidJourney Prompts",
            state.get("prompts_attempts", []),
            "prompts",
            state.get("prompts_score", 0),
            state.get("prompts_passed", False)
        )
        
        # Keywords attempts
        render_component_section(
            "🔍 SEO Keywords",
            state.get("keywords_attempts", []),
            "keywords",
            state.get("keywords_score", 0),
            state.get("keywords_passed", False)
        )


def render_image_generation_tab(state: dict):
    """Render Image Generation tab with folder monitoring."""
    st.markdown("## 🖼️ Image Generation")
    st.markdown("Place your generated images in a folder, and we'll monitor it for you.")
    
    # Folder selection
    default_folder = state.get("images_folder_path", "./generated_images/")
    folder_path = st.text_input(
        "📁 Image Folder Path",
        value=default_folder,
        help="Path to the folder containing your generated images"
    )
    
    # Update state
    if folder_path != default_folder:
        state["images_folder_path"] = folder_path
        st.session_state.workflow_state = state
    
    # Refresh button
    col1, col2 = st.columns([1, 4])
    with col1:
        refresh_btn = st.button("🔄 Refresh", key="refresh_images")
    
    # Get expected number of images from prompts
    expected_count = len(state.get("midjourney_prompts", []))
    
    if expected_count == 0:
        st.info("💡 Generate a design package first to see expected image count.")
        return
    
    st.markdown(f"**Expected Images:** {expected_count}")
    
    # Monitor folder
    if folder_path and os.path.exists(folder_path):
        images = get_images_in_folder(folder_path)
        validation = validate_image_count(folder_path, expected_count)
        
        # Status display
        found_count = validation["found_count"]
        status = validation["status"]
        
        # Show informational status (not blocking)
        if status == "complete":
            st.info(f"📊 Found {found_count} of {expected_count} images (all expected images present)")
        elif status == "partial":
            st.info(f"📊 Found {found_count} of {expected_count} images ({validation['missing_count']} missing - you can still publish with available images)")
        elif status == "empty":
            st.info(f"📁 Folder is empty. Place images in: `{folder_path}`")
        else:
            st.info(f"📊 Found {found_count} images (expected {expected_count})")
        
        # Update state
        state["uploaded_images"] = images
        # Images ready if any images exist (not requiring all expected)
        state["images_ready"] = len(images) > 0
        st.session_state.workflow_state = state
        
        # Validation button to explicitly mark images as ready
        if images:
            col1, col2 = st.columns([2, 1])
            with col1:
                if status == "complete":
                    st.success(f"✅ All {found_count} expected images found - Ready to publish!")
                elif status == "partial":
                    st.warning(f"⚠️ Found {found_count} of {expected_count} images. You can still publish with available images.")
                else:
                    st.info(f"📊 Found {found_count} images (expected {expected_count})")
            with col2:
                if st.button("✅ Mark Images as Ready", key="validate_images_btn", help="Explicitly mark these images as ready for Pinterest publishing"):
                    state["images_ready"] = True
                    st.session_state.workflow_state = state
                    st.success("✅ Images marked as ready for Pinterest publishing!")
                    st.rerun()
        
        # Image gallery
        if images:
            st.markdown("### 📸 Image Gallery")
            
            # Display images in grid
            cols_per_row = 3
            for i in range(0, len(images), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, img_path in enumerate(images[i:i+cols_per_row]):
                    with cols[j]:
                        try:
                            # Create thumbnail
                            thumbnail = create_thumbnail(img_path, (300, 300))
                            if thumbnail:
                                st.image(thumbnail, use_container_width=True)
                            
                            # Image info
                            metadata = get_image_metadata(img_path)
                            st.caption(f"📄 {metadata.get('filename', Path(img_path).name)}")
                            st.caption(f"📊 {metadata.get('size_mb', 0)} MB")
                        except Exception as e:
                            st.error(f"Error loading image: {e}")
                            st.text(Path(img_path).name)
    else:
        st.warning(f"⚠️ Folder not found: {folder_path}")
        st.info(f"Please create the folder or update the path.")


def render_placeholder_tab(tab_name: str):
    """Render placeholder tab for future workflow steps."""
    st.markdown(f"## {tab_name}")
    st.info("🚧 This workflow step is coming soon!")
    st.markdown("This tab is ready for future implementation.")


def render_design_generation_tab():
    """Render the Design Generation tab with all three sections."""
    st.markdown("## 🎨 Design Generation")
    
    # Get workflow state
    workflow_state = st.session_state.get("workflow_state")
    
    # Input section
    st.subheader("📝 Describe Your Coloring Book")
    
    user_request = st.text_area(
        "What kind of coloring book would you like to create?",
        placeholder="Example: A forest animals coloring book for adults with intricate mandala patterns...",
        height=100,
        key="design_user_request"
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        generate_btn = st.button("🚀 Generate", type="primary", disabled=st.session_state.get("is_running", False))
    with col2:
        if st.button("🔄 Clear", disabled=st.session_state.get("is_running", False)):
            st.session_state.workflow_state = None
            st.rerun()
    
    # Check for pending question
    if workflow_state:
        pending_question = workflow_state.get("pending_question", "")
        if pending_question and not st.session_state.get("is_running", False):
            st.markdown("---")
            st.info("💬 **Agent Question**")
            st.markdown(f"**{pending_question}**")
            
            answer_key = "user_answer_input"
            user_answer = st.text_input(
                "Your answer:",
                key=answer_key,
                placeholder="Type your answer here..."
            )
            
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("✅ Submit Answer", type="primary"):
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
                if st.button("❌ Skip Question"):
                    workflow_state["user_answer"] = "No response provided"
                    workflow_state["pending_question"] = ""
                    workflow_state["status"] = "generating"
                    st.session_state.workflow_state = workflow_state
                    st.session_state.is_running = True
                    st.rerun()
    
    # Generation process
    if generate_btn and user_request.strip():
        st.session_state.is_running = True
        st.markdown("---")
        
        with st.spinner("🔄 Running multi-agent workflow with per-component evaluation..."):
            try:
                final_state = run_coloring_book_agent(user_request)
                st.session_state.workflow_state = final_state
                st.session_state.is_running = False
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error: {e}")
                st.session_state.is_running = False
    
    elif generate_btn and not user_request.strip():
        st.warning("Please enter a description.")
    
    # Resume workflow if waiting for user answer
    if workflow_state and workflow_state.get("status") == "waiting_for_user" and workflow_state.get("user_answer"):
        st.session_state.is_running = True
        st.markdown("---")
        with st.spinner("🔄 Continuing workflow with your answer..."):
            try:
                app = create_coloring_book_graph()
                current_state = workflow_state.copy()
                updated_state = app.invoke(current_state)
                st.session_state.workflow_state = updated_state
                st.session_state.is_running = False
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error continuing workflow: {e}")
                import traceback
                st.code(traceback.format_exc())
                st.session_state.is_running = False
    
    # Display results if workflow state exists
    if workflow_state and workflow_state.get("status") == "complete":
        st.markdown("---")
        
        # Top Section: Progress Overview
        render_progress_overview(workflow_state)
        
        # Middle Section: Final Results
        render_final_results_compact(workflow_state)
        
        # Bottom Section: Collapsed Attempt History
        render_attempt_history_collapsed(workflow_state)


def main():
    """Main Streamlit application with multi-tab interface."""
    
    # Header
    st.title("🎨 Coloring Book Workflow Assistant")
    st.markdown("*Multi-stage workflow for coloring book creation*")
    
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
        st.markdown("### 💾 Saved Designs")
        
        # Save current state
        workflow_state = st.session_state.get("workflow_state")
        if workflow_state and workflow_state.get("title"):
            save_name = st.text_input("Save as:", value=workflow_state.get("title", ""), key="save_name_input")
            if st.button("💾 Save Current Design", key="save_design_btn"):
                try:
                    filepath = save_workflow_state(workflow_state, name=save_name if save_name else None)
                    st.success(f"✅ Design saved!")
                    st.info(f"Saved to: `{filepath}`")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving: {e}")
        
        st.markdown("---")
        st.markdown("### 📂 Load Previous Design")
        
        # List saved states
        saved_states = list_saved_states()
        if saved_states:
            for state_info in saved_states[:10]:  # Show latest 10
                with st.expander(f"📄 {state_info['title']}", expanded=False):
                    st.caption(f"Saved: {state_info['saved_at']}")
                    if state_info['description']:
                        st.text(state_info['description'][:150])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("📂 Load", key=f"load_{state_info['name']}"):
                            loaded_state = load_workflow_state(state_info['filepath'])
                            if loaded_state:
                                st.session_state.workflow_state = loaded_state
                                st.success("✅ Design loaded!")
                                st.rerun()
                            else:
                                st.error("❌ Failed to load design")
                    with col2:
                        if st.button("🗑️ Delete", key=f"delete_{state_info['name']}"):
                            if delete_saved_state(state_info['filepath']):
                                st.success("✅ Deleted!")
                                st.rerun()
                            else:
                                st.error("❌ Failed to delete")
        else:
            st.info("No saved designs yet. Generate a design and save it!")
        
        st.markdown("---")
        st.markdown("### 📋 Workflow Stages")
        st.markdown("""
        1. **Design Generation** - Create design package
        2. **Image Generation** - Upload/generate images
        3. **Pinterest Publishing** - Publish to Pinterest
        4. **Future Steps** - Coming soon
        """)
    
    # Initialize session state
    if "workflow_state" not in st.session_state:
        st.session_state.workflow_state = None
    
    if "is_running" not in st.session_state:
        st.session_state.is_running = False
    
    # Multi-tab interface
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎨 Design Generation",
        "🖼️ Image Generation",
        "📌 Pinterest Publishing",
        "📄 Future Step"
    ])
    
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
            render_pinterest_tab(workflow_state)
        else:
            st.info("💡 Generate a design package and upload images first.")
    
    with tab4:
        render_placeholder_tab("Future Step")
    
    # Footer
    st.markdown("---")
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

