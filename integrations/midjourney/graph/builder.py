"""StateGraph construction and compilation."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from integrations.midjourney.graph.edges import should_continue
from integrations.midjourney.graph.nodes.orchestrator import pick_next_prompt
from integrations.midjourney.graph.nodes.web_automation import process_prompt_web
from integrations.midjourney.graph.state import AgentState


def create_graph():
    """Build and compile the Midjourney automation LangGraph."""
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("pick_next_prompt", pick_next_prompt)
    graph.add_node("process_prompt_web", process_prompt_web)

    # Entry point
    graph.set_entry_point("pick_next_prompt")

    # Conditional: pick_next_prompt → generate or end
    graph.add_conditional_edges(
        "pick_next_prompt",
        should_continue,
        {
            "generate": "process_prompt_web",
            "end": END,
        },
    )

    # After processing one prompt → pick next
    graph.add_edge("process_prompt_web", "pick_next_prompt")

    return graph.compile()
