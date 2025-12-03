"""User interaction and file output tools."""

import json
import os
from datetime import datetime
from langchain_core.tools import tool


@tool
def ask_user(question: str) -> str:
    """
    Ask the user a clarifying question and wait for their response.
    Use this when you need more information to proceed with the task.
    
    Args:
        question: The question to ask the user.
        
    Returns:
        The user's response as a string.
    """
    print(f"\n❓ Agent Question: {question}")
    response = input("Your answer: ")
    return response.strip() if response.strip() else "No response provided"


@tool
def save_report(
    title: str,
    description: str,
    midjourney_prompts: list,
    seo_keywords: list,
    output_dir: str = "."
) -> str:
    """
    Save the complete coloring book design package to a JSON file.
    
    Args:
        title: The coloring book title.
        description: The coloring book description.
        midjourney_prompts: List of MidJourney prompts.
        seo_keywords: List of SEO keywords.
        output_dir: Directory to save the file (default: current directory).
        
    Returns:
        A message indicating the save status and filename.
    """
    report_data = {
        "title": title,
        "description": description,
        "midjourney_prompts": midjourney_prompts,
        "seo_keywords": seo_keywords,
        "generated_at": datetime.now().isoformat(),
        "stats": {
            "title_length": len(title),
            "description_word_count": len(description.split()),
            "prompt_count": len(midjourney_prompts),
            "keyword_count": len(seo_keywords)
        }
    }
    
    # Create safe filename from title
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)
    safe_title = safe_title.replace(" ", "_").lower()[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"coloring_book_{safe_title}_{timestamp}.json"
    
    filepath = os.path.join(output_dir, filename)
    
    try:
        os.makedirs(output_dir, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        return f"✅ Report saved successfully to: {filepath}"
    except Exception as e:
        return f"❌ Failed to save report: {str(e)}"


@tool
def display_results(
    title: str,
    description: str,
    midjourney_prompts: list,
    seo_keywords: list
) -> str:
    """
    Display the generated coloring book design package to the user.
    
    Args:
        title: The coloring book title.
        description: The coloring book description.
        midjourney_prompts: List of MidJourney prompts.
        seo_keywords: List of SEO keywords.
        
    Returns:
        A formatted string of the results.
    """
    output = []
    output.append("\n" + "=" * 60)
    output.append("✨ YOUR COMPLETE COLORING BOOK DESIGN PACKAGE ✨")
    output.append("=" * 60)
    
    output.append(f"\n📖 TITLE:\n   {title}")
    output.append(f"\n📝 DESCRIPTION:\n   {description}")
    
    output.append(f"\n🎨 MIDJOURNEY PROMPTS ({len(midjourney_prompts)} designs):")
    for i, prompt in enumerate(midjourney_prompts, 1):
        output.append(f"   {i:2d}. {prompt}")
    
    output.append(f"\n🔍 SEO KEYWORDS ({len(seo_keywords)} high-traffic terms):")
    for i, keyword in enumerate(seo_keywords, 1):
        output.append(f"   {i:2d}. {keyword}")
    
    output.append("\n" + "=" * 60)
    
    result = "\n".join(output)
    print(result)
    return result

