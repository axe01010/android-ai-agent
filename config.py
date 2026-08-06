"""Central configuration for android-ai-agent.

Configuration is layered, in order of increasing precedence:

1. Defaults baked into :data:`DEFAULTS` below.
2. A user config file (``config.yaml`` in the project root, or the path given
   with ``--config``).
3. Environment variables (``AAIAGENT_*``).
4. CLI flags (``--verbose``, ``--dry-run``, ...).

The :func:`load_config` helper merges all layers into one plain dict that is
passed into the router and every plugin's execution context.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("agent.config")

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"
ENV_PREFIX = "AAIAGENT_"

DEFAULTS: dict[str, Any] = {
    # --- router -----------------------------------------------------------
    "router": {
        "unknown_action": "apps",
        "fallback_slot": "fallback",
        "case_sensitive": False,
    },
    # --- execution ----------------------------------------------------------
    "execution": {
        "dry_run": False,            # log intended actions instead of running them
        "require_confirmation": False,  # ask before executing each action
        "timeout_seconds": 30,
        "max_history": 200,          # entries kept in the session log
    },
    # --- logging -------------------------------------------------------------
    "logging": {
        "level": "INFO",
        "file": "agent.log",
        "format": "%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    },
    # --- devices / bridges ---------------------------------------------------
    "bridge": {
        "type": "mock",              # mock | adb | termux-api
        "adb_host": "127.0.0.1",
        "adb_port": 5555,
    },
    # --- plugins --------------------------------------------------------------
    "plugins": {
        "auto_discover": True,
        "disable": [],               # plugin keys to skip
    },
}

# Optional env overrides: AAIAGENT_EXECUTION_DRY_RUN=1 etc.
_ENV_MAP = {
    "EXECUTION_DRY_RUN": ("execution", "dry_run"),
    "EXECUTION_REQUIRE_CONFIRMATION": ("execution", "require_confirmation"),
    "LOGGING_LEVEL": ("logging", "level"),
    "BRIDGE_TYPE": ("bridge", "type"),
    "PLUGINS_DISABLE": ("plugins", "disable"),
}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge ``override`` into a copy of ``base``."""
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _env_overrides() -> dict[str, Any]:
    """Read ``AAIAGENT_*`` environment variables into a nested config dict."""
    result: dict[str, Any] = {}
    for env_name, path in _ENV_MAP.items():
        raw = os.environ.get(ENV_PREFIX + env_name)
        if raw is None:
            continue
        node = result
        for part in path[:-1]:
            node = node.setdefault(part, {})
        value: Any = raw
        lowered = raw.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            value = True
        elif lowered in {"0", "false", "no", "off"}:
            value = False
        elif env_name.endswith("_DISABLE") and "," in raw:
            value = [p.strip() for p in raw.split(",") if p.strip()]
        node[path[-1]] = value
    return result


def load_config(path: str | os.PathLike | None = None) -> dict[str, Any]:
    """Load the effective configuration (defaults <- file <- env)."""
    cfg = deep_merge(DEFAULTS, {})

    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if config_path.exists():
        try:
            if config_path.suffix == ".json":
                data = json.loads(config_path.read_text(encoding="utf-8"))
            else:  # .yaml / .yml
                import yaml

                data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            cfg = deep_merge(cfg, data)
            logger.info("loaded config from %s", config_path)
        except Exception as exc:  # never hard-fail on a bad config
            logger.warning("could not read %s: %s — using defaults", config_path, exc)

    cfg = deep_merge(cfg, _env_overrides())
    return cfg


def get(cfg: dict[str, Any], dotted: str, default: Any = None) -> Any:
    """Dot-path accessor, e.g. ``get(cfg, "execution.dry_run")``."""
    node: Any = cfg
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node
