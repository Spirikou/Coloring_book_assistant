import os
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser

# Load environment variables
load_dotenv()

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

def create_coloring_book_design():
    """Generate a complete coloring book design package with clear reasoning steps."""
    
    # Initialize the language model
    llm = initialize_llm()
    
    # Get user input
    print("🎨 Welcome to the Advanced Coloring Book Design Generator! 🎨")
    print("=" * 60)
    
    user_input = input("Describe the coloring book design you'd like to create: ")
    
    if not user_input.strip():
        print("Please provide a description. Using default creative prompt...")
        user_input = "a magical forest with hidden creatures and geometric patterns"
    
    print("\n🔄 Processing your request through our 3-step reasoning process...\n")
    
    try:
        # Step 1: Generate title and description
        print("📝 Step 1: Generating title and description...")
        title_desc = generate_title_and_description(user_input, llm)
        print("✅ Title and description generated!")
        
        # Step 2: Create MidJourney prompts
        print("🎨 Step 2: Creating MidJourney prompts...")
        midjourney_prompts = generate_midjourney_prompts(title_desc["description"], llm)
        print("✅ MidJourney prompts created!")
        
        # Step 3: Extract SEO keywords
        print("🔍 Step 3: Extracting SEO keywords...")
        seo_keywords = extract_seo_keywords(title_desc["description"], llm)
        print("✅ SEO keywords extracted!")
        
        # Display the complete results
        print("\n" + "=" * 60)
        print("✨ YOUR COMPLETE COLORING BOOK DESIGN PACKAGE ✨")
        print("=" * 60)
        
        print(f"\n📖 TITLE:")
        print(f"   {title_desc['title']}")
        
        print(f"\n📝 DESCRIPTION:")
        print(f"   {title_desc['description']}")
        
        print(f"\n🎨 MIDJOURNEY PROMPTS (10 designs):")
        for i, prompt in enumerate(midjourney_prompts, 1):
            print(f"   {i:2d}. {prompt}")
        
        print(f"\n🔍 SEO KEYWORDS (10 high-traffic terms):")
        for i, keyword in enumerate(seo_keywords, 1):
            print(f"   {i:2d}. {keyword}")
        
        print("\n" + "=" * 60)
        print("🎉 Complete design package generated successfully! 🎉")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error generating design package: {e}")
        print("Please check your OpenAI API key and try again.")

def main():
    """Main function to run the coloring book design generator."""
    try:
        create_coloring_book_design()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye! Thanks for using the Coloring Book Assistant!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
