"""Conditional routing functions for the LangGraph graph."""

from __future__ import annotations

from integrations.midjourney.graph.state import AgentState


def should_continue(state: AgentState) -> str:
    """After pick_next_prompt: decide whether to generate or finish."""
    progress = state.get("_progress")
    if progress is not None and getattr(progress, "stop_requested", False):
        return "end"
    if state.get("stop_requested"):
        return "end"
    if state.get("global_status") == "completed":
        return "end"
    return "generate"
