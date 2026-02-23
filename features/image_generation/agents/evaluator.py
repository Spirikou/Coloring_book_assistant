"""Image quality evaluator - LLM-as-judge for coloring book images."""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Callable

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from config import IMAGE_EVALUATOR_MODEL, IMAGE_EVALUATIONS_FILE

PASS_THRESHOLD = 80

IMAGE_EVALUATOR_PROMPT = """You are a strict quality evaluator for black-and-white coloring book page images.

## CONTEXT
These images are intended for a coloring book. They should be black line art on white background, suitable for printing and coloring.

## EVALUATION CRITERIA

### Color Assessment (CRITICAL)
- **Pure black line art on white** = ideal (full score)
- **Light gray tint or subtle shading** = acceptable (minor deduction, NOT a failure)
- **Full color, colored areas, or strong color** = CRITICAL failure (deduct heavily, fail)

### Clarity (High)
- Sharp lines, no blur
- Readable details
- Clean edges

### Deformities (High)
- No extra limbs, distorted anatomy, broken lines
- No AI artifacts (extra fingers, merged objects, etc.)

### Line Art Quality (High)
- Consistent line weight
- No unintended marks or noise
- Clean black/white contrast

### Coloring Book Fit (Medium)
- Enclosed regions suitable for coloring
- No tiny gaps that would be hard to color
- Balanced composition

### Artifacts (High)
- No AI glitches, duplicated elements, or visual noise

## RESPONSE FORMAT (JSON only)
{{
    "passed": true/false (true if score >= 80),
    "score": 0-100,
    "issues": [
        {{"issue": "description", "severity": "critical|major|minor", "suggestion": "how to fix"}}
    ],
    "strengths": ["what's good"],
    "summary": "Brief one-sentence assessment"
}}

Return ONLY valid JSON, no other text."""


def _get_evaluator_llm() -> ChatOpenAI:
    """Get the LLM for image evaluation."""
    return ChatOpenAI(
        model=IMAGE_EVALUATOR_MODEL,
        temperature=0.2,
        api_key=os.getenv("OPENAI_API_KEY"),
    )


def _parse_json_response(response: str) -> dict:
    """Parse JSON from LLM response, handling markdown code blocks."""
    response = response.strip()
    if response.startswith("```json"):
        response = response[7:]
    if response.startswith("```"):
        response = response[3:]
    if response.endswith("```"):
        response = response[:-3]
    return json.loads(response.strip())


def _image_to_base64(image_path: Path) -> tuple[str, str]:
    """Read image file and return (base64_string, mime_type)."""
    with open(image_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("utf-8")
    suffix = image_path.suffix.lower()
    mime = "image/png" if suffix in (".png",) else "image/jpeg"
    if suffix in (".webp",):
        mime = "image/webp"
    return b64, mime


def evaluate_image(
    image_path: Path,
    prompt_hint: str | None = None,
) -> dict:
    """
    Evaluate a single coloring book image using LLM vision.

    Args:
        image_path: Path to the image file.
        prompt_hint: Optional Midjourney prompt for context.

    Returns:
        dict with: passed, score, issues, strengths, summary
    """
    llm = _get_evaluator_llm()
    b64, mime = _image_to_base64(image_path)

    text = IMAGE_EVALUATOR_PROMPT
    if prompt_hint:
        text += f"\n\nOptional context (Midjourney prompt used): {prompt_hint}"

    content = [
        {"type": "text", "text": text},
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
    ]
    message = HumanMessage(content=content)

    try:
        response = llm.invoke([message])
        result_text = response.content if hasattr(response, "content") else str(response)
        evaluation = _parse_json_response(result_text)
        evaluation["passed"] = evaluation.get("score", 0) >= PASS_THRESHOLD
        return evaluation
    except Exception as e:
        return {
            "passed": False,
            "score": 0,
            "issues": [
                {
                    "issue": f"Evaluation error: {e}",
                    "severity": "critical",
                    "suggestion": "Retry analysis",
                }
            ],
            "strengths": [],
            "summary": f"Evaluation failed: {e}",
        }


def evaluate_images_in_folder(
    folder: Path,
    prompt_hint_map: dict[str, str] | None = None,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, dict]:
    """
    Evaluate all images in a folder.

    Args:
        folder: Path to folder containing images.
        prompt_hint_map: Optional dict mapping filename -> prompt hint.
        on_progress: Optional callback(current, total, filename) for UI progress.

    Returns:
        dict mapping filename -> evaluation result
    """
    from features.image_generation.monitor import list_images_in_folder

    paths = list_images_in_folder(str(folder))
    paths = [Path(p) if not isinstance(p, Path) else p for p in paths]
    prompt_hint_map = prompt_hint_map or {}
    results = {}
    total = len(paths)

    for i, p in enumerate(paths):
        if on_progress:
            on_progress(i + 1, total, p.name)
        hint = prompt_hint_map.get(p.name)
        results[p.name] = evaluate_image(p, prompt_hint=hint)

    return results


def save_image_evaluations(folder: Path, results: dict[str, dict]) -> Path:
    """Save evaluation results to image_evaluations.json in the folder."""
    folder = Path(folder)
    data = {
        "evaluated_at": datetime.now().isoformat(),
        "model": IMAGE_EVALUATOR_MODEL,
        "images": results,
    }
    path = folder / IMAGE_EVALUATIONS_FILE
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    return path


def load_image_evaluations(folder: Path) -> dict[str, dict]:
    """
    Load evaluation results from image_evaluations.json.

    Returns:
        dict mapping filename -> evaluation result (empty dict if file missing)
    """
    folder = Path(folder)
    path = folder / IMAGE_EVALUATIONS_FILE
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("images", {})
    except Exception:
        return {}
