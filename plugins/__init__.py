"""android-ai-agent plugin package.

Exposes the plugin framework's public API so plugins and the router can do::

    from plugins import Plugin, PluginSpec, discover, load, run

The package-level ``__init__`` re-exports the core interfaces from
:mod:`plugins.base`. Keeping an ``__init__.py`` here also makes ``plugins/`` a
real importable Python package (the upstream tree relied on namespace-package
behaviour, which silently breaks in some interpreters).
"""

from plugins.base import (
    OK,
    ERROR,
    Plugin,
    PluginSpec,
    Registry,
    discover,
    load,
    register,
    run,
)

__all__ = [
    "OK",
    "ERROR",
    "Plugin",
    "PluginSpec",
    "Registry",
    "discover",
    "load",
    "register",
    "run",
]
__version__ = "0.2.0"