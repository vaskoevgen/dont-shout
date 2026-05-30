# dont-shout

Reminds you to stop shouting when headphones are connected — speaks a voice alert and shows a notification when your mic picks up that you're talking too loudly.

Works alongside games and other apps — the mic is shared, not grabbed exclusively.

## How it works

On startup it listens to your mic for 3 seconds to measure ambient noise, then sets a threshold automatically. No manual calibration needed.

While running it continuously monitors the mic. When your voice exceeds the threshold and headphones are connected, it:
1. Speaks a voice alert through your headphones
2. Shows a desktop notification

On Windows the mic is opened via **sounddevice** in WASAPI shared mode, so games, Discord, and other apps can use the mic at the same time.

## Requirements

- Python 3.10+
- Windows / macOS / Linux

## Install (Windows)

1. Install Python from [python.org](https://python.org) — tick **"Add Python to PATH"** during install
2. Double-click `install.bat`

`install.bat` will:
- Stop any previously running instance automatically
- Install all Python dependencies (`sounddevice`, `numpy`, `plyer`, `pycaw`, `pyttsx3`)
- Add dont-shout to your Windows startup folder so it runs on every login
- Offer to start it immediately

**Updating:** `git pull` then run `install.bat` again — it handles everything.

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
| `CONSECUTIVE_CHUNKS_REQUIRED` | `3` | Loud chunks in a row before alerting (prevents false-positives from single spikes) |
| `AMBIENT_SAMPLE_SECONDS` | `3` | How long to sample ambient noise on startup — stay quiet during this |
| `HEADPHONE_KEYWORDS` | `["headphone", ...]` | Device name substrings used to detect headphones |
| `HEADPHONE_CHECK_INTERVAL` | `5.0` | How often (seconds) to re-check if headphones are connected |

### Headphones not detected?

Run this in a command prompt to print your actual audio device names:

```cmd
python -c "from pycaw.pycaw import AudioUtilities; [print(d) for d in AudioUtilities.GetAllDevices()]"
```

Add the relevant word to `HEADPHONE_KEYWORDS` in `main.py`.

## Stopping it

Task Manager → find `pythonw.exe` → End Task.

To remove from startup: `Win+R` → `shell:startup` → delete `dont-shout.vbs`.
