<p align="center">
  <img src="https://github.com/axe01010/android-ai-agent/raw/main/assets/banner.png" alt="android-ai-agent" width="100%" />
</p>

<p align="center">
  <img src="https://img.shields.io/github/stars/axe01010/android-ai-agent?style=for-the-badge&color=7C3AED&logo=github" />
  <img src="https://img.shields.io/github/forks/axe01010/android-ai-agent?style=for-the-badge&color=3DDC84&logo=github" />
  <img src="https://img.shields.io/github/license/axe01010/android-ai-agent?style=for-the-badge&color=7C3AED" />
  <img src="https://img.shields.io/github/last-commit/axe01010/android-ai-agent?style=for-the-badge&color=3DDC84" />
</p>

# 🤖 Android AI Agent

<p align="center">
  <img src="https://img.shields.io/badge/AI-Agent-7C3AED?style=for-the-badge&logo=openai&logoColor=white" />
  <img src="https://img.shields.io/badge/Android-3DDC84?style=for-the-badge&logo=android&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" />
</p>

> **Control your Android phone with natural language.** A small, privacy-first AI
> agent that routes free-form prompts to a pluggable set of *capabilities* —
> apps, settings, messages, camera — so your device actually does things when
> you ask.

**No cloud. No API keys. No server.** Everything runs locally on your device or
workstation.

---

## ✨ Features

- 🗣️ **Natural-language routing** — "open Chrome", "set an alarm for 7:30",
  "send a text …", "take a photo" map to concrete device actions.
- 🔌 **Pluggable capability system** — add a new device action by dropping one
  file into `plugins/`. No framework changes needed.
- 📦 **Two plugin styles** — fast *function style* plugins and rich *class-based*
  plugins with state, lifecycle hooks and config access.
- ⚙️ **Layered configuration** — `config.yaml` → `AGENT_*` env vars → CLI flags,
  merged deterministically.
- 🧭 **Deterministic routing** — keyword phrases are ordered and transparent;
  a safe fallback always answers.
- 📒 **Session history** — every dispatch is logged with timestamps for
  transparency and debugging.
- 🔒 **Privacy-first** — built for single-user, local execution by default.
- 🧪 **Dry-run mode** — preview exactly what each prompt would do before letting
  it through.

---

## 🚀 Quick Start

### 1. Clone & install

```bash
git clone https://github.com/axe01010/android-ai-agent.git
cd android-ai-agent
pip install -r requirements.txt     # PyYAML, for config.yaml support
```

### 2. Run an interactive session

```bash
python agent.py
```

```text
🤖 Android AI Agent — type 'help', 'list' or 'exit'.
agent> open Chrome
agent> set an alarm for 7:30
agent> take a photo of the whiteboard
agent> what time is it?
```

### 3. Run a one-shot command

```bash
python agent.py "Open Chrome"
python agent.py --list               # show all plugins, capabilities, routes
python agent.py --dry-run -v "turn on wifi"   # preview, don't execute
```

### 4. Typical output

```json
{
  "status": "ok",
  "action": "open",
  "app": "chrome",
  "command": "am start -a android.intent.action.MAIN -n com.android.chrome/com.android.chrome.MainActivity",
  "plugin": "apps"
}
```

---

## 🧩 How it works

```
  your prompt
       │
       ▼
 ┌─────────────┐    phrase match?     ┌────────────────────────────┐
 │   Router    │ ───────────────────▶ │  Plugin registry (discover) │
 │  route()    │                      │  apps, settings, messages,  │
 └─────────────┘                      │  camera, + yours            │
       │                              └─────────────┬──────────────┘
       ▼                                             ▼
 ┌─────────────┐   config + history    ┌────────────────────────────┐
 │  do_step()  │ ────────────────────▶ │  plugin.execute(ctx)       │
 └─────────────┘                       └────────────────────────────┘
       │                                          │
       ▼                                          ▼
   structured JSON result            device action (adb / mock / termux-api)
```

**The router** (`agent.route`) matches an ordered list of keyword phrases to a
`(plugin, action)` pair. The **registry** (`plugins.discover`) scans the
`plugins/` package at import time. **`do_step`** resolves the right plugin,
executes it with a shared context (config + history), and normalises any return
value into a structured dict the agent loop can report.

---

## 🔌 Built-in plugins

| Plugin     | Key        | Actions                                        |
|------------|------------|------------------------------------------------|
| Apps       | `apps`     | `open`, `search`, `install`, `list`, `kill`     |
| Settings   | `settings` | `alarm`, `dnd`, `silent`, `brightness`, `volume`, `wifi`, `time` |
| Messages   | `messages` | `send`, `reply`, `read`                        |
| Camera     | `camera`   | `snap`, `video`, `flash`                       |

Discover them live:

```bash
python agent.py --list
```

---

## 📁 Project structure

```
android-ai-agent/
├── agent.py              # CLI, router, REPL, do_step() entry points
├── config.py             # layered config (defaults <- file <- env <- CLI)
├── config.yaml           # optional user overrides
├── plugins/              # capability plugins
│   ├── base.py           # Plugin base class + registry (discover/load/run)
│   ├── apps.py           # app launch / search / install
│   ├── settings.py       # alarms, DND, brightness, volume, wifi
│   ├── messages.py       # compose / send / read messages
│   └── camera.py         # photo / video / flash
├── examples/
│   ├── batch_demo.py     # drive the agent programmatically
│   └── custom_plugin.py  # write & register a custom plugin
├── docs/
│   ├── architecture.md   # routing & plugin internals
│   ├── installation.md   # setup, bridges, config reference
│   └── plugins.md        # guide to writing plugins
├── requirements.txt
├── setup.py
└── README.md
```

---

## 💡 Use cases

- **Personal device automation** — batch common tasks ("set alarm", "open app").
- **Voice-assistant backend** — pair with a TTS/STT layer to make the agent
  fully hands-free.
- **Scripted device control** — call `agent.do_step` from Python to orchestrate
  multiple device actions.
- **Educational framework** — the small router + registry is a clean blueprint
  for building your own agent harness.

---

## ❓ FAQ

**Does this ship a real LLM?** No — routing is rule-based so it works offline,
deterministically, with zero tokens. Plug the routing output into an LLM later
if you want smarter intent parsing.

**How do I connect a real device?** Set `bridge.type: adb` in `config.yaml` and
ensure `adb` is on your `PATH` with a connected device. `bridge.type: termux-api`
uses the Termux:API helpers. Default is `mock`, which logs without touching the
device.

**Can I disable a plugin?** Yes — set `plugins.disable: ["camera"]` in
`config.yaml` or via `AGENT_PLUGINS_DISABLE=camera`.

**How do I add my own action?** Drop a plugin into `plugins/`, then (optionally)
add a phrase to `DEFAULT_ROUTES`. See `docs/plugins.md`.

---

## 🤝 Contributing

Contributions are welcome! Please read [`CONTRIBUTING.md`](CONTRIBUTING.md)
first, keep the style consistent, and add tests where it makes sense. Fork →
branch → PR.

## 📜 License

Released under the [MIT License](LICENSE). Use it, fork it, learn from it.