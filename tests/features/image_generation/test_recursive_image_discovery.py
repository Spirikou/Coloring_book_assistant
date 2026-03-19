from __future__ import annotations

from pathlib import Path


def test_get_images_in_folder_recursive_excludes_cover(tmp_path: Path) -> None:
    from features.image_generation.monitor import get_images_in_folder

    # Root images
    (tmp_path / "a.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (tmp_path / "b.jpg").write_bytes(b"\xff\xd8\xff")

    # Nested concept folder
    concept = tmp_path / "Concept_A"
    concept.mkdir()
    (concept / "c.webp").write_bytes(b"RIFFxxxxWEBP")

    # Cover folder should be excluded
    cover = tmp_path / "cover"
    cover.mkdir()
    (cover / "cover.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    found = get_images_in_folder(str(tmp_path), recursive=True)
    # Should include 3 images, excluding cover.png
    assert len(found) == 3
    assert all("cover" not in Path(p).parts for p in found)


def test_list_images_in_folder_recursive_returns_paths(tmp_path: Path) -> None:
    from features.image_generation.monitor import list_images_in_folder

    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "x.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    paths = list_images_in_folder(str(tmp_path), recursive=True)
    assert any(p.name == "x.png" for p in paths)

