"""Pipeline templates and step definitions for the Orchestration tab."""

from __future__ import annotations

PIPELINE_STEP_IDS = ["design", "image", "evaluate", "canva", "pinterest"]

PIPELINE_STEPS = [
    {
        "id": "design",
        "label": "Design Generation",
        "description": "Create design package (title, prompts, keywords)",
        "requires_design_package": False,
    },
    {
        "id": "image",
        "label": "Image Generation",
        "description": "Generate images via Midjourney (Publish, Upscale, Download)",
        "requires_design_package": True,
    },
    {
        "id": "evaluate",
        "label": "Evaluation",
        "description": "Evaluate image quality with LLM",
        "requires_design_package": True,
    },
    {
        "id": "canva",
        "label": "Canva Design",
        "description": "Create multi-page layout in Canva",
        "requires_design_package": True,
    },
    {
        "id": "pinterest",
        "label": "Pinterest Publishing",
        "description": "Publish pins to Pinterest",
        "requires_design_package": True,
    },
]

TEMPLATES: dict[str, list[str]] = {
    "Full Pipeline": ["design", "image", "evaluate", "canva", "pinterest"],
    "Design Only": ["design"],
    "Design to Images": ["design", "image", "evaluate"],
    "Images to Distribution": ["image", "evaluate", "canva", "pinterest"],
    "Publish Only": ["evaluate", "canva", "pinterest"],
    "Empty": [],
}


def get_step_by_id(step_id: str) -> dict | None:
    """Get step definition by ID."""
    for step in PIPELINE_STEPS:
        if step["id"] == step_id:
            return step
    return None


def get_template_steps(template_name: str) -> list[str]:
    """Get step IDs for a template. Returns empty list if template not found."""
    return list(TEMPLATES.get(template_name, []))


def get_all_template_names() -> list[str]:
    """Get list of built-in template names (excluding Empty)."""
    return [n for n in TEMPLATES if n != "Empty"]


def validate_pipeline(
    steps: list[str],
    has_design_package: bool,
    has_user_request: bool = False,
    has_board_name: bool = False,
    pipeline_steps: list[dict] | None = None,
) -> list[str]:
    """
    Validate pipeline configuration. Returns list of error messages.
    Empty list means valid.
    """
    errors: list[str] = []
    steps_def = pipeline_steps or PIPELINE_STEPS
    step_ids = {s["id"] for s in steps_def}

    if not steps:
        errors.append("Pipeline is empty. Add at least one step.")
        return errors

    for step_id in steps:
        if step_id not in step_ids:
            errors.append(f"Unknown step: {step_id}")
            continue
        step = get_step_by_id(step_id)
        if step and step.get("requires_design_package") and not has_design_package:
            # Design package required when Image is first step (or any step that needs it)
            # and Design is not in pipeline
            if "design" not in steps:
                errors.append(
                    f"Step '{step['label']}' requires a design package. "
                    "Select a design package or add Design step."
                )

    if "design" in steps and not has_user_request:
        errors.append("Design step requires a design idea (user request).")

    if "pinterest" in steps and not has_board_name:
        errors.append("Pinterest step requires a board name.")

    return errors
