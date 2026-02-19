"""Pre-flight health checks for web automation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from integrations.midjourney.automation.browser_utils import check_browser_connection
from integrations.midjourney.automation.browser_config import DEBUG_PORT


@dataclass
class HealthCheckResult:
    """Result of a single health check."""

    name: str
    status: bool
    message: str
    severity: str  # "error", "warning", "info"


@dataclass
class HealthReport:
    """Complete health check report."""

    all_healthy: bool
    checks: List[HealthCheckResult]

    def has_errors(self) -> bool:
        return any(c.severity == "error" and not c.status for c in self.checks)

    def has_warnings(self) -> bool:
        return any(c.severity == "warning" and not c.status for c in self.checks)


def _check_playwright() -> HealthCheckResult:
    """Check if Playwright is installed and importable."""
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401

        return HealthCheckResult(
            name="Playwright",
            status=True,
            message="Installed",
            severity="info",
        )
    except ImportError as e:
        return HealthCheckResult(
            name="Playwright",
            status=False,
            message=f"Not installed: {e}. Run: pip install playwright && playwright install chromium",
            severity="error",
        )


def run_health_checks(
    output_folder: Optional[Path] = None,
    browser_port: Optional[int] = None,
) -> HealthReport:
    """Run pre-flight health checks for web automation."""
    checks: List[HealthCheckResult] = []
    port = browser_port or DEBUG_PORT
    out = output_folder or Path("./output")

    # Browser connection
    conn = check_browser_connection(port)
    if conn["connected"]:
        checks.append(
            HealthCheckResult(
                name="Browser",
                status=True,
                message=f"Connected on port {port}",
                severity="info",
            )
        )
    else:
        checks.append(
            HealthCheckResult(
                name="Browser",
                status=False,
                message=f"Not connected. Start Brave with --remote-debugging-port={port}",
                severity="error",
            )
        )

    # Playwright
    checks.append(_check_playwright())

    # Output directory
    try:
        out.mkdir(parents=True, exist_ok=True)
        test = out / ".test_write"
        test.write_text("test")
        test.unlink()
        checks.append(
            HealthCheckResult(
                name="Output Directory",
                status=True,
                message=f"Writable: {out}",
                severity="info",
            )
        )
    except Exception as e:
        checks.append(
            HealthCheckResult(
                name="Output Directory",
                status=False,
                message=str(e),
                severity="error",
            )
        )

    all_healthy = not any(c.severity == "error" and not c.status for c in checks)
    return HealthReport(all_healthy=all_healthy, checks=checks)
