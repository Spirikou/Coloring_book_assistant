"""Tools for the Coloring Book Assistant agent."""

from tools.content_tools import (
    # Theme expansion (new)
    expand_and_research_theme,
    # Generation with refinement
    generate_and_refine_title_description,
    generate_and_refine_prompts,
    generate_and_refine_keywords,
    # Legacy tools
    generate_title_description,
    generate_midjourney_prompts,
    extract_seo_keywords,
)
from tools.search_tools import web_search, search_coloring_book_trends
from tools.user_tools import ask_user, save_report, display_results

__all__ = [
    # Theme expansion
    "expand_and_research_theme",
    # Generation with refinement
    "generate_and_refine_title_description",
    "generate_and_refine_prompts",
    "generate_and_refine_keywords",
    # Legacy tools
    "generate_title_description",
    "generate_midjourney_prompts",
    "extract_seo_keywords",
    # Search tools
    "web_search",
    "search_coloring_book_trends",
    # User tools
    "ask_user",
    "save_report",
    "display_results",
]

