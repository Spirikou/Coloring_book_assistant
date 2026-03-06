"""Tests for Pinterest publisher fast path (use_folder_directly)."""

import tempfile
from pathlib import Path

import pytest

pytest.importorskip("playwright", reason="playwright not installed")


def test_prepare_publishing_folder_use_folder_directly():
    """When use_folder_directly=True and folder has book_config.json, returns folder without creating new one."""
    from workflows.pinterest.publisher import PinterestPublishingWorkflow

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "book_config.json").write_text('{"title": "Test", "description": "", "seo_keywords": []}')
        (tmp_path / "image1.png").write_bytes(b"\x89PNG\r\n\x1a\n")

        workflow = PinterestPublishingWorkflow()
        result = workflow.prepare_publishing_folder(
            design_state={"title": "Test", "description": "", "seo_keywords": []},
            images_folder=str(tmp_path),
            use_folder_directly=True,
        )
        assert result == str(tmp_path.resolve())
        # No new publish_ folder should have been created
        assert not any(Path(tmp_path).parent.iterdir()) or len(list(Path(tmp_path).parent.iterdir())) <= 1
