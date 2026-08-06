#!/usr/bin/env python3
"""Example: drive the agent programmatically (batch mode).

Shows how to reuse the agent's routing engine from another script via the
``do_step`` public API. Run with::

    python examples/batch_demo.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import load_config  # noqa: E402
from agent import do_step  # noqa: E402


TASKS = [
    "Open Chrome",
    "set an alarm for 7:30",
    "take a photo of the whiteboard",
    "send a text to 555-0123 saying I am running late",
    "turn on wifi",
    "this sentence has no obvious intent",
]


def main() -> None:
    config = load_config()
    history: list[dict] = []
    print(f"Processing {len(TASKS)} tasks against default config\n")
    for i, task in enumerate(TASKS, 1):
        result = do_step(task, config, history)
        print(f"[{i}] {task!r}")
        print(f"    -> plugin={result.get('plugin')} action={result.get('action')} "
              f"status={result.get('status')}")
        detail = {k: v for k, v in result.items()
                  if k not in ("plugin", "action", "status")}
        if detail:
            for k, v in detail.items():
                print(f"       {k}={v}")
    print(f"\nSession history: {len(history)} entries logged.")


if __name__ == "__main__":
    main()