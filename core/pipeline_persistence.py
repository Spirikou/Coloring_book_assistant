"""Save and load custom pipeline templates."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import SAVED_DESIGNS_DIR

PIPELINE_TEMPLATES_DIR = SAVED_DESIGNS_DIR / "pipeline_templates"


def _ensure_dir() -> Path:
    """Ensure pipeline templates directory exists."""
    PIPELINE_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    return PIPELINE_TEMPLATES_DIR


def _slugify(name: str, max_len: int = 40) -> str:
    """Create a safe filename from template name."""
    safe = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).strip()
    safe = safe.replace(" ", "_")[:max_len].strip("_")
    return safe or "template"


def save_custom_template(name: str, steps: list[str]) -> str:
    """
    Save a custom pipeline template.

    Args:
        name: Display name for the template
        steps: List of step IDs (e.g. ["image", "canva", "pinterest"])

    Returns:
        Path to the saved file
    """
    _ensure_dir()
    slug = _slugify(name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{slug}_{timestamp}.json"
    filepath = PIPELINE_TEMPLATES_DIR / filename

    data = {
        "name": name,
        "steps": steps,
        "_metadata": {
            "saved_at": datetime.now().isoformat(),
            "version": "1.0",
        },
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return str(filepath)


def list_custom_templates() -> list[dict]:
    """
    List all custom pipeline templates.

    Returns:
        List of dicts: {name, steps, filepath, saved_at}
    """
    _ensure_dir()
    templates = []

    for filepath in sorted(PIPELINE_TEMPLATES_DIR.glob("*.json"), reverse=True):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            meta = data.get("_metadata", {})
            saved_at = meta.get("saved_at", filepath.stat().st_mtime)
            if isinstance(saved_at, str):
                try:
                    saved_at = datetime.fromisoformat(saved_at).strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    saved_at = str(saved_at)
            templates.append({
                "name": data.get("name", filepath.stem),
                "steps": data.get("steps", []),
                "filepath": str(filepath),
                "saved_at": saved_at,
            })
        except Exception:
            continue

    return templates


def load_custom_template(name: str) -> Optional[list[str]]:
    """
    Load a custom template by name. Matches by exact name or by template name
    in the most recent file with that name.

    Args:
        name: Template display name

    Returns:
        List of step IDs, or None if not found
    """
    templates = list_custom_templates()
    for t in templates:
        if t["name"] == name:
            return t.get("steps", [])
    return None


def delete_custom_template(name: str) -> bool:
    """
    Delete a custom template by name.

    Returns:
        True if deleted, False if not found
    """
    templates = list_custom_templates()
    for t in templates:
        if t["name"] == name:
            try:
                Path(t["filepath"]).unlink()
                return True
            except Exception:
                return False
    return False
