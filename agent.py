#!/usr/bin/env python3
"""Android AI Agent - natural-language task execution."""
import argparse

ROUTES = {
    "open ": ("apps", "open"),
    "search ": ("apps", "search"),
    "alarm": ("settings", "alarm"),
    "dnd": ("settings", "dnd"),
    "send ": ("messages", "send"),
    "photo": ("camera", "snap"),
}

def route(text):
    text = text.lower().strip()
    for key, target in ROUTES.items():
        if text.startswith(key):
            return target
    return ("apps", "fallback")

def main():
    ap = argparse.ArgumentParser(prog="agent")
    ap.add_argument("prompt", nargs="*", default=["Open Chrome and search for Python"])
    p = " ".join(ap.prompt)
    mod, act = route(p)
    print(f"[agent] routing '{p}' -> plugins.{mod}.run(action={act})")
    try:
        m = __import__("plugins." + mod, fromlist=["run"])
        m.run(action=act, prompt=p)
    except ModuleNotFoundError as e:
        print(f"[agent] plugin not installed: {e}")

if __name__ == "__main__":
    main()