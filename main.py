import os
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

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
        "description": "A detailed description of approximately 200 words that follows the same style, tone, and structure as the example provided. The description should:
            - Introduce the book with an engaging hook
            - Describe the theme and style of the illustrations in detail
            - Highlight the creative and relaxing benefits of coloring
            - Mention the variety of pages and elements included
            - Emphasize the value for both adults and teens
            - Encourage the reader to explore inside the book and make a purchase
            - End with a strong call-to-action line (BUY NOW)
            
            After the main description, append the section exactly as below:

            Why You Will Love this Book:

            - Relax while coloring and let your stress fade away
            - 50 beautiful illustrations to express your creativity
            - Single-sided pages to prevent color bleeding and make them easy to frame
            - Large print 8.5" x 8.5" white pages with high-quality matte cover
            - Great for all skill levels
        "
    }}
    
    Guidelines:
    - The title should include practical keywords relevant to the theme and feel natural to a human reader
    - The description must be approximately 200 words and match the example structure
    - Use the exact "Why You Will Love this Book" section provided (word for word, no changes)
    - Keep the tone professional but friendly
    - Highlight specific design elements, complexity level, and unique features
    - Make sure the description sounds approachable, clear, and suitable for a real product listing
    - CRITICAL: Avoid AI-generated sounding words and phrases. DO NOT use words like:
      "whimsical", "enchanting", "captivating", "mesmerizing", "breathtaking", "stunning", 
      "magical", "delightful", "charming", "wondrous", "ethereal", "spellbinding", "fantastical",
      "mystical", "serene", "tranquil", "blissful", "exquisite", "gorgeous", "magnificent"
    - Instead, use natural, direct language that sounds human-written:
      * Use concrete descriptions and specific details about what's actually in the book
      * Write like a real person describing a product they've actually seen and used
      * Use straightforward, practical language
      * Be specific about art style, patterns, designs, and features rather than using flowery adjectives
      * Use words like "detailed", "intricate", "varied", "relaxing", "creative", "fun" instead of overly descriptive adjectives
    - Write as if you're a real seller on Amazon or Etsy describing your product to potential buyers
    
    Return ONLY the raw JSON object without any markdown formatting, code blocks, or additional text.
    """)
    
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({"user_input": user_input})
    
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        # Fallback - return empty object
        return {"title": "", "description": ""}

def generate_midjourney_prompts(description, llm):
    """Step 2: Create 50 MidJourney prompts for image designs."""
    
    prompt = ChatPromptTemplate.from_template("""
    You are an expert at creating MidJourney prompts for coloring book designs. Based on this description:
    
    Description: {description}
    
    Create 50 diverse MidJourney prompts that would generate excellent coloring book pages. Each prompt should:
    - Be optimized for MidJourney (include style keywords, quality settings)
    - Generate black and white line art suitable for coloring
    - Use ONLY short, targeted keywords separated by commas - NO wordy phrases or full sentences
    - Follow this exact format with keyword lists:
        "kameleo, drip, trippy, psychedelic, coloring book page, clean and simple line art --v 5 --q 2 --no color --ar 1:1"
    
    Return a JSON array with this structure:
    [
        "prompt 1",
        "prompt 2",
        ...
        "prompt 50"
    ]
    
    CRITICAL FORMATTING RULES:
    - Use ONLY comma-separated keywords - NO descriptive phrases or sentences
    - Each keyword should be 1-3 words maximum
    - Always include "coloring book page" and "clean and simple line art" as keywords
    - Add MidJourney parameters at the end: "--v 5 --q 2 --no color --ar 1:1"
    - Keep prompts concise - aim for 5-10 keywords before the required phrases
    
    Keyword Guidelines:
    - Use specific subject keywords (animal names, object names, pattern types)
    - Use style keywords (geometric, mandala, surreal, abstract, floral, etc.)
    - Use mood/theme keywords (trippy, psychedelic, nature, fantasy, etc.)
    - Avoid full descriptive sentences - break them into individual keywords
    - Ensure diversity across all 50 prompts (different subjects, styles, themes)
    
    Return ONLY the raw JSON array without any markdown formatting, code blocks, or additional text.
    """)

    
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({"description": description})
    
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        # Fallback - return empty list
        return []

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
    Return ONLY the raw JSON array without any markdown formatting, code blocks, or additional text.
    """)
    
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({"description": description})
    
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        # Fallback - return empty list
        return []

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
        # Use original user prompt if description is empty
        description_for_prompts = title_desc["description"] if title_desc["description"] else user_input
        midjourney_prompts = generate_midjourney_prompts(description_for_prompts, llm)
        print("✅ MidJourney prompts created!")
        
        # Step 3: Extract SEO keywords
        print("🔍 Step 3: Extracting SEO keywords...")
        # Use original user prompt if description is empty
        description_for_keywords = title_desc["description"] if title_desc["description"] else user_input
        seo_keywords = extract_seo_keywords(description_for_keywords, llm)
        print("✅ SEO keywords extracted!")
        
        # Display the complete results
        print("\n" + "=" * 60)
        print("✨ YOUR COMPLETE COLORING BOOK DESIGN PACKAGE ✨")
        print("=" * 60)
        
        print(f"\n📖 TITLE:")
        print(f"   {title_desc['title']}")
        
        print(f"\n📝 DESCRIPTION:")
        print(f"   {title_desc['description']}")
        
        print(f"\n🎨 MIDJOURNEY PROMPTS ({len(midjourney_prompts)} designs):")
        for i, prompt in enumerate(midjourney_prompts, 1):
            print(f"   {i:2d}. {prompt}")
        
        print(f"\n🔍 SEO KEYWORDS ({len(seo_keywords)} high-traffic terms):")
        for i, keyword in enumerate(seo_keywords, 1):
            print(f"   {i:2d}. {keyword}")
        
        print("\n" + "=" * 60)
        print("🎉 Complete design package generated successfully! 🎉")
        print("=" * 60)
        
        # Save results to JSON file
        report_data = {
            "title": title_desc["title"],
            "description": title_desc["description"],
            "midjourney_prompts": midjourney_prompts,
            "seo_keywords": seo_keywords
        }
        
        filename = f"coloring_book_design_{title_desc['title'].replace(' ', '_').lower()}.json"
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")
        
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
