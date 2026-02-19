"""Midjourney automation integration for Coloring Book Assistant."""

from __future__ import annotations

from integrations.midjourney.config import AgentConfig
from integrations.midjourney.graph.builder import create_graph
from integrations.midjourney.graph.state import AgentState, PromptTask
from integrations.midjourney.automation.rate_limiter import RateLimiter, RateLimitConfig

__all__ = [
    "AgentConfig",
    "AgentState",
    "PromptTask",
    "create_graph",
    "run_agent",
]


def _build_initial_state(
    prompts: list[str],
    config: AgentConfig,
) -> AgentState:
    """Construct the initial AgentState from user prompts and config."""
    tasks: list[PromptTask] = [
        PromptTask(
            prompt=p,
            status="pending",
            attempt=1,
            image_path="",
            images=[],
            error="",
        )
        for p in prompts
    ]
    return AgentState(
        tasks=tasks,
        current_index=0,
        output_folder=str(config.output_folder),
        max_retries=config.max_retries,
        dry_run=config.dry_run,
        global_status="running",
        stop_requested=False,
        generation_timeout=config.generation_timeout,
        browser_debug_port=config.browser_debug_port,
        rate_limiter=RateLimiter(
            RateLimitConfig(
                prompts_per_minute=config.rate_limit_prompts_per_minute
            )
        ),
        button_coordinates=getattr(config, "button_coordinates", {}) or {},
        viewport=getattr(config, "viewport", None) or {"width": 1920, "height": 1080},
        coordinates_viewport=getattr(config, "coordinates_viewport", None) or {"width": 1920, "height": 1080},
        debug_show_clicks=getattr(config, "debug_show_clicks", False),
    )


def run_agent(
    prompts: list[str],
    config: AgentConfig | None = None,
) -> AgentState:
    """Run the Midjourney automation agent synchronously."""
    if config is None:
        config = AgentConfig()

    graph = create_graph()
    initial_state = _build_initial_state(prompts, config)
    return graph.invoke(initial_state)
