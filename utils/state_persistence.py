"""Utilities for saving and loading workflow state."""

import json
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime


# Directory for saved states
SAVED_STATES_DIR = Path("./saved_designs")
SAVED_STATES_DIR.mkdir(exist_ok=True)


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
    state_to_save = {}
    for key, value in state.items():
        # Skip non-serializable items or convert them
        try:
            json.dumps(value)  # Test if serializable
            state_to_save[key] = value
        except (TypeError, ValueError):
            # Skip non-serializable items (like LangChain messages)
            if key not in ["messages"]:  # Skip messages as they're complex objects
                state_to_save[key] = str(value)
    
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

