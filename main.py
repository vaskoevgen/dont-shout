#!/usr/bin/env python3
"""
dont-shout: speaks a warning when you talk too loudly
into your mic while headphones are connected.

On Windows: reads the mic peak meter via Windows Audio API —
no audio stream is opened, so the mic stays completely free for games.

On macOS/Linux: uses sounddevice in shared mode.

Shows a system tray icon with current status.
"""

import os
import platform
import subprocess
import threading
import time
from pathlib import Path

import pystray
import pyttsx3
from PIL import Image, ImageDraw
from plyer import notification

PID_FILE = Path(__file__).parent / ".dont-shout.pid"

# ── Configuration ─────────────────────────────────────────────────────────────

# Message spoken aloud when you're too loud.
ALERT_MESSAGE = "Don't shout, your mic can hear you fine."

# Multiplier over ambient noise level to trigger an alert.
# Increase if too sensitive, decrease if not sensitive enough.
SENSITIVITY = 3.0

# Seconds to wait before alerting again.
COOLDOWN_SECONDS = 10

# How many consecutive loud readings before triggering (avoids single-noise spikes).
CONSECUTIVE_REQUIRED = 3

# Seconds to sample ambient noise on startup — stay quiet during this.
AMBIENT_SAMPLE_SECONDS = 3

# Device name substrings used to detect headphones.
HEADPHONE_KEYWORDS = [
    "headphone", "headset", "earphone", "earbuds", "airpods",
]

# How often (seconds) to re-check if headphones are connected.
HEADPHONE_CHECK_INTERVAL = 5.0

# How often (seconds) to poll the mic level.
POLL_INTERVAL = 0.05

# ── Tray icon ─────────────────────────────────────────────────────────────────

def make_level_icon(level: float, threshold: float, headphones: bool) -> Image.Image:
    """Draw a live bar chart: bar height = mic level, yellow line = threshold.
    Bar is always shown so the user can verify the mic is being read.
    Color indicates state:
      green  = headphones detected, below threshold
      red    = above threshold (about to alert)
      blue   = mic active but headphones not detected (alerts won't fire)
    Small dot in top-right corner: green=headphones on, gray=no headphones.
    """
    SIZE = 64
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Dark background
    draw.rectangle([0, 0, SIZE - 1, SIZE - 1], fill=(30, 30, 30))

    # Level bar — always visible
    bar_h = int(min(level, 1.0) * (SIZE - 2))
    if level >= threshold:
        bar_color = (210, 50, 50)   # red: above threshold
    elif headphones:
        bar_color = (30, 180, 30)   # green: headphones on, below threshold
    else:
        bar_color = (60, 120, 210)  # blue: no headphones, just monitoring

    if bar_h > 0:
        draw.rectangle([4, SIZE - 1 - bar_h, SIZE - 5, SIZE - 1], fill=bar_color)

    # Threshold line in yellow
    t_y = SIZE - 1 - int(min(threshold, 1.0) * (SIZE - 2))
    draw.line([0, t_y, SIZE - 1, t_y], fill=(255, 220, 0), width=2)

    # Small headphone indicator dot (top-right)
    dot_color = (30, 200, 30) if headphones else (130, 130, 130)
    draw.ellipse([SIZE - 14, 2, SIZE - 2, 14], fill=dot_color)

    return img


def update_tray(
    icon: pystray.Icon,
    headphones: bool,
    alerted: bool = False,
    level: float = 0.0,
    threshold: float = 0.0,
) -> None:
    level_pct = int(level * 100)
    threshold_pct = int(threshold * 100)
    icon.icon = make_level_icon(level, threshold, headphones)
    if alerted:
        icon.title = f"dont-shout: ALERT! level {level_pct}% / threshold {threshold_pct}%"
    elif headphones:
        icon.title = f"dont-shout: level {level_pct}% / threshold {threshold_pct}%"
    else:
        icon.title = f"dont-shout: no headphones detected"


# ── Mic capture (WASAPI shared mode on Windows, default on macOS/Linux) ────────

def open_mic_stream():
    import numpy as np
    import sounddevice as sd

    if platform.system() == "Windows":
        # Explicitly use WASAPI shared mode so the mic is shared with games
        hostapis = sd.query_hostapis()
        wasapi = next((a for a in hostapis if "WASAPI" in a["name"]), None)
        if wasapi and wasapi["default_input_device"] >= 0:
            try:
                extra = sd.WasapiSettings(exclusive=False)
                stream = sd.InputStream(
                    device=wasapi["default_input_device"],
                    samplerate=44100, channels=1, dtype="int16", blocksize=1024,
                    extra_settings=extra,
                )
                stream.start()
                print("Mic opened via WASAPI shared mode.")
                return stream, np
            except Exception as e:
                print(f"[WARN] WASAPI shared mode failed, falling back: {e}")

    stream = sd.InputStream(samplerate=44100, channels=1, dtype="int16", blocksize=1024)
    stream.start()
    return stream, np


def get_mic_peak_stream(stream, np) -> float:
    data, _ = stream.read(1024)
    return float(np.sqrt(np.mean(data.astype(np.float64) ** 2))) / 32768.0


# ── Headphone detection ────────────────────────────────────────────────────────

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
        return any(kw in result.stdout.lower() for kw in HEADPHONE_KEYWORDS)
    except Exception as e:
        print(f"[WARN] macOS audio check failed: {e}")
    return False


def _check_linux() -> bool:
    try:
        result = subprocess.run(
            ["pactl", "list", "sinks"],
            capture_output=True, text=True, timeout=5,
        )
        return any(kw in result.stdout.lower() for kw in HEADPHONE_KEYWORDS)
    except Exception as e:
        print(f"[WARN] Linux audio check failed: {e}")
    return False


# ── Alert ─────────────────────────────────────────────────────────────────────

_tts_engine: pyttsx3.Engine | None = None


def get_tts_engine() -> pyttsx3.Engine | None:
    global _tts_engine
    if _tts_engine is None:
        try:
            _tts_engine = pyttsx3.init()
        except Exception as e:
            print(f"[WARN] TTS init failed: {e}")
    return _tts_engine


def alert(icon: pystray.Icon, level: float, threshold: float) -> None:
    update_tray(icon, headphones=True, alerted=True, level=level, threshold=threshold)

    engine = get_tts_engine()
    if engine:
        try:
            engine.say(ALERT_MESSAGE)
            engine.runAndWait()
        except Exception as e:
            print(f"[WARN] Speech failed: {e}")

    notification.notify(
        title="Don't shout!",
        message=ALERT_MESSAGE,
        app_name="dont-shout",
        timeout=5,
    )
    print(f"[{time.strftime('%H:%M:%S')}] Alert fired")


# ── Monitoring loop (runs in background thread) ────────────────────────────────

def run(icon: pystray.Icon, get_level) -> None:
    icon.title = f"dont-shout: measuring ambient for {AMBIENT_SAMPLE_SECONDS}s..."

    samples = []
    deadline = time.time() + AMBIENT_SAMPLE_SECONDS
    while time.time() < deadline:
        samples.append(get_level())
        time.sleep(POLL_INTERVAL)

    baseline = max(samples) if samples else 0.01
    threshold = max(baseline * SENSITIVITY, 0.01)
    print(f"Ambient peak: {baseline:.4f}  →  threshold: {threshold:.4f}")

    last_alerted = 0.0
    last_headphone_check = 0.0
    last_tray_update = 0.0
    headphones = False
    loud_streak = 0

    while True:
        level = get_level()

        if level > threshold:
            loud_streak += 1
        else:
            loud_streak = 0

        now = time.time()
        if now - last_headphone_check >= HEADPHONE_CHECK_INTERVAL:
            headphones = is_headphones_connected()
            last_headphone_check = now

        # Update tray tooltip ~4x per second (not every 50ms poll to avoid flicker)
        if now - last_tray_update >= 0.25:
            update_tray(icon, headphones, level=level, threshold=threshold)
            last_tray_update = now

        if (
            loud_streak >= CONSECUTIVE_REQUIRED
            and (now - last_alerted) >= COOLDOWN_SECONDS
            and headphones
        ):
            alert(icon, level=level, threshold=threshold)
            last_alerted = now
            loud_streak = 0
            # restore icon color after alert
            time.sleep(2)
            update_tray(icon, headphones, level=level, threshold=threshold)

        time.sleep(POLL_INTERVAL)


# ── Main ──────────────────────────────────────────────────────────────────────

def print_audio_devices() -> None:
    """Print all audio devices so you can find the right keyword for HEADPHONE_KEYWORDS."""
    try:
        from pycaw.pycaw import AudioUtilities
        print("Audio devices found:")
        for d in AudioUtilities.GetAllDevices():
            print(f"  {d}")
    except Exception as e:
        print(f"Error: {e}")


def main() -> None:
    PID_FILE.write_text(str(os.getpid()))

    icon = pystray.Icon(
        "dont-shout",
        icon=make_level_icon(0.0, 0.0, False),
        title="dont-shout: starting...",
        menu=pystray.Menu(
            pystray.MenuItem("dont-shout", None, enabled=False),
            pystray.MenuItem("Stop", lambda icon, item: icon.stop()),
        ),
    )

    stream, np_mod = open_mic_stream()
    get_level = lambda: get_mic_peak_stream(stream, np_mod)

    thread = threading.Thread(target=run, args=(icon, get_level), daemon=True)
    thread.start()

    try:
        icon.run()  # blocks main thread; tray icon lives here
    finally:
        if stream:
            stream.stop()
            stream.close()
        PID_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    import sys
    if "--list-devices" in sys.argv:
        print_audio_devices()
    else:
        main()
