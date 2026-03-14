"""Design generation constants."""

# Concept selection limits
MAX_SELECTED_CONCEPTS = 10
MIN_CONCEPT_VARIATIONS = 5
MAX_CONCEPT_VARIATIONS = 10

# Cover prompts (background-only, no title text)
COVER_PROMPTS_COUNT = 15

# Canonical Midjourney prompt suffixes (used in generator and evaluator)
# Inside pages: B&W line art, thick outlines, no shading/gradient, square
INSIDE_PAGE_SUFFIX = (
    "coloring book page, black and white line art, thick outlines, white background "
    "--no shading color gradient shadow depth --ar 1:1"
)
# Cover: full color, no text; aspect ratio is configurable (see COVER_DEFAULT_ASPECT_RATIO)
COVER_DEFAULT_ASPECT_RATIO = "2:3"
COVER_BASE_SUFFIX = "book cover, rich colors, illustrated, no text"
