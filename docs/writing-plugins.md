# Writing a plugin — android-ai-agent

The fastest path from "I want the agent to do X" to "done" is a plugin. You do
**not** need to touch `agent.py` or the router. There are two styles.

## Style 1 — functional (simplest)

Create `plugins/weather.py`:

```python
def run(action, prompt, **ctx):
    """Fetch or simulate a weather report."""
    if action != "forecast":
        return {"status": "error", "error": f"unknown weather action: {action}"}
    return {"status": "ok", "action": "forecast",
            "detail": "Partly cloudy, 21C — (stub; a real bridge calls the API)"}
```

The framework calls `run(action, prompt, **context)` and normalises whatever
you return into a `{"status": ...}` dict.

## Style 2 — class-based (richest)

```python
from plugins.base import Plugin

class WeatherPlugin(Plugin):
    name = "weather"
    description = "Local weather forecasts."
    capabilities = ["forecast", "alerts"]

    def execute(self, context):
        action = context.get("action", "forecast")
        prompt = context.get("prompt", "")
        if action == "forecast":
            return self._forecast(prompt)
        if action == "alerts":
            return {"status": "ok", "alerts": [], "action": "alerts"}
        return {"status": "error", "error": f"unknown action {action}"}

    def _forecast(self, prompt):
        # `self.state` holds config merged in via on_load().
        unit = self.state.get("unit", "c")
        return {"status": "ok", "action": "forecast", "unit": unit,
                "detail": "Partly cloudy, 21C (stub)"}

# Keep the functional entry point for backward-compatible callers.
run = WeatherPlugin().execute  # bound method with signature (action, prompt)
```

> ⚠️ `run = WeatherPlugin().execute` binds the *class* signature
> `(context)`. If you want to keep a genuine `run(action, prompt)` function,
> write a thin wrapper like the shipped plugins do:

```python
def run(action, prompt, **ctx):
    return WeatherPlugin().execute({"action": action, "prompt": prompt, **ctx})
```

## Register a route

Add a phrase → `(weather, action)` entry in `DEFAULT_ROUTES` in `agent.py`:

```python
("weather", "weather", "forecast"),      # "what's the weather" -> weather.forecast
```

Order matters — first match wins. Put specific phrases before generic ones.

## Checklist

- [ ] File at `plugins/<name>.py` (lowercase, unique).
- [ ] `class <Name>Plugin(Plugin)` with `name`, `description`, `capabilities`.
- [ ] `execute()` returns a JSON-serialisable dict, never raises.
- [ ] Every action method returns a `command` string a bridge can execute.
- [ ] Functional `run()` wrapper kept for compat.
- [ ] Confirm with `python agent.py --list` that it's discovered and `ready`.

## Testing your plugin

`do_step()` calls `run()` which never raises — invalid actions become
`{"status":"error", "error": ...}`. Drive it directly:

```python
from agent import do_step, load_config
cfg = load_config()
result = do_step("what's the weather in Lisbon", cfg, [])
assert result["status"] == "ok"
assert result["plugin"] == "weather"
```