"""Content generation tools with built-in evaluation and refinement."""

import os
import json
import uuid
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

from features.design_generation.agents.evaluator import (
    evaluate_title_description,
    evaluate_prompts,
    evaluate_cover_prompts,
    evaluate_keywords,
    evaluate_theme_creativity,
    format_feedback,
    BANNED_AI_WORDS,
    REQUIRED_SECTION,
    MAX_ATTEMPTS,
    PASS_THRESHOLD
)
from features.design_generation.tools.search_tools import web_search
from features.design_generation.constants import (
    MIN_CONCEPT_VARIATIONS,
    MAX_CONCEPT_VARIATIONS,
    COVER_PROMPTS_COUNT,
)

load_dotenv()


def get_llm():
    """Get the language model instance."""
    from config import CONTENT_MODEL, CONTENT_MODEL_TEMPERATURE
    return ChatOpenAI(
        model=CONTENT_MODEL,
        temperature=CONTENT_MODEL_TEMPERATURE,
        api_key=os.getenv("OPENAI_API_KEY")
    )


# =============================================================================
# CONCEPT VARIATIONS (preliminary research - not exposed to executor)
# =============================================================================

def generate_concept_variations(user_idea: str, num_variations: int = 5) -> list[dict]:
    """
    Generate N creative variations of the user's idea with different themes and art styles.
    Called directly from UI for preliminary concept research. Not exposed to executor agent.

    Args:
        user_idea: The user's initial idea (e.g., "dog", "forest animals").
        num_variations: Number of variations to generate (5-10, default 5).

    Returns:
        List of N dicts, each with id, theme_concept, art_style, style_description,
        unique_angle, and mixable_components (theme, style).
    """
    num_variations = max(MIN_CONCEPT_VARIATIONS, min(MAX_CONCEPT_VARIATIONS, num_variations))

    llm = get_llm()
    prompt = ChatPromptTemplate.from_template("""
You are a creative director for a coloring book publishing company. Generate {num_variations} DISTINCT and CREATIVE variations of this idea for coloring books.

## USER'S IDEA:
{user_idea}

## YOUR TASK:
Create exactly {num_variations} variations. Each variation must be UNIQUE and DIFFERENT from the others.
- Include 2-3 THEME TWISTS (e.g., "dogs in space", "hairy dogs", "underwater dogs")
- Include 2-3 ART STYLE suggestions (e.g., "Asian ink wash", "Pop manga", "Art Nouveau")
- Mix theme twists and art styles across the variations
- Be creative and diverse - avoid near-duplicates
- Each variation should feel like a distinct coloring book concept

## RESPONSE FORMAT (JSON array with exactly {num_variations} objects):
[
  {{
    "theme_concept": "Creative theme twist (e.g., dogs in space)",
    "art_style": "Art style name (e.g., Asian ink wash, Pop manga)",
    "style_description": "1-2 sentences describing this style for coloring books",
    "unique_angle": "What makes this concept special and marketable"
  }},
  ... ({num_variations} total)
]

Return ONLY the JSON array, no other text.""")
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({"user_idea": user_idea, "num_variations": num_variations})
    try:
        result = result.strip()
        if result.startswith("```json"):
            result = result[7:]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]
        variations = json.loads(result.strip())
        if not isinstance(variations, list):
            variations = [variations] if isinstance(variations, dict) else []
        # Ensure exactly num_variations, add ids and mixable_components
        out = []
        for i, v in enumerate(variations[:num_variations]):
            if isinstance(v, dict):
                theme = v.get("theme_concept", v.get("theme", ""))
                style = v.get("art_style", v.get("style", ""))
                out.append({
                    "id": str(uuid.uuid4()),
                    "theme_concept": theme,
                    "art_style": style,
                    "style_description": v.get("style_description", ""),
                    "unique_angle": v.get("unique_angle", ""),
                    "mixable_components": {
                        "theme": theme,
                        "style": style,
                    },
                })
        return out[:num_variations]
    except json.JSONDecodeError:
        return []


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
1. **Mandala/Zentangle** - Intricate circular patterns, meditative ( for example Johanna Basford style)
2. **Art Nouveau** - Flowing organic lines, botanical, elegant curves ( for example Alphonse Mucha inspired)
3. **Hyperdetailed/Morphia** - Complex transformations, hidden elements (for example Kerby Rosanes style)
4. **Geometric/Sacred Geometry** - Mathematical patterns, symmetry
5. **Vintage/Retro** - Old-fashioned charm, nostalgic elements
6. **Folk Art** - Cultural patterns, traditional motifs
7. **Kawaii/Cute/Chibby** - Japanese cute style, round shapes, adorable characters
8. **Gothic/Dark Fantasy** - Dramatic, mysterious, detailed darkness
9. **Botanical/Scientific** - Precise plant illustrations, nature studies
10. **Fantasy** - Dreamy, imaginative, fairy-tale elements

## REQUIREMENTS:
1. **Match Theme to Style**: Which artistic style BEST complements this theme?
2. **Find Signature Artist**: Who is the most famous artist in this style for coloring books?
3. **Create Unique Angle**: How can we make this stand out from existing books?
4. **Define Visual Language**: What specific visual elements define this style?
5. **No Color Terms**: visual_elements and style_keywords must describe form, line, pattern, and composition only. NEVER include color words (red, blue, vibrant, pastel, etc.) - these are black and white coloring pages.

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
        # Ensure main_theme (primary subject) is set for prompt generation and evaluation
        if not theme_data.get("main_theme"):
            theme_data["main_theme"] = (theme_data.get("original_input") or "").split(" in ")[0].strip() or (theme_data.get("expanded_theme") or "").split(" in ")[0].strip()

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

def _generate_title_description_internal(user_input: str, feedback: str = "", theme_context: dict = None, custom_instructions: str = "") -> dict:
    """Internal function to generate title and description influenced by theme."""
    llm = get_llm()
    
    feedback_section = ""
    if feedback:
        feedback_section = f"""
    
    IMPORTANT - Previous attempt had issues. Fix these problems:
    {feedback}
    """
    
    # Build custom instructions section
    custom_section = ""
    if custom_instructions:
        custom_section = f"""
## USER'S SPECIAL INSTRUCTIONS (MUST FOLLOW):
{custom_instructions}

Apply these instructions while generating the title and description!
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
{custom_section}
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
- Write like a real Amazon seller, not an AI (avoid AI words)
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
        "custom_section": custom_section,
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


def _generate_prompts_internal(description: str, feedback: str = "", theme_context: dict = None, custom_instructions: str = "") -> list:
    """Internal function to generate MidJourney prompts influenced by theme and artistic style."""
    llm = get_llm()
    
    feedback_section = ""
    if feedback:
        feedback_section = f"""

IMPORTANT - Previous attempt had issues. Fix these problems:
{feedback}
"""
    
    # Build custom instructions section
    custom_section = ""
    if custom_instructions:
        custom_section = f"""
## USER'S SPECIAL INSTRUCTIONS (MUST FOLLOW):
{custom_instructions}

Apply these instructions when creating the prompts!
"""
    
    # Derive main theme (primary subject) for anchor—e.g. "Highland cows", "Easter", "dogs"
    main_theme = ""
    if theme_context:
        main_theme = theme_context.get("main_theme") or ""
        if not main_theme and theme_context.get("original_input"):
            main_theme = (theme_context["original_input"] or "").split(" in ")[0].strip()
        if not main_theme and theme_context.get("expanded_theme"):
            main_theme = (theme_context["expanded_theme"] or "").split(" in ")[0].strip()

    main_theme_section = ""
    if main_theme:
        main_theme_section = f"""
## MAIN THEME (PRIMARY — MUST APPLY TO EVERY PROMPT):
**{main_theme}**

Every prompt MUST be clearly about this subject. The artistic style is how it is drawn, not what it is. Do NOT create prompts that are only about the style (e.g. generic Celtic patterns or mandalas) without the main theme—e.g. every prompt should feature {main_theme} or direct variations (scenes, details, compositions involving {main_theme}).
"""

    # Build artistic style guidance (secondary: how it looks)
    style_section = ""
    if theme_context:
        artistic_style = theme_context.get('artistic_style', '')
        signature_artist = theme_context.get('signature_artist', '')
        style_keywords = theme_context.get('style_keywords', [])
        visual_elements = theme_context.get('visual_elements', [])
        page_ideas = theme_context.get('page_ideas', [])
        
        style_section = f"""
## ARTISTIC STYLE DIRECTION (how to draw — secondary to main theme):
- **Style**: {artistic_style}
- **Artist Inspiration**: {signature_artist}
- **Style Keywords to Include**: {', '.join(style_keywords)}
- **Visual Elements**: {', '.join(visual_elements)}
- **Page Ideas**: {', '.join(page_ideas)}

EVERY prompt should reflect this artistic style in the keywords, but the SUBJECT must always tie back to the MAIN THEME above.
"""
    
    prompt = ChatPromptTemplate.from_template("""
You are an expert at creating MidJourney prompts for coloring book designs in a SPECIFIC artistic style.

## BOOK DESCRIPTION:
{description}
{main_theme_section}
{style_section}
{custom_section}
{feedback_section}

## PROMPT FORMAT:
Create approximately 50 prompts (target 48–55). Each prompt MUST follow this EXACT format:

"[subject], [style keywords], [details], [art style], coloring book page, clean and simple line art, black and white --no color --ar 1:1"

## CRITICAL RULES:
1. Approximately 50 prompts (e.g. 48–55); quality and theme consistency matter more than exact count.
2. Keywords ONLY - NO sentences or phrases
3. Each keyword is 1-3 words max
4. MUST include "coloring book page" in every prompt
5. MUST include "clean and simple line art" in every prompt
6. MUST include "black and white" in every prompt
7. MUST end with "--no color --ar 1:1"
8. EVERY prompt must center on the MAIN THEME (primary subject) when specified above; do not drift into generic style-only prompts.
9. EVERY prompt must include the ARTISTIC STYLE in the keywords (how it's drawn).
10. NEVER include color-related keywords - these are black and white line art pages. Banned: red, blue, green, yellow, orange, purple, pink, vibrant, colorful, colourful, pastel, hue, multicolored, rainbow, golden, silver, crimson, azure, etc.

## GOOD (main theme + style): Highland cow, Celtic knot border, floral wreath, coloring book page, clean and simple line art, black and white --no color --ar 1:1
## BAD (style only, no main theme): Celtic knot, mandala, decorative border, coloring book page... — missing the main subject

## BAD PROMPTS (DO NOT DO THIS):
"A beautiful owl sitting majestically in an enchanted forest" - TOO WORDY, uses banned words, no style keywords
"owl, vibrant feathers, red flowers, blue sky, coloring book page..." - CONTAINS COLOR WORDS (vibrant, red, blue) - forbidden for black and white line art

Return a JSON array with approximately 50 prompts. No markdown, just the array.""")

    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({
        "description": description,
        "main_theme_section": main_theme_section,
        "style_section": style_section,
        "custom_section": custom_section,
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


def _generate_cover_prompts_internal(
    description: str,
    feedback: str = "",
    theme_context: dict = None,
    custom_instructions: str = "",
) -> list:
    """Internal function to generate MidJourney prompts for book cover backgrounds (full color, no text)."""
    llm = get_llm()

    feedback_section = ""
    if feedback:
        feedback_section = f"""

IMPORTANT - Previous attempt had issues. Fix these problems:
{feedback}
"""

    custom_section = ""
    if custom_instructions:
        custom_section = f"""
## USER'S SPECIAL INSTRUCTIONS (MUST FOLLOW):
{custom_instructions}

Apply these when creating the cover prompts!
"""

    main_theme = ""
    style_section = ""
    if theme_context:
        main_theme = theme_context.get("main_theme") or ""
        if not main_theme and theme_context.get("original_input"):
            main_theme = (theme_context.get("original_input") or "").split(" in ")[0].strip()
        if not main_theme and theme_context.get("expanded_theme"):
            main_theme = (theme_context.get("expanded_theme") or "").split(" in ")[0].strip()
        artistic_style = theme_context.get("artistic_style", "")
        style_keywords = theme_context.get("style_keywords", [])
        visual_elements = theme_context.get("visual_elements", [])
        style_section = f"""
## THEME & STYLE (match the inside pages):
- **Main theme**: {main_theme}
- **Artistic style**: {artistic_style}
- **Style keywords**: {', '.join(style_keywords)}
- **Visual elements**: {', '.join(visual_elements)}
"""

    prompt = ChatPromptTemplate.from_template("""
You are an expert at creating MidJourney prompts for BOOK COVER BACKGROUND images. These are full-color illustrated backgrounds; the user will add the book title in another tool. No text or title in the image.

## BOOK DESCRIPTION:
{description}
{style_section}
{custom_section}
{feedback_section}

## PROMPT FORMAT:
Create exactly {cover_count} prompts. Each prompt MUST follow this format:

"[theme/subject], [style keywords], book cover, [details], rich colors, illustrated, no text, no letters, no words --ar 2:1"

## CRITICAL RULES:
1. EXACTLY {cover_count} prompts.
2. Keywords ONLY - NO sentences.
3. MUST include "book cover" or "cover art" or "cover design" in every prompt.
4. MUST include "no text" or "no words" or "no letters" so the image has no title/text.
5. MUST end with "--ar 2:1" (landscape book cover ratio).
6. MUST imply full color (e.g. "rich colors", "illustrated", "full color"). Do NOT use "black and white" or "--no color".
7. Do NOT include: "coloring book page", "clean and simple line art", "black and white" — those are for inside pages only.
8. Match the book theme and artistic style above so the cover fits the inside pages.

## GOOD: forest animals, art nouveau border, book cover, decorative frame, rich colors, illustrated, no text --ar 2:1
## BAD: owl, coloring book page, clean and simple line art, black and white --no color --ar 1:1 (that is for inside pages)

Return a JSON array with exactly {cover_count} prompts. No markdown, just the array.""")

    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({
        "description": description,
        "style_section": style_section,
        "custom_section": custom_section,
        "feedback_section": feedback_section,
        "cover_count": COVER_PROMPTS_COUNT,
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


def _generate_keywords_internal(description: str, feedback: str = "", theme_context: dict = None, custom_instructions: str = "") -> list:
    """Internal function to generate SEO keywords influenced by theme and artistic style."""
    llm = get_llm()
    
    feedback_section = ""
    if feedback:
        feedback_section = f"""

IMPORTANT - Previous attempt had issues. Fix these problems:
{feedback}
"""
    
    # Build custom instructions section
    custom_section = ""
    if custom_instructions:
        custom_section = f"""
## USER'S SPECIAL INSTRUCTIONS (MUST FOLLOW):
{custom_instructions}

Apply these instructions when selecting keywords!
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
{custom_section}
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
- "cow coloring book" (short-tail)
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
        "custom_section": custom_section,
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
def generate_and_refine_title_description(user_input: str, theme_context: dict = None, custom_instructions: str = "") -> dict:
    """
    Generate and refine a title and description with automatic quality evaluation.
    Uses the theme context (artistic style, signature artist) to influence the output.
    Attempts up to 5 times until quality score >= 80.
    Each attempt builds on the BEST previous attempt.
    
    Args:
        user_input: The user's description of the coloring book theme.
        theme_context: Optional dict with expanded_theme, artistic_style, signature_artist, etc.
        custom_instructions: Optional free text instructions from user (e.g., "make it more playful").
        
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
        content = _generate_title_description_internal(user_input, feedback, theme_context, custom_instructions)
        
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
def generate_and_refine_prompts(description: str, theme_context: dict = None, custom_instructions: str = "") -> dict:
    """
    Generate and refine MidJourney prompts with automatic quality evaluation.
    Uses the theme context (artistic style, visual elements) to influence the prompts.
    Attempts up to 5 times until quality score >= 80.
    Each attempt builds on the BEST previous attempt.
    
    Args:
        description: The coloring book description to base prompts on.
        theme_context: Optional dict with artistic_style, style_keywords, visual_elements, etc.
        custom_instructions: Optional free text instructions from user (e.g., "add more fantasy elements").
        
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
        prompts = _generate_prompts_internal(description, feedback, theme_context, custom_instructions)
        
        # Evaluate (pass theme_context so evaluator can check main-theme consistency)
        evaluation = evaluate_prompts(prompts, theme_context=theme_context)
        
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
def generate_and_refine_cover_prompts(description: str, theme_context: dict = None, custom_instructions: str = "") -> dict:
    """
    Generate and refine MidJourney prompts for book cover backgrounds (full color, no title text).
    Uses theme context so cover matches the inside pages. Attempts up to 5 times until quality passes.

    Args:
        description: The coloring book description to base cover prompts on.
        theme_context: Optional dict with artistic_style, style_keywords, visual_elements, etc.
        custom_instructions: Optional free text (e.g. "space for title at top").

    Returns:
        Dictionary with final_content (list of cover prompts) and attempts history.
    """
    attempts = []
    feedback = ""
    best_attempt = None
    best_score = -1

    for attempt_num in range(1, MAX_ATTEMPTS + 1):
        print(f"   📖 Cover Prompts - Attempt {attempt_num}/{MAX_ATTEMPTS}")

        prompts = _generate_cover_prompts_internal(description, feedback, theme_context, custom_instructions)
        evaluation = evaluate_cover_prompts(prompts, theme_context=theme_context)

        score = evaluation.get("score", 0)
        attempt_record = {
            "attempt": attempt_num,
            "content": prompts,
            "evaluation": evaluation,
            "feedback": feedback,
        }
        attempts.append(attempt_record)

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
                "attempts_needed": attempt_num,
            }

        feedback = format_feedback(best_attempt["evaluation"], "Cover Prompts")
        if best_attempt["content"]:
            feedback += f"\n\n📋 BEST COVER PROMPTS SO FAR (score {best_score}/100):\n"
            for i, p in enumerate(best_attempt["content"][:5], 1):
                feedback += f"{i}. {p}\n"

    print(f"      ❌ Max attempts reached. Using best attempt (score: {best_score})")
    return {
        "final_content": best_attempt["content"],
        "attempts": attempts,
        "passed": False,
        "final_score": best_score,
        "attempts_needed": MAX_ATTEMPTS,
    }


@tool
def generate_and_refine_keywords(description: str, theme_context: dict = None, custom_instructions: str = "") -> dict:
    """
    Generate and refine SEO keywords with automatic quality evaluation.
    Uses the theme context (artistic style, unique angle) to influence keyword selection.
    Attempts up to 5 times until quality score >= 80.
    Each attempt builds on the BEST previous attempt.
    
    Args:
        description: The coloring book description to extract keywords from.
        theme_context: Optional dict with artistic_style, unique_angle, style_keywords, etc.
        custom_instructions: Optional free text instructions from user (e.g., "focus on holiday keywords").
        
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
        keywords = _generate_keywords_internal(description, feedback, theme_context, custom_instructions)
        
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
# REGENERATE FUNCTIONS (for rerun/regenerate - not exposed as tools)
# =============================================================================

def regenerate_art_style(theme_context: dict, new_style_hint: str) -> dict:
    """
    Regenerate art style fields in theme_context with a new style hint.
    Returns updated theme_context with artistic_style, style_keywords, etc. updated.

    Args:
        theme_context: Current theme context from expanded_theme.
        new_style_hint: User's new style suggestion (e.g., "Pop manga", "Asian ink wash").

    Returns:
        Updated theme_context dict with new style applied.
    """
    llm = get_llm()
    prompt = ChatPromptTemplate.from_template("""
Update the artistic style for this coloring book theme. Keep the theme/subject the same, only change the style.

## CURRENT THEME CONTEXT:
- Expanded theme: {expanded_theme}
- Current artistic style: {artistic_style}

## NEW STYLE HINT FROM USER:
{new_style_hint}

## TASK:
Return a JSON object with updated style-related fields. Keep expanded_theme, unique_angle, target_audience the same.
Update: artistic_style, style_description, signature_artist, style_keywords, visual_elements, mood.

{{
    "artistic_style": "new style name",
    "style_description": "1-2 sentences",
    "signature_artist": "artist for this style",
    "style_keywords": ["keyword1", "keyword2", "keyword3"],
    "visual_elements": ["element1", "element2"],
    "mood": ["mood1", "mood2"]
}}

Return ONLY the JSON object.""")
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({
        "expanded_theme": theme_context.get("expanded_theme", ""),
        "artistic_style": theme_context.get("artistic_style", ""),
        "new_style_hint": new_style_hint,
    })
    try:
        result = result.strip()
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        result = json.loads(result.strip())
        updated = dict(theme_context)
        for k, v in result.items():
            if v is not None:
                updated[k] = v
        return updated
    except json.JSONDecodeError:
        updated = dict(theme_context)
        updated["artistic_style"] = new_style_hint
        sk = list(theme_context.get("style_keywords", []))
        if new_style_hint not in sk:
            updated["style_keywords"] = [new_style_hint] + sk[:4]
        return updated


def regenerate_title_description(theme_context: dict, user_input: str = "", custom_instructions: str = "") -> dict:
    """
    Regenerate title and description. Returns dict with final_content and attempts.
    
    Args:
        theme_context: Theme context from expanded_theme.
        user_input: Original user input/request.
        custom_instructions: Optional free text instructions (e.g., "make it more playful").
    """
    ui = user_input or f"{theme_context.get('expanded_theme', '')} in {theme_context.get('artistic_style', '')} style"
    return generate_and_refine_title_description.invoke({
        "user_input": ui, 
        "theme_context": theme_context,
        "custom_instructions": custom_instructions
    })


def regenerate_prompts(theme_context: dict, description: str, custom_instructions: str = "") -> dict:
    """
    Regenerate MidJourney prompts. Returns dict with final_content and attempts.
    
    Args:
        theme_context: Theme context from expanded_theme.
        description: Book description.
        custom_instructions: Optional free text instructions (e.g., "add more fantasy elements").
    """
    return generate_and_refine_prompts.invoke({
        "description": description, 
        "theme_context": theme_context,
        "custom_instructions": custom_instructions
    })


def regenerate_cover_prompts(theme_context: dict, description: str, custom_instructions: str = "") -> dict:
    """
    Regenerate cover prompts. Returns dict with final_content and attempts.
    """
    return generate_and_refine_cover_prompts.invoke({
        "description": description,
        "theme_context": theme_context,
        "custom_instructions": custom_instructions,
    })


def regenerate_keywords(theme_context: dict, description: str, custom_instructions: str = "") -> dict:
    """
    Regenerate SEO keywords. Returns dict with final_content and attempts.
    
    Args:
        theme_context: Theme context from expanded_theme.
        description: Book description.
        custom_instructions: Optional free text instructions (e.g., "focus on holiday keywords").
    """
    return generate_and_refine_keywords.invoke({
        "description": description, 
        "theme_context": theme_context,
        "custom_instructions": custom_instructions
    })


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
