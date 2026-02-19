"""Rate limiting to prevent triggering Discord/Midjourney limits."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Optional

from integrations.midjourney.utils.logging_config import logger


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""

    prompts_per_minute: int = 5
    operations_per_second: float = 2.0
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 60.0


class RateLimiter:
    """Rate limiter to prevent triggering Discord/Midjourney limits."""

    def __init__(self, config: Optional[RateLimitConfig] = None) -> None:
        self.config = config or RateLimitConfig()
        self.prompt_timestamps: deque = deque()
        self.operation_timestamps: deque = deque()
        self.violations = 0
        self.last_violation_time: Optional[float] = None

    def wait_if_needed(self, operation: str = "operation") -> None:
        """Wait if necessary to respect rate limits."""
        now = time.time()
        self._clean_old_timestamps(now)

        if operation == "prompt":
            if len(self.prompt_timestamps) >= self.config.prompts_per_minute:
                oldest = self.prompt_timestamps[0]
                wait_time = 60 - (now - oldest) + 0.1
                if wait_time > 0:
                    logger.info(
                        "Rate limit: waiting %.1fs before next prompt...",
                        wait_time,
                    )
                    time.sleep(wait_time)
                    self._clean_old_timestamps(time.time())
            self.prompt_timestamps.append(time.time())

        if len(self.operation_timestamps) >= self.config.operations_per_second:
            oldest = self.operation_timestamps[0]
            wait_time = 1.0 - (now - oldest) + 0.05
            if wait_time > 0:
                time.sleep(wait_time)
                self._clean_old_timestamps(time.time())
        self.operation_timestamps.append(time.time())

    def _clean_old_timestamps(self, now: float) -> None:
        while self.prompt_timestamps and (now - self.prompt_timestamps[0]) > 60:
            self.prompt_timestamps.popleft()
        while (
            self.operation_timestamps
            and (now - self.operation_timestamps[0]) > 1.0
        ):
            self.operation_timestamps.popleft()
