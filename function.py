"""MIT License

Copyright (c) 2023 - present Vocard Development

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import json
import os
import re
import time
import logging
import voicelink

from discord.ext import commands
from typing import Optional

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

logger: logging.Logger = logging.getLogger("vocard")

if not os.path.exists(os.path.join(ROOT_DIR, "settings.json")):
    raise Exception("Settings file not set!")

def open_json(path: str) -> dict:
    try:
        with open(os.path.join(ROOT_DIR, path), encoding="utf8") as json_file:
            data = json.load(json_file)
        section = os.getenv("BOT_SECTION")
        if section and isinstance(data.get(section), dict):
            return data[section]
        return data
    except:
        return {}

def update_json(path: str, new_data: dict) -> None:
    try:
        with open(os.path.join(ROOT_DIR, path), encoding="utf8") as json_file:
            data = json.load(json_file)
    except:
        data = {}

    section = os.getenv("BOT_SECTION")
    if section and isinstance(data.get(section), dict):
        data[section].update(new_data)
    else:
        data.update(new_data)

    with open(os.path.join(ROOT_DIR, path), "w", encoding="utf8") as json_file:
        json.dump(data, json_file, indent=4, ensure_ascii=False)

# ── Runtime state ────────────────────────────────────────────────────────────
# banlist: {user_id: expiry_unix_ts}  — None means permanent ban
_banlist: dict[int, float | None] = {}
_service_enabled: bool = True
_service_disabled_reason: str = ""

# ── Duration helpers ─────────────────────────────────────────────────────────
_DURATION_RE = re.compile(r"^(\d+)\s*([smhdw])$", re.IGNORECASE)
_DURATION_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}

def parse_duration(duration_str: str) -> float | None:
    """'30m' / '2h' / '1d' / '1w' → Unix expiry timestamp.
    Returns None for permanent (empty / 'perm' / 'permanent')."""
    if not duration_str or duration_str.lower() in ("perm", "permanent"):
        return None
    m = _DURATION_RE.match(duration_str.strip())
    if not m:
        return None
    return time.time() + int(m.group(1)) * _DURATION_UNITS[m.group(2).lower()]

def format_ban_remaining(expiry: float) -> str:
    """Format seconds-until-expiry into a human-readable string."""
    remaining = max(0, int(expiry - time.time()))
    d, rem = divmod(remaining, 86400)
    h, rem = divmod(rem, 3600)
    m, s   = divmod(rem, 60)
    if d:   return f"{d}d {h}h" if h else f"{d}d"
    if h:   return f"{h}h {m}m" if m else f"{h}h"
    if m:   return f"{m}m"
    return f"{s}s"

# ── Internal persistence ─────────────────────────────────────────────────────
def _persist_banlist() -> None:
    update_json("settings.json", {"banlist": {str(k): v for k, v in _banlist.items()}})

# ── Public API ───────────────────────────────────────────────────────────────
def init_runtime_state() -> None:
    """Call once after Config is fully initialised (in setup_hook)."""
    global _banlist, _service_enabled, _service_disabled_reason
    cfg = voicelink.Config()
    raw = getattr(cfg, "banlist", {})
    if isinstance(raw, dict):
        _banlist = {int(k): v for k, v in raw.items()}
    else:
        # backward-compat: old format was a plain list of ints (permanent)
        _banlist = {uid: None for uid in raw}
    _service_enabled = getattr(cfg, "service_enabled", True)
    _service_disabled_reason = getattr(cfg, "service_disabled_reason", "")

def is_service_enabled() -> bool:
    return _service_enabled

def get_service_reason() -> str:
    return _service_disabled_reason

def is_banned(user_id: int) -> bool:
    """True if user is actively banned (permanent or temp, not expired)."""
    if user_id not in _banlist:
        return False
    expiry = _banlist[user_id]
    if expiry is None:
        return True  # permanent
    if time.time() < expiry:
        return True  # temp — still active
    # expired — lazy cleanup
    del _banlist[user_id]
    _persist_banlist()
    return False

def get_ban_expiry(user_id: int) -> float | None:
    """Returns expiry Unix timestamp, or None for permanent / not banned."""
    return _banlist.get(user_id)

def get_banlist() -> dict[int, float | None]:
    return dict(_banlist)

def set_service_state(enabled: bool, reason: str = "") -> None:
    global _service_enabled, _service_disabled_reason
    _service_enabled = enabled
    _service_disabled_reason = reason
    update_json("settings.json", {"service_enabled": enabled, "service_disabled_reason": reason})

def ban_user(user_id: int, expiry: float | None = None) -> None:
    """expiry = Unix timestamp or None for permanent ban."""
    _banlist[user_id] = expiry
    _persist_banlist()

def unban_user(user_id: int) -> bool:
    """Returns True if the user was in the banlist and was removed."""
    if user_id not in _banlist:
        return False
    del _banlist[user_id]
    _persist_banlist()
    return True

def cleanup_expired_bans() -> int:
    """Remove expired temp bans. Returns number of entries cleaned up."""
    now = time.time()
    expired = [uid for uid, exp in list(_banlist.items()) if exp is not None and exp <= now]
    for uid in expired:
        del _banlist[uid]
    if expired:
        _persist_banlist()
    return len(expired)

def cooldown_check(ctx: commands.Context) -> Optional[commands.Cooldown]:
    if ctx.author.id in voicelink.Config().bot_access_user:
        return None
    cooldown = voicelink.Config().cooldowns_settings.get(f"{ctx.command.parent.qualified_name} {ctx.command.name}" if ctx.command.parent else ctx.command.name)
    if not cooldown:
        return None
    return commands.Cooldown(cooldown[0], cooldown[1])

def get_aliases(name: str) -> list:
    return voicelink.Config().aliases_settings.get(name, [])