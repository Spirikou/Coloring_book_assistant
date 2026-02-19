"""Orchestrator node — manages the prompt queue."""

from __future__ import annotations

from integrations.midjourney.graph.state import AgentState
from integrations.midjourney.utils.logging_config import logger


def pick_next_prompt(state: AgentState) -> AgentState:
    """Advance current_index to the next pending task, or signal completion."""
    tasks = state["tasks"]
    current = state.get("current_index", 0)

    # Find the next pending task starting from current_index
    for i in range(current, len(tasks)):
        if tasks[i].get("status") == "pending":
            logger.info(
                "Picking prompt %d/%d: %s",
                i + 1,
                len(tasks),
                tasks[i]["prompt"][:60],
            )
            tasks[i]["status"] = "generating"
            if tasks[i].get("attempt", 0) == 0:
                tasks[i]["attempt"] = 1
            return {
                **state,
                "tasks": tasks,
                "current_index": i,
                "global_status": "running",
            }

    # All tasks processed
    logger.info("All prompts processed")
    return {**state, "global_status": "completed"}
