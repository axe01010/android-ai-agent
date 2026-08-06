#!/usr/bin/env python3
"""Example: writing a custom plugin (function style) and loading it.

This registers a "weather" plugin in the default in-memory registry and asks
the agent core to route to it. It demonstrates the three steps every new
capability goes through:

    1. declare a ``run(action, prompt, ctx)`` callable,
    2. register it with ``plugins.register(...)``,
    3. let ``agent.do_step`` dispatch to it on a keyword match.

Run::

    python examples/custom_plugin.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import load_config  # noqa: E402
from agent import do_step  # noqa: E402


def run(action: str, prompt: str, ctx: dict | None = None, **kwargs) -> dict:
    """Function-style plugin: reports a (fake) weather reading for a city."""
    import re as _re
    m = _re.search(r"[Ii]n\s+([A-Z][A-Za-z]*(?:\s[A-Za-z]+)*)", prompt)
    city = m.group(1).strip() if m else (prompt.replace("weather", "").strip() or "your city")
    return {"status": "ok", "city": city, "celsius": 21, "condition": "sunny"}


def main() -> None:
    from plugins import register

    # Register the plugin so discover()/dispatch both see it.
    register(key="weather", module="examples.custom_plugin",
             description="Report the current weather for a city.",
             capabilities=["weather"])

    config = load_config()
    history: list[dict] = []

    # Add a phrase route so "weather in ...", "weather" reach the plugin.
    custom_routes = [("weather", "weather", "weather")]

    result = do_step("What is the weather in Austin?", config, history,
                     routes=custom_routes)
    print("Custom-plugin dispatch result:")
    for k, v in result.items():
        print(f"  {k}: {v}")

    if result.get("city") == "Austin":
        print("\nOK — your function-style plugin was discovered and dispatched to.")
    else:
        print("\nTip: the route above is an example; adjust phrases to your needs.")


if __name__ == "__main__":
    main()