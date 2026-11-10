# Quick guide

🇬🇧 English · 🇪🇸 [Español](guide.es.md) · [← Back to the README](../README.md)

## How to open it

| From | Address |
|---|---|
| Phone (same WiFi as the PC) | `http://mixer.local:8080` |
| If that doesn't open | `http://192.168.x.x:8080` (your PC's IP; the server prints it on start) |
| The PC itself | `http://localhost:8080` (no PIN asked) |

## PIN

- **Create or change it:** double-click `setup-pin.bat`.
- **Remove it:** run the same script and leave the PIN empty.
- Each device asks for it **once** and remembers it for 90 days (renewed every time you open the Mixer).
- After 5 wrong attempts in a row from the same device it is locked for 5 minutes (doubling if it keeps trying).
- If you change the PIN, every device has to enter it again.

## Start-up

- It starts by itself when you log in to Windows (`MixerRemoto` shortcut in the Startup folder).
- A watchdog (`supervisor.py`) restarts it if it crashes or hangs. Logs: `supervisor.log` and `server.log`.
- **Install or repair** autostart: `install-autostart.bat`.
- **Start it by hand** (with a window, to see messages): `start.bat`.

## Discord (lower the music when someone talks)

Step-by-step setup: [discord.en.md](discord.en.md) (`setup-discord.bat`). Connection log: `rpc.log`.

## Language

The interface follows your browser's language and has an **ES · EN** button at the very bottom. Console messages and logs follow the Windows language; you can force it with the environment variable `MIXER_LANG=es` or `MIXER_LANG=en`.

## If something fails

| Symptom | What to do |
|---|---|
| "Reconnecting…" on the phone | The PC is off or asleep, or the Mixer isn't running. |
| "There is no active audio output" | Turn on your headphones or plug in speakers. |
| It asks for the PIN again | Browser data was cleared, 90 days passed, or the PIN was changed. |

## Files you must not share

`pin.json` (PIN hash) and `discord_rpc.json` (your Discord application's codes). Both are in `.gitignore`.
