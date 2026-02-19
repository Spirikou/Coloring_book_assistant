"""Thread-safe shared progress state between LangGraph and Streamlit."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class SharedProgress:
    """Bridge between the background agent thread and the Streamlit UI."""

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # Prompt-level progress
    total_prompts: int = 0
    completed_prompts: int = 0
    current_prompt: str = ""
    current_attempt: int = 0

    # Image-level (derived: 4 per prompt)
    images_created: int = 0
    images_estimated_total: int = 0

    # Global status
    status: str = "idle"  # idle | running | completed | error
    error_message: str = ""

    # Per-task results (list of dicts matching PromptTask)
    results: list[dict] = field(default_factory=list)

    # Stop flag
    stop_requested: bool = False

    def update(self, **kwargs) -> None:
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self, k):
                    setattr(self, k, v)

    def snapshot(self) -> dict:
        """Return a copy of all fields for the UI to read."""
        with self._lock:
            return {
                "total_prompts": self.total_prompts,
                "completed_prompts": self.completed_prompts,
                "current_prompt": self.current_prompt,
                "current_attempt": self.current_attempt,
                "images_created": self.images_created,
                "images_estimated_total": self.images_estimated_total,
                "status": self.status,
                "error_message": self.error_message,
                "results": list(self.results),
                "stop_requested": self.stop_requested,
            }

    def request_stop(self) -> None:
        with self._lock:
            self.stop_requested = True

    def reset(self) -> None:
        with self._lock:
            self.total_prompts = 0
            self.completed_prompts = 0
            self.current_prompt = ""
            self.current_attempt = 0
            self.images_created = 0
            self.images_estimated_total = 0
            self.status = "idle"
            self.error_message = ""
            self.results = []
            self.stop_requested = False
