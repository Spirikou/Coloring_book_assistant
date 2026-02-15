"""Centralized configuration for Coloring Book Assistant."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = Path(os.getenv("CB_OUTPUT_DIR", str(PROJECT_ROOT)))
# Use saved_designs at project root for backward compatibility
SAVED_DESIGNS_DIR = OUTPUT_DIR / "saved_designs"
PINTEREST_PUBLISH_DIR = OUTPUT_DIR / "pinterest_publish"
