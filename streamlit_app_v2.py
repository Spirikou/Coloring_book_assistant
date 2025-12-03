import streamlit as st
import os
import json
from dotenv import load_dotenv

# Import functions from main.py to avoid duplication
from main import (
    initialize_llm,
    generate_title_and_description,
    generate_midjourney_prompts,
    extract_seo_keywords
)

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="🎨 Coloring Book Design Generator",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main Streamlit application."""
    
    # Header
    st.title("🎨 Advanced Coloring Book Design Generator")
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
            st.success("✅ OpenAI API key loaded")
        
        st.markdown("---")
        st.markdown("### 📋 How it works:")
        st.markdown("""
        1. **📝 Title & Description**: Generate a marketable title and compelling description
        2. **🎨 MidJourney Prompts**: Create 50 AI prompts for coloring book pages
        3. **🔍 SEO Keywords**: Extract high-traffic keywords for marketing
        """)
        
        st.markdown("---")
        st.markdown("### 💡 Tips:")
        st.markdown("""
        - Be specific about your theme
        - Mention artistic style preferences
        - Include target audience details
        """)
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "generated_content" not in st.session_state:
        st.session_state.generated_content = None
    
    # Chat interface
    st.subheader(" Describe Your Coloring Book Vision")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Describe the coloring book design you'd like to create..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("🔄 Processing your request through our 3-step reasoning process..."):
                try:
                    # Initialize LLM
                    llm = initialize_llm()
                    
                    # Step 1: Generate title and description
                    with st.status("📝 Step 1: Generating title and description...", expanded=False) as status:
                        title_desc = generate_title_and_description(prompt, llm)
                        status.update(label="✅ Title and description generated!", state="complete")
                    
                    # Step 2: Create MidJourney prompts
                    with st.status("🎨 Step 2: Creating MidJourney prompts...", expanded=False) as status:
                        # Use original user prompt if description is empty
                        description_for_prompts = title_desc["description"] if title_desc["description"] else prompt
                        midjourney_prompts = generate_midjourney_prompts(description_for_prompts, llm)
                        status.update(label="✅ MidJourney prompts created!", state="complete")
                    
                    # Step 3: Extract SEO keywords
                    with st.status("🔍 Step 3: Extracting SEO keywords...", expanded=False) as status:
                        # Use original user prompt if description is empty
                        description_for_keywords = title_desc["description"] if title_desc["description"] else prompt
                        seo_keywords = extract_seo_keywords(description_for_keywords, llm)
                        status.update(label="✅ SEO keywords extracted!", state="complete")
                    
                    # Store generated content
                    st.session_state.generated_content = {
                        "title": title_desc["title"],
                        "description": title_desc["description"],
                        "midjourney_prompts": midjourney_prompts,
                        "seo_keywords": seo_keywords
                    }
                    
                    # Display results
                    st.success("🎉 Complete design package generated successfully!")
                    
                except Exception as e:
                    st.error(f"❌ Error generating design package: {e}")
                    st.info("Please check your OpenAI API key and try again.")
        
        # Add assistant response to chat history
        st.session_state.messages.append({
            "role": "assistant", 
            "content": "✅ Your coloring book design package has been generated! Check the results below."
        })
    
    # Display generated content
    if st.session_state.generated_content:
        st.markdown("---")
        st.subheader("✨ Your Complete Coloring Book Design Package")
        
        content = st.session_state.generated_content
        
        # Create tabs for better organization
        tab1, tab2, tab3, tab4 = st.tabs(["📖 Title & Description", "🎨 MidJourney Prompts", "🔍 SEO Keywords", "📋 Full Report"])
        
        with tab1:
            st.markdown(f"### 📖 **Title**")
            st.info(content["title"])
            
            st.markdown(f"### 📝 **Description**")
            st.write(content["description"])
        
        with tab2:
            num_prompts = len(content["midjourney_prompts"])
            st.markdown(f"### 🎨 **MidJourney Prompts ({num_prompts} designs)**")
            for i, prompt in enumerate(content["midjourney_prompts"], 1):
                with st.expander(f"Prompt {i}"):
                    st.code(prompt, language="text")
                    if st.button(f"📋 Copy Prompt {i}", key=f"copy_prompt_{i}"):
                        st.write("✅ Copied to clipboard!")
        
        with tab3:
            st.markdown("### 🔍 **SEO Keywords (10 high-traffic terms)**")
            cols = st.columns(2)
            for i, keyword in enumerate(content["seo_keywords"]):
                with cols[i % 2]:
                    st.markdown(f"**{i+1}.** {keyword}")
        
        with tab4:
            st.markdown("### 📋 **Complete Report**")
            
            # Title and Description
            st.markdown(f"**Title:** {content['title']}")
            st.markdown(f"**Description:** {content['description']}")
            
            # MidJourney Prompts
            st.markdown("**MidJourney Prompts:**")
            for i, prompt in enumerate(content["midjourney_prompts"], 1):
                st.markdown(f"{i}. {prompt}")
            
            # SEO Keywords
            st.markdown("**SEO Keywords:**")
            keywords_text = ", ".join(content["seo_keywords"])
            st.markdown(keywords_text)
            
            # Download button
            report_data = {
                "title": content["title"],
                "description": content["description"],
                "midjourney_prompts": content["midjourney_prompts"],
                "seo_keywords": content["seo_keywords"]
            }
            
            st.download_button(
                label="📥 Download Report as JSON",
                data=json.dumps(report_data, indent=2),
                file_name=f"coloring_book_design_{content['title'].replace(' ', '_').lower()}.json",
                mime="application/json"
            )
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            <p>🎨 Built with Streamlit & LangChain | Powered by OpenAI GPT-4o-mini</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()

