import streamlit as st
import os
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="🎨 Coloring Book Design Generator",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

def initialize_llm():
    """Initialize the language model with consistent settings."""
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY")
    )

def generate_title_and_description(user_input, llm):
    """Step 1: Generate title and description from user input."""
    
    prompt = ChatPromptTemplate.from_template("""
    You are a professional coloring book designer and marketing expert. Based on the user's request, create:
    
    User Request: {user_input}
    
    Please provide a JSON response with the following structure:
    {{
        "title": "A catchy, marketable title for the coloring book (max 60 characters)",
        "description": "A detailed description of approximately 100 words that covers the theme, artistic style, target audience, unique features, and appeal to coloring book enthusiasts. Include specific details about the design elements, complexity level, and what makes this coloring book special."
    }}
    
    Guidelines:
    - The title should be SEO-friendly and appealing
    - The description should be approximately 100 words and very detailed
    - Highlight the artistic style (realistic, fantasy, mandala, zentangle, etc.)
    - Include target audience information
    - Mention unique features and design elements
    - Focus on popular coloring book themes and styles
    - Make it sound professional and marketable
    
    Return ONLY the JSON object, no additional text.
    """)
    
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({"user_input": user_input})
    
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        # Fallback if JSON parsing fails
        return {
            "title": "Creative Coloring Adventure",
            "description": "A beautiful collection of intricate designs perfect for relaxation and creativity. This coloring book features detailed mandala patterns, nature-inspired illustrations, and geometric designs that provide hours of mindful coloring. Each page offers varying complexity levels suitable for both beginners and experienced colorists. The designs are printed on high-quality paper with single-sided pages to prevent bleed-through. Perfect for stress relief, meditation, and artistic expression."
        }

def generate_midjourney_prompts(description, llm):
    """Step 2: Create 10 MidJourney prompts for image designs."""
    
    prompt = ChatPromptTemplate.from_template("""
    You are an expert at creating MidJourney prompts for coloring book designs. Based on this description:
    
    Description: {description}
    
    Create 10 diverse MidJourney prompts that would generate excellent coloring book pages. Each prompt should:
    - Be optimized for MidJourney (include style keywords, quality settings)
    - Generate black and white line art suitable for coloring
    - Be specific and detailed
    - Vary in complexity and focus
    
    Return a JSON array with this structure:
    [
        "prompt 1",
        "prompt 2",
        ...
        "prompt 10"
    ]
    
    Each prompt should be a complete MidJourney command ready to use.
    Return ONLY the JSON array, no additional text.
    """)
    
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({"description": description})
    
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        # Fallback prompts
        return [
            "black and white line art, coloring book style, intricate patterns --ar 1:1 --style raw",
            "detailed mandala design, coloring book illustration, zen art --ar 1:1 --style raw",
            "fantasy creature outline, coloring book page, detailed linework --ar 1:1 --style raw",
            "nature scene coloring book, botanical illustrations, line art --ar 1:1 --style raw",
            "geometric patterns coloring page, abstract design, black and white --ar 1:1 --style raw",
            "animal portrait coloring book, detailed line drawing --ar 1:1 --style raw",
            "architectural coloring page, building outline, intricate details --ar 1:1 --style raw",
            "floral mandala coloring book, symmetrical design, line art --ar 1:1 --style raw",
            "fantasy landscape coloring page, detailed linework --ar 1:1 --style raw",
            "ornamental border design, coloring book style, decorative patterns --ar 1:1 --style raw"
        ]

def extract_seo_keywords(description, llm):
    """Step 3: Extract 10 high-traffic, SEO-optimized keywords."""
    
    prompt = ChatPromptTemplate.from_template("""
    You are an SEO expert specializing in coloring book marketing. Based on this description:
    
    Description: {description}
    
    Extract 10 high-traffic, SEO-optimized keywords that would help this coloring book rank well in search engines. Focus on:
    - Popular coloring book search terms
    - Trending art and design keywords
    - Terms people actually search for when buying coloring books
    - Mix of short-tail and long-tail keywords
    
    Return a JSON array with this structure:
    [
        "keyword 1",
        "keyword 2",
        ...
        "keyword 10"
    ]
    
    Keywords should be relevant, searchable, and have good search volume potential.
    Return ONLY the JSON array, no additional text.
    """)
    
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({"description": description})
    
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        # Fallback keywords
        return [
            "coloring book",
            "adult coloring",
            "stress relief",
            "mindfulness",
            "art therapy",
            "relaxation",
            "creative therapy",
            "meditation coloring",
            "zen coloring",
            "therapeutic art"
        ]

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
        2. **🎨 MidJourney Prompts**: Create 10 AI prompts for coloring book pages
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
    st.subheader("💬 Describe Your Coloring Book Vision")
    
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
                        midjourney_prompts = generate_midjourney_prompts(title_desc["description"], llm)
                        status.update(label="✅ MidJourney prompts created!", state="complete")
                    
                    # Step 3: Extract SEO keywords
                    with st.status("🔍 Step 3: Extracting SEO keywords...", expanded=False) as status:
                        seo_keywords = extract_seo_keywords(title_desc["description"], llm)
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
            st.markdown("### 🎨 **MidJourney Prompts (10 designs)**")
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
