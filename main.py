#!/usr/bin/env python3
"""
dont-shout: speaks a warning when you talk too loudly
into your mic while headphones are connected.

Threshold is measured automatically on startup from ambient noise —
no manual calibration needed.

Uses sounddevice (WASAPI shared mode on Windows) so the mic is shared
with games and other apps simultaneously.
"""

import os
import platform
import subprocess
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
import pyttsx3
from plyer import notification

PID_FILE = Path(__file__).parent / ".dont-shout.pid"

# ── Configuration ─────────────────────────────────────────────────────────────

# Message spoken aloud when you're too loud.
ALERT_MESSAGE = "Don't shout, your mic can hear you fine."

# Multiplier over ambient noise level to trigger an alert.
# 3.0 means "3x louder than the background" = you're speaking aloud.
# Increase if too sensitive, decrease if not sensitive enough.
SENSITIVITY = 3.0

# Seconds to wait before alerting again.
COOLDOWN_SECONDS = 10

# How many consecutive loud chunks before triggering (avoids single-noise spikes).
CONSECUTIVE_CHUNKS_REQUIRED = 3

# Seconds to sample ambient noise on startup — stay quiet during this.
AMBIENT_SAMPLE_SECONDS = 3

# Device name substrings used to detect headphones.
HEADPHONE_KEYWORDS = [
    "headphone", "headset", "earphone", "earbuds", "airpods",
]

# How often (seconds) to re-check if headphones are connected.
HEADPHONE_CHECK_INTERVAL = 5.0

# ── Audio constants ────────────────────────────────────────────────────────────

CHUNK = 1024
RATE = 44100  # standard Windows audio rate; required for WASAPI shared mode
CHANNELS = 1


def rms(data: np.ndarray) -> float:
    return float(np.sqrt(np.mean(data.astype(np.float64) ** 2)))


# ── Auto-calibration ───────────────────────────────────────────────────────────

def measure_ambient(stream: sd.InputStream) -> float:
    print(f"Measuring ambient noise for {AMBIENT_SAMPLE_SECONDS}s — stay quiet...", flush=True)
    samples = []
    for _ in range(int(RATE / CHUNK * AMBIENT_SAMPLE_SECONDS)):
        data, _ = stream.read(CHUNK)
        samples.append(rms(data))
    baseline = max(samples) if samples else 100.0
    threshold = max(baseline * SENSITIVITY, 200.0)
    print(f"Ambient peak: {baseline:.0f}  →  alert threshold: {threshold:.0f}\n")
    return threshold


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
    _speak(ALERT_MESSAGE)
    notification.notify(
        title="Don't shout!",
        message=ALERT_MESSAGE,
        app_name="dont-shout",
        timeout=5,
    )
    print(f"[{time.strftime('%H:%M:%S')}] Alert fired")


def _speak(text: str) -> None:
    engine = get_tts_engine()
    if engine is None:
        return
    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"[WARN] Speech failed: {e}")


# ── Main loop ─────────────────────────────────────────────────────────────────

def open_mic_stream() -> sd.InputStream:
    """Open mic in WASAPI shared mode on Windows so other apps can use it too."""
    if platform.system() == "Windows":
        try:
            hostapis = sd.query_hostapis()
            wasapi = next((api for api in hostapis if "WASAPI" in api["name"]), None)
            if wasapi and wasapi["default_input_device"] >= 0:
                # WasapiSettings(exclusive=False) forces shared mode at PortAudio level
                wasapi_settings = sd.WasapiSettings(exclusive=False)
                stream = sd.InputStream(
                    device=wasapi["default_input_device"],
                    samplerate=RATE, channels=CHANNELS,
                    dtype="int16", blocksize=CHUNK,
                    extra_settings=wasapi_settings,
                )
                stream.start()
                print("Mic opened via WASAPI shared mode.")
                return stream
        except Exception as e:
            print(f"[WARN] WASAPI shared mode failed, falling back: {e}")
    stream = sd.InputStream(samplerate=RATE, channels=CHANNELS, dtype="int16", blocksize=CHUNK)
    stream.start()
    return stream


def main() -> None:
    PID_FILE.write_text(str(os.getpid()))

    stream = open_mic_stream()

    threshold = measure_ambient(stream)
    print("dont-shout running... Ctrl+C to stop.")

    last_alerted = 0.0
    last_headphone_check = 0.0
    headphones = False
    loud_streak = 0

    try:
        while True:
            data, _ = stream.read(CHUNK)
            level = rms(data)

            if level > threshold:
                loud_streak += 1
            else:
                loud_streak = 0

            now = time.time()

            if now - last_headphone_check >= HEADPHONE_CHECK_INTERVAL:
                headphones = is_headphones_connected()
                last_headphone_check = now

            if (
                loud_streak >= CONSECUTIVE_CHUNKS_REQUIRED
                and (now - last_alerted) >= COOLDOWN_SECONDS
                and headphones
            ):
                alert()
                last_alerted = now
                loud_streak = 0

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        stream.stop()
        stream.close()
        PID_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
