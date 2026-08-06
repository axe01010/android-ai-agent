"""apps plugin — launch, search and install applications on the device.

Class-based :class:`~plugins.base.Plugin` implementation. A small in-memory app
registry stands in for the device launcher; on a real device each entry would
resolve through ``adb shell am start`` or the Android intent resolver.
"""

from __future__ import annotations

from typing import Any

from plugins.base import Plugin

# A tiny, hard-coded app registry standing in for the device launcher.
KNOWN_APPS: dict[str, dict[str, str]] = {
    "chrome":   {"package": "com.android.chrome", "activity": "MainActivity"},
    "gmail":    {"package": "com.google.android.gm", "activity": "MainActivity"},
    "youtube":  {"package": "com.google.android.youtube", "activity": ".MainActivity"},
    "maps":     {"package": "com.google.android.apps.maps", "activity": ".MainActivity"},
    "camera":   {"package": "com.google.android.GoogleCamera", "activity": ".Main"},
    "settings": {"package": "com.android.settings", "activity": ".Settings"},
    "spotify":  {"package": "com.spotify.music", "activity": "MainActivity"},
    "twitter":  {"package": "com.twitter.android", "activity": "MainActivity"},
    "whatsapp": {"package": "com.whatsapp", "activity": "MainActivity"},
    "vscode":   {"package": "com.taylorhong.codeeditor", "activity": "MainActivity"},
}


def _normalise(name: str) -> str:
    return name.strip().lower().replace(" ", "")


class AppsPlugin(Plugin):
    """Launch, search, install, list and stop applications."""

    name = "apps"
    description = "Launch, search, install and stop applications on the device."
    capabilities = ["open", "search", "install", "list", "kill", "fallback"]

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        action = context.get("action", "open")
        prompt = context.get("prompt", "")
        if action == "open":
            return self._open(prompt)
        if action == "search":
            return self._search(prompt)
        if action == "install":
            return self._install(prompt)
        if action == "list":
            return self._list()
        if action == "kill":
            return self._kill(prompt)
        if action == "fallback":
            return self._fallback(prompt)
        return {"status": "error", "error": f"unknown apps action: {action}"}

    # -- actions ----------------------------------------------------------------
    def _open(self, prompt: str) -> dict[str, Any]:
        target = (self.args_after(prompt, "open").split(" and ")[0] or "").strip()
        app = _normalise(target)
        if not app:
            return {"status": "error", "message": "no app name provided"}
        entry = KNOWN_APPS.get(app)
        if entry is None:
            suggestions = [_normalise(k) for k in KNOWN_APPS if _normalise(k).startswith(app)]
            return {"status": "error",
                    "message": f"unknown app '{app}' (suggest: {suggestions or 'none'})"}
        if entry["activity"].startswith("."):
            component = f"{entry['package']}/{entry['package']}{entry['activity']}"
        else:
            component = f"{entry['package']}/{entry['package']}.{entry['activity']}"
        return {"status": "ok", "action": "open", "app": app,
                "command": f"am start -a android.intent.action.MAIN -n {component}",
                "detail": f"launched {app}"}

    def _search(self, prompt: str) -> dict[str, Any]:
        engine = getattr(self, "search_engine", "https://www.google.com/search?q=")
        query = (self.args_after(prompt, "search web for")
                 or self.args_after(prompt, "google")
                 or self.args_after(prompt, "search"))
        if not query:
            return {"status": "error", "message": "no search query provided"}
        return {"status": "ok", "action": "search", "query": query,
                "url": engine + query.replace(" ", "+")}

    def _install(self, prompt: str) -> dict[str, Any]:
        pkg = self.args_after(prompt, "install").strip()
        if not pkg:
            return {"status": "error", "message": "no package given to install"}
        return {"status": "ok", "action": "install", "package": pkg,
                "command": f"adb install -r {pkg}.apk"}

    def _list(self) -> dict[str, Any]:
        return {"status": "ok", "action": "list", "installed": sorted(KNOWN_APPS.keys())}

    def _kill(self, prompt: str) -> dict[str, Any]:
        target = self.args_after(prompt, "kill").strip() or prompt.strip()
        package = KNOWN_APPS.get(_normalise(target), {}).get("package", target)
        return {"status": "ok", "action": "kill", "app": target,
                "command": f"am force-stop {package}"}

    def _fallback(self, prompt: str) -> dict[str, Any]:
        return {"status": "ok", "action": "fallback",
                "detail": "No specific intent matched; suggested: open an app or ask for help. (input: %s)"
                          % prompt[:60]}


# Keep the original functional entry point working for callers that import it.
def run(action: str, prompt: str, **ctx: Any) -> dict[str, Any]:
    """Backwards-compatible functional entry point."""
    return AppsPlugin().execute({"action": action, "prompt": prompt, **ctx})