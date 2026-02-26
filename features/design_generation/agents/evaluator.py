"""Evaluator Agent - Component-specific evaluators with detailed criteria and creativity assessment."""

import os
import json
import re
from typing import Dict, List, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

load_dotenv()

# Expanded list of banned AI-sounding words
BANNED_AI_WORDS = [
    # Overused enchantment words
    "whimsical", "enchanting", "captivating", "mesmerizing", "breathtaking",
    "stunning", "magical", "delightful", "charming", "wondrous", "ethereal",
    "spellbinding", "fantastical", "mystical", "serene", "tranquil", "blissful",
    "exquisite", "gorgeous", "magnificent", "majestic", "sublime", "divine",
    # Overused journey/story words
    "tapestry", "symphony", "kaleidoscope", "mosaic", "treasure trove",
    "embark", "journey", "realm", "unveil", "beacon", "testament",
    "adventure awaits", "world of", "discover the", "immerse yourself",
    # Overused emotional words
    "heartwarming", "soul-stirring", "awe-inspiring", "jaw-dropping",
    "mind-blowing", "life-changing", "transformative", "transcendent",
    # Overused quality descriptors
    "unparalleled", "unprecedented", "unmatched", "second to none",
    "best-in-class", "world-class", "cutting-edge", "state-of-the-art",
    # Filler phrases
    "in today's world", "in this day and age", "at the end of the day",
    "it goes without saying", "needless to say", "rest assured",
]

# Color-related words banned from MidJourney prompts (black and white line art only)
BANNED_COLOR_WORDS = [
    "red", "blue", "green", "yellow", "orange", "purple", "pink", "brown", "gold", "golden",
    "silver", "vibrant", "colorful", "colourful", "pastel", "multicolored", "multicoloured",
    "rainbow", "crimson", "azure", "emerald", "amber", "hue", "hues", "colored", "coloured",
    "color", "colour", "chromatic", "vivid colors", "bold colors", "soft colors",
]

# Marketing clichés to avoid (separate from AI words)
MARKETING_CLICHES = [
    # Generic coloring book phrases
    "escape from the stresses", "unwind and relax", "perfect for all ages",
    "hours of fun", "endless hours", "perfect gift", "great gift idea",
    "suitable for beginners", "all skill levels", "from beginners to experts",
    # Generic selling phrases
    "look no further", "what are you waiting for", "order now",
    "don't miss out", "limited time", "act now", "buy now",
    "you won't regret", "you'll love", "trust us",
    # Overused marketing
    "takes you on a journey", "transport yourself", "lose yourself in",
    "designed with you in mind", "carefully crafted", "lovingly created",
    "meticulously designed", "hand-picked", "curated collection",
    # Empty superlatives
    "truly unique", "one-of-a-kind", "like no other", "nothing else compares",
    "absolutely perfect", "simply the best", "truly amazing",
]

# Configurable scoring weights
SCORING_WEIGHTS = {
    "title_description": {
        "technical_correctness": 0.30,
        "creativity_uniqueness": 0.25,
        "human_quality": 0.25,
        "market_appeal": 0.20
    },
    "prompts": {
        "technical_format": 0.25,
        "creative_variety": 0.35,
        "artistic_coherence": 0.20,
        "midjourney_effectiveness": 0.20
    },
    "keywords": {
        "technical_count": 0.20,
        "niche_opportunity": 0.35,
        "search_effectiveness": 0.25,
        "buyer_intent": 0.20
    },
    "theme": {
        "uniqueness": 0.25,
        "artistic_fit": 0.25,
        "market_opportunity": 0.20,
        "target_audience": 0.15,
        "creative_potential": 0.15
    }
}

# Required section that must appear verbatim in description
REQUIRED_SECTION = """Why You Will Love this Book:

- Relax while coloring and let your stress fade away
- 50 beautiful illustrations to express your creativity
- Single-sided pages to prevent color bleeding and make them easy to frame
- Large print 8.5" x 8.5" white pages with high-quality matte cover
- Great for all skill levels"""

MAX_ATTEMPTS = 10
PASS_THRESHOLD = 80


def get_evaluator_llm():
    """Get the LLM for evaluation with lower temperature for consistency."""
    from config import DESIGN_EVALUATOR_MODEL
    return ChatOpenAI(
        model=DESIGN_EVALUATOR_MODEL,
        temperature=0.2,
        api_key=os.getenv("OPENAI_API_KEY")
    )


def parse_json_response(response: str) -> dict:
    """Parse JSON from LLM response, handling markdown code blocks."""
    response = response.strip()
    if response.startswith("```json"):
        response = response[7:]
    if response.startswith("```"):
        response = response[3:]
    if response.endswith("```"):
        response = response[:-3]
    return json.loads(response.strip())


# =============================================================================
# TITLE & DESCRIPTION EVALUATOR
# =============================================================================

TITLE_DESC_EVALUATOR_PROMPT = """You are a strict quality evaluator for coloring book titles and descriptions, with emphasis on creativity and human-like quality.

## TITLE EVALUATION CRITERIA:

### Technical (20 points)
1. **Character Count**: Must be EXACTLY 60 characters or less
   - Current title: "{title}" has {title_length} characters

2. **Keyword Integration**: 
   - Must contain relevant, searchable keywords naturally
   - Should be what someone would actually search for on Amazon

### Creativity & Uniqueness (20 points)
3. **Uniqueness Score**:
   - Is this title creative and memorable?
   - Does it stand out from generic titles like "Beautiful Coloring Book"?
   - Would it catch someone's eye while scrolling?

4. **Hook Factor**:
   - Does it create curiosity or interest?
   - Is there a unique angle or twist?

### No AI Words (deduct points if found): {banned_words_sample}

## DESCRIPTION EVALUATION CRITERIA:

### Technical (25 points)
1. **Word Count**: Must be 180-220 words (current: {desc_word_count} words)

2. **Required Section**: MUST contain this EXACT text:
   ```
   {required_section}
   ```

### Human Quality (20 points)
3. **Voice Authenticity**:
   - Does it sound like a real seller wrote this?
   - Is the tone conversational, not robotic?
   - Are there varied sentence structures?

4. **Cliché-Free**:
   - No overused marketing phrases
   - No AI-sounding language
   - Banned words: {banned_words_full}

### Creativity & Sales (15 points)
5. **Unique Selling Points**:
   - Does it highlight what makes THIS book special?
   - Are there specific, concrete details?
   - Does it paint a picture of the experience?

6. **Emotional Appeal**:
   - Does it connect with the target audience?
   - Does it make you WANT to buy?

## SCORING BREAKDOWN:
- Title Technical: 20 points
- Title Creativity: 20 points
- Description Technical: 25 points
- Description Human Quality: 20 points
- Description Creativity: 15 points

## RESPONSE FORMAT (JSON only):
{{
    "passed": true/false (true if score >= 80),
    "score": 0-100,
    "creativity_scores": {{
        "title_uniqueness": 0-10,
        "title_hook_factor": 0-10,
        "description_voice": 0-10,
        "description_originality": 0-10
    }},
    "title_issues": [
        {{"issue": "description", "severity": "critical|major|minor", "suggestion": "how to fix"}}
    ],
    "description_issues": [
        {{"issue": "description", "severity": "critical|major|minor", "suggestion": "how to fix"}}
    ],
    "strengths": ["what's working well"],
    "summary": "Brief assessment with creativity focus"
}}

Return ONLY valid JSON, no other text."""


def evaluate_title_description(title: str, description: str) -> dict:
    """
    Evaluate title and description with detailed criteria including creativity 
    and human-quality assessment.
    
    Returns:
        dict with: passed, score, creativity_scores, title_issues, description_issues, 
                  strengths, human_quality, summary, metrics
    """
    llm = get_evaluator_llm()
    
    # Pre-calculate metrics
    title_length = len(title)
    desc_word_count = len(description.split())
    
    # Check for banned words
    found_banned = []
    desc_lower = description.lower()
    title_lower = title.lower()
    for word in BANNED_AI_WORDS:
        if word.lower() in desc_lower or word.lower() in title_lower:
            found_banned.append(word)
    
    # Check for clichés
    found_cliches = check_cliches(description) + check_cliches(title)
    
    # Check sentence variety
    sentence_variety = check_sentence_variety(description)
    
    # Check authenticity
    authenticity = check_authenticity(description)
    
    # Check for required section
    has_required_section = REQUIRED_SECTION.strip() in description
    
    prompt = ChatPromptTemplate.from_template(TITLE_DESC_EVALUATOR_PROMPT)
    chain = prompt | llm | StrOutputParser()
    
    try:
        result = chain.invoke({
            "title": title,
            "title_length": title_length,
            "desc_word_count": desc_word_count,
            "banned_words_sample": ", ".join(BANNED_AI_WORDS[:15]) + "...",
            "banned_words_full": ", ".join(BANNED_AI_WORDS),
            "required_section": REQUIRED_SECTION,
            "description": description
        })
        
        evaluation = parse_json_response(result)
        
        # Add human quality assessment
        evaluation["human_quality"] = {
            "sentence_variety": sentence_variety,
            "authenticity": authenticity,
            "cliches_found": found_cliches
        }
        
        # Adjust score based on human quality if not already factored in
        human_penalty = 0
        if found_cliches:
            human_penalty += min(10, len(found_cliches) * 2)
        if authenticity["score"] < 5:
            human_penalty += 5
        if sentence_variety["score"] < 4:
            human_penalty += 3
        
        # Apply penalty but don't double-penalize
        adjusted_score = max(0, evaluation.get("score", 0) - human_penalty)
        evaluation["score"] = adjusted_score
        evaluation["passed"] = adjusted_score >= PASS_THRESHOLD
        
        # Add pre-calculated checks
        evaluation["metrics"] = {
            "title_length": title_length,
            "desc_word_count": desc_word_count,
            "found_banned_words": found_banned,
            "found_cliches": found_cliches[:5],
            "has_required_section": has_required_section,
            "authenticity_score": authenticity["score"],
            "sentence_variety_score": sentence_variety["score"]
        }
        
        return evaluation
        
    except Exception as e:
        return {
            "passed": False,
            "score": 0,
            "creativity_scores": {},
            "title_issues": [],
            "description_issues": [{"issue": f"Evaluation error: {e}", "severity": "critical", "suggestion": "Retry"}],
            "strengths": [],
            "human_quality": {"sentence_variety": {}, "authenticity": {}, "cliches_found": []},
            "summary": f"Evaluation failed: {e}",
            "metrics": {"title_length": title_length, "desc_word_count": desc_word_count}
        }


# =============================================================================
# MIDJOURNEY PROMPTS EVALUATOR
# =============================================================================

PROMPTS_EVALUATOR_PROMPT = """You are a strict quality evaluator for MidJourney coloring book prompts, with emphasis on main-theme consistency, creative variety, and artistic coherence.

## EVALUATION CRITERIA:
{main_theme_section}

### Technical Requirements (25 points)
1. **Count** (5 points): Target is around 50 prompts (e.g. 45–55). Current count: {prompt_count}. Slightly under or over (e.g. 48 or 52) is acceptable. Do NOT fail or heavily penalize solely for not being exactly 50. Only deduct meaningfully if far off (e.g. under 40 or over 65).

2. **Format Validation** (check EACH prompt):
   - Must be comma-separated keywords ONLY (NO sentences)
   - Each keyword should be 1-3 words max
   - Good: "owl, mandala, forest, detailed feathers, coloring book page, clean and simple line art, black and white --no color --ar 1:1"
   - Bad: "A beautiful owl sitting in a magical forest with intricate mandala patterns"

3. **Required Elements** (in EVERY prompt):
   - Must contain "coloring book page"
   - Must contain "clean and simple line art"
   - Must contain "black and white"
   - Must end with "--no color --ar 1:1"

4. **NO COLOR KEYWORDS** (CRITICAL - deduct heavily if found):
   - These are black and white line art pages. NEVER use color-related keywords.
   - Banned: red, blue, green, yellow, vibrant, colorful, pastel, hue, multicolored, rainbow, golden, etc.
   - Any prompt containing color words FAILS this criterion.

### Creative Variety (40 points)
5. **Subject Diversity** (10 points):
   - Are there varied subjects within the main theme? (e.g. different scenes, poses, compositions)
   - Does each prompt feel unique, not repetitive?

6. **Style Diversity** (10 points):
   - Mix of styles: mandala, geometric, realistic, abstract, floral, zentangle
   - Not all prompts use the same style approach

7. **Creative Combinations** (10 points):
   - Are keywords combined in interesting ways?
   - Unexpected pairings that would create visually striking pages
   - Example: "steampunk owl, clockwork feathers, Victorian frame" vs boring "owl, tree, leaves"

8. **Artistic Coherence** (10 points):
   - Do prompts work well together as a collection?
   - Is there a unifying theme while maintaining variety?
   - Would a colorist enjoy the journey through these pages?

### MidJourney Effectiveness (20 points)
9. **Keyword Quality**:
   - Specific, visual keywords that MidJourney will interpret well
   - No vague terms like "beautiful", "nice", "good"
   - NO color-related keywords (see criterion 4 - critical for black and white)
   - Keywords that produce clean line art

10. **Coloring Appropriateness**:
   - Will the resulting images work as coloring pages?
   - Not too simple (boring) or too complex (frustrating)
   - Good balance of detail and white space

## SAMPLE PROMPTS TO EVALUATE:
{prompts_sample}

## RESPONSE FORMAT (JSON only):
{{
    "passed": true/false (true if score >= 80),
    "score": 0-100,
    "creativity_scores": {{
        "subject_diversity": 0-10,
        "style_diversity": 0-10,
        "creative_combinations": 0-10,
        "artistic_coherence": 0-10
    }},
    "main_theme_consistency_score": 0-25,
    "prompts_off_theme": [],
    "issues": [
        {{"issue": "description", "severity": "critical|major|minor", "suggestion": "how to fix", "affected_prompts": [1, 5, 12]}}
    ],
    "diversity_assessment": {{
        "subjects_variety": "low|medium|high",
        "styles_variety": "low|medium|high", 
        "themes_variety": "low|medium|high",
        "creative_risk_taking": "low|medium|high"
    }},
    "standout_prompts": ["prompt numbers that are particularly creative"],
    "strengths": ["what's working well creatively"],
    "summary": "Brief assessment with creativity focus"
}}

Return ONLY valid JSON, no other text."""

PROMPTS_EVALUATOR_MAIN_THEME_BLOCK = """
### Main theme consistency (25 points) — CRITICAL
The main theme for this book is: **{main_theme}**
- Every prompt must be clearly about this theme (subject). Prompts that are only about the artistic style or unrelated subjects (e.g. generic patterns with no link to the main theme) must fail this criterion.
- Deduct heavily if a significant portion of prompts do not reflect the main theme. List prompt numbers that are off-theme in "prompts_off_theme".
- Score "main_theme_consistency_score" 0–25; below 15 is a serious failure.
"""


def evaluate_prompts(prompts: list, theme_context: dict = None) -> dict:
    """
    Evaluate MidJourney prompts with detailed criteria.
    When theme_context is provided with a main_theme, evaluates that every prompt
    stays on the main theme (primary subject); count is soft (target ~50, not a critical fail).

    Returns:
        dict with: passed, score, issues, diversity_assessment, main_theme_consistency_score,
                   prompts_off_theme, summary
    """
    llm = get_evaluator_llm()

    # Derive main theme for evaluation when theme_context is provided
    main_theme = ""
    if theme_context:
        main_theme = theme_context.get("main_theme") or ""
        if not main_theme and theme_context.get("original_input"):
            main_theme = (theme_context.get("original_input") or "").split(" in ")[0].strip()
        if not main_theme and theme_context.get("expanded_theme"):
            main_theme = (theme_context.get("expanded_theme") or "").split(" in ")[0].strip()

    main_theme_section = ""
    if main_theme:
        main_theme_section = PROMPTS_EVALUATOR_MAIN_THEME_BLOCK.format(main_theme=main_theme)

    prompt_count = len(prompts)

    # Pre-check: validate format of each prompt
    format_issues = []
    for i, p in enumerate(prompts):
        if not p.endswith("--ar 1:1"):
            format_issues.append(f"Prompt {i+1} missing MidJourney parameters")
        if "coloring book page" not in p.lower():
            format_issues.append(f"Prompt {i+1} missing 'coloring book page'")
        if "clean and simple line art" not in p.lower():
            format_issues.append(f"Prompt {i+1} missing 'clean and simple line art'")
        if "black and white" not in p.lower():
            format_issues.append(f"Prompt {i+1} missing 'black and white'")
        # Check for banned color words (black and white line art only)
        p_lower = p.lower()
        for color_word in BANNED_COLOR_WORDS:
            if re.search(r'\b' + re.escape(color_word) + r'\b', p_lower):
                format_issues.append(f"Prompt {i+1} contains color word: '{color_word}' (forbidden for B&W)")
                break

    # Prepare sample (show 10 prompts for evaluation)
    if len(prompts) > 10:
        sample_indices = [0, 1, 2, 3, 4, 24, 25, 47, 48, 49]  # First 5, middle 2, last 3
        prompts_sample = "\n".join([f"{i+1}. {prompts[i]}" for i in sample_indices if i < len(prompts)])
    else:
        prompts_sample = "\n".join([f"{i+1}. {p}" for i, p in enumerate(prompts)])

    prompt_template = ChatPromptTemplate.from_template(PROMPTS_EVALUATOR_PROMPT)
    chain = prompt_template | llm | StrOutputParser()

    try:
        result = chain.invoke({
            "main_theme_section": main_theme_section,
            "prompt_count": prompt_count,
            "prompts_sample": prompts_sample
        })

        evaluation = parse_json_response(result)
        # Inject color-word issues from pre-check so they trigger refinement
        color_issues = [f for f in format_issues if "color word" in f]
        if color_issues:
            existing_issues = evaluation.get("issues", [])
            sample = ", ".join(color_issues[:5])
            if len(color_issues) > 5:
                sample += f" (+{len(color_issues)-5} more)"
            evaluation["issues"] = existing_issues + [
                {"issue": f"{len(color_issues)} prompt(s) contain color keywords. Examples: {sample}", "severity": "critical", "suggestion": "Remove ALL color-related words from prompts - use only black and white line art descriptors"}
            ]
            evaluation["passed"] = False
            evaluation["score"] = min(evaluation.get("score", 100), 70)  # Cap score when color words found
        # When main theme was provided, fail if main-theme consistency is very low
        if main_theme:
            mt_score = evaluation.get("main_theme_consistency_score")
            if mt_score is not None and mt_score < 15:
                evaluation["passed"] = False
                evaluation["score"] = min(evaluation.get("score", 100), 75)
        evaluation["metrics"] = {
            "prompt_count": prompt_count,
            "main_theme": main_theme or None,
            "pre_check_issues": format_issues[:10]
        }

        return evaluation

    except Exception as e:
        return {
            "passed": False,
            "score": 0,
            "issues": [{"issue": f"Evaluation error: {e}", "severity": "critical", "suggestion": "Retry"}],
            "diversity_assessment": {"subjects_variety": "unknown", "styles_variety": "unknown", "themes_variety": "unknown"},
            "summary": f"Evaluation failed: {e}",
            "metrics": {"prompt_count": prompt_count}
        }


# =============================================================================
# COVER PROMPTS EVALUATOR
# =============================================================================

COVER_PROMPTS_EVALUATOR_PROMPT = """You are a strict quality evaluator for MidJourney prompts that generate BOOK COVER BACKGROUND images (full color, no title text). These are for coloring book covers; the user will add the title in another tool.

## EVALUATION CRITERIA:

{theme_section}

### Technical Requirements (25 points)
1. **Count**: Target is 3–5 cover prompts. Current count: {prompt_count}. Slightly under or over is acceptable. Do NOT fail solely for 4 or 6 prompts.

2. **Format**: Each prompt must be comma-separated keywords (no full sentences). Must end with "--ar 2:3" (portrait book cover ratio).

3. **Cover-specific (CRITICAL)**:
   - Must describe a BOOK COVER BACKGROUND (e.g. contain "book cover", "cover art", "cover design", or "illustrated cover").
   - Must specify NO TEXT in the image: e.g. "no text", "no letters", "no words", or "no typography" so the image is a background only.
   - Must imply FULL COLOR (rich colors, illustrated). Must NOT contain "black and white" or "--no color".

4. **Forbidden (inside-page wording)**: Deduct heavily if any prompt contains:
   - "coloring book page", "clean and simple line art", "black and white", "--no color"
   These are for inside pages only; cover prompts must be full-color background art.

### Theme & Style (25 points)
5. **Theme consistency**: Prompts should match the book theme and artistic style (see theme context above).
6. **Visual variety**: Different compositions or angles for cover options (e.g. frame, banner, full bleed).

### MidJourney Effectiveness (25 points)
7. **Keyword quality**: Specific, visual keywords that produce strong illustrated cover art.
8. **Cover suitability**: Resulting images would work as a background for adding title later.

## COVER PROMPTS TO EVALUATE:
{prompts_sample}

## RESPONSE FORMAT (JSON only):
{{
    "passed": true/false (true if score >= 80),
    "score": 0-100,
    "issues": [
        {{"issue": "description", "severity": "critical|major|minor", "suggestion": "how to fix", "affected_prompts": [1, 2]}}
    ],
    "cover_specific_score": 0-25,
    "theme_consistency_score": 0-25,
    "strengths": ["what's working well"],
    "summary": "Brief assessment for cover background prompts"
}}

Return ONLY valid JSON, no other text."""


def evaluate_cover_prompts(prompts: list, theme_context: dict = None) -> dict:
    """
    Evaluate MidJourney cover background prompts (full color, no text).
    Criteria: book cover background, no inside-page wording, theme consistency, --ar 2:3.

    Returns:
        dict with: passed, score, issues, summary
    """
    llm = get_evaluator_llm()

    main_theme = ""
    if theme_context:
        main_theme = theme_context.get("main_theme") or ""
        if not main_theme and theme_context.get("original_input"):
            main_theme = (theme_context.get("original_input") or "").split(" in ")[0].strip()
        if not main_theme and theme_context.get("expanded_theme"):
            main_theme = (theme_context.get("expanded_theme") or "").split(" in ")[0].strip()
    style = (theme_context or {}).get("artistic_style", "")
    theme_section = f"The main theme for this book is: **{main_theme}**. Style: **{style}**. Cover prompts should match this theme and style."

    prompt_count = len(prompts)

    # Pre-check: forbidden inside-page phrasing; required --ar 2:3; prefer "no text"
    format_issues = []
    for i, p in enumerate(prompts):
        p_lower = p.lower()
        if "--ar 2:3" not in p_lower and "--ar 2:3" not in p.replace(" ", ""):
            format_issues.append(f"Prompt {i+1} should end with --ar 2:3 for book cover")
        if "coloring book page" in p_lower or "clean and simple line art" in p_lower or "black and white" in p_lower or "--no color" in p_lower:
            format_issues.append(f"Prompt {i+1} contains inside-page wording (cover must be full color, no B&W)")
        if "book cover" not in p_lower and "cover art" not in p_lower and "cover design" not in p_lower and "cover background" not in p_lower:
            format_issues.append(f"Prompt {i+1} should mention book cover/cover art/cover design")
        if "no text" not in p_lower and "no letters" not in p_lower and "no words" not in p_lower and "no typography" not in p_lower:
            format_issues.append(f"Prompt {i+1} should include 'no text' or 'no words' so the image is title-free")

    prompts_sample = "\n".join([f"{i+1}. {p}" for i, p in enumerate(prompts)])

    prompt_template = ChatPromptTemplate.from_template(COVER_PROMPTS_EVALUATOR_PROMPT)
    chain = prompt_template | llm | StrOutputParser()

    try:
        result = chain.invoke({
            "theme_section": theme_section,
            "prompt_count": prompt_count,
            "prompts_sample": prompts_sample,
        })
        evaluation = parse_json_response(result)
        if format_issues:
            existing = evaluation.get("issues", [])
            evaluation["issues"] = existing + [
                {"issue": f"Pre-check: {'; '.join(format_issues[:5])}" + ("; ..." if len(format_issues) > 5 else ""), "severity": "major", "suggestion": "Fix format and cover-specific requirements"}
            ]
            evaluation["passed"] = False
            evaluation["score"] = min(evaluation.get("score", 100), 75)
        evaluation["metrics"] = {"prompt_count": prompt_count, "pre_check_issues": format_issues[:10]}
        return evaluation
    except Exception as e:
        return {
            "passed": False,
            "score": 0,
            "issues": [{"issue": f"Evaluation error: {e}", "severity": "critical", "suggestion": "Retry"}],
            "summary": f"Evaluation failed: {e}",
            "metrics": {"prompt_count": prompt_count},
        }


# =============================================================================
# SEO KEYWORDS EVALUATOR
# =============================================================================

KEYWORDS_EVALUATOR_PROMPT = """You are an SEO strategist evaluating coloring book keywords for both search effectiveness AND niche opportunity.

## EVALUATION CRITERIA:

### Technical Requirements (30 points)
1. **Count**: Must have EXACTLY 10 keywords (current: {keyword_count})

2. **Keyword Types Mix**:
   - Should have 4-5 short-tail keywords (1-2 words): e.g., "coloring book", "adult coloring"
   - Should have 5-6 long-tail keywords (3+ words): e.g., "stress relief coloring book for adults"

3. **No Duplicates**:
   - No exact duplicates
   - No near-duplicates (e.g., "adult coloring" and "coloring for adults")

### Niche Opportunity (40 points)
4. **Competitive Balance** (15 points):
   - Mix of high-competition (broader reach) and low-competition (easier ranking)
   - Not ALL generic terms that are impossible to rank for
   - At least 2-3 niche-specific keywords

5. **Unique Angle Keywords** (15 points):
   - Keywords that capture the UNIQUE aspects of this book
   - Not just "coloring book" variations
   - Theme: "{theme_hint}"

6. **Buyer Intent** (10 points):
   - Keywords that indicate purchase intent
   - "...for adults", "gift for...", "...book"
   - Avoid browser-only searches

### Search Quality (30 points)
7. **Relevance**:
   - ALL keywords must be relevant to coloring books
   - Terms people actually search for on Amazon

8. **Search Volume Potential**:
   - Keywords with realistic search volume
   - Not too generic (just "book") or too specific

## KEYWORDS TO EVALUATE:
{keywords}

## RESPONSE FORMAT (JSON only):
{{
    "passed": true/false (true if score >= 80),
    "score": 0-100,
    "niche_scores": {{
        "competitive_balance": 0-15,
        "unique_angle": 0-15,
        "buyer_intent": 0-10
    }},
    "issues": [
        {{"issue": "description", "severity": "critical|major|minor", "suggestion": "how to fix", "affected_keywords": ["keyword1"]}}
    ],
    "keyword_analysis": {{
        "short_tail_count": 0,
        "long_tail_count": 0,
        "duplicates_found": [],
        "irrelevant_keywords": [],
        "high_competition": ["keywords"],
        "niche_opportunity": ["keywords"],
        "buyer_intent_keywords": ["keywords"]
    }},
    "strengths": ["what's working well"],
    "summary": "Brief assessment with niche opportunity focus"
}}

Return ONLY valid JSON, no other text."""


def evaluate_keywords(keywords: list, theme_hint: str = "") -> dict:
    """
    Evaluate SEO keywords with detailed criteria.
    
    Returns:
        dict with: passed, score, issues, keyword_analysis, summary
    """
    llm = get_evaluator_llm()
    
    keyword_count = len(keywords)
    
    # Pre-check for duplicates
    duplicates = []
    seen = set()
    for kw in keywords:
        kw_lower = kw.lower().strip()
        if kw_lower in seen:
            duplicates.append(kw)
        seen.add(kw_lower)
    
    # Categorize by length
    short_tail = [kw for kw in keywords if len(kw.split()) <= 2]
    long_tail = [kw for kw in keywords if len(kw.split()) > 2]
    
    prompt = ChatPromptTemplate.from_template(KEYWORDS_EVALUATOR_PROMPT)
    chain = prompt | llm | StrOutputParser()
    
    try:
        result = chain.invoke({
            "keyword_count": keyword_count,
            "keywords": ", ".join(keywords),
            "theme_hint": theme_hint or "coloring book"
        })
        
        evaluation = parse_json_response(result)
        evaluation["metrics"] = {
            "keyword_count": keyword_count,
            "short_tail_count": len(short_tail),
            "long_tail_count": len(long_tail),
            "duplicates": duplicates
        }
        
        return evaluation
        
    except Exception as e:
        return {
            "passed": False,
            "score": 0,
            "issues": [{"issue": f"Evaluation error: {e}", "severity": "critical", "suggestion": "Retry"}],
            "keyword_analysis": {"short_tail_count": len(short_tail), "long_tail_count": len(long_tail)},
            "summary": f"Evaluation failed: {e}",
            "metrics": {"keyword_count": keyword_count}
        }


# =============================================================================
# THEME CREATIVITY EVALUATOR
# =============================================================================

THEME_CREATIVITY_EVALUATOR_PROMPT = """You are an expert creative director evaluating coloring book theme concepts for creativity, uniqueness, and market potential.

## THEME TO EVALUATE:
{theme_data}

## EVALUATION CRITERIA:

### 1. UNIQUENESS (25 points)
- Is this angle fresh in the coloring book market?
- Does it offer something different from existing best-sellers?
- Would it stand out on Amazon/Etsy?
- Penalize generic concepts like "flowers" or "animals" without a unique twist

### 2. ARTISTIC STYLE FIT (25 points)
- Does the chosen artistic style match the theme well?
- Is the style popular and proven (e.g., mandala, Art Nouveau, zentangle)?
- Will the style translate well to coloring book format?
- Is it inspired by successful artists like Johanna Basford, Kerby Rosanes?

### 3. MARKET OPPORTUNITY (20 points)
- Is there demand for this theme?
- Is the competition manageable (not oversaturated)?
- Does the research support this concept?
- Would the target audience actually buy this?

### 4. TARGET AUDIENCE CLARITY (15 points)
- Is the audience well-defined (adults, teens, specific interests)?
- Does the concept appeal to that audience?
- Is the difficulty level appropriate?

### 5. CREATIVE POTENTIAL (15 points)
- Will this concept inspire diverse, interesting designs?
- Can it sustain 50 unique pages?
- Does it have visual storytelling potential?

## SCORING WEIGHTS:
- Uniqueness: 25%
- Artistic Style Fit: 25%
- Market Opportunity: 20%
- Target Audience: 15%
- Creative Potential: 15%

## RESPONSE FORMAT (JSON only):
{{
    "passed": true/false (true if score >= 80),
    "score": 0-100,
    "creativity_breakdown": {{
        "uniqueness": {{"score": 0-25, "assessment": "explanation"}},
        "artistic_style_fit": {{"score": 0-25, "assessment": "explanation"}},
        "market_opportunity": {{"score": 0-20, "assessment": "explanation"}},
        "target_audience": {{"score": 0-15, "assessment": "explanation"}},
        "creative_potential": {{"score": 0-15, "assessment": "explanation"}}
    }},
    "issues": [
        {{"issue": "description", "severity": "critical|major|minor", "suggestion": "how to improve"}}
    ],
    "strengths": ["what's working well"],
    "summary": "Brief creative assessment"
}}

Return ONLY valid JSON, no other text."""


def evaluate_theme_creativity(theme_data: dict) -> dict:
    """
    Evaluate an expanded theme for creativity, uniqueness, and market fit.
    
    Args:
        theme_data: Dictionary with theme, artistic_style, unique_angle, 
                   target_audience, market_research, etc.
    
    Returns:
        dict with: passed, score, creativity_breakdown, issues, strengths, summary
    """
    llm = get_evaluator_llm()
    
    # Format theme data for evaluation
    theme_str = json.dumps(theme_data, indent=2)
    
    prompt = ChatPromptTemplate.from_template(THEME_CREATIVITY_EVALUATOR_PROMPT)
    chain = prompt | llm | StrOutputParser()
    
    try:
        result = chain.invoke({"theme_data": theme_str})
        evaluation = parse_json_response(result)
        
        # Add the original theme data to the evaluation
        evaluation["evaluated_theme"] = theme_data
        
        return evaluation
        
    except Exception as e:
        return {
            "passed": False,
            "score": 0,
            "creativity_breakdown": {
                "uniqueness": {"score": 0, "assessment": "Evaluation failed"},
                "artistic_style_fit": {"score": 0, "assessment": "Evaluation failed"},
                "market_opportunity": {"score": 0, "assessment": "Evaluation failed"},
                "target_audience": {"score": 0, "assessment": "Evaluation failed"},
                "creative_potential": {"score": 0, "assessment": "Evaluation failed"}
            },
            "issues": [{"issue": f"Evaluation error: {e}", "severity": "critical", "suggestion": "Retry"}],
            "strengths": [],
            "summary": f"Evaluation failed: {e}",
            "evaluated_theme": theme_data
        }


# =============================================================================
# HUMAN-LIKE WRITING ASSESSMENT HELPERS
# =============================================================================

def check_cliches(text: str) -> list:
    """Check for marketing clichés in text."""
    found = []
    text_lower = text.lower()
    for cliche in MARKETING_CLICHES:
        if cliche.lower() in text_lower:
            found.append(cliche)
    return found


def check_sentence_variety(text: str) -> dict:
    """Analyze sentence variety in a text."""
    import re
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return {"score": 0, "assessment": "No sentences found"}
    
    lengths = [len(s.split()) for s in sentences]
    avg_length = sum(lengths) / len(lengths)
    
    # Check for variety
    short = sum(1 for l in lengths if l < 10)
    medium = sum(1 for l in lengths if 10 <= l < 20)
    long = sum(1 for l in lengths if l >= 20)
    
    # Check for sentence starters
    starters = [s.split()[0].lower() if s.split() else "" for s in sentences]
    unique_starters = len(set(starters))
    starter_variety = unique_starters / len(starters) if starters else 0
    
    # Calculate variety score
    length_variety = min(short, medium, long) / max(1, len(sentences) / 3)
    overall_variety = (length_variety * 0.5 + starter_variety * 0.5) * 10
    
    return {
        "score": round(overall_variety, 1),
        "avg_length": round(avg_length, 1),
        "short_sentences": short,
        "medium_sentences": medium,
        "long_sentences": long,
        "unique_starters_ratio": round(starter_variety, 2),
        "assessment": "Good variety" if overall_variety > 6 else "Needs more variety" if overall_variety > 3 else "Repetitive structure"
    }


def check_authenticity(text: str) -> dict:
    """Check if text sounds authentic (human-written)."""
    ai_indicators = 0
    human_indicators = 0
    
    # Check for AI patterns
    text_lower = text.lower()
    
    # AI red flags
    if text_lower.count("whether you") > 0:
        ai_indicators += 1
    if text_lower.count("this book offers") > 0:
        ai_indicators += 1
    if text_lower.count("features include") > 0:
        ai_indicators += 1
    if re.search(r'designed to\s+(help|provide|offer)', text_lower):
        ai_indicators += 1
    if text_lower.count("explore a world") > 0:
        ai_indicators += 1
    
    # Human-sounding indicators
    if re.search(r'\bi\b', text_lower):  # First person
        human_indicators += 1
    if "!" in text:  # Enthusiasm
        human_indicators += 1
    if re.search(r'you\'ll|you\'re|we\'ve|isn\'t', text_lower):  # Contractions
        human_indicators += 2
    if re.search(r'grab|snag|pick up', text_lower):  # Casual language
        human_indicators += 1
    
    score = max(0, min(10, 5 + human_indicators * 1.5 - ai_indicators * 2))
    
    return {
        "score": round(score, 1),
        "ai_patterns_found": ai_indicators,
        "human_patterns_found": human_indicators,
        "assessment": "Authentic" if score > 7 else "Somewhat robotic" if score > 4 else "Sounds like AI"
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_feedback(evaluation: dict, component: str) -> str:
    """
    Format evaluation results as detailed, actionable feedback for the executor.
    Includes specific examples, priority ranking, and positive reinforcement.
    """
    score = evaluation.get("score", 0)
    
    if evaluation.get("passed", False):
        # Still provide feedback on what to maintain
        strengths = evaluation.get("strengths", [])
        if strengths:
            return f"✅ {component} PASSED (Score: {score}/100)\n\nStrengths to maintain:\n" + "\n".join(f"  + {s}" for s in strengths)
        return f"✅ {component} PASSED with score {score}/100."
    
    feedback_parts = [f"❌ {component} needs improvement (Score: {score}/100)\n"]
    
    # Get issues based on component type
    if component == "Title & Description":
        issues = evaluation.get("title_issues", []) + evaluation.get("description_issues", [])
        
        # Add creativity-specific feedback
        creativity = evaluation.get("creativity_scores", {})
        if creativity:
            low_scores = [(k, v) for k, v in creativity.items() if v < 6]
            if low_scores:
                feedback_parts.append("📊 Creativity Scores that need work:")
                for key, value in low_scores:
                    feedback_parts.append(f"  • {key.replace('_', ' ').title()}: {value}/10")
                feedback_parts.append("")
                
    elif component == "Theme":
        issues = evaluation.get("issues", [])
        # Add creativity breakdown feedback
        breakdown = evaluation.get("creativity_breakdown", {})
        low_scores = []
        for key, data in breakdown.items():
            if isinstance(data, dict) and data.get("score", 100) < 15:
                low_scores.append((key, data))
        
        if low_scores:
            feedback_parts.append("📊 Areas needing improvement:")
            for key, data in low_scores:
                feedback_parts.append(f"  • {key.replace('_', ' ').title()}: {data.get('score', 0)} pts")
                feedback_parts.append(f"    → {data.get('assessment', 'Needs work')}")
            feedback_parts.append("")
            
    elif component == "MidJourney Prompts":
        issues = evaluation.get("issues", [])
        
        # Main theme consistency (critical when main theme was provided)
        mt_score = evaluation.get("main_theme_consistency_score")
        prompts_off = evaluation.get("prompts_off_theme") or []
        if mt_score is not None and (mt_score < 15 or prompts_off):
            feedback_parts.append("🎯 Main theme consistency (CRITICAL):")
            feedback_parts.append(f"  • Score: {mt_score}/25 — prompts must center on the main theme.")
            if prompts_off:
                feedback_parts.append(f"  • Prompts off-theme (revise or replace): {prompts_off[:15]}")
                if len(prompts_off) > 15:
                    feedback_parts.append(f"    ... and {len(prompts_off) - 15} more.")
            feedback_parts.append("")
        
        # Add creativity scores
        creativity = evaluation.get("creativity_scores", {})
        if creativity:
            low_scores = [(k, v) for k, v in creativity.items() if v < 6]
            if low_scores:
                feedback_parts.append("📊 Creative areas needing work:")
                for key, value in low_scores:
                    feedback_parts.append(f"  • {key.replace('_', ' ').title()}: {value}/10")
                feedback_parts.append("")
        
        # Highlight standout prompts if any
        standouts = evaluation.get("standout_prompts", [])
        if standouts:
            feedback_parts.append(f"✓ Good prompts to use as reference: {', '.join(str(s) for s in standouts[:3])}")
            feedback_parts.append("")
            
    elif component == "SEO Keywords":
        issues = evaluation.get("issues", [])
        
        # Add niche scores
        niche = evaluation.get("niche_scores", {})
        if niche:
            low_scores = [(k, v) for k, v in niche.items() if v < niche.get(k.replace("_score", "_max"), 10) * 0.6]
            if low_scores:
                feedback_parts.append("📊 Niche opportunity scores:")
                for key, value in niche.items():
                    feedback_parts.append(f"  • {key.replace('_', ' ').title()}: {value}")
                feedback_parts.append("")
        
        # Show keyword analysis
        analysis = evaluation.get("keyword_analysis", {})
        if analysis:
            if analysis.get("niche_opportunity"):
                feedback_parts.append(f"✓ Good niche keywords: {', '.join(analysis['niche_opportunity'][:3])}")
            if analysis.get("high_competition"):
                feedback_parts.append(f"⚠ High competition (hard to rank): {', '.join(analysis['high_competition'][:3])}")
            feedback_parts.append("")
    else:
        issues = evaluation.get("issues", [])
    
    # Sort issues by severity (critical first)
    severity_order = {"critical": 0, "major": 1, "minor": 2}
    sorted_issues = sorted(issues, key=lambda x: severity_order.get(x.get("severity", "minor"), 2))
    
    # Add prioritized issues with examples
    if sorted_issues:
        feedback_parts.append("🔧 Issues to fix (in priority order):\n")
        
        for i, issue in enumerate(sorted_issues[:5], 1):  # Limit to top 5 issues
            severity = issue.get("severity", "unknown").upper()
            issue_text = issue.get("issue", "No description")
            suggestion = issue.get("suggestion", "No suggestion")
            
            # Add severity emoji
            emoji = "🔴" if severity == "CRITICAL" else "🟡" if severity == "MAJOR" else "🟢"
            
            feedback_parts.append(f"{i}. {emoji} [{severity}] {issue_text}")
            feedback_parts.append(f"   → How to fix: {suggestion}")
            
            # Add affected items if available
            affected = issue.get("affected_prompts") or issue.get("affected_keywords")
            if affected:
                feedback_parts.append(f"   → Affected: {affected[:5]}")
            
            feedback_parts.append("")
    
    # Add positive reinforcement - strengths to maintain
    strengths = evaluation.get("strengths", [])
    if strengths:
        feedback_parts.append("✅ Strengths to maintain:")
        for strength in strengths[:3]:
            feedback_parts.append(f"  + {strength}")
    
    # Add metrics summary if available
    metrics = evaluation.get("metrics", {})
    if metrics:
        feedback_parts.append("\n📈 Quick stats:")
        for key, value in list(metrics.items())[:4]:
            feedback_parts.append(f"  • {key.replace('_', ' ').title()}: {value}")
    
    return "\n".join(feedback_parts)
