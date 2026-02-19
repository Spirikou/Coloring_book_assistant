"""Midjourney config - delegates to project config.get_midjourney_config()."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from config import get_midjourney_config


def get_file_config_overrides(config_path: Path | None = None) -> dict[str, Any]:
    """Load config from project config. Used as base overrides by midjourney code."""
    return get_midjourney_config(config_path)


class AgentConfig(BaseSettings):
    """Pydantic config for Midjourney agent. Used by run_agent and CLI."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    output_folder: Path = Field(
        default=Path("./output"),
        description="Directory where downloaded images are saved",
    )
    max_retries: int = Field(
        default=3,
        description="Max regeneration attempts per prompt before giving up",
    )
    generation_timeout: float = Field(
        default=300.0,
        description="Max seconds to wait for Midjourney generation",
    )
    dry_run: bool = Field(
        default=False,
        description="When True, log actions instead of driving the GUI",
    )
    browser_debug_port: int = Field(
        default=9222,
        description="Chrome DevTools Protocol port for browser connection",
    )
    rate_limit_prompts_per_minute: int = Field(
        default=5,
        description="Max prompts per minute for rate limiting",
    )
    checkpoint_enabled: bool = Field(
        default=False,
        description="Save checkpoints for resume on failure",
    )
    button_coordinates: dict[str, list[int]] = Field(
        default_factory=dict,
        description="x,y coordinates for Creation Actions buttons (download, upscale_subtle, etc.)",
    )
    viewport: dict[str, int] = Field(
        default_factory=lambda: {"width": 1920, "height": 1080},
        description="Target viewport for automation (auto-detected if omitted)",
    )
    coordinates_viewport: dict[str, int] = Field(
        default_factory=lambda: {"width": 1920, "height": 1080},
        description="Viewport at which button_coordinates were recorded (for scaling)",
    )
    debug_show_clicks: bool = Field(
        default=False,
        description="When True, show red circle at click location before each coordinate-based click",
    )
