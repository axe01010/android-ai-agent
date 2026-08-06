# Configuration — android-ai-agent

Everything the agent decides about *how to run* (as opposed to *what to do*)
lives in the layered config system.

## Layers (lowest → highest precedence)

1. **Baked-in defaults** — `DEFAULTS` in `config.py`.
2. **User config file** — `config.yaml` in the project root, or the path passed
   with `--config`.
3. **Environment variables** — `AAIAGENT_*` (see below).
4. **Command-line flags** — `--verbose`, `--dry-run`, etc.

Deep merge means a file only has to override the keys it cares about.

## The defaults

```yaml
router:
  unknown_action: "apps"      # plugin when nothing matches
  fallback_slot: "fallback"   # action on that plugin
  case_sensitive: false

execution:
  dry_run: false              # log intended actions, run nothing
  require_confirmation: false
  timeout_seconds: 30
  max_history: 200

logging:
  level: INFO
  file: agent.log

bridge:
  type: mock                  # mock | adb | termux-api
  adb_host: 127.0.0.1
  adb_port: 5555

plugins:
  auto_discover: true
  disable: []                 # e.g. ["camera"] to switch a plugin off
```

## Environment overrides

Prefix `AAIAGENT_` turns any env variable into a config override with the same
shape:

```bash
AAIAGENT_EXECUTION_DRY_RUN=1          # == execution.dry_run: true
AAIAGENT_EXECUTION_REQUIRE_CONFIRMATION=0
AAIAGENT_LOGGING_LEVEL=DEBUG
AAIAGENT_BRIDGE_TYPE=termux-api
AAIAGENT_PLUGINS_DISABLE=camera,messages
```

Booleans accept `1/true/yes/on` and `0/false/no/off` (case-insensitive);
`*_DISABLE` accepts a comma-separated list.

## Good to know

- **Bad config never blocks.** A missing or malformed file logs a warning and
  the agent runs from defaults — important on a device you can't debug easily.
- **`--dry-run`** sets `execution.dry_run` for one invocation without editing
  your config file.
- Add your own keys freely — plugin-specific settings you drop into
  `config.yaml` flow into every plugin's `context["config"]` unchanged.
- When you deploy `bridge.type: termux-api`, each plugin's returned `command`
  is what that bridge turns into a `termux-*` shell call.