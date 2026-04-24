"""
Force-syncs slash commands to Discord for both bots.
Does NOT require MongoDB or Lavalink to be running.

Usage: python force_sync.py
"""

import asyncio
import os
import sys
import json
import logging
import unittest.mock as mock

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

logging.basicConfig(level=logging.WARNING)

def open_json(path: str) -> dict:
    try:
        with open(os.path.join(ROOT_DIR, path), encoding="utf8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Cannot read {path}: {e}")
        return {}

async def sync_bot(settings_file: str, label: str):
    import discord
    from discord.ext import commands
    from voicelink.config import Config
    # Reset singleton so each bot gets its own config
    Config._instance = None
    Config(open_json(settings_file))

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    bot = commands.Bot(
        command_prefix="/",
        help_command=None,
        intents=intents,
    )

    # Patch MongoDB so cogs load without a real DB connection
    mongo_patch = mock.AsyncMock()
    mongo_patch.get_settings = mock.AsyncMock(return_value={})
    mongo_patch.get_user = mock.AsyncMock(return_value={})

    import voicelink.mongodb as mongodb_mod
    original_handler = mongodb_mod.MongoDBHandler
    mongodb_mod.MongoDBHandler = mongo_patch
    import voicelink
    voicelink.MongoDBHandler = mongo_patch

    loaded = []
    failed = []
    cogs_dir = os.path.join(ROOT_DIR, "cogs")
    for module in sorted(os.listdir(cogs_dir)):
        if module.endswith(".py"):
            name = module[:-3]
            try:
                await bot.load_extension(f"cogs.{name}")
                loaded.append(name)
            except Exception as e:
                failed.append(f"{name}: {e}")

    print(f"\n[{label}] Loaded cogs: {', '.join(loaded)}")
    if failed:
        print(f"[{label}] Skipped: {'; '.join(failed)}")

    @bot.event
    async def on_ready():
        try:
            cmds = await bot.tree.sync()
            print(f"[{label}] Synced {len(cmds)} slash commands!")
            for c in cmds:
                print(f"  /{c.name}")
        except Exception as e:
            print(f"[{label}] Sync failed: {e}")
        await bot.close()

    token = Config().token
    if not token:
        print(f"[{label}] No token found in {settings_file}!")
        return

    print(f"[{label}] Connecting to Discord...")
    await bot.start(token)

async def main():
    print("=== Force Sync Commands ===\n")
    await sync_bot("settings.json", "Bot 1 (main)")
    # Reset for second bot
    import voicelink.config as cfg
    cfg.Config._instance = None
    await sync_bot("settings2.json", "Bot 2")
    print("\n=== Done! Commands will appear in Discord within ~1 minute ===")

if __name__ == "__main__":
    asyncio.run(main())
