# Architecture

This document explains how **Android AI Agent** is put together: the router,
the plugin registry, the execution context, and the layered config flow. It is
written for anyone extending the engine.

## Overview

The agent is deliberately small and embodies a single idea:

> **Turn a natural-language prompt into a *known* (plugin, action) pair, then
> execute it against a device bridge.**

Everything else — config, history, dry-run, plugin discovery — is supporting
machinery around that core. Keeping that core simple is what makes the project
easy to extend and audit.

```
                        ┌──────────────────────────────┐
   "open Chrome"  ────▶ │  router.route(prompt)        │
                        │  matches phrase list         │
                        └──────────────┬───────────────┘
                                       │ (plugin="apps", action="open")
                                       ▼
                        ┌──────────────────────────────┐
                        │  plugins.discover()          │  keys: [apps, settings,
                        │  registry of PluginSpecs     │        messages, camera]
                        └──────────────┬───────────────┘
                                       │ load(plugin)
                                       ▼
                        ┌──────────────────────────────┐
                        │  plugin.run(impl, action,    │
                        │         prompt, config,      │
                        │         history)             │
                        └──────────────┬───────────────┘
                                       │ structured dict
                                       ▼
                        ┌──────────────────────────────┐
                        │  do_step()                   │
                        │  *. append to history        │
                        │  *. report / return JSON      │
                        └──────────────────────────────┘
```

## 2. The router: `route()`

`agent.route(text, routes=..., fallback...)` maps a string to a
`(plugin, action)` tuple. Routing is **ordered and substring-based**:

- The phrase list (`DEFAULT_ROUTES`) is evaluated top to bottom.
- The first phrase contained in `text` wins.
- `routes` ordering matters — put more specific phrases before general ones.

```python
DEFAULT_ROUTES = [
    ("take a photo",   "camera",   "snap"),
    ("open ",          "apps",     "open"),
    # ...more
]
```

`do_step` uses this to select a target and falls back to the router's
catch-all (`unknown_action` / `fallback_slot`) when nothing matches, so the
agent is never speechless.

## 3. The plugin registry: `plugins/base.py`

Two abstractions:

- **`PluginSpec`** — a lightweight metadata record (key, module, description,
  capabilities, has_run). Used for introspection (`--list`) without importing
  plugin logic.
- **`Registry`** — an in-memory store (module-level `DEFAULT_REGISTRY`) where
  plugins can be registered programmatically via `plugins.register(...)`.

Discovery is lazy: `plugins.discover("plugins")` walks the package with
`pkgutil.iter_modules` and builds `PluginSpec`s. Loading is separate: `load(key)`
imports the module and returns an instantiated `Plugin` (class style) or its
plain `run()` function (function style).

### Plugin invocation contract

`plugins.run(plugin, action, prompt, config=..., **ctx)` normalises a plugin's
return value. Every plugin must return a **dict** (or `None`, which is coerced
to `{"status": "ok"}`). Errors are caught and reported as
`{"status": "error", "error": ...}` so a bad plugin can never crash the loop.

## 4. Execution context

Every plugin `execute(context)` receives a context dict with at least:

| key      | meaning                                        |
|----------|------------------------------------------------|
| `action` | the slot to perform (e.g. `"open"`)            |
| `prompt` | the raw, free-form user prompt                 |
| `config` | the effective merged config                    |
| `history`| the running list of previous dispatches        |

Plugins subclassing `Plugin` also get helpers:

- `Plugin._cfg(context, "execution.dry_run", False)` — dotted config access.
- `Plugin.args_after(prompt, "open")` — pull the argument after a trigger word.

Lifecycle hooks `on_load(config)` / `on_unload()` fire at start / shutdown and
share `self.state`.

## 5. Layered configuration

`config.py` merges sources in increasing precedence:

1. **Defaults** baked into `DEFAULTS`.
2. **`config.yaml`** (project root, or `--config`).
3. **`AGENT_*` environment variables** (mapped in `_ENV_MAP`).
4. **CLI flags** (e.g. `--dry-run`).

`deep_merge` recursively merges dicts. `load_config()` returns one plain dict
which is threaded into every plugin context — plugins read config, never the
environment directly.

## 6. Code-style conventions

- Type hints + docstrings on **every** public function.
- Functions return plain dicts (`{"status": ...}`) so results are JSON-serialisable.
- Logging via the `logging` module — `-v` / `-vv` raise the CLI verbosity.
- Errors are caught locally and surfaced as structured results, not exceptions.

## 7. Blast radius & extensibility

To add a capability you touch **exactly one new file** (the plugin module). To
hook it to a phrase, add one tuple to `DEFAULT_ROUTES`. Config, history and
dry-run work for free because they live in the router, not in plugins.

Read [plugins.md](plugins.md) for the step-by-step plugin authoring guide.