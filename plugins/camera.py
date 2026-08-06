"""camera plugin — take photos, record video and toggle the flash.

In mock / dry-run mode we infer intent (front vs rear, video clips, flash
state) and log it; over a ``termux-api`` or ``adb`` bridge this maps to a real
capture request.
"""

from __future__ import annotations

import datetime
import random
import re
from typing import Any

from plugins.base import Plugin


class CameraPlugin(Plugin):
    """Take photos, record short videos and toggle the flash."""

    name = "camera"
    description = "Take photos, record short videos and toggle the flash."
    capabilities = ["snap", "video", "flash"]

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        action = context.get("action", "snap")
        prompt = context.get("prompt", "")
        if action == "video":
            return self._video(prompt)
        if action == "flash":
            return self._flash(prompt)
        return self._snap(prompt)

    def _snap(self, prompt: str) -> dict[str, Any]:
        facing = "front" if re.search(r"front|selfie", prompt, re.I) else "rear"
        shot_id = f"IMG_{datetime.datetime.now():%Y%m%d_%H%M%S}_{random.randint(100, 999)}"
        return {"status": "ok", "action": "snap", "facing": facing, "shot_id": shot_id,
                "note": "captured (mock bridge: no bytes persisted)"}

    def _video(self, prompt: str) -> dict[str, Any]:
        match = re.search(r"(\d+)\s*(?:sec|seconds|s)", prompt, re.I)
        seconds = int(match.group(1)) if match else 10
        return {"status": "ok", "action": "video", "duration_seconds": seconds, "facing": "rear"}

    def _flash(self, prompt: str) -> dict[str, Any]:
        on = not re.search(r"off|disable", prompt, re.I)
        return {"status": "ok", "action": "flash", "enabled": on}


def run(action: str, prompt: str, **ctx: Any) -> dict[str, Any]:
    """Backwards-compatible functional entry point."""
    return CameraPlugin().execute({"action": action, "prompt": prompt, **ctx})