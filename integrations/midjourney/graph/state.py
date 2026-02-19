"""Agent state schema — the system's data contract."""

from __future__ import annotations

from typing import TypedDict


class PromptTask(TypedDict, total=False):
    """Tracks a single Midjourney prompt through its lifecycle."""

    prompt: str
    status: str          # "pending" | "generating" | "accepted" | "failed"
    attempt: int         # current attempt number (starts at 1)
    image_path: str      # local path to first downloaded image (legacy)
    images: list         # [{path, upscale_index}, ...]
    error: str           # last error message, if any


class AgentState(TypedDict, total=False):
    """Top-level LangGraph state for the Midjourney automation agent."""

    tasks: list[PromptTask]
    current_index: int
    output_folder: str
    max_retries: int
    dry_run: bool        # when True, no GUI interaction — actions are logged only
    global_status: str   # "running" | "paused" | "completed" | "error"
    stop_requested: bool
    generation_timeout: float
    rate_limiter: object  # RateLimiter, optional
    browser_debug_port: int
    navigated: bool      # True after first navigate_to_imagine
    button_coordinates: dict  # x,y for Creation Actions buttons
    viewport: dict       # target viewport for automation (user's screen)
    coordinates_viewport: dict  # viewport at which button_coordinates were recorded
    debug_show_clicks: bool  # show red circle at click location before each click
