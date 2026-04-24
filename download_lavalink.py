"""Download Lavalink.jar for both lavalink and lavalink2 build contexts."""
import os
import shutil
import urllib.request

LAVALINK_URL = "https://github.com/lavalink-devs/Lavalink/releases/latest/download/Lavalink.jar"
DESTINATIONS = [
    "lavalink/Lavalink.jar",
    "lavalink2/Lavalink.jar",
]

def download():
    print(f"Downloading Lavalink.jar from GitHub...")
    tmp = "Lavalink.jar.tmp"
    try:
        urllib.request.urlretrieve(LAVALINK_URL, tmp)
        for dest in DESTINATIONS:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy(tmp, dest)
            print(f"  -> {dest}")
        print("Done.")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

if __name__ == "__main__":
    download()
