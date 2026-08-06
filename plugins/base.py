"""Plugin base classes and the plugin registry for android-ai-agent.

Every capability in the agent is a *plugin*: a self-contained module that
implements a small, well-defined interface so the core router stays thin and
new device actions can be added without touching the main loop.

Two ways to write a plugin
--------------------------
1. **Class style (recommended).** Subclass :class:`Plugin`, set ``name``,
   ``description`` and ``capabilities``, and implement :meth:`Plugin.execute`.
2. **Function style (quick).** Define a single ``run(action, prompt, ctx=None)``
   function (plus an optional ``on_load()`` hook).

The registry (:func:`discover`) walks the ``plugins`` package and exposes every
plugin to the router at import time.
"""

from __future__ import annotations

import importlib
import inspect
import json
import logging
import pkgutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("agent.plugins")

# Default values returned by plugins so the agent loop always has structured output.
OK = {"status": "ok"}
ERROR = {"status": "error"}


@dataclass
class PluginSpec:
    """Introspection record for one discovered plugin."""

    key: str
    module: str
    description: str = ""
    capabilities: list[str] = field(default_factory=list)
    has_run: bool = False

    @classmethod
    def from_module(cls, module) -> "PluginSpec":
        """Build a spec from a module, preferring its class-based plugin.

        Note: the loop variable must not be named ``cls`` — it would shadow the
        classmethod's own ``cls`` and break the constructor call below.
        """
        key = module.__name__.rsplit(".", 1)[-1]
        desc = ""
        caps: list[str] = []
        has_run = hasattr(module, "run")

        for plugin_cls in _module_plugins(module):
            if plugin_cls.name:
                key = plugin_cls.name
            desc = plugin_cls.description
            caps = list(plugin_cls.capabilities)
            break

        if not desc:
            doc = getattr(module, "__doc__") or ""
            desc = doc.strip().splitlines()[0].strip() if doc.strip() else key
        return cls(key=key, module=module.__name__, description=desc,
                   capabilities=caps, has_run=has_run)


class Plugin:
    """Base class for rich, class-based plugins.

    Subclasses must set ``name`` and may override :meth:`capabilities` and
    :meth:`execute`. ``on_load`` fires once at load time (state lives on
    ``self.state``); ``on_unload`` fires at shutdown.
    """

    #: Short machine key used by the router / CLI.
    name: str = "base"
    #: Human-friendly description surfaced in ``agent list`` and --help.
    description: str = "No description provided."
    #: Slot names this plugin can perform (free-form, used for filtering).
    capabilities: list[str] = []

    def __init__(self) -> None:
        self.state: dict[str, Any] = {}

    # -- lifecycle hooks -------------------------------------------------------
    def on_load(self, config: dict[str, Any]) -> None:
        """Called when the plugin is loaded. Override to read config."""
        self.state.update(config)

    def on_unload(self) -> None:
        """Called at shutdown. Override to persist state / release handles."""

    # -- the one required method ----------------------------------------------
    def execute(self, context: dict[str, Any]) -> Any:
        """Perform the plugin's action. Return a dict for the agent loop."""
        raise NotImplementedError(f"{self.name} must implement execute()")

    # -- helpers -----------------------------------------------------------------
    def _cfg(self, context: dict[str, Any], dotted: str, default: Any = None) -> Any:
        """Read a dotted path (e.g. ``execution.dry_run``) from the context config."""
        cfg = context.get("config", {}) or {}
        node: Any = cfg
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    @staticmethod
    def args_after(prompt: str, trigger: str = "") -> str:
        """Return prompt text after ``trigger`` (case-insensitive) or the whole prompt."""
        t = prompt.strip()
        if trigger and t.lower().startswith(trigger.lower()):
            return t[len(trigger):].strip()
        return t


def _module_plugins(mod) -> list[type[Plugin]]:
    """Return the :class:`Plugin` subclasses defined directly in ``mod``."""
    out: list[type[Plugin]] = []
    for _, member in inspect.getmembers(mod, inspect.isclass):
        if issubclass(member, Plugin) and member is not Plugin:
            out.append(member)
    return out


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
class Registry:
    """In-memory plugin registry for programmatic registration.

    Lets users register plugins without depending on filesystem discovery and
    keeps an explicit, greppable inventory of capabilities.
    """

    def __init__(self) -> None:
        self._specs: dict[str, PluginSpec] = {}

    def register(self, key: str, module: str, description: str = "",
                 capabilities: list[str] | None = None) -> None:
        self._specs[key] = PluginSpec(
            key=key, module=module, description=description,
            capabilities=list(capabilities or []), has_run=False,
        )

    def specs(self) -> dict[str, PluginSpec]:
        return dict(self._specs)

    def exists(self, key: str) -> bool:
        return key in self._specs

    def capabilities(self, key: str) -> list[str]:
        return self._specs[key].capabilities if self.exists(key) else []


#: Module-level default registry used by :func:`register`.
DEFAULT_REGISTRY: Registry = Registry()


def register(key: str, module: str, description: str = "",
             capabilities: list[str] | None = None) -> None:
    """Register a plugin programmatically in the default registry."""
    DEFAULT_REGISTRY.register(key, module, description, capabilities)


def discover(package_name: str = "plugins") -> dict[str, PluginSpec]:
    """Scan a package for plugins and return their specs keyed by name.

    Finds both functional ``run()`` modules and class-based :class:`Plugin`
    subclasses, and merges in anything registered via :func:`register`.
    Registration is lazy — only metadata is collected here; actual loading
    happens in :func:`load`. Support modules (``base``, ``registry``, ``_*``)
    are skipped.
    """
    specs: dict[str, PluginSpec] = dict(DEFAULT_REGISTRY.specs())
    pkg = importlib.import_module(package_name)
    for modinfo in pkgutil.iter_modules(pkg.__path__, prefix=package_name + "."):
        mod_name = modinfo.name.rsplit(".", 1)[-1]
        if mod_name in {"base", "registry"} or mod_name.startswith("_"):
            continue  # support modules are not plugins
        try:
            module = importlib.import_module(modinfo.name)
        except Exception as exc:  # never let one bad plugin kill the router
            logger.warning("skipping plugin module %s: %s", modinfo.name, exc)
            continue
        spec = PluginSpec.from_module(module)
        specs[spec.key] = spec
    return specs


def capabilities(package_name: str = "plugins") -> dict[str, list[str]]:
    """Map every discovered plugin key to its capability tags."""
    return {k: s.capabilities for k, s in discover(package_name).items()}


def load(key: str, package_name: str = "plugins") -> Plugin | Callable[..., dict]:
    """Load and return a plugin runner for ``key``.

    Resolution order:
      1. a class-based :class:`Plugin` in a ``package_name.<key>`` module,
      2. the module's plain ``run()`` function,
      3. a programmatically-registered plugin (see :func:`register`).
    """
    module = None
    registered_module = DEFAULT_REGISTRY.specs().get(key)
    if registered_module is not None:
        registered_module = registered_module.module

    # Prefer the filesystem module, then the registry's recorded module.
    for candidate in (f"{package_name}.{key}", registered_module):
        if not candidate:
            continue
        try:
            module = importlib.import_module(candidate)
            break
        except (ModuleNotFoundError, ImportError):
            module = None
            continue

    if module is None:
        raise ModuleNotFoundError(f"no plugin 'plugins.{key}' and no registered module for it")

    for cls in _module_plugins(module):
        if cls.name == key or cls.name == "base" or registered_module:
            return cls()
    # fall back to the functional style plugin
    if hasattr(module, "run"):
        _fire_ready(module)
        return module.run
    raise AttributeError(f"plugin '{key}' has neither a Plugin class nor a run() function")


def _fire_ready(module) -> None:
    """Fire a function-style plugin's on_load / on_ready if it exposes one."""
    hook = getattr(module, "on_load", None) or getattr(module, "on_ready", None)
    if callable(hook):
        try:
            hook()
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning("plugin on_load failed: %s", exc)


def run(plugin: Plugin | Callable[..., Any], action: str, prompt: str,
        config: dict[str, Any] | None = None, **ctx: Any) -> dict[str, Any]:
    """Uniformly execute a loaded plugin and normalise its return value."""
    context: dict[str, Any] = {
        "action": action,
        "prompt": prompt,
        "config": config or {},
        **ctx,
    }
    try:
        if isinstance(plugin, Plugin):
            plugin.on_load(context.get("config", {}))
            result = plugin.execute(context)
            return _as(result)
        # functional plugin — context already carries action/prompt as keys
        result = plugin(**context)
        return _as(result)
    except Exception as exc:
        logger.exception("plugin %r failed", getattr(plugin, "name", plugin))
        return {**ERROR, "error": str(exc)}


def _as(result: Any) -> dict[str, Any]:
    if result is None:
        return dict(OK)
    if isinstance(result, dict):
        return result
    return {"status": "ok", "result": str(result)}


def save_manifest(specs: dict[str, PluginSpec], path: str | Path) -> None:
    """Persist a plugin inventory to JSON (useful for reports / CI)."""
    payload = {
        key: {
            "module": s.module,
            "description": s.description,
            "capabilities": s.capabilities,
            "has_run": s.has_run,
        }
        for key, s in specs.items()
    }
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")