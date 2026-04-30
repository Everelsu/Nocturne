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

import os
import json

from pathlib import Path
from dotenv import load_dotenv
from typing import (
    Dict,
    List,
    Any,
    Union,
    Optional
)

from .enums import SearchType

load_dotenv()

class Config:
    _instance: Optional['Config'] = None
    WORKING_DIR: Path = Path(__file__).resolve().parent.parent
    LAST_SESSION_FILE_DIR: str = WORKING_DIR / "last-session.json"

    def __new__(cls, settings: Dict[str, Any] = None) -> 'Config':
        if settings is not None:
            instance = super(Config, cls).__new__(cls)
            instance.__init__(settings)
            cls._instance = instance
            return instance

        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)

        return cls._instance

    def __init__(self, settings: Dict[str, Any] = None) -> None:
        if hasattr(self, 'initialized'):
            return

        settings = settings or {}

        # ── Secrets: env vars have PRIORITY over settings.json ──────────────
        self.token: str          = os.getenv("TOKEN")          or settings.get("token", "")
        self.client_id: int      = int(os.getenv("CLIENT_ID", 0) or settings.get("client_id", 0))
        self.genius_token: str   = os.getenv("GENIUS_TOKEN")   or settings.get("genius_token", "")
        self.mongodb_url: str    = os.getenv("MONGODB_URL")    or settings.get("mongodb_url", "")
        self.mongodb_name: str   = os.getenv("MONGODB_NAME")   or settings.get("mongodb_name", "Nocturne")

        # ── Non-secret settings ──────────────────────────────────────────────
        self.invite_link: str = ""
        self.nodes: Dict[str, Dict[str, Union[str, int, bool]]] = settings.get("nodes", {})

        # Override node credentials via env vars (Railway-friendly)
        # LAVALINK_HOST / LAVALINK_PORT / LAVALINK_PASSWORD override the first node
        self._apply_lavalink_env_overrides()

        self.max_queue: int        = settings.get("default_max_queue", 1000)
        self.search_platform: SearchType = (
            SearchType.from_platform(settings.get("default_search_platform", "youtube"))
            or SearchType.YOUTUBE
        )
        self.bot_prefix: str       = settings.get("prefix", "")
        self.activity: List[Dict[str, str]] = settings.get("activity", [{"listen": "/help"}])
        self.logging: Dict[Union[str, Dict[str, Union[str, bool]]]] = settings.get("logging", {})
        self.embed_color: str      = int(settings.get("embed_color", "0xb3b3b3"), 16)
        self.bot_access_user: List[int] = settings.get("bot_access_user", [])
        self.banlist: List[int]         = settings.get("banlist", [])
        self.service_enabled: bool      = settings.get("service_enabled", True)
        self.service_disabled_reason: str = settings.get("service_disabled_reason", "")
        self.sources_settings: Dict[Dict[str, str]] = settings.get("sources_settings", {})
        self.cooldowns_settings: Dict[str, List[int]] = settings.get("cooldowns", {})
        self.aliases_settings: Dict[str, List[str]]   = settings.get("aliases", {})
        self.controller: Dict[str, Dict[str, Any]]    = settings.get("default_controller", {})
        self.voice_status_template: str = settings.get("default_voice_status_template", "")
        self.webpanel_url: str     = os.getenv("WEBPANEL_URL") or settings.get("webpanel_url", "")
        self.lyrics_platform: str  = settings.get("lyrics_platform", "A_ZLyrics").lower()
        self.playlist_settings: Dict[str, Union[str, int]] = settings.get("playlist_settings", {})
        self.timer_settings: Dict[str, int] = settings.get("timer_settings", {})
        self.version: str = settings.get("version", "")

        # IPC client — env vars override json values
        ipc_raw: dict = settings.get("ipc_client", {})
        self.ipc_client: Dict[str, Union[str, bool, int]] = {
            "host":     os.getenv("IPC_HOST")     or ipc_raw.get("host", "vocard-dashboard"),
            "port":     int(os.getenv("IPC_PORT") or ipc_raw.get("port", 8080)),
            "password": os.getenv("IPC_PASSWORD") or ipc_raw.get("password", "changeme"),
            "secure":   ipc_raw.get("secure", False),
            "enable":   (os.getenv("IPC_ENABLE", "").lower() in ("1", "true", "yes"))
                        if os.getenv("IPC_ENABLE") is not None
                        else ipc_raw.get("enable", False),
        }

        # YouTube OAuth tokens for rate-limiting (env: YOUTUBE_OAUTH_TOKENS — JSON array string)
        yt_env = os.getenv("YOUTUBE_OAUTH_TOKENS")
        if yt_env:
            try:
                yt_tokens = json.loads(yt_env)
                for node in self.nodes.values():
                    if "yt_ratelimit" in node:
                        node["yt_ratelimit"]["tokens"] = yt_tokens
            except Exception:
                pass

        self.initialized = True

    # ── helpers ─────────────────────────────────────────────────────────────

    def _apply_lavalink_env_overrides(self) -> None:
        """
        Override Lavalink node settings via env vars.

        LAVALINK_HOST / LAVALINK_PORT / LAVALINK_PASSWORD
            → applied to the FIRST node in the nodes dict
        LAVALINK2_HOST / LAVALINK2_PORT / LAVALINK2_PASSWORD
            → applied to the SECOND node (if present)

        This lets Railway services set internal hostnames without
        touching settings.json.
        """
        env_overrides = [
            ("LAVALINK_HOST",     "LAVALINK_PORT",  "LAVALINK_PASSWORD"),
            ("LAVALINK2_HOST",    "LAVALINK2_PORT", "LAVALINK2_PASSWORD"),
        ]
        node_keys = list(self.nodes.keys())
        for idx, (host_var, port_var, pass_var) in enumerate(env_overrides):
            if idx >= len(node_keys):
                break
            node = self.nodes[node_keys[idx]]
            if os.getenv(host_var):
                node["host"] = os.getenv(host_var)
            if os.getenv(port_var):
                node["port"] = int(os.getenv(port_var))
            if os.getenv(pass_var):
                node["password"] = os.getenv(pass_var)

    # ── class-level accessors ────────────────────────────────────────────────

    @classmethod
    def get_source_config(cls, source: str, type: str) -> Union[str, None]:
        if not isinstance(source, str) or not isinstance(type, str):
            return None
        normalized_source: str = source.lower().strip().replace(" ", "")
        source_settings: dict[str, str] = cls._instance.sources_settings.get(
            normalized_source,
            cls._instance.sources_settings.get("others", {})
        )
        return source_settings.get(type)

    @classmethod
    def get_playlist_config(cls) -> tuple[int, int, str]:
        config = cls._instance.playlist_settings
        return (
            config.get("max_playlists", 5),
            config.get("max_tracks_per_playlist", 500),
            config.get("default_playlist_name", "Favourite"),
        )
