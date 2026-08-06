# Installation & Usage

Covers environment setup, connecting to a real device, and a reference for the
command line and configuration options.

## Requirements

- **Python 3.8+** (3.10+ recommended).
- `pip` and (optionally) a `venv`.
- For real device control: `adb` (Android Debug Bridge) **or** the
  [Termux:API](https://github.com/termux/termux-api) add-on.
- `PyYAML` if you want to use `config.yaml` (installed by `requirements.txt`).

## Install

```bash
git clone https://github.com/axe01010/android-ai-agent.git
cd android-ai-agent
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
```

Or install as a package to get the `agent` console command:

```bash
pip install -e .
agent "open Chrome"            # same as: python agent.py "open Chrome"
```

## CLI reference

```
usage: agent [-h] [-i] [-l] [--config CONFIG] [--dry-run] [-v]

positional:
  prompt                task to execute; omit for interactive REPL

options:
  -h, --help            show help
  -i, --interactive     force the REPL even if a prompt is given
  -l, --list            list plugins & routes, then exit
  --config CONFIG       path to a config.yaml
  --dry-run             log intended actions without executing them
  -v, --verbose         -v = INFO, -vv = DEBUG
```

### Examples

```bash
# interactive session
python agent.py

# one-shot
python agent.py "Open Chrome"
python agent.py "set an alarm for 6:45"

# preview without executing
python agent.py --dry-run "turn on wifi"

# inspect the registry
python agent.py --list

# scripted / programmatic (see examples/)
python examples/batch_demo.py
```

## Connecting a real device

The agent ships with three `bridge.type` modes:

| mode          | what happens                                              |
|---------------|-----------------------------------------------------------|
| `mock` (default)| Logs intent, no device interaction. Great for development.|
| `adb`         | Runs real shell commands against a connected device. |
| `termux-api`  | Uses Termux:API intents (lightweight, on-device).          |

Set it in `config.yaml`:

```yaml
bridge:
  type: adb          # or termux-api, or mock
  adb_host: 127.0.0.1
  adb_port: 5555
```

Make sure `adb` is installed and authorised:

```bash
adb devices            # confirm the device is connected & authorised
adb shell pm list packages -3   # quick sanity check
```

## Configuration reference

All keys below are optional; defaults are in `config.py`'s `DEFAULTS`.

| key                            | type      | default | description                          |
|--------------------------------|-----------|---------|--------------------------------------|
| `router.unknown_action`      | str       | `apps`    | plugin used when no route matches |
| `router.fallback_slot`       | str       | `fallback`| slot used as the catch-all        |
| `router.case_sensitive`      | bool      | `false`   | (reserved)                          |
| `execution.dry_run`          | bool      | `false`   | log, don't act                      |
| `execution.require_confirmation` | bool | `false`   | ask before each action          |
| `execution.timeout_seconds`  | int       | `30`      | plugin timeout                     |
| `execution.max_history`      | int       | `200`     | session history cap                |
| `logging.level`              | str       | `INFO`    | root log level                     |
| `logging.file`               | str       | `agent.log`| log file path                       |
| `bridge.type`               | str       | `mock`    | `mock` / `adb` / `termux-api`      |
| `plugins.auto_discover`     | bool      | `true`    | scan `plugins/` at import time     |
| `plugins.disable`           | list      | `[]`      | plugin keys to exclude              |

### Environment overrides

Config keys can be set from the environment using the `AGENT_` prefix. For a
dotted key like `execution.dry_run`, uppercase the path with `_` separators:

```bash
export AGENT_EXECUTION_DRY_RUN=1      # == execution.dry_run: true
export AGENT_LOGGING_LEVEL=DEBUG       # == logging.level: DEBUG
export AGENT_PLUGINS_DISABLE=camera    # == plugins.disable: ["camera"]
```

## Troubleshooting

- **`ModuleNotFoundError: No module named 'yaml'`** — `pm install pyyaml` or
  `pip install PyYAML`, or switch to a JSON config file.
- **`adb: command not found`** — install platform-tools or use
  `bridge.type: termux-api`.
- **Plugin skipped at startup** — the plugin raised during import; check its
  `python3 -c "import plugins.<name>"` for errors.
- **Prompt routes to `apps.fallback`** — no phrase matched; add yours to
  `DEFAULT_ROUTES` or the config router map.