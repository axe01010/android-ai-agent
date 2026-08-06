"""settings plugin — alarms, do-not-disturb, silent, brightness, volume and wifi.

Every action parses its argument from the free-text prompt (when a value is
expected, e.g. a brightness %) and returns a structured dict echoing the value
a real integration would push to ``settings put`` / ``svc`` / the status bar.
"""

from __future__ import annotations

import datetime
import re
from typing import Any

from plugins.base import Plugin


class SettingsPlugin(Plugin):
    """Read and change device settings (alarms, DND, silent, brightness, volume)."""

    name = "settings"
    description = "Set alarms and adjust device settings (DND, silent, brightness, volume, wifi)."
    capabilities = ["alarm", "dnd", "silent", "brightness", "volume", "wifi", "time"]

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        action = context.get("action", "dnd")
        prompt = context.get("prompt", "")
        if action == "alarm":
            return self._alarm(prompt)
        if action == "dnd" or action == "silent":
            return self._dnd(prompt)
        if action == "brightness":
            return self._brightness(prompt)
        if action == "volume":
            return self._volume(prompt)
        if action == "wifi":
            return self._wifi(prompt)
        if action == "time":
            return self._time()
        return {"status": "error", "error": f"unknown settings action: {action}"}

    # -- actions ---------------------------------------------------------------
    def _alarm(self, prompt: str) -> dict[str, Any]:
        match = re.search(r"(\d{1,2})[:.\-]?\s?(\d{2})", prompt)
        if not match:
            return {"status": "error", "message": "no alarm time found (e.g. 'set alarm 7:30')"}
        hh, mm = int(match.group(1)), int(match.group(2))
        if not (0 <= hh < 24 and 0 <= mm < 60):
            return {"status": "error", "message": f"invalid time: {match.group(0)}"}
        return {"status": "ok", "action": "alarm", "time": f"{hh:02d}:{mm:02d}",
                "command": f"alarm set {hh:02d}:{mm:02d}"}

    def _dnd(self, prompt: str) -> dict[str, Any]:
        enabled = not re.search(r"\b(off|disable|stop|cancel)\b", prompt, re.I)
        return {"status": "ok", "action": "dnd", "enabled": enabled,
                "command": "settings put global zen_mode " + ("1" if enabled else "0")}

    def _brightness(self, prompt: str) -> dict[str, Any]:
        match = re.search(r"(\d{1,3})\s*%?", prompt)
        level = int(match.group(1)) if match else 50
        level = max(0, min(level, 100))
        return {"status": "ok", "action": "brightness", "level": level,
                "command": f"settings put system screen_brightness {level // 100 * 255}"}

    def _volume(self, prompt: str) -> dict[str, Any]:
        match = re.search(r"(\d{1,3})\s*%?", prompt)
        level = int(match.group(1)) if match else 50
        level = max(0, min(level, 100))
        return {"status": "ok", "action": "volume", "level": level,
                "command": f"media volume to {level}%"}

    def _wifi(self, prompt: str) -> dict[str, Any]:
        on = not re.search(r"\b(off|disable)\b", prompt, re.I)
        return {"status": "ok", "action": "wifi", "enabled": on,
                "command": "svc wifi " + ("enable" if on else "disable")}

    def _time(self) -> dict[str, Any]:
        return {"status": "ok", "action": "time",
                "now": datetime.datetime.now().strftime("%H:%M:%S")}


# Backwards-compatible functional entry point.
def run(action: str, prompt: str, **ctx: Any) -> dict[str, Any]:
    """Backwards-compatible functional entry point."""
    return SettingsPlugin().execute({"action": action, "prompt": prompt, **ctx})