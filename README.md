# dont-shout

Reminds you to stop shouting when headphones are connected — plays a sound and shows a notification when your mic picks up that you're speaking too loudly.

## How it works

On startup it listens to your mic for 3 seconds to measure ambient noise, then sets a threshold automatically. No manual calibration needed.

While running it continuously monitors the mic. When your voice exceeds the threshold and headphones are connected, it:
1. Speaks a voice alert through your headphones
2. Shows a desktop notification

## Requirements

- Python 3.10+
- Windows / macOS / Linux

## Install (Windows)

Double-click `install.bat`. It will:
- Install all Python dependencies (including the tricky `pyaudio` on Windows)
- Add dont-shout to your Windows startup folder so it runs on every login
- Offer to start it immediately

The only prerequisite is Python from [python.org](https://python.org) — tick **"Add Python to PATH"** during install.

## Install (macOS / Linux)

```bash
pip install -r requirements.txt
python main.py
```

## Tuning sensitivity

All settings are at the top of `main.py`:

| Constant | Default | Description |
|----------|---------|-------------|
| `ALERT_MESSAGE` | `"Don't shout..."` | The text spoken aloud when you trigger an alert |
| `SENSITIVITY` | `3.0` | Multiplier over ambient noise to trigger. Raise if too sensitive, lower if not enough. |
| `COOLDOWN_SECONDS` | `10` | Minimum seconds between alerts |
| `CONSECUTIVE_CHUNKS_REQUIRED` | `3` | Loud chunks in a row before alerting (prevents spike false-positives) |
| `AMBIENT_SAMPLE_SECONDS` | `3` | How long to sample on startup |
| `HEADPHONE_KEYWORDS` | `["headphone", ...]` | Device name substrings to match |

## Stopping it

Task Manager → find `pythonw.exe` → End Task.

To remove from startup: `Win+R` → `shell:startup` → delete `dont-shout.vbs`.
