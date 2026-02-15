"""Core shared infrastructure."""

from core.state import ColoringBookState
from core.persistence import (
    save_workflow_state,
    load_workflow_state,
    list_saved_states,
    delete_saved_state,
)

__all__ = [
    "ColoringBookState",
    "save_workflow_state",
    "load_workflow_state",
    "list_saved_states",
    "delete_saved_state",
]
