#!/usr/bin/env python3
"""Push a Discord DM to the owner via the bochi bot token (session-independent).

Used by the local launchd meta-change pipeline to notify the owner when the
Pokemon Champions environment shifts. Unlike the bochi MCP `reply` tool (which
only works inbound from a running Claude Code session), this talks to the
Discord REST API directly, so it works from cron/launchd with no session.

Usage:
    echo "message body" | notify_discord.py
    notify_discord.py "message body"
    notify_discord.py --user 836994758236831744 "message body"

Exit codes:
    0  sent
    2  bad usage / empty message
    3  token missing
    4  Discord API error
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Owner Discord snowflake (from ~/.claude/channels/discord/access.json allowFrom).
DEFAULT_RECIPIENT = "836994758236831744"
ENV_PATH = Path.home() / ".claude" / "channels" / "discord" / ".env"
API_BASE = "https://discord.com/api/v10"
TIMEOUT_S = 15


def read_token(env_path: Path = ENV_PATH) -> str:
    """Read DISCORD_BOT_TOKEN from the bochi Discord .env. Never logged."""
    if not env_path.is_file():
        raise FileNotFoundError(f"discord .env not found: {env_path}")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DISCORD_BOT_TOKEN="):
            token = line.split("=", 1)[1].strip().strip('"').strip("'")
            if token:
                return token
    raise ValueError("DISCORD_BOT_TOKEN not set in .env")


def _post(path: str, token: str, payload: dict) -> dict:
    """POST JSON to the Discord API and return the parsed response."""
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "pokechamp-meta-notifier (local)",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return json.loads(resp.read().decode("utf-8"))


def open_dm(token: str, user_id: str) -> str:
    """Open (or fetch) the DM channel with the recipient, return its channel id."""
    data = _post("/users/@me/channels", token, {"recipient_id": user_id})
    channel_id = data.get("id")
    if not channel_id:
        raise RuntimeError(f"no DM channel id in response: {data}")
    return channel_id


def send_dm(token: str, user_id: str, content: str) -> str:
    """Send a DM to the recipient. Returns the posted message id."""
    channel_id = open_dm(token, user_id)
    data = _post(f"/channels/{channel_id}/messages", token, {"content": content})
    return data.get("id", "")


def _parse_args(argv):
    """Return (recipient_id, message) from argv, reading stdin if no message arg."""
    recipient = DEFAULT_RECIPIENT
    rest = []
    i = 0
    while i < len(argv):
        if argv[i] == "--user" and i + 1 < len(argv):
            recipient = argv[i + 1]
            i += 2
            continue
        rest.append(argv[i])
        i += 1
    message = " ".join(rest).strip() if rest else sys.stdin.read().strip()
    return recipient, message


def main(argv):
    recipient, message = _parse_args(argv)
    if not message:
        print("error: empty message (pass as arg or via stdin)", file=sys.stderr)
        return 2
    if len(message) > 1900:  # Discord hard limit 2000; leave margin.
        message = message[:1897] + "..."
    try:
        token = read_token()
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    try:
        msg_id = send_dm(token, recipient, message)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:300]
        print(f"error: Discord API {exc.code}: {body}", file=sys.stderr)
        return 4
    except (urllib.error.URLError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4
    print(f"sent message id={msg_id} to user={recipient}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
