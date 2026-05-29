# dont-shout

Reminds you to use your mic (not your outside voice) when headphones are connected and a game is running.

## How it works

Every few seconds it checks:
1. Are headphones connected?
2. Is a game running?

If both are true, it shows a desktop notification: **"Headphones on — don't shout!"**

## Requirements

- Python 3.10+
- Windows / macOS / Linux

## Install & Run

### Windows (automatic)

Run the install script once — it sets up Python dependencies and adds the app to Windows startup:

```bat
install.bat
```

Then start it manually the first time (or just reboot):

```bat
pythonw main.py
```

### Manual (any OS)

```bash
pip install -r requirements.txt

# Windows only:
pip install pycaw

python main.py
```

## Configuration

All settings are at the top of `main.py` — just edit the constants directly:

| Constant | Default | Description |
|----------|---------|-------------|
| `CHECK_INTERVAL_SECONDS` | `5` | How often to check |
| `NOTIFICATION_COOLDOWN_SECONDS` | `60` | Min time between notifications |
| `HEADPHONE_KEYWORDS` | `["headphone", ...]` | Device name substrings to match |
| `GAMES` | `[...]` | Game process names to watch for |

### Adding a game

1. Start the game
2. Open Task Manager → Details tab
3. Copy the process name (without `.exe`)
4. Add it (lowercase) to the `GAMES` list in `main.py`

## Stopping it

If started via `install.bat`, it runs as a background process on login.
To stop it: Task Manager → find `pythonw.exe` → End Task.

To remove from startup: press `Win+R`, type `shell:startup`, delete the `dont-shout.vbs` shortcut.
