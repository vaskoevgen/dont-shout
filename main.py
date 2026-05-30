#!/usr/bin/env python3
"""
dont-shout: speaks a warning when you talk too loudly
into your mic while headphones are connected.

On Windows: reads the mic peak meter via Windows Audio API —
no audio stream is opened, so the mic stays completely free for games.

On macOS/Linux: uses sounddevice in shared mode.
"""

import os
import platform
import subprocess
import time
from pathlib import Path

import pyttsx3
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

# How often (seconds) to poll the mic level (Windows peak meter path).
POLL_INTERVAL = 0.05

# ── Windows peak meter (no audio stream needed) ────────────────────────────────

_windows_meter = None


def _init_windows_meter():
    """Initialize COM meter object once and cache it."""
    global _windows_meter
    if _windows_meter is None:
        import comtypes
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import IAudioMeterInformation, IMMDeviceEnumerator, CLSID_MMDeviceEnumerator

        enumerator = comtypes.CoCreateInstance(
            CLSID_MMDeviceEnumerator, IMMDeviceEnumerator, CLSCTX_ALL
        )
        mic = enumerator.GetDefaultAudioEndpoint(1, 0)  # eCapture=1, eConsole=0
        interface = mic.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
        _windows_meter = cast(interface, POINTER(IAudioMeterInformation))
    return _windows_meter


def get_mic_peak_windows() -> float:
    """Return mic peak level (0.0–1.0) via Windows meter API. No stream, no exclusive access."""
    try:
        return _init_windows_meter().GetPeakValue()
    except Exception as e:
        print(f"[WARN] Mic meter read failed: {e}")
        return 0.0


# ── sounddevice path (macOS / Linux) ──────────────────────────────────────────

def open_mic_stream():
    import numpy as np
    import sounddevice as sd
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


def alert() -> None:
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


# ── Main loop ─────────────────────────────────────────────────────────────────

def run(get_level):
    """Shared monitoring loop. get_level() must return a float 0.0–1.0."""
    print(f"Measuring ambient for {AMBIENT_SAMPLE_SECONDS}s — stay quiet...", flush=True)
    samples = []
    deadline = time.time() + AMBIENT_SAMPLE_SECONDS
    while time.time() < deadline:
        samples.append(get_level())
        time.sleep(POLL_INTERVAL)

    baseline = max(samples) if samples else 0.01
    threshold = max(baseline * SENSITIVITY, 0.01)
    print(f"Ambient peak: {baseline:.4f}  →  threshold: {threshold:.4f}\n")
    print("dont-shout running... Ctrl+C to stop.")

    last_alerted = 0.0
    last_headphone_check = 0.0
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

        if (
            loud_streak >= CONSECUTIVE_REQUIRED
            and (now - last_alerted) >= COOLDOWN_SECONDS
            and headphones
        ):
            alert()
            last_alerted = now
            loud_streak = 0

        time.sleep(POLL_INTERVAL)


def main() -> None:
    PID_FILE.write_text(str(os.getpid()))

    try:
        if platform.system() == "Windows":
            print("Windows detected: using peak meter API (mic stays free for games).")
            run(get_mic_peak_windows)
        else:
            stream, np = open_mic_stream()
            try:
                run(lambda: get_mic_peak_stream(stream, np))
            finally:
                stream.stop()
                stream.close()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        PID_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
