"""Content generation tools with built-in evaluation and refinement."""

import os
import json
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

from agents.evaluator import (
    evaluate_title_description,
    evaluate_prompts,
    evaluate_keywords,
    evaluate_theme_creativity,
    format_feedback,
    BANNED_AI_WORDS,
    REQUIRED_SECTION,
    MAX_ATTEMPTS,
    PASS_THRESHOLD
)
from tools.search_tools import web_search

load_dotenv()


def get_llm():
    """Get the language model instance."""
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY")
    )


# =============================================================================
# THEME EXPANSION FUNCTIONS
# =============================================================================

def _search_artistic_style(theme: str) -> dict:
    """Search for the best artistic style and associated author for the theme."""
    print("   🎨 Searching for best artistic style...")
    
    style_results = {}
    
    # Search for artistic styles that match the theme
    try:
        style_query = f"best artistic style for {theme} coloring book illustration"
        style_search = web_search.invoke({"query": style_query, "max_results": 3})
        style_results["style_research"] = style_search if style_search else ""
    except Exception as e:
        style_results["style_research"] = f"Search failed: {e}"
    
    # Search for famous coloring book artists in this style
    try:
        artist_query = f"famous coloring book artist {theme} style Johanna Basford Kerby Rosanes"
        artist_search = web_search.invoke({"query": artist_query, "max_results": 3})
        style_results["artist_research"] = artist_search if artist_search else ""
    except Exception as e:
        style_results["artist_research"] = f"Search failed: {e}"
    
    return style_results


def _expand_theme_internal(user_input: str, style_research: dict, feedback: str = "") -> dict:
    """Internal function to expand user input into a detailed creative theme with artistic style."""
    llm = get_llm()
    
    feedback_section = ""
    if feedback:
        feedback_section = f"""

IMPORTANT - Previous theme expansion had issues. Address these:
{feedback}
"""
    
    style_context = style_research.get("style_research", "")
    artist_context = style_research.get("artist_research", "")
    
    prompt = ChatPromptTemplate.from_template("""
You are a creative director for a coloring book publishing company. Your job is to craft a UNIQUE theme and select the PERFECT artistic style.

## USER'S THEME IDEA:
{user_input}

## ARTISTIC STYLE RESEARCH:
{style_context}

## ARTIST RESEARCH:
{artist_context}
{feedback_section}

## YOUR TASK:
Create a unique creative concept by pairing the theme with the ideal artistic style and a signature artist inspiration.

## ARTISTIC STYLES TO CONSIDER:
1. **Mandala/Zentangle** - Intricate circular patterns, meditative (Johanna Basford style)
2. **Art Nouveau** - Flowing organic lines, botanical, elegant curves (Alphonse Mucha inspired)
3. **Hyperdetailed/Morphia** - Complex transformations, hidden elements (Kerby Rosanes style)
4. **Geometric/Sacred Geometry** - Mathematical patterns, symmetry
5. **Vintage/Retro** - Old-fashioned charm, nostalgic elements
6. **Folk Art** - Cultural patterns, traditional motifs
7. **Kawaii/Cute** - Japanese cute style, round shapes, adorable characters
8. **Gothic/Dark Fantasy** - Dramatic, mysterious, detailed darkness
9. **Botanical/Scientific** - Precise plant illustrations, nature studies
10. **Whimsical Fantasy** - Dreamy, imaginative, fairy-tale elements

## REQUIREMENTS:
1. **Match Theme to Style**: Which artistic style BEST complements this theme?
2. **Find Signature Artist**: Who is the most famous artist in this style for coloring books?
3. **Create Unique Angle**: How can we make this stand out from existing books?
4. **Define Visual Language**: What specific visual elements define this style?

## RESPONSE FORMAT (JSON only):
{{
    "original_input": "{user_input}",
    "expanded_theme": "A detailed, evocative description of the theme concept",
    "artistic_style": "The chosen artistic style (be specific)",
    "style_description": "Detailed description of what this style looks like",
    "signature_artist": "The most famous coloring book artist in this style",
    "artist_books": "Famous coloring books by this artist",
    "why_this_style": "Why this style is perfect for this theme",
    "unique_angle": "What makes this concept unique and special",
    "target_audience": "Who will love this book and why",
    "difficulty_level": "beginner|intermediate|advanced",
    "visual_elements": ["specific", "visual", "elements", "to", "include"],
    "style_keywords": ["keywords", "that", "define", "the", "style"],
    "mood": ["mood", "descriptors"],
    "page_ideas": ["idea 1", "idea 2", "idea 3", "idea 4", "idea 5"]
}}

Return ONLY valid JSON, no other text.""")
    
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({
        "user_input": user_input,
        "style_context": style_context,
        "artist_context": artist_context,
        "feedback_section": feedback_section
    })
    
    try:
        result = result.strip()
        if result.startswith("```json"):
            result = result[7:]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]
        return json.loads(result.strip())
    except json.JSONDecodeError:
        return {
            "original_input": user_input,
            "expanded_theme": "",
            "artistic_style": "",
            "signature_artist": "",
            "error": "Failed to parse theme expansion"
        }


@tool
def expand_and_research_theme(user_input: str) -> dict:
    """
    Expand a basic theme idea into a unique creative concept with the perfect artistic style.
    Searches for the best artistic style that matches the theme and finds a signature
    artist associated with that style for inspiration.
    
    This should be called FIRST before generating title/description.
    The output will influence all subsequent content generation.
    
    Args:
        user_input: The user's basic theme idea (e.g., "forest animals").
        
    Returns:
        Dictionary with expanded_theme, artistic_style, signature_artist, and unique_angle.
    """
    print("\n🎨 Step 0: Theme & Artistic Style Development")
    
    # Phase 1: Search for best artistic style and artist
    print("   🔍 Researching artistic styles and artists...")
    style_research = _search_artistic_style(user_input)
    
    # Phase 2: Theme Expansion with Evaluation Loop
    attempts = []
    feedback = ""
    best_attempt = None
    best_score = -1
    
    for attempt_num in range(1, MAX_ATTEMPTS + 1):
        print(f"   🎨 Theme Development - Attempt {attempt_num}/{MAX_ATTEMPTS}")
        
        # Generate expanded theme (with feedback from best attempt if available)
        theme_data = _expand_theme_internal(user_input, style_research, feedback)
        theme_data["style_research"] = style_research
        
        # Evaluate creativity
        evaluation = evaluate_theme_creativity(theme_data)
        
        score = evaluation.get("score", 0)
        
        # Record attempt
        attempt_record = {
            "attempt": attempt_num,
            "content": theme_data,
            "evaluation": evaluation,
            "feedback": feedback
        }
        attempts.append(attempt_record)
        
        # Track best attempt
        if score > best_score:
            best_score = score
            best_attempt = attempt_record
            print(f"      Creativity Score: {score}/100 ⭐ NEW BEST")
        else:
            print(f"      Creativity Score: {score}/100 (best: {best_score})")
        
        passed = evaluation.get("passed", False) or score >= PASS_THRESHOLD
        
        if passed:
            print(f"      ✅ PASSED")
            return {
                "final_theme": theme_data,
                "style_research": style_research,
                "attempts": attempts,
                "passed": True,
                "final_score": score,
                "attempts_needed": attempt_num
            }
        
        # Prepare feedback for next attempt - BUILD ON BEST ATTEMPT
        feedback = format_feedback(best_attempt["evaluation"], "Theme")
        # Include the best theme for reference
        best_theme = best_attempt["content"]
        feedback += f"\n\n📋 BEST THEME SO FAR (score {best_score}/100) - IMPROVE THIS:\n"
        feedback += f"Theme: {best_theme.get('expanded_theme', '')[:100]}...\n"
        feedback += f"Artistic Style: {best_theme.get('artistic_style', '')}\n"
        feedback += f"Signature Artist: {best_theme.get('signature_artist', '')}\n"
        feedback += f"Unique Angle: {best_theme.get('unique_angle', '')[:100]}..."
    
    # Return BEST attempt if none passed
    print(f"      ❌ Max attempts reached. Using best attempt (score: {best_score})")
    return {
        "final_theme": best_attempt["content"],
        "style_research": style_research,
        "attempts": attempts,
        "passed": False,
        "final_score": best_score,
        "attempts_needed": MAX_ATTEMPTS
    }


# =============================================================================
# INTERNAL GENERATION FUNCTIONS (not exposed as tools)
# =============================================================================

def _generate_title_description_internal(user_input: str, feedback: str = "", theme_context: dict = None) -> dict:
    """Internal function to generate title and description influenced by theme."""
    llm = get_llm()
    
    feedback_section = ""
    if feedback:
        feedback_section = f"""
    
    IMPORTANT - Previous attempt had issues. Fix these problems:
    {feedback}
    """
    
    # Build theme context section
    theme_section = ""
    if theme_context:
        theme_section = f"""
## CREATIVE DIRECTION (from theme development):
- **Theme**: {theme_context.get('expanded_theme', user_input)}
- **Artistic Style**: {theme_context.get('artistic_style', 'Not specified')}
- **Signature Artist Inspiration**: {theme_context.get('signature_artist', 'Not specified')}
- **Unique Angle**: {theme_context.get('unique_angle', 'Not specified')}
- **Target Audience**: {theme_context.get('target_audience', 'Adults')}
- **Style Keywords**: {', '.join(theme_context.get('style_keywords', []))}
- **Mood**: {', '.join(theme_context.get('mood', []))}

USE THIS CREATIVE DIRECTION to craft the title and description!
"""
    
    prompt = ChatPromptTemplate.from_template("""
You are a professional coloring book designer and marketing expert. Create a title and description that captures the unique creative vision.

## USER'S ORIGINAL REQUEST:
{user_input}
{theme_section}
{feedback_section}

## RESPONSE FORMAT (JSON only):
{{
    "title": "A catchy, marketable title for the coloring book (max 60 characters)",
    "description": "A detailed description of approximately 200 words..."
}}

## TITLE REQUIREMENTS:
- MAXIMUM 60 characters (count carefully!)
- Reflect the ARTISTIC STYLE and UNIQUE ANGLE
- Include the signature artist's style influence if relevant (e.g., "Zentangle-Style", "Art Nouveau")
- Make it stand out - NOT generic like "Beautiful Coloring Book"
- Include searchable keywords naturally

## DESCRIPTION REQUIREMENTS:
- Approximately 180-220 words
- Highlight the ARTISTIC STYLE prominently
- Mention the style inspiration/artist influence
- Write like a real Amazon seller, not an AI
- Include specific details about what's in the book
- Match the MOOD from the theme

## CRITICAL - MUST INCLUDE THIS EXACT SECTION AT THE END:

Why You Will Love this Book:

- Relax while coloring and let your stress fade away
- 50 beautiful illustrations to express your creativity
- Single-sided pages to prevent color bleeding and make them easy to frame
- Large print 8.5" x 8.5" white pages with high-quality matte cover
- Great for all skill levels

## BANNED WORDS - DO NOT USE:
{banned_words}

Return ONLY the raw JSON object without any markdown formatting.""")
    
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({
        "user_input": user_input,
        "theme_section": theme_section,
        "feedback_section": feedback_section,
        "banned_words": ", ".join(BANNED_AI_WORDS[:20])
    })
    
    try:
        # Clean up response
        result = result.strip()
        if result.startswith("```json"):
            result = result[7:]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]
        return json.loads(result.strip())
    except json.JSONDecodeError:
        return {"title": "", "description": "", "error": "Failed to parse response"}


def _generate_prompts_internal(description: str, feedback: str = "", theme_context: dict = None) -> list:
    """Internal function to generate MidJourney prompts influenced by theme and artistic style."""
    llm = get_llm()
    
    feedback_section = ""
    if feedback:
        feedback_section = f"""

IMPORTANT - Previous attempt had issues. Fix these problems:
{feedback}
"""
    
    # Build artistic style guidance
    style_section = ""
    if theme_context:
        artistic_style = theme_context.get('artistic_style', '')
        signature_artist = theme_context.get('signature_artist', '')
        style_keywords = theme_context.get('style_keywords', [])
        visual_elements = theme_context.get('visual_elements', [])
        page_ideas = theme_context.get('page_ideas', [])
        
        style_section = f"""
## ARTISTIC STYLE DIRECTION:
- **Style**: {artistic_style}
- **Artist Inspiration**: {signature_artist}
- **Style Keywords to Include**: {', '.join(style_keywords)}
- **Visual Elements**: {', '.join(visual_elements)}
- **Page Ideas**: {', '.join(page_ideas)}

EVERY prompt should reflect this artistic style! Include style-specific keywords.
"""
    
    prompt = ChatPromptTemplate.from_template("""
You are an expert at creating MidJourney prompts for coloring book designs in a SPECIFIC artistic style.

## BOOK DESCRIPTION:
{description}
{style_section}
{feedback_section}

## PROMPT FORMAT:
Create EXACTLY 50 prompts. Each prompt MUST follow this EXACT format:

"[subject], [style keywords], [details], coloring book page, clean and simple line art --v 5 --q 2 --no color --ar 1:1"

## CRITICAL RULES:
1. EXACTLY 50 prompts (not 49, not 51)
2. Keywords ONLY - NO sentences or phrases
3. Each keyword is 1-3 words max
4. MUST include "coloring book page" in every prompt
5. MUST include "clean and simple line art" in every prompt
6. MUST end with "--v 5 --q 2 --no color --ar 1:1"
7. EVERY prompt must reflect the ARTISTIC STYLE specified above

## STYLE-SPECIFIC EXAMPLES:
- Mandala style: "owl, mandala pattern, zentangle, intricate circles, coloring book page, clean and simple line art --v 5 --q 2 --no color --ar 1:1"
- Art Nouveau: "peacock, art nouveau, flowing lines, decorative border, coloring book page, clean and simple line art --v 5 --q 2 --no color --ar 1:1"
- Kerby Rosanes style: "elephant, morphing into flowers, hyperdetailed, hidden elements, coloring book page, clean and simple line art --v 5 --q 2 --no color --ar 1:1"

## BAD PROMPTS (DO NOT DO THIS):
"A beautiful owl sitting majestically in an enchanted forest" - TOO WORDY, uses banned words, no style keywords

Return a JSON array with exactly 50 prompts. No markdown, just the array.""")

    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({
        "description": description,
        "style_section": style_section,
        "feedback_section": feedback_section
    })
    
    try:
        result = result.strip()
        if result.startswith("```json"):
            result = result[7:]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]
        return json.loads(result.strip())
    except json.JSONDecodeError:
        return []


def _generate_keywords_internal(description: str, feedback: str = "", theme_context: dict = None) -> list:
    """Internal function to generate SEO keywords influenced by theme and artistic style."""
    llm = get_llm()
    
    feedback_section = ""
    if feedback:
        feedback_section = f"""

IMPORTANT - Previous attempt had issues. Fix these problems:
{feedback}
"""
    
    # Build theme-specific keyword guidance
    theme_section = ""
    if theme_context:
        artistic_style = theme_context.get('artistic_style', '')
        signature_artist = theme_context.get('signature_artist', '')
        unique_angle = theme_context.get('unique_angle', '')
        style_keywords = theme_context.get('style_keywords', [])
        target_audience = theme_context.get('target_audience', '')
        
        theme_section = f"""
## THEME & STYLE CONTEXT:
- **Artistic Style**: {artistic_style}
- **Artist Inspiration**: {signature_artist}
- **Unique Angle**: {unique_angle}
- **Target Audience**: {target_audience}
- **Style Keywords**: {', '.join(style_keywords)}

Include keywords that capture both the THEME and the ARTISTIC STYLE!
"""
    
    prompt = ChatPromptTemplate.from_template("""
You are an SEO expert specializing in coloring book marketing on Amazon.

## BOOK DESCRIPTION:
{description}
{theme_section}
{feedback_section}

## TASK:
Generate EXACTLY 10 SEO keywords that capture both the THEME and ARTISTIC STYLE.

## REQUIREMENTS:
1. EXACTLY 10 keywords (not 9, not 11)
2. Mix of short-tail (1-2 words) and long-tail (3+ words):
   - 4-5 short-tail: "coloring book", "adult coloring", style keywords
   - 5-6 long-tail: combining theme + style + audience
3. Include at least 2 keywords mentioning the ARTISTIC STYLE
4. Include at least 1 keyword mentioning the artist name/style if famous
5. No duplicates or near-duplicates
6. Terms people actually search for on Amazon

## STYLE-SPECIFIC KEYWORD EXAMPLES:
- Mandala style: "mandala coloring book", "zentangle patterns for adults"
- Art Nouveau: "art nouveau coloring", "botanical art coloring book"
- Kerby Rosanes style: "detailed coloring book", "morphia style coloring"

## GOOD EXAMPLES:
- "adult coloring book" (short-tail)
- "mandala stress relief coloring" (long-tail with style)
- "intricate animal designs coloring book" (long-tail with theme)

## BAD EXAMPLES:
- "book" (too generic)
- "beautiful artistic creative coloring experience" (not a real search term)

Return a JSON array with exactly 10 keywords. No markdown, just the array.""")
    
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({
        "description": description,
        "theme_section": theme_section,
        "feedback_section": feedback_section
    })
    
    try:
        result = result.strip()
        if result.startswith("```json"):
            result = result[7:]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]
        return json.loads(result.strip())
    except json.JSONDecodeError:
        return []


# =============================================================================
# GENERATE AND REFINE TOOLS (exposed as tools with evaluation loop)
# =============================================================================

@tool
def generate_and_refine_title_description(user_input: str, theme_context: dict = None) -> dict:
    """
    Generate and refine a title and description with automatic quality evaluation.
    Uses the theme context (artistic style, signature artist) to influence the output.
    Attempts up to 5 times until quality score >= 80.
    Each attempt builds on the BEST previous attempt.
    
    Args:
        user_input: The user's description of the coloring book theme.
        theme_context: Optional dict with expanded_theme, artistic_style, signature_artist, etc.
        
    Returns:
        Dictionary with final_content and attempts history.
    """
    attempts = []
    feedback = ""
    best_attempt = None
    best_score = -1
    
    for attempt_num in range(1, MAX_ATTEMPTS + 1):
        print(f"   📝 Title/Description - Attempt {attempt_num}/{MAX_ATTEMPTS}")
        
        # Generate (with feedback from best attempt if available)
        content = _generate_title_description_internal(user_input, feedback, theme_context)
        
        # Evaluate
        evaluation = evaluate_title_description(
            content.get("title", ""),
            content.get("description", "")
        )
        
        score = evaluation.get("score", 0)
        
        # Record attempt
        attempt_record = {
            "attempt": attempt_num,
            "content": content,
            "evaluation": evaluation,
            "feedback": feedback
        }
        attempts.append(attempt_record)
        
        # Track best attempt
        if score > best_score:
            best_score = score
            best_attempt = attempt_record
            print(f"      Score: {score}/100 ⭐ NEW BEST")
        else:
            print(f"      Score: {score}/100 (best: {best_score})")
        
        passed = evaluation.get("passed", False) or score >= PASS_THRESHOLD
        
        if passed:
            print(f"      ✅ PASSED")
            return {
                "final_content": content,
                "attempts": attempts,
                "passed": True,
                "final_score": score,
                "attempts_needed": attempt_num
            }
        
        # Prepare feedback for next attempt - BUILD ON BEST ATTEMPT
        feedback = format_feedback(best_attempt["evaluation"], "Title & Description")
        # Include the best content so far for the LLM to improve upon
        feedback += f"\n\n📋 BEST ATTEMPT SO FAR (score {best_score}/100) - IMPROVE THIS:\n"
        feedback += f"Title: {best_attempt['content'].get('title', '')}\n"
        feedback += f"Description excerpt: {best_attempt['content'].get('description', '')[:200]}..."
    
    # Return BEST attempt if none passed
    print(f"      ❌ Max attempts reached. Using best attempt (score: {best_score})")
    return {
        "final_content": best_attempt["content"],
        "attempts": attempts,
        "passed": False,
        "final_score": best_score,
        "attempts_needed": MAX_ATTEMPTS
    }


@tool
def generate_and_refine_prompts(description: str, theme_context: dict = None) -> dict:
    """
    Generate and refine MidJourney prompts with automatic quality evaluation.
    Uses the theme context (artistic style, visual elements) to influence the prompts.
    Attempts up to 5 times until quality score >= 80.
    Each attempt builds on the BEST previous attempt.
    
    Args:
        description: The coloring book description to base prompts on.
        theme_context: Optional dict with artistic_style, style_keywords, visual_elements, etc.
        
    Returns:
        Dictionary with final_content (list of prompts) and attempts history.
    """
    attempts = []
    feedback = ""
    best_attempt = None
    best_score = -1
    
    for attempt_num in range(1, MAX_ATTEMPTS + 1):
        print(f"   🎨 MidJourney Prompts - Attempt {attempt_num}/{MAX_ATTEMPTS}")
        
        # Generate (with feedback from best attempt if available)
        prompts = _generate_prompts_internal(description, feedback, theme_context)
        
        # Evaluate
        evaluation = evaluate_prompts(prompts)
        
        score = evaluation.get("score", 0)
        
        # Record attempt
        attempt_record = {
            "attempt": attempt_num,
            "content": prompts,
            "evaluation": evaluation,
            "feedback": feedback
        }
        attempts.append(attempt_record)
        
        # Track best attempt
        if score > best_score:
            best_score = score
            best_attempt = attempt_record
            print(f"      Score: {score}/100, Count: {len(prompts)} ⭐ NEW BEST")
        else:
            print(f"      Score: {score}/100, Count: {len(prompts)} (best: {best_score})")
        
        passed = evaluation.get("passed", False) or score >= PASS_THRESHOLD
        
        if passed:
            print(f"      ✅ PASSED")
            return {
                "final_content": prompts,
                "attempts": attempts,
                "passed": True,
                "final_score": score,
                "attempts_needed": attempt_num
            }
        
        # Prepare feedback for next attempt - BUILD ON BEST ATTEMPT
        feedback = format_feedback(best_attempt["evaluation"], "MidJourney Prompts")
        # Include some of the best prompts for reference
        best_prompts = best_attempt["content"]
        if best_prompts:
            feedback += f"\n\n📋 BEST PROMPTS SO FAR (score {best_score}/100) - USE AS REFERENCE:\n"
            for i, p in enumerate(best_prompts[:5], 1):
                feedback += f"{i}. {p}\n"
            feedback += f"... and {len(best_prompts) - 5} more. Keep the good ones, fix the issues."
    
    # Return BEST attempt if none passed
    print(f"      ❌ Max attempts reached. Using best attempt (score: {best_score})")
    return {
        "final_content": best_attempt["content"],
        "attempts": attempts,
        "passed": False,
        "final_score": best_score,
        "attempts_needed": MAX_ATTEMPTS
    }


@tool
def generate_and_refine_keywords(description: str, theme_context: dict = None) -> dict:
    """
    Generate and refine SEO keywords with automatic quality evaluation.
    Uses the theme context (artistic style, unique angle) to influence keyword selection.
    Attempts up to 5 times until quality score >= 80.
    Each attempt builds on the BEST previous attempt.
    
    Args:
        description: The coloring book description to extract keywords from.
        theme_context: Optional dict with artistic_style, unique_angle, style_keywords, etc.
        
    Returns:
        Dictionary with final_content (list of keywords) and attempts history.
    """
    attempts = []
    feedback = ""
    best_attempt = None
    best_score = -1
    
    for attempt_num in range(1, MAX_ATTEMPTS + 1):
        print(f"   🔍 SEO Keywords - Attempt {attempt_num}/{MAX_ATTEMPTS}")
        
        # Generate (with feedback from best attempt if available)
        keywords = _generate_keywords_internal(description, feedback, theme_context)
        
        # Evaluate
        evaluation = evaluate_keywords(keywords, description[:100])
        
        score = evaluation.get("score", 0)
        
        # Record attempt
        attempt_record = {
            "attempt": attempt_num,
            "content": keywords,
            "evaluation": evaluation,
            "feedback": feedback
        }
        attempts.append(attempt_record)
        
        # Track best attempt
        if score > best_score:
            best_score = score
            best_attempt = attempt_record
            print(f"      Score: {score}/100, Count: {len(keywords)} ⭐ NEW BEST")
        else:
            print(f"      Score: {score}/100, Count: {len(keywords)} (best: {best_score})")
        
        passed = evaluation.get("passed", False) or score >= PASS_THRESHOLD
        
        if passed:
            print(f"      ✅ PASSED")
            return {
                "final_content": keywords,
                "attempts": attempts,
                "passed": True,
                "final_score": score,
                "attempts_needed": attempt_num
            }
        
        # Prepare feedback for next attempt - BUILD ON BEST ATTEMPT
        feedback = format_feedback(best_attempt["evaluation"], "SEO Keywords")
        # Include the best keywords for reference
        best_keywords = best_attempt["content"]
        if best_keywords:
            feedback += f"\n\n📋 BEST KEYWORDS SO FAR (score {best_score}/100) - IMPROVE THESE:\n"
            feedback += ", ".join(best_keywords)
            feedback += "\n\nKeep the good keywords, replace the weak ones."
    
    # Return BEST attempt if none passed
    print(f"      ❌ Max attempts reached. Using best attempt (score: {best_score})")
    return {
        "final_content": best_attempt["content"],
        "attempts": attempts,
        "passed": False,
        "final_score": best_score,
        "attempts_needed": MAX_ATTEMPTS
    }


# =============================================================================
# LEGACY TOOLS (kept for backwards compatibility)
# =============================================================================

@tool
def generate_title_description(user_input: str) -> dict:
    """
    Generate a marketable title and description (without evaluation loop).
    Use generate_and_refine_title_description for quality-assured output.
    """
    return _generate_title_description_internal(user_input)


@tool
def generate_midjourney_prompts(description: str) -> list:
    """
    Generate MidJourney prompts (without evaluation loop).
    Use generate_and_refine_prompts for quality-assured output.
    """
    return _generate_prompts_internal(description)


@tool
def extract_seo_keywords(description: str) -> list:
    """
    Extract SEO keywords (without evaluation loop).
    Use generate_and_refine_keywords for quality-assured output.
    """
    return _generate_keywords_internal(description)
