"""Utilities for saving and loading workflow state."""

import json
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

from config import (
    IMAGE_EVALUATIONS_FILE,
    SAVED_DESIGNS_DIR,
    PINTEREST_PUBLISH_DIR,
    SAVED_DESIGN_PACKAGES_DIR,
)

SAVED_STATES_DIR = SAVED_DESIGNS_DIR
PINTEREST_CONFIG_FILE = PINTEREST_PUBLISH_DIR / "pinterest_config.json"
SAVED_STATES_DIR.mkdir(parents=True, exist_ok=True)


def _prepare_state_for_json(state: dict) -> dict:
    """Prepare state for JSON serialization. Skips/converts non-serializable values."""
    result = {}
    for key, value in state.items():
        try:
            json.dumps(value)
            result[key] = value
        except (TypeError, ValueError):
            if key not in ["messages"]:
                result[key] = str(value)
    return result


def save_workflow_state(state: Dict, name: Optional[str] = None) -> str:
    """
    Save workflow state to a JSON file.
    
    Args:
        state: The workflow state dictionary
        name: Optional custom name for the saved state. If None, auto-generates from title/timestamp.
    
    Returns:
        Path to the saved file
    """
    # Generate filename
    if name:
        # Sanitize name for filename
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')[:50]  # Limit length
        filename = f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    else:
        # Auto-generate from title or timestamp
        title = state.get("title", "")
        if title:
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title.replace(' ', '_')[:30]  # Limit length
            filename = f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        else:
            filename = f"design_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    filepath = SAVED_STATES_DIR / filename
    
    # Prepare state for JSON serialization
    state_to_save = _prepare_state_for_json(state)
    
    # Add metadata
    state_to_save["_metadata"] = {
        "saved_at": datetime.now().isoformat(),
        "saved_by": "user",
        "version": "1.0"
    }
    
    # Save to file
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(state_to_save, f, indent=2, ensure_ascii=False, default=str)
    
    return str(filepath)


def load_workflow_state(filepath: str) -> Optional[Dict]:
    """
    Load workflow state from a JSON file.
    
    Args:
        filepath: Path to the saved state file
    
    Returns:
        The workflow state dictionary, or None if loading failed
    """
    try:
        path = Path(filepath)
        if not path.exists():
            return None
        
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
        
        # Remove metadata before returning
        state.pop("_metadata", None)
        
        # Reinitialize some fields that might be needed
        if "messages" not in state:
            state["messages"] = []
        if "status" not in state:
            state["status"] = "completed"
        
        return state
    except Exception as e:
        print(f"Error loading state: {e}")
        return None


def list_saved_states() -> List[Dict]:
    """
    List all saved workflow states.
    
    Returns:
        List of dicts with info about each saved state: {name, filepath, saved_at, title, description}
    """
    states = []
    
    if not SAVED_STATES_DIR.exists():
        return states
    
    for filepath in sorted(SAVED_STATES_DIR.glob("*.json"), reverse=True):  # Newest first
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                state = json.load(f)
            
            metadata = state.get("_metadata", {})
            saved_at = metadata.get("saved_at", filepath.stat().st_mtime)
            
            # Try to parse timestamp
            try:
                if isinstance(saved_at, str):
                    saved_at_dt = datetime.fromisoformat(saved_at)
                else:
                    saved_at_dt = datetime.fromtimestamp(saved_at)
                saved_at_str = saved_at_dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                saved_at_str = str(saved_at)
            
            states.append({
                "name": filepath.stem,
                "filepath": str(filepath),
                "saved_at": saved_at_str,
                "title": state.get("title", "Untitled"),
                "description": state.get("description", "")[:100] + "..." if len(state.get("description", "")) > 100 else state.get("description", ""),
                "has_images": bool(state.get("images_folder_path")),
                "has_pinterest": bool(state.get("pinterest_board_name"))
            })
        except Exception as e:
            print(f"Error reading state file {filepath}: {e}")
            continue
    
    return states


def save_pinterest_config(board_name: str, images_folder_path: str) -> bool:
    """
    Save Pinterest publishing configuration (board name, images folder path).

    Args:
        board_name: Pinterest board name
        images_folder_path: Path to folder containing images

    Returns:
        True if saved successfully
    """
    try:
        PINTEREST_PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
        config = {
            "board_name": board_name or "",
            "images_folder_path": images_folder_path or "",
            "_metadata": {
                "saved_at": datetime.now().isoformat(),
            },
        }
        with open(PINTEREST_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving Pinterest config: {e}")
        return False


def load_pinterest_config() -> Optional[Dict]:
    """
    Load saved Pinterest configuration.

    Returns:
        Dict with board_name, images_folder_path, or None if not found
    """
    try:
        if not PINTEREST_CONFIG_FILE.exists():
            return None
        with open(PINTEREST_CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        config.pop("_metadata", None)
        return config
    except Exception as e:
        print(f"Error loading Pinterest config: {e}")
        return None


def save_preview_to_images_folder(
    images_folder: str,
    title: str,
    description: str,
    seo_keywords: Optional[List[str]] = None,
) -> bool:
    """
    Save preview modifications (title, description) to book_config.json in the images folder.
    Use this to persist edits before publishing so they survive app restarts.

    Args:
        images_folder: Path to folder containing images
        title: Pin title
        description: Pin description
        seo_keywords: Optional list of SEO keywords (preserves existing if None)

    Returns:
        True if saved successfully
    """
    try:
        path = Path(images_folder)
        if not path.exists() or not path.is_dir():
            return False
        config_file = path / BOOK_CONFIG_FILE
        # Load existing to preserve seo_keywords if not provided
        existing = {}
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                pass
        config = {
            "title": title or "",
            "description": description or "",
            "seo_keywords": seo_keywords if seo_keywords is not None else existing.get("seo_keywords", []),
        }
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving preview to images folder: {e}")
        return False


# Pinterest publish session helpers
IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"]
PUBLISHED_PINS_FILE = "published_pins.json"
BOOK_CONFIG_FILE = "book_config.json"
DESIGN_JSON_FILE = "design.json"


def list_publish_sessions() -> List[Dict]:
    """
    List all Pinterest publish sessions (publish_* folders).

    Returns:
        List of dicts: {folder_path, timestamp, title, description_preview, image_count, published_count}
    """
    sessions = []
    if not PINTEREST_PUBLISH_DIR.exists():
        return sessions

    for folder in sorted(PINTEREST_PUBLISH_DIR.glob("publish_*"), reverse=True):
        if not folder.is_dir():
            continue
        try:
            config = load_session_config(str(folder))
            if config is None:
                config = {"title": folder.name, "description": ""}

            # Count images
            image_count = sum(
                1 for f in folder.iterdir()
                if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
            )

            # Count published from published_pins.json
            published_count = 0
            pins_file = folder / PUBLISHED_PINS_FILE
            if pins_file.exists():
                try:
                    with open(pins_file, "r", encoding="utf-8") as f:
                        pins = json.load(f)
                    published_count = sum(
                        1 for v in pins.values()
                        if isinstance(v, dict) and v.get("status") == "success"
                    )
                except Exception:
                    pass

            # Extract timestamp from folder name (publish_YYYYMMDD_HHMMSS)
            ts = folder.name.replace("publish_", "")
            try:
                ts_dt = datetime.strptime(ts, "%Y%m%d_%H%M%S")
                timestamp_str = ts_dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                timestamp_str = ts

            sessions.append({
                "folder_path": str(folder.resolve()),
                "folder_name": folder.name,
                "timestamp": timestamp_str,
                "title": config.get("title", "Untitled"),
                "description_preview": (config.get("description", "")[:80] + "..." if len(config.get("description", "")) > 80 else config.get("description", "")),
                "image_count": image_count,
                "published_count": published_count,
            })
        except Exception as e:
            print(f"Error reading session {folder}: {e}")
            continue

    return sessions


def load_session_config(folder_path: str) -> Optional[Dict]:
    """
    Load book_config.json from a publish session folder.

    Returns:
        Dict with title, description, seo_keywords, or None if not found
    """
    try:
        path = Path(folder_path)
        config_file = path / BOOK_CONFIG_FILE
        if not config_file.exists():
            return None
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading session config: {e}")
        return None


def delete_publish_session(folder_path: str) -> bool:
    """
    Delete an entire publish session folder and all its contents.

    Returns:
        True if deleted successfully
    """
    try:
        import shutil
        path = Path(folder_path)
        if not path.exists() or not path.is_dir():
            return False
        # Ensure we're only deleting publish_* folders under PINTEREST_PUBLISH_DIR
        try:
            path.resolve().relative_to(PINTEREST_PUBLISH_DIR.resolve())
        except ValueError:
            return False  # Path not under publish dir
        if not path.name.startswith("publish_"):
            return False
        shutil.rmtree(path)
        return True
    except Exception as e:
        print(f"Error deleting publish session: {e}")
        return False


def delete_session_image(folder_path: str, filename: str) -> bool:
    """
    Delete an image file from a publish session folder.
    Optionally remove its entry from published_pins.json so it can be re-published.

    Returns:
        True if deleted successfully
    """
    try:
        path = Path(folder_path)
        image_file = path / filename
        if not image_file.exists() or not image_file.is_file():
            return False
        image_file.unlink()

        # Remove from published_pins.json so re-run can retry
        pins_file = path / PUBLISHED_PINS_FILE
        if pins_file.exists():
            try:
                with open(pins_file, "r", encoding="utf-8") as f:
                    pins = json.load(f)
                if filename in pins:
                    del pins[filename]
                    with open(pins_file, "w", encoding="utf-8") as f:
                        json.dump(pins, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
        return True
    except Exception as e:
        print(f"Error deleting session image: {e}")
        return False


def create_design_package(state: dict, name: Optional[str] = None) -> str:
    """
    Create a new design package folder with design.json only (no images yet).
    Returns path to the new folder.
    """
    SAVED_DESIGN_PACKAGES_DIR.mkdir(parents=True, exist_ok=True)
    if name:
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')[:50]
        slug = f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    else:
        title = state.get("title", "")
        if title:
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title.replace(' ', '_')[:30]
            slug = f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        else:
            slug = f"design_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    pkg_path = SAVED_DESIGN_PACKAGES_DIR / slug
    pkg_path.mkdir(parents=True, exist_ok=True)
    state_copy = dict(state)
    state_copy["images_folder_path"] = str(pkg_path.resolve())
    state_copy["design_package_path"] = str(pkg_path.resolve())
    state_to_save = _prepare_state_for_json(state_copy)
    state_to_save["_metadata"] = {
        "saved_at": datetime.now().isoformat(),
        "saved_by": "design_package",
        "version": "1.0"
    }
    design_file = pkg_path / DESIGN_JSON_FILE
    with open(design_file, "w", encoding="utf-8") as f:
        json.dump(state_to_save, f, indent=2, ensure_ascii=False, default=str)
    return str(pkg_path.resolve())


def save_design_package(
    state: dict,
    source_images_folder: str | Path,
    package_path: Optional[str | Path] = None,
    cover_source_folder: Optional[str | Path] = None,
) -> str:
    """
    Create or update a design package: copy images + write design.json and book_config.json.
    If package_path provided, update existing package. Otherwise create new folder.
    If cover_source_folder is provided and exists, copies its images into pkg/cover.
    Returns path to the package folder.
    """
    import shutil
    source = Path(source_images_folder)
    if not source.exists() or not source.is_dir():
        raise ValueError(f"Source folder not found: {source_images_folder}")
    if package_path is None:
        package_path = create_design_package(state)
    pkg = Path(package_path)
    pkg.mkdir(parents=True, exist_ok=True)
    # Copy inside images
    for ext in IMAGE_EXTENSIONS:
        for f in source.glob(f"*{ext}"):
            if f.is_file():
                shutil.copy2(f, pkg / f.name)
    # Copy image evaluations if present
    eval_file = source / IMAGE_EVALUATIONS_FILE
    if eval_file.exists() and eval_file.is_file():
        shutil.copy2(eval_file, pkg / IMAGE_EVALUATIONS_FILE)
    # Copy cover images to pkg/cover if provided
    if cover_source_folder:
        cover_src = Path(cover_source_folder)
        if cover_src.exists() and cover_src.is_dir():
            pkg_cover = pkg / "cover"
            pkg_cover.mkdir(parents=True, exist_ok=True)
            for ext in IMAGE_EXTENSIONS:
                for f in cover_src.glob(f"*{ext}"):
                    if f.is_file():
                        shutil.copy2(f, pkg_cover / f.name)
            cover_eval = cover_src / IMAGE_EVALUATIONS_FILE
            if cover_eval.exists() and cover_eval.is_file():
                shutil.copy2(cover_eval, pkg_cover / IMAGE_EVALUATIONS_FILE)
    # Update design.json
    state_copy = dict(state)
    state_copy["images_folder_path"] = str(pkg.resolve())
    state_copy["design_package_path"] = str(pkg.resolve())
    state_to_save = _prepare_state_for_json(state_copy)
    state_to_save["_metadata"] = {
        "saved_at": datetime.now().isoformat(),
        "saved_by": "save_design_package",
        "version": "1.0"
    }
    with open(pkg / DESIGN_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(state_to_save, f, indent=2, ensure_ascii=False, default=str)
    # Write book_config.json for Pinterest
    book_config = {
        "title": state.get("title", ""),
        "description": state.get("description", ""),
        "seo_keywords": state.get("seo_keywords", [])
    }
    with open(pkg / BOOK_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(book_config, f, indent=2, ensure_ascii=False)
    return str(pkg.resolve())


def _update_design_package_metadata(state: dict, package_path: str | Path) -> None:
    """Update design.json and book_config.json in existing package. No image copy."""
    pkg = Path(package_path)
    state_copy = dict(state)
    state_copy["images_folder_path"] = str(pkg.resolve())
    state_copy["design_package_path"] = str(pkg.resolve())
    state_to_save = _prepare_state_for_json(state_copy)
    state_to_save["_metadata"] = {"saved_at": datetime.now().isoformat(), "version": "1.0"}
    with open(pkg / DESIGN_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(state_to_save, f, indent=2, ensure_ascii=False, default=str)
    book_config = {
        "title": state.get("title", ""),
        "description": state.get("description", ""),
        "seo_keywords": state.get("seo_keywords", [])
    }
    with open(pkg / BOOK_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(book_config, f, indent=2, ensure_ascii=False)


def list_design_packages() -> List[Dict]:
    """List design packages (subfolders with design.json). Returns name, path, title, image_count, saved_at."""
    packages = []
    if not SAVED_DESIGN_PACKAGES_DIR.exists():
        return packages
    for folder in sorted(SAVED_DESIGN_PACKAGES_DIR.iterdir(), reverse=True):
        if not folder.is_dir():
            continue
        design_file = folder / DESIGN_JSON_FILE
        if not design_file.exists():
            continue
        try:
            with open(design_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            meta = data.get("_metadata", {})
            saved_at = meta.get("saved_at", folder.stat().st_mtime)
            if isinstance(saved_at, str):
                saved_at_str = datetime.fromisoformat(saved_at).strftime("%Y-%m-%d %H:%M:%S")
            else:
                saved_at_str = datetime.fromtimestamp(saved_at).strftime("%Y-%m-%d %H:%M:%S")
            image_count = sum(
                1 for f in folder.iterdir()
                if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
            )
            packages.append({
                "name": folder.name,
                "path": str(folder.resolve()),
                "title": data.get("title", "Untitled"),
                "image_count": image_count,
                "saved_at": saved_at_str,
            })
        except Exception as e:
            print(f"Error reading design package {folder}: {e}")
            continue
    return packages


def load_design_package(folder_path: str | Path) -> Optional[Dict]:
    """Load design.json from a design package folder. Sets images_folder_path and design_package_path."""
    path = Path(folder_path)
    design_file = path / DESIGN_JSON_FILE
    if not design_file.exists():
        return None
    try:
        with open(design_file, "r", encoding="utf-8") as f:
            state = json.load(f)
        state.pop("_metadata", None)
        state["images_folder_path"] = str(path.resolve())
        state["design_package_path"] = str(path.resolve())
        if "messages" not in state:
            state["messages"] = []
        if "status" not in state:
            state["status"] = "completed"
        return state
    except Exception as e:
        print(f"Error loading design package: {e}")
        return None


def delete_design_package(folder_path: str) -> bool:
    """Delete a design package folder. Only if under SAVED_DESIGN_PACKAGES_DIR."""
    try:
        import shutil
        path = Path(folder_path).resolve()
        base = SAVED_DESIGN_PACKAGES_DIR.resolve()
        path.relative_to(base)  # raises ValueError if not under base
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
            return True
        return False
    except (ValueError, Exception) as e:
        print(f"Error deleting design package: {e}")
        return False


def delete_saved_state(filepath: str) -> bool:
    """
    Delete a saved workflow state file.
    
    Args:
        filepath: Path to the saved state file
    
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        path = Path(filepath)
        if path.exists() and path.is_file():
            path.unlink()
            return True
        return False
    except Exception as e:
        print(f"Error deleting state file: {e}")
        return False
