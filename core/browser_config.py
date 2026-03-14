"""Browser slots configuration and connection testing.

This module defines up to four browser "slots" that can be configured via the
Streamlit UI. Each slot has:
    - role:   midjourney | pinterest | canva | unused
    - port:   Chrome DevTools Protocol port (int)
    - label:  optional human-friendly name

Configuration is persisted to a small JSON file under the project output
directory so it survives app restarts.
"""

from __future__ import annotations

import json
import socket
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, TypedDict

from config import OUTPUT_DIR

BrowserRole = Literal["midjourney", "pinterest", "canva", "unused"]


class BrowserSlotDict(TypedDict):
    """JSON-serializable representation of a browser slot."""

    id: str
    role: BrowserRole
    port: int
    label: str


@dataclass
class BrowserSlot:
    """In-memory representation of a browser slot."""

    id: str
    role: BrowserRole
    port: int
    label: str = ""

    def to_dict(self) -> BrowserSlotDict:
        data = asdict(self)
        # Dataclasses + Literal are JSON-friendly already
        return BrowserSlotDict(**data)  # type: ignore[arg-type]

    @classmethod
    def from_dict(cls, data: BrowserSlotDict) -> "BrowserSlot":
        return cls(**data)


CONFIG_DIR = OUTPUT_DIR / "config"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
SLOTS_CONFIG_FILE = CONFIG_DIR / "browser_slots.json"


def _default_slots() -> list[BrowserSlot]:
    """Return four default slots.

    - slot1: midjourney on 9222
    - slot2: pinterest on 9223
    - slot3: canva on 9224
    - slot4: unused on 9225
    """
    return [
        BrowserSlot(id="slot1", role="midjourney", port=9222, label="Midjourney"),
        BrowserSlot(id="slot2", role="pinterest", port=9223, label="Pinterest 1"),
        BrowserSlot(id="slot3", role="canva", port=9224, label="Canva 1"),
        BrowserSlot(id="slot4", role="unused", port=9225, label="Spare"),
    ]


def load_slots() -> list[BrowserSlot]:
    """Load browser slots from JSON file or return defaults if missing/invalid."""
    if not SLOTS_CONFIG_FILE.exists():
        return _default_slots()
    try:
        with open(SLOTS_CONFIG_FILE, encoding="utf-8") as f:
            raw = json.load(f) or []
        slots: list[BrowserSlot] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                slot_dict: BrowserSlotDict = {
                    "id": str(item.get("id", "")),
                    "role": item.get("role", "unused"),
                    "port": int(item.get("port", 0)),
                    "label": str(item.get("label", "")),
                }  # type: ignore[assignment]
                slots.append(BrowserSlot.from_dict(slot_dict))
            except Exception:
                continue
        if not slots:
            return _default_slots()
        # Ensure we always have exactly four slots by padding/truncating.
        while len(slots) < 4:
            slots.append(_default_slots()[len(slots)])
        if len(slots) > 4:
            slots = slots[:4]
        return slots
    except Exception:
        return _default_slots()


def save_slots(slots: list[BrowserSlot]) -> None:
    """Persist browser slots to JSON file."""
    data = [slot.to_dict() for slot in slots]
    with open(SLOTS_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


class ValidationError(Exception):
    """Raised when a slots configuration is invalid."""


def validate_slots(slots: list[BrowserSlot]) -> None:
    """Validate roles, ports, and uniqueness constraints.

    Rules:
    - Exactly one slot may have role 'midjourney'.
    - Ports must be positive integers.
    - Ports must be unique across non-unused slots.
    """
    if len(slots) != 4:
        raise ValidationError("Expected exactly 4 browser slots.")

    midjourney_slots = [s for s in slots if s.role == "midjourney"]
    if len(midjourney_slots) == 0:
        raise ValidationError("At least one slot must be configured as 'midjourney'.")
    if len(midjourney_slots) > 1:
        raise ValidationError("Only one slot can have role 'midjourney'.")

    used_ports: dict[int, str] = {}
    for slot in slots:
        if slot.role == "unused":
            continue
        if slot.port <= 0:
            raise ValidationError(f"Slot {slot.id}: port must be a positive integer.")
        if slot.port in used_ports:
            other = used_ports[slot.port]
            raise ValidationError(
                f"Port {slot.port} is used by both {other} and {slot.id}. Ports must be unique."
            )
        used_ports[slot.port] = slot.id


def test_connection(port: int, timeout_sec: float = 1.0) -> tuple[bool, str]:
    """Best-effort check that something is listening on the given port.

    We avoid importing heavy browser or Playwright dependencies here.
    Instead, we attempt a TCP connection to localhost:port. If it succeeds,
    we report 'connected', otherwise we return False with a short reason.
    """
    if port <= 0:
        return False, "Invalid port"
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout_sec)
    try:
        sock.connect(("127.0.0.1", port))
        return True, "Connection successful"
    except OSError as e:
        return False, f"Connection failed: {e}"
    finally:
        try:
            sock.close()
        except Exception:
            pass


def check_browser_connection(port: int, timeout_sec: float = 1.0) -> dict[str, object]:
    """Check if a browser is listening on the given CDP port.

    Returns a dict with: connected (bool), port (int), error (str | None).
    Use get_port_for_role(role) to obtain the port for a given slot role.
    """
    if port <= 0:
        return {"connected": False, "port": port, "error": "Invalid port"}
    ok, msg = test_connection(port, timeout_sec)
    if ok:
        return {"connected": True, "port": port, "error": None}
    return {"connected": False, "port": port, "error": msg}


def get_slots_summary() -> list[dict[str, str]]:
    """Return a lightweight summary for UI display."""
    slots = load_slots()
    summary: list[dict[str, str]] = []
    for s in slots:
        summary.append(
            {
                "id": s.id,
                "role": s.role,
                "port": str(s.port),
                "label": s.label or "",
            }
        )
    return summary


def get_port_for_role(role: str) -> int:
    """Return the port of the first slot with the given role.
    Used so Canva/Pinterest tabs check the correct browser instance.
    Falls back to 9222 if no slot has that role.
    """
    slots = load_slots()
    for slot in slots:
        if slot.role == role:
            return slot.port
    return 9222

