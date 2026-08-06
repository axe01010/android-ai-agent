#!/usr/bin/env python3
"""CLI demo for android-ai-agent.

Shows how to drive the router programmatically (batch / headless), keep a
session history, and print structured results — the same path the interactive
REPL uses under the hood.

Run:
    python examples/cli_demo.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import do_step, load_config, _print_registry

SAMPLE_PROMPTS = [
    "open Chrome",
    "set an alarm for 07:30",
    "turn on wifi",
    "take a photo",
    "record a video for 15 seconds",
    "do not disturb",
    "send a text to Alex saying on my way",
    "what time is it",
    "flip the table",          # -> apps.fallback
]


def main() -> int:
    config = load_config()
    history: list[dict] = []

    _print_registry(config)
    print("\n━━━ Running %d sample prompts ━━━\n" % len(SAMPLE_PROMPTS))

    failures = 0
    for prompt in SAMPLE_PROMPTS:
        result = do_step(prompt, config, history)
        status = result.get("status")
        if status == "error":
            failures += 1
        print(json.dumps(result, indent=2))

    print("\n━━━ Session history ━━━")
    for entry in history:
        print(f"  {'OK ' if entry['status'] == 'ok' else 'ERR'} "
              f"{entry['plugin']:<8}.{entry['action']:<10} -> "
              f"{entry['prompt'][:50]!r}")

    print(f"\n{len(history)} steps, {failures} error(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())