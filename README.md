# dont-shout

Reminds you to stop shouting when headphones are connected — speaks a voice alert and shows a notification when your mic picks up that you're talking too loudly.

Works alongside games and other apps — the mic is never grabbed exclusively.

## How it works

On startup it samples the mic for 3 seconds to measure ambient noise, then sets a threshold automatically. No manual calibration needed.

While running it continuously monitors the mic. When your voice exceeds the threshold and headphones are connected, it:
1. Speaks a voice alert through your headphones
2. Shows a desktop notification

A **system tray icon** shows a live mic level bar:
- Green bar — headphones detected, below threshold
- Blue bar — mic is active, but headphones were not detected
- Red bar — level is above the alert threshold
- Yellow line — current threshold
- Dot in the top-right — green when headphones are detected, gray otherwise

The tray tooltip shows the current mic level and threshold.

**On Windows:** uses `sounddevice` with WASAPI shared mode, so the mic stays available to games, Discord, and other apps.

**On macOS/Linux:** uses `sounddevice` to sample the mic.

## Remote TTS messages

The app also polls `TTS_MESSAGE_URL` every `TTS_POLL_INTERVAL` seconds. If the remote text file is non-empty and changed since the last check, dont-shout speaks that text through the same TTS engine.

By default this points at:

```text
https://raw.githubusercontent.com/vaskoevgen/dont-shout/tts-messages/message.txt
```

Change `TTS_MESSAGE_URL` in `main.py` if you want to use your own text endpoint.

## Requirements

- Python 3.10+
- Windows / macOS / Linux

## Install (Windows)

1. Install Python from [python.org](https://python.org) — tick **"Add Python to PATH"** during install
2. Double-click `install.bat`

`install.bat` will:
- Stop any previously running instance automatically
- Install Python dependencies (`sounddevice`, `numpy`, `plyer`, `pycaw`, `pyttsx3`, `pystray`, `Pillow`)
- Add dont-shout to your Windows startup folder so it runs on every login
- Offer to start it immediately

**Updating:** `git pull` then run `install.bat` again — it handles everything.

## Uninstall (Windows)

Double-click `uninstall.bat`.

It will:
- Stop the running dont-shout instance if one is found
- Remove the startup shortcut
- Remove the generated `launch.vbs`

The app files stay in this folder so you can delete them manually or keep the repo.

## Install (macOS / Linux)

```bash
pip install -r requirements.txt
python main.py
```

## Tuning sensitivity

All settings are at the top of `main.py`:

| Constant | Default | Description |
|----------|---------|-------------|
| `ALERT_MESSAGE` | `"Don't shout..."` | The text spoken aloud when alert fires |
| `SENSITIVITY` | `3.0` | Multiplier over ambient noise to trigger. Raise if too sensitive, lower if not enough. |
| `COOLDOWN_SECONDS` | `10` | Minimum seconds between alerts |
| `CONSECUTIVE_REQUIRED` | `3` | Loud readings in a row before alerting (prevents false-positives from single spikes) |
| `AMBIENT_SAMPLE_SECONDS` | `3` | How long to sample ambient noise on startup — stay quiet during this |
| `HEADPHONE_KEYWORDS` | `["headphone", ...]` | Device name substrings used to detect headphones |
| `HEADPHONE_CHECK_INTERVAL` | `5.0` | How often (seconds) to re-check if headphones are connected |
| `POLL_INTERVAL` | `0.05` | How often (seconds) to sample the mic level |
| `TTS_MESSAGE_URL` | GitHub raw text URL | Remote text file to speak when its content changes |
| `TTS_POLL_INTERVAL` | `90` | How often (seconds) to check for remote TTS messages |

### Headphones not detected?

Run this in a command prompt to print your actual audio device names:

```cmd
python -c "from pycaw.pycaw import AudioUtilities; [print(d) for d in AudioUtilities.GetAllDevices()]"
```

Add the relevant word to `HEADPHONE_KEYWORDS` in `main.py`.

## Stopping it

On Windows, run `uninstall.bat` to stop dont-shout and remove it from startup.

To stop it temporarily without uninstalling: Task Manager → find `pythonw.exe` → End Task.

On macOS/Linux, press `Ctrl+C` in the terminal where `python main.py` is running.
