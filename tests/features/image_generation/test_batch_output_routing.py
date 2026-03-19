from __future__ import annotations

from pathlib import Path


def test_resolve_batch_output_folder_prefers_existing_images_folder(tmp_path: Path) -> None:
    from features.image_generation.midjourney_runner import resolve_batch_output_folder

    pkg = tmp_path / "pkg_a"
    design = {"title": "A", "images_folder_path": str(pkg)}

    out = resolve_batch_output_folder(design, default_output_folder=tmp_path / "fallback")

    assert out == pkg
    assert out.exists()
    assert out.is_dir()


def test_resolve_batch_output_folder_auto_creates_package(tmp_path: Path, monkeypatch) -> None:
    import config
    import core.persistence as persistence
    from features.image_generation.midjourney_runner import resolve_batch_output_folder

    monkeypatch.setattr(config, "SAVED_DESIGN_PACKAGES_DIR", tmp_path)
    monkeypatch.setattr(persistence, "SAVED_DESIGN_PACKAGES_DIR", tmp_path)

    design = {
        "title": "Auto Package",
        "description": "Created on demand",
        "midjourney_prompts": ["prompt 1"],
    }

    out = resolve_batch_output_folder(design, default_output_folder=tmp_path / "fallback", auto_create_package=True)

    assert out.exists()
    assert (out / "design.json").exists()
    assert design.get("images_folder_path") == str(out.resolve())
    assert design.get("design_package_path") == str(out.resolve())


def test_run_batch_automated_thread_writes_to_each_package_root(tmp_path: Path, monkeypatch) -> None:
    from features.image_generation import midjourney_runner as runner

    pkg_a = tmp_path / "pkg_a"
    pkg_b = tmp_path / "pkg_b"
    pkg_a.mkdir(parents=True, exist_ok=True)
    pkg_b.mkdir(parents=True, exist_ok=True)
    base_output = tmp_path / "base_output"
    base_output.mkdir(parents=True, exist_ok=True)

    def _fake_run_automated_thread(
        prompts,
        button_coordinates,
        browser_port,
        output_folder,
        stop_flag,
        shared,
        publish_progress,
        uxd_progress,
        download_progress,
        viewport=None,
        coordinates_viewport=None,
        debug_show_clicks=False,
    ):
        output = Path(output_folder)
        output.mkdir(parents=True, exist_ok=True)
        file_path = output / f"ui_batch_{len(prompts)}.png"
        file_path.write_bytes(b"\x89PNG\r\n\x1a\n")
        shared["publish_status"] = "completed"
        shared["uxd_action_status"] = "completed"
        shared["download_status"] = "completed"
        shared["downloaded_paths"] = [str(file_path)]

    monkeypatch.setattr(runner, "run_automated_thread", _fake_run_automated_thread)

    shared = {}
    runner.run_batch_automated_thread(
        designs_with_folders=[
            ({"title": "A", "midjourney_prompts": ["p1"]}, pkg_a, 0),
            ({"title": "B", "midjourney_prompts": ["p2", "p3"]}, pkg_b, 1),
        ],
        button_coordinates={"upscale_subtle": [1, 1], "download": [1, 1]},
        browser_port=9222,
        stop_flag={"stop": False},
        shared=shared,
        publish_progress={},
        uxd_progress={},
        download_progress={},
    )

    assert any(p.suffix.lower() == ".png" for p in pkg_a.glob("*.png"))
    assert any(p.suffix.lower() == ".png" for p in pkg_b.glob("*.png"))
    assert not any(p.suffix.lower() == ".png" for p in base_output.glob("*.png"))
