#!/usr/bin/env python3
"""
dont-shout: reminds you to use your mic (not your outside voice)
when headphones are connected and a game is running.
"""

import platform
import subprocess
import time

import psutil
from plyer import notification

# ── Configuration ─────────────────────────────────────────────────────────────

CHECK_INTERVAL_SECONDS = 5
NOTIFICATION_COOLDOWN_SECONDS = 60

HEADPHONE_KEYWORDS = [
    "headphone", "headset", "earphone", "earbuds", "airpods",
]

# Process names to watch for (lowercase, no .exe).
# To find a game's name: Task Manager → Details tab while the game is running.
GAMES = [
    "csgo", "cs2", "dota2", "fortnite", "valorant", "minecraft",
    "leagueoflegends", "witcher3", "cyberpunk2077", "overwatch",
    "rocketleague", "pubg", "gta5", "elden_ring", "eldenring",
    "apex_legends", "apexlegends", "battlefield", "cod",
    "modernwarfare", "warzone", "steam", "epicgameslauncher",
]

# ── Core logic ────────────────────────────────────────────────────────────────

def is_game_running() -> tuple[bool, str]:
    for proc in psutil.process_iter(["name"]):
        try:
            name = proc.info["name"].lower().replace(".exe", "").replace(" ", "")
            for game in GAMES:
                if game in name:
                    return True, proc.info["name"]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False, ""


def is_headphones_connected() -> bool:
    system = platform.system()
    if system == "Windows":
        return _check_windows()
    elif system == "Darwin":
        return _check_mac()
    else:
        return _check_linux()


def _check_windows() -> bool:
    try:
        from pycaw.pycaw import AudioUtilities
        for device in AudioUtilities.GetAllDevices():
            if any(kw in str(device).lower() for kw in HEADPHONE_KEYWORDS):
                return True
    except Exception as e:
        print(f"[WARN] Windows audio check failed: {e}")
    return False


def _check_mac() -> bool:
    try:
        result = subprocess.run(
            ["system_profiler", "SPAudioDataType"],
            capture_output=True, text=True, timeout=5,
        )
        output = result.stdout.lower()
        return any(kw in output for kw in HEADPHONE_KEYWORDS)
    except Exception as e:
        print(f"[WARN] macOS audio check failed: {e}")
    return False


def _check_linux() -> bool:
    try:
        result = subprocess.run(
            ["pactl", "list", "sinks"],
            capture_output=True, text=True, timeout=5,
        )
        output = result.stdout.lower()
        return any(kw in output for kw in HEADPHONE_KEYWORDS)
    except Exception as e:
        print(f"[WARN] Linux audio check failed: {e}")
    return False


def show_notification(game_name: str) -> None:
    notification.notify(
        title="Headphones on — don't shout!",
        message=f"Playing {game_name}: use your mic, not your outside voice.",
        app_name="dont-shout",
        timeout=10,
    )
    print(f"[{time.strftime('%H:%M:%S')}] Notified for: {game_name}")


# ── Main loop ─────────────────────────────────────────────────────────────────

def main() -> None:
    print("dont-shout running... Ctrl+C to stop.")
    last_notified = 0.0

    while True:
        headphones = is_headphones_connected()
        game_running, game_name = is_game_running()

        now = time.time()
        if headphones and game_running and (now - last_notified) >= NOTIFICATION_COOLDOWN_SECONDS:
            show_notification(game_name)
            last_notified = now

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
