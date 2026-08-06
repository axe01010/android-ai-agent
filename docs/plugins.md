# Writing Plugins

This guide walks through authoring a plugin for **Android AI Agent** in both
supported styles: *function style* (fast, single-file) and *class style*
(richer, stateful). A short, useful plugin takes about a dozen lines.

## The contract

A plugin is a Python module in the `plugins/` package. Discovery
(`plugins.discover`) picks it up automatically at import time. To actually
*receive prompts*, a phrase in the router must map to
`(your_plugin_key, your_action)`.

Every plugin ultimately returns a **dict**:

```python
{"status": "ok", "action": "open", "target": "chrome", ...}
```

The agent loop (and CLI) JSON-serialises it onward.

## Style 1 — function plugin (fast)

Defined a module named after the plugin key with a `run` function.

```python
# plugins/notes.py
"""notes plugin — append/open/read quick notes on the device."""

def run(action, prompt, ctx=None):
    note = prompt.replace("note", "", 1).strip() or "(empty)"
    if action == "add":
        return {"status": "ok", "action": "add", "note": note,
                "stored_in": "~/.aq_notes"}
    if action == "read":
        return {"status": "ok", "action": "read", "note": note}
    return {"status": "error", "error": f"unknown notes action: {action}"}
```

Now tell the router a phrase reaches it. Two options:

- Add a tuple to `DEFAULT_ROUTES` in `agent.py`:
  ```python
  ("note ", "notes", "add"),
  ```
- Or register programmatically:
  ```python
  from plugins import register
  register("notes", "plugins.notes", "Quick device notes.",
           capabilities=["add", "read"])
  ```

## Style 2 — class plugin (recommended)

Subclass `Plugin`, set `name`, `description`, `capabilities`, and implement
`execute(context)`.

```python
# plugins/notes.py
from plugins.base import Plugin

class NotesPlugin(Plugin):
    name = "notes"
    description = "Add, read and clear quick notes."
    capabilities = ["add", "read", "clear"]

    def execute(self, context):
        action = context["action"]
        prompt = context["prompt"]
        if action == "add":
            return self._add(prompt)
        if action == "clear":
            return {"status": "ok", "action": "clear"}
        return self._read(prompt)

    def _add(self, prompt):
        note = self.args_after(prompt, "note").strip() or "(empty)"
        return {"status": "ok", "action": "add", "note": note}

    def _read(self, prompt):
        return {"status": "ok", "action": "read", "note": "no notes yet"}
```

Advantages over the function style: per-plugin `self.state`, lifecycle hooks
(`on_load`/`on_unload`), config access via `self._cfg(context, ...)`, and the
`args_after` argument-parsing helper.

## Reading config & history

`context` holds `config`, `prompt`, `action`, and `history`. To read a setting
with a default:

```python
dry = self._cfg(context, "execution.dry_run", False)
search = self._cfg(context, "plugins.notes.path", "~/.aq_notes")
```

To peek at prior dispatches:

```python
for entry in context.get("history", [])[-5:]:
    log(entry["prompt"], entry["action"])
```

## Registering a custom plugin live (no filesystem)

If your plugin lives outside `plugins/` (e.g. an app you build on top), register
it in the default registry:

```python
from plugins import register

register(
    key="weather",
    module="my_app.weather_plugin",           # importable path
    description="Report the weather.",
    capabilities=["weather"],
)
```

`discover()` and `load()` both honour the registry, so routing works the same.

## Router wiring cheat-sheet

| phrase             | plugin   | action    | example prompt           |
|--------------------|----------|-----------|--------------------------|
| `open ` / `launch `| `apps`   | `open`  | "open Chrome"            |
| `search `        | `apps`   | `search`| "search python tutorials" |
| `set an alarm`   | `settings`| `alarm` | "set an alarm for 7:30" |
| `do not disturb` | `settings`| `dnd`  | "dnd"                     |
| `brightness`     | `settings`| `brightness` | "brightness to 80"  |
| `send a text`    | `messages`| `send` | "send a text to 555-0100" |
| `take a photo`   | `camera` | `snap`   | "take a photo"              |

Add your own phrases to `DEFAULT_ROUTES` in order of specificity.

## Checklist for a good plugin

- [ ] Docstring with a one-line purpose.
- [ ] Returns only dicts (or `None`).
- [ ] Handles an unknown action gracefully (doesn't raise).
- [ ] Reads config via `context["config"]`, not `os.getenv` directly.
- [ ] Add a `--list`-friendly `description` and `capabilities`.
- [ ] Keep it offline-first unless a bridge is explicitly configured.