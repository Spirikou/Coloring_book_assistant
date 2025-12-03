"""Agents for the Coloring Book Assistant."""

from agents.executor import create_executor_agent, get_executor_tools
from agents.evaluator import (
    evaluate_title_description,
    evaluate_prompts,
    evaluate_keywords,
    evaluate_theme_creativity,
    format_feedback,
    check_cliches,
    check_sentence_variety,
    check_authenticity,
    BANNED_AI_WORDS,
    MARKETING_CLICHES,
    SCORING_WEIGHTS,
    MAX_ATTEMPTS,
    PASS_THRESHOLD,
)

__all__ = [
    "create_executor_agent",
    "get_executor_tools",
    "evaluate_title_description",
    "evaluate_prompts",
    "evaluate_keywords",
    "evaluate_theme_creativity",
    "format_feedback",
    "check_cliches",
    "check_sentence_variety",
    "check_authenticity",
    "BANNED_AI_WORDS",
    "MARKETING_CLICHES",
    "SCORING_WEIGHTS",
    "MAX_ATTEMPTS",
    "PASS_THRESHOLD",
]
