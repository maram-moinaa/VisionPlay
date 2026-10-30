"""JSON messages sent from the tracking engine to browser clients."""

from typing import Any

from config import DWELL_DURATION_SECONDS

def cursor_message(x: float, y: float) -> dict[str, Any]:
    return {"type": "cursor", "x": x, "y": y}


def gesture_message(name: str) -> dict[str, Any]:
    return {"type": "gesture", "name": name}


def status_message(camera: str, tracking: bool, message: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "status",
        "camera": camera,
        "tracking": tracking,
        "dwell_seconds": DWELL_DURATION_SECONDS,
    }
    if message is not None:
        result["message"] = message
    return result
