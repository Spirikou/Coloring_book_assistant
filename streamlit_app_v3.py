"""
Streamlit Frontend v3 - Per-Component Evaluation with Full Attempt Visibility

Shows all attempts (up to 5) for each component so you can verify
that the evaluator agent is doing a good job.

Run with: uv run streamlit run streamlit_app_v3.py
"""

import streamlit as st
import os
import json
from dotenv import load_dotenv

from graph import run_coloring_book_agent

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="🎨 Coloring Book Generator",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)


def render_attempt(attempt: dict, attempt_num: int, component_type: str):
    """Render a single attempt with content and evaluation."""
    evaluation = attempt.get("evaluation", {})
    content = attempt.get("content", {})
    feedback = attempt.get("feedback", "")
    score = evaluation.get("score", 0)
    passed = evaluation.get("passed", False) or score >= 80
    
    # Color based on score
    if score >= 80:
        color = "green"
        icon = "✅"
    elif score >= 60:
        color = "orange"
        icon = "🟡"
    else:
        color = "red"
        icon = "❌"
    
    with st.expander(f"Attempt {attempt_num} - {icon} Score: {score}/100", expanded=(not passed)):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 📝 Generated Content")
            
            if component_type == "title":
                # Title & Description
                title = content.get("title", "") if isinstance(content, dict) else ""
                desc = content.get("description", "") if isinstance(content, dict) else ""
                
                st.markdown("**Title:**")
                st.info(f"{title} ({len(title)} chars)")
                
                st.markdown("**Description:**")
                word_count = len(desc.split()) if desc else 0
                st.text_area("Description text", desc, height=150, disabled=True, label_visibility="collapsed", key=f"desc_{component_type}_{attempt_num}")
                st.caption(f"Word count: {word_count}")
                
            elif component_type == "prompts":
                # MidJourney Prompts
                prompts = content if isinstance(content, list) else []
                st.markdown(f"**Prompts Generated:** {len(prompts)}")
                
                if prompts:
                    # Show first 3 prompts
                    for i, p in enumerate(prompts[:3], 1):
                        st.code(p, language="text")
                    if len(prompts) > 3:
                        st.caption(f"... and {len(prompts) - 3} more prompts")
                        
            elif component_type == "keywords":
                # SEO Keywords
                keywords = content if isinstance(content, list) else []
                st.markdown(f"**Keywords Generated:** {len(keywords)}")
                
                if keywords:
                    # Show all keywords in chips
                    keyword_str = " | ".join(keywords)
                    st.write(keyword_str)
        
        with col2:
            st.markdown("### 🔍 Evaluator Assessment")
            
            # Score display
            st.metric("Quality Score", f"{score}/100", 
                     delta="PASSED" if passed else "NEEDS IMPROVEMENT",
                     delta_color="normal" if passed else "inverse")
            
            # Issues found
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
            
            # Summary
            summary = evaluation.get("summary", "")
            if summary:
                st.markdown(f"**Summary:** {summary}")
            
            # Metrics (if available)
            metrics = evaluation.get("metrics", {})
            if metrics:
                st.markdown("**Metrics:**")
                st.json(metrics)
        
        # Feedback sent to next attempt
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
    
    # Color based on score
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
                st.markdown(f"**Artist's Books:** {content.get('artist_books', 'N/A')}")
                st.markdown(f"**Why This Style:** {content.get('why_this_style', 'N/A')}")
                st.markdown(f"**Unique Angle:** {content.get('unique_angle', 'N/A')}")
                st.markdown(f"**Target Audience:** {content.get('target_audience', 'N/A')}")
                
                # Visual elements
                visual_elements = content.get('visual_elements', [])
                if visual_elements:
                    st.markdown("**Visual Elements:**")
                    st.write(" | ".join(visual_elements[:10]))
                
                # Style keywords
                style_kw = content.get('style_keywords', [])
                if style_kw:
                    st.markdown("**Style Keywords:**")
                    st.write(" | ".join(style_kw[:10]))
                
                # Mood
                mood = content.get('mood', [])
                if mood:
                    st.markdown("**Mood:**")
                    st.write(" | ".join(mood[:10]))
        
        with col2:
            st.markdown("### 🔍 Creativity Assessment")
            
            # Score display
            st.metric("Creativity Score", f"{score}/100", 
                     delta="PASSED" if passed else "NEEDS IMPROVEMENT",
                     delta_color="normal" if passed else "inverse")
            
            # Creativity breakdown
            breakdown = evaluation.get("creativity_breakdown", {})
            if breakdown:
                st.markdown("**Score Breakdown:**")
                for key, data in breakdown.items():
                    if isinstance(data, dict):
                        sub_score = data.get("score", 0)
                        assessment = data.get("assessment", "")
                        st.markdown(f"- **{key.replace('_', ' ').title()}**: {sub_score} pts")
                        if assessment:
                            st.caption(f"  {assessment[:100]}...")
            
            # Strengths
            strengths = evaluation.get("strengths", [])
            if strengths:
                st.markdown("**✓ Strengths:**")
                for s in strengths[:3]:
                    st.markdown(f"- {s}")
            
            # Issues
            issues = evaluation.get("issues", [])
            if issues:
                st.markdown("**Issues Found:**")
                for issue in issues[:3]:
                    severity = issue.get("severity", "unknown").upper()
                    issue_text = issue.get("issue", "")
                    severity_icon = {"CRITICAL": "🔴", "MAJOR": "🟠", "MINOR": "🟡"}.get(severity, "⚪")
                    st.markdown(f"{severity_icon} **[{severity}]** {issue_text[:80]}...")
        
        # Feedback
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
    
    # Show all attempts
    for i, attempt in enumerate(attempts, 1):
        if component_type == "theme":
            render_theme_attempt(attempt, i)
        else:
            render_attempt(attempt, i, component_type)
    
    st.markdown("---")


def render_final_results(state: dict):
    """Render the final results summary."""
    st.markdown("## 📊 Final Results Summary")
    
    # Quality metrics - now including theme
    theme_attempts = state.get("theme_attempts", [])
    has_theme = len(theme_attempts) > 0
    
    if has_theme:
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            theme_passed = state.get("theme_passed", False)
            st.metric("Theme", 
                     f"{state.get('theme_score', 0)}/100",
                     delta="✓" if theme_passed else "✗",
                     delta_color="normal" if theme_passed else "inverse")
    else:
        col1, col2, col3, col4, col5 = st.columns(5)
        col1 = col2  # Shift columns if no theme
    
    with col2 if has_theme else col1:
        title_passed = state.get("title_passed", False)
        st.metric("Title/Desc", 
                 f"{state.get('title_score', 0)}/100",
                 delta="✓" if title_passed else "✗",
                 delta_color="normal" if title_passed else "inverse")
    
    with col3 if has_theme else col2:
        prompts_passed = state.get("prompts_passed", False)
        st.metric("Prompts", 
                 f"{state.get('prompts_score', 0)}/100",
                 delta="✓" if prompts_passed else "✗",
                 delta_color="normal" if prompts_passed else "inverse")
    
    with col4 if has_theme else col3:
        keywords_passed = state.get("keywords_passed", False)
        st.metric("Keywords", 
                 f"{state.get('keywords_score', 0)}/100",
                 delta="✓" if keywords_passed else "✗",
                 delta_color="normal" if keywords_passed else "inverse")
    
    with col5 if has_theme else col4:
        total_attempts = (len(state.get("theme_attempts", [])) +
                         len(state.get("title_attempts", [])) + 
                         len(state.get("prompts_attempts", [])) + 
                         len(state.get("keywords_attempts", [])))
        st.metric("Total Attempts", total_attempts)
    
    # Final content tabs
    st.markdown("### 📦 Final Generated Content")
    
    # Add Theme tab if we have theme data
    expanded_theme = state.get("expanded_theme", {})
    if expanded_theme:
        tab0, tab1, tab2, tab3, tab4 = st.tabs(["🎨 Theme", "📖 Title & Description", "🎨 Prompts", "🔍 Keywords", "📥 Download"])
        
        with tab0:
            st.markdown("### Creative Direction")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Expanded Theme:** {expanded_theme.get('expanded_theme', 'N/A')}")
                st.markdown(f"**Artistic Style:** {expanded_theme.get('artistic_style', 'N/A')}")
                st.markdown(f"**Signature Artist:** {expanded_theme.get('signature_artist', 'N/A')}")
                st.markdown(f"**Artist's Famous Books:** {expanded_theme.get('artist_books', 'N/A')}")
                st.markdown(f"**Why This Style:** {expanded_theme.get('why_this_style', 'N/A')}")
            with col2:
                st.markdown(f"**Unique Angle:** {expanded_theme.get('unique_angle', 'N/A')}")
                st.markdown(f"**Target Audience:** {expanded_theme.get('target_audience', 'N/A')}")
                st.markdown(f"**Difficulty Level:** {expanded_theme.get('difficulty_level', 'N/A')}")
            
            # Visual elements and style keywords
            visual = expanded_theme.get('visual_elements', [])
            if visual:
                st.markdown("**Visual Elements:**")
                st.write(" • ".join(visual))
            
            style_kw = expanded_theme.get('style_keywords', [])
            if style_kw:
                st.markdown("**Style Keywords:**")
                st.write(" • ".join(style_kw))
            
            mood = expanded_theme.get('mood', [])
            if mood:
                st.markdown("**Mood:**")
                st.write(" • ".join(mood))
            
            # Style research
            style_research = state.get("style_research", {})
            if style_research:
                with st.expander("🔍 Style & Artist Research"):
                    if style_research.get("style_research"):
                        st.markdown("**Artistic Style Research:**")
                        st.text(str(style_research.get("style_research", ""))[:1000])
                    if style_research.get("artist_research"):
                        st.markdown("**Artist Research:**")
                        st.text(str(style_research.get("artist_research", ""))[:1000])
    else:
        tab1, tab2, tab3, tab4 = st.tabs(["📖 Title & Description", "🎨 Prompts", "🔍 Keywords", "📥 Download"])
    
    with tab1:
        st.markdown(f"**Title:** {state.get('title', 'N/A')}")
        st.markdown("**Description:**")
        st.write(state.get("description", "N/A"))
    
    with tab2:
        prompts = state.get("midjourney_prompts", [])
        st.markdown(f"**{len(prompts)} MidJourney Prompts:**")
        
        search = st.text_input("🔍 Filter prompts", key="prompt_filter")
        filtered = [p for p in prompts if search.lower() in p.lower()] if search else prompts
        
        for i, p in enumerate(filtered, 1):
            with st.expander(f"Prompt {i}"):
                st.code(p, language="text")
    
    with tab3:
        keywords = state.get("seo_keywords", [])
        st.markdown(f"**{len(keywords)} SEO Keywords:**")
        for i, kw in enumerate(keywords, 1):
            st.markdown(f"{i}. {kw}")
    
    with tab4:
        report = {
            "title": state.get("title", ""),
            "description": state.get("description", ""),
            "midjourney_prompts": state.get("midjourney_prompts", []),
            "seo_keywords": state.get("seo_keywords", []),
            "quality_scores": {
                "title_description": state.get("title_score", 0),
                "prompts": state.get("prompts_score", 0),
                "keywords": state.get("keywords_score", 0)
            },
            "attempts_needed": {
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


def main():
    """Main Streamlit application."""
    
    # Header
    st.title("🎨 Coloring Book Design Generator")
    st.markdown("*Per-Component Evaluation with Full Attempt Visibility*")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # API Key check
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            st.error("⚠️ OpenAI API key not found!")
            st.info("Please set your OPENAI_API_KEY in the .env file")
            return
        else:
            st.success("✅ API key loaded")
        
        st.markdown("---")
        st.markdown("### 🔄 How It Works")
        st.markdown("""
        Each component is generated and evaluated for **creativity & quality**:
        
        **0. Theme Expansion** (NEW!)
        - Researches market trends
        - Creates unique creative angle
        - Evaluates: uniqueness, artistic fit, market opportunity
        
        **1. Title & Description**
        - Up to 5 attempts
        - Checks: creativity, human-like voice, no clichés
        
        **2. MidJourney Prompts**
        - Up to 5 attempts
        - Checks: creative variety, artistic coherence
        
        **3. SEO Keywords**
        - Up to 5 attempts
        - Checks: niche opportunity, buyer intent
        
        **Pass Threshold: 80/100**
        """)
        
        st.markdown("---")
        st.markdown("### 🎨 Creativity Assessment")
        st.markdown("""
        The evaluator now checks:
        - **Uniqueness**: Is it generic or creative?
        - **Human Quality**: Does it sound like AI?
        - **Market Fit**: Will it stand out?
        - **Voice Authenticity**: Sentence variety
        """)
        
        st.markdown("---")
        st.markdown("### 🔍 Evaluator Verification")
        st.markdown("""
        View ALL attempts to verify the evaluator is:
        - Catching creativity issues
        - Identifying AI-sounding text
        - Providing actionable feedback
        - Rewarding unique angles
        """)
    
    # Initialize session state
    if "workflow_state" not in st.session_state:
        st.session_state.workflow_state = None
    
    if "is_running" not in st.session_state:
        st.session_state.is_running = False
    
    # Input section
    st.subheader("📝 Describe Your Coloring Book")
    
    user_request = st.text_area(
        "What kind of coloring book would you like to create?",
        placeholder="Example: A forest animals coloring book for adults with intricate mandala patterns...",
        height=100
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        generate_btn = st.button("🚀 Generate", type="primary", disabled=st.session_state.is_running)
    with col2:
        if st.button("🔄 Clear", disabled=st.session_state.is_running):
            st.session_state.workflow_state = None
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
    
    # Display results
    if st.session_state.workflow_state:
        state = st.session_state.workflow_state
        
        st.markdown("---")
        st.header("📋 Per-Component Attempt History")
        st.markdown("*Review each attempt to verify evaluator quality - including creativity assessment*")
        
        # Theme Expansion attempts (NEW)
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
        
        # Final results
        render_final_results(state)
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            <p>🎨 Built with Streamlit & LangGraph | Per-Component Evaluation System</p>
        </div>
        """, 
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
