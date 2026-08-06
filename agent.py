#!/usr/bin/env python3
"""Android AI Agent — natural-language task execution on your device.

A small, privacy-first agent that routes free-form prompts to a registry of
*plugins* (apps, settings, messages, camera, ...), enforces configuration,
logs a session history and reports every decision transparently — all without
sending data to the cloud.

Quick start
-----------
    python agent.py "Open Chrome"
    python agent.py "send a text to 5551234567 saying I'm on my way"
    python agent.py --list                 # show plugins & default routes
    python agent.py --dry-run --verbose    # see what would happen, run nothing
    python agent.py                        # start the interactive REPL

Add your own capabilities by dropping a plugin into ``plugins/`` — see
``plugins/base.py`` for the interface and ``docs/writing-plugins.md`` for a
guide. Keep this entry point callable exactly as before: it always resolves a
prompt to ``plugins.<mod>.run(action=...)``.
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import load_config  # noqa: E402
from plugins import discover, load, run  # noqa: E402

logger = logging.getLogger("agent")

# ---------------------------------------------------------------------------
# Keyword routing — ordered list of (phrase, plugin, action). Order matters:
# the *first* phrase found as a substring wins, so put specific phrases before
# generic ones (e.g. "take a photo" before "photo").
# ---------------------------------------------------------------------------
DEFAULT_ROUTES: list[tuple[str, str, str]] = [
    # camera
    ("take a photo", "camera", "snap"),
    ("take picture", "camera", "snap"),
    ("snap", "camera", "snap"),
    ("record a video", "camera", "video"),
    ("record video", "camera", "video"),
    ("video", "camera", "video"),
    ("flash on", "camera", "flash"),
    ("flash off", "camera", "flash"),   # routed to camera; action parses "off"
    # settings
    ("set an alarm", "settings", "alarm"),
    ("set alarm", "settings", "alarm"),
    ("alarm", "settings", "alarm"),
    ("do not disturb", "settings", "dnd"),
    ("silent", "settings", "dnd"),
    ("dnd", "settings", "dnd"),
    ("brightness", "settings", "brightness"),
    ("volume", "settings", "volume"),
    ("turn on wifi", "settings", "wifi"),
    ("turn off wifi", "settings", "wifi"),
    ("wifi", "settings", "wifi"),
    ("what time", "settings", "time"),
    ("what's the time", "settings", "time"),
    ("time", "settings", "time"),
    # messages
    ("send a text", "messages", "send"),
    ("send an sms", "messages", "send"),
    ("send a message", "messages", "send"),
    ("message ", "messages", "send"),
    ("text ", "messages", "send"),
    ("send ", "messages", "send"),
    ("reply ", "messages", "reply"),
    ("read messages", "messages", "read"),
    # apps
    ("open ", "apps", "open"),
    ("launch ", "apps", "open"),
    ("search ", "apps", "search"),
    ("list apps", "apps", "list"),
    ("kill ", "apps", "kill"),
]


def route(text: str, routes: list[tuple[str, str, str]] | None = None,
          fallback_plugin: str = "apps", fallback_slot: str = "fallback") -> tuple[str, str]:
    """Map a free-form prompt to a ``(plugin_key, action)`` target.

    The first configured phrase found in the (lower-cased) text wins. When
    nothing matches we return the fallback so the agent can always answer
    instead of crashing. ``routes`` overrides the built-in :data:`DEFAULT_ROUTES`.
    """
    text = (text or "").strip().lower()
    table = routes if routes is not None else DEFAULT_ROUTES
    for phrase, plug, slot in table:
        if phrase.strip() and phrase.strip() in text:
            return plug, slot
    return fallback_plugin, fallback_slot


def _effective_registry(config: dict[str, Any]) -> dict[str, Any]:
    """Discover plugins, honouring ``config.plugins.disable`` / ``auto_discover``."""
    if not config.get("plugins", {}).get("auto_discover", True):
        return {}
    registry = discover("plugins")
    disabled = set(config.get("plugins", {}).get("disable", []))
    return {k: v for k, v in registry.items() if k not in disabled}


def do_step(prompt: str, config: dict[str, Any],
            history: list[dict[str, Any]] | None = None,
            routes: list[tuple[str, str, str]] | None = None) -> dict[str, Any]:
    """Route and execute a single prompt; append the outcome to ``history``.

    ``routes`` overrides :data:`DEFAULT_ROUTES` for programmatic callers.
    """
    history = history if history is not None else []
    router = config.get("router", {})

    plugin_key, action = route(
        prompt,
        routes=routes,
        fallback_plugin=router.get("unknown_action", "apps"),
        fallback_slot=router.get("fallback_slot", "fallback"),
    )

    # Never dispatch to a disabled/unknown plugin — bounce to the catch-all.
    known = set(discover("plugins").keys())
    disabled = set(config.get("plugins", {}).get("disable", []))
    if plugin_key not in known or plugin_key in disabled:
        plugin_key = router.get("unknown_action", "apps")
        action = router.get("fallback_slot", "fallback")

    try:
        impl = load(plugin_key, "plugins")
    except (ImportError, AttributeError) as exc:
        logger.error("plugin load failed for '%s': %s", plugin_key, exc)
        return {"status": "error", "plugin": plugin_key, "error": str(exc)}

    result = run(impl, action, prompt, config=config, history=history)
    result.setdefault("plugin", plugin_key)
    result.setdefault("action", action)
    history.append({
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "prompt": prompt, "plugin": plugin_key, "action": action,
        "status": result.get("status", "ok"),
    })
    return result


# -- REPL -------------------------------------------------------------------
def repl(config: dict[str, Any], history: list[dict[str, Any]]) -> None:
    """Interactive REPL over the router, sharing one session history."""
    print("🤖 Android AI Agent — type 'help', 'list', 'routes' or 'exit'.")
    while True:
        try:
            line = input("agent> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            break
        if not line:
            continue
        if line.lower() in ("exit", "quit", "q"):
            break
        if line.lower() in ("help", "?"):
            print("Commands: exit/quit, help/?, list, routes. Otherwise type a task, e.g. 'open Chrome'.")
            continue
        if line.lower() == "list":
            _print_registry(config)
            continue
        if line.lower() == "routes":
            _print_routes()
            continue
        print(json.dumps(do_step(line, config, history), indent=2))


# ---------------------------------------------------------------------------
# Printers
# ---------------------------------------------------------------------------
def _print_registry(config: dict[str, Any]) -> None:
    specs = discover("plugins")
    disabled = set(config.get("plugins", {}).get("disable", []))
    if not specs:
        print("(no plugins discovered)")
        return
    print(f"{'PLUGIN':<10} {'CAPABILITIES':<44} STATUS")
    for key in sorted(specs):
        spec = specs[key]
        status = "disabled" if key in disabled else "ready"
        caps = ", ".join(spec.capabilities) if spec.capabilities else "-"
        print(f"{key:<10} {caps:<44} {status}")
    print()
    _print_routes()


def _print_routes() -> None:
    print("Default routes (phrase -> plugin.action):")
    for phrase, plug, slot in DEFAULT_ROUTES:
        print(f"  {phrase.strip():<22} -> {plug}.{slot}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="agent",
        description="Android AI Agent — control your device with natural language.",
        epilog="Examples:\n"
               "  python agent.py \"Open Chrome\"\n"
               "  python agent.py --list\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("prompt", nargs="*", default=[],
                    help="task to execute; omit for interactive mode")
    ap.add_argument("-i", "--interactive", action="store_true", help="force the REPL")
    ap.add_argument("-l", "--list", action="store_true", help="list plugins & routes, then exit")
    ap.add_argument("--config", default=None, help="path to a config.yaml/config.json")
    ap.add_argument("--dry-run", action="store_true", help="set execution.dry_run for this run")
    ap.add_argument("-v", "--verbose", action="count", default=0, help="-v info, -vv debug")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose >= 2 else (logging.INFO if args.verbose >= 1 else logging.WARNING),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    config = load_config(args.config)
    if args.dry_run:
        config.setdefault("execution", {})["dry_run"] = True
    history: list[dict[str, Any]] = []

    if args.list:
        _print_registry(config)
        return 0

    if args.prompt and not args.interactive:
        text = " ".join(args.prompt)
        result = do_step(text, config, history)
        print(json.dumps(result, indent=2))
        return 0 if result.get("status") in (None, "ok") else 1

    repl(config, history)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())