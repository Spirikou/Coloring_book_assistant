"""Tests for design package persistence."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_packages_dir(monkeypatch):
    """Use a temp directory for SAVED_DESIGN_PACKAGES_DIR in tests."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        import config
        monkeypatch.setattr(config, "SAVED_DESIGN_PACKAGES_DIR", tmp_path)
        import core.persistence as persistence
        monkeypatch.setattr(persistence, "SAVED_DESIGN_PACKAGES_DIR", tmp_path)
        yield tmp_path


def test_create_design_package(temp_packages_dir):
    """Creates folder, design.json exists, state has path."""
    from core.persistence import create_design_package

    state = {"title": "Test Design", "description": "A test"}
    path = create_design_package(state)
    assert Path(path).exists()
    assert Path(path).is_dir()
    design_file = Path(path) / "design.json"
    assert design_file.exists()
    import json
    with open(design_file) as f:
        data = json.load(f)
    assert data.get("title") == "Test Design"
    assert data.get("images_folder_path") == path
    assert data.get("design_package_path") == path


def test_save_design_package_new(temp_packages_dir):
    """Creates package with images from temp folder."""
    from core.persistence import save_design_package

    with tempfile.TemporaryDirectory() as src:
        src_path = Path(src)
        # Create a dummy image
        (src_path / "test.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        state = {"title": "With Images", "description": "Test"}
        path = save_design_package(state, str(src_path))
        assert Path(path).exists()
        assert (Path(path) / "design.json").exists()
        assert (Path(path) / "book_config.json").exists()
        assert (Path(path) / "test.png").exists()


def test_save_design_package_update(temp_packages_dir):
    """Updates existing package."""
    from core.persistence import create_design_package, save_design_package

    state = {"title": "Original", "description": "First"}
    path = create_design_package(state)
    with tempfile.TemporaryDirectory() as src:
        src_path = Path(src)
        (src_path / "new.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        state["title"] = "Updated"
        state["description"] = "Second"
        result = save_design_package(state, str(src_path), package_path=path)
    assert result == path
    import json
    with open(Path(path) / "design.json") as f:
        data = json.load(f)
    assert data.get("title") == "Updated"
    assert (Path(path) / "new.png").exists()


def test_list_design_packages(temp_packages_dir):
    """Returns packages with correct structure."""
    from core.persistence import create_design_package, list_design_packages

    create_design_package({"title": "First", "description": "A"})
    create_design_package({"title": "Second", "description": "B"})
    packages = list_design_packages()
    assert len(packages) == 2
    titles = {p["title"] for p in packages}
    assert "First" in titles
    assert "Second" in titles
    for p in packages:
        assert "name" in p
        assert "path" in p
        assert "title" in p
        assert "image_count" in p
        assert "saved_at" in p


def test_load_design_package(temp_packages_dir):
    """Restores state, sets paths."""
    from core.persistence import create_design_package, load_design_package

    state = {"title": "Load Test", "description": "For loading"}
    path = create_design_package(state)
    loaded = load_design_package(path)
    assert loaded is not None
    assert loaded["title"] == "Load Test"
    assert loaded["images_folder_path"] == str(Path(path).resolve())
    assert loaded["design_package_path"] == str(Path(path).resolve())


def test_delete_design_package(temp_packages_dir):
    """Removes folder; rejects path outside base."""
    from core.persistence import create_design_package, delete_design_package

    state = {"title": "To Delete", "description": "X"}
    path = create_design_package(state)
    assert Path(path).exists()
    result = delete_design_package(path)
    assert result is True
    assert not Path(path).exists()

    # Reject path outside base
    with tempfile.TemporaryDirectory() as other:
        result = delete_design_package(other)
        assert result is False
