"""messages plugin — compose, send, reply and read SMS / chat messages.

In mock mode messages are recorded into the session log. Over a real bridge
(``termux-api``) the payload would be handed to the compose / intent system;
the interface here is what the rest of the agent depends on.
"""

from __future__ import annotations

import datetime
import re
from typing import Any

from plugins.base import Plugin


def _extract_recipient(prompt: str) -> str | None:
    """Pull a plausible phone recipient from the prompt if present."""
    match = re.search(r"[\+]?[\d][\d\s\-]{6,}", prompt)
    return match.group(0).strip() if match else None


def _extract_body(prompt: str) -> str:
    """Strip a leading 'send text to <recipient>' prefix, keep the rest."""
    cleaned = re.sub(r"^send\s+(?:a\s+)?(?:text|sms|message)\s+(?:to\s+)?(?:[\+\d][\d\s\-]{6,}\s+)?",
                     "", prompt.strip(), flags=re.I)
    return cleaned.strip() or "(no message body)"


class MessagesPlugin(Plugin):
    """Compose, send, reply to and read SMS / chat messages."""

    name = "messages"
    description = "Compose, send, reply to and read SMS / chat messages."
    capabilities = ["send", "reply", "read"]

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        action = context.get("action", "send")
        prompt = context.get("prompt", "")
        if action == "reply":
            return self._reply(prompt)
        if action == "read":
            return self._read(context)
        return self._send(prompt)

    def _send(self, prompt: str) -> dict[str, Any]:
        return {"status": "ok", "action": "send",
                "recipient": _extract_recipient(prompt), "body": _extract_body(prompt),
                "queued_at": datetime.datetime.now().isoformat(timespec="seconds")}

    def _reply(self, prompt: str) -> dict[str, Any]:
        return {"status": "ok", "action": "reply",
                "recipient": _extract_recipient(prompt), "body": _extract_body(prompt)}

    def _read(self, context) -> dict[str, Any]:
        history = context.get("history", [])
        sent = [m for m in history if isinstance(m, dict) and m.get("action") == "send"]
        return {"status": "ok", "action": "read", "recent": sent[-10:]}


def run(action: str, prompt: str, **ctx: Any) -> dict[str, Any]:
    """Backwards-compatible functional entry point."""
    return MessagesPlugin().execute({"action": action, "prompt": prompt, **ctx})