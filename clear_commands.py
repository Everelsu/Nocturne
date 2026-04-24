"""
Clears all global slash commands for both bots, then resets version
so they re-register cleanly on next startup.

Usage: python clear_commands.py
"""

import asyncio
import aiohttp
import json
import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

async def clear_global_commands(session: aiohttp.ClientSession, token: str, client_id: str, name: str):
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json"
    }
    url = f"https://discord.com/api/v10/applications/{client_id}/commands"

    # GET current commands
    async with session.get(url, headers=headers) as resp:
        if resp.status != 200:
            print(f"[{name}] Failed to fetch commands: {resp.status}")
            return
        commands = await resp.json()
        print(f"[{name}] Found {len(commands)} global command(s)")

    # PUT empty array = wipe all global commands
    async with session.put(url, headers=headers, json=[]) as resp:
        if resp.status == 200:
            print(f"[{name}] All global commands cleared!")
        else:
            text = await resp.text()
            print(f"[{name}] Error clearing: {resp.status} - {text}")

def load_settings(path: str) -> dict:
    try:
        with open(os.path.join(ROOT_DIR, path), encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Cannot read {path}: {e}")
        return {}

def reset_version(path: str):
    data = load_settings(path)
    if not data:
        return
    data["version"] = ""
    with open(os.path.join(ROOT_DIR, path), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"[{path}] version reset to '' — bot will re-sync commands on next start")

async def main():
    s1 = load_settings("settings.json")
    s2 = load_settings("settings2.json")

    if not s1 or not s2:
        print("Could not load settings files.")
        return

    async with aiohttp.ClientSession() as session:
        await clear_global_commands(session, s1["token"], s1["client_id"], "vocard (main)")
        await clear_global_commands(session, s2["token"], s2["client_id"], "vocard2")

    # Reset versions so both bots call tree.sync() on next start
    reset_version("settings.json")
    reset_version("settings2.json")

    print("\nDone! Restart both bots — they will re-register their commands cleanly.")

if __name__ == "__main__":
    asyncio.run(main())
