[English](README.md) | [简体中文](README.zh-CN.md)

# Spotify Ad Break

[![CI](https://github.com/gg686-jkl/spotify-adbreak/actions/workflows/ci.yml/badge.svg)](https://github.com/gg686-jkl/spotify-adbreak/actions/workflows/ci.yml)

`spotify-adbreak` is a standalone Python service for Linux that detects Spotify
ads over MPRIS, mutes only Spotify's own audio stream, and fills the ad break
with a shuffled playlist of local music. When the ad ends, the local music stops
and Spotify is unmuted automatically.

This is an independent project derived from
[spotify-ad-muter](https://github.com/Rishabh-Bajpai/spotify-ad-muter) by
Rishabh Bajpai (MIT). The upstream project was itself inspired by
[danigm/spotify-ad-blocker](https://github.com/danigm/spotify-ad-blocker).
The original copyright notice is retained in `LICENSE`; see `NOTICE` for full
attribution.

> **Unofficial and not affiliated with Spotify.** This tool mutes Spotify's
> local audio stream during an ad; it does not block, skip, or remove ads. Use
> at your own risk: it may conflict with Spotify's Terms of Service. See
> [DISCLAIMER.md](DISCLAIMER.md). This is not legal advice.

## For AI agents

If you are an AI coding agent asked to install this project, expand and copy
the prompt below. It is self-contained, asks before privileged or destructive
steps, and verifies the result instead of assuming success.

<details>
<summary><strong>One-shot installation prompt (copy this)</strong></summary>

```text
You are an installation and configuration agent for the open-source project
"spotify-adbreak". Your job is to install and configure it for the current
Linux desktop user, end to end, with minimal questions.

Repository: https://github.com/gg686-jkl/spotify-adbreak
License: MIT. Read README.md and DISCLAIMER.md before starting.

The user asked you to do this. This project is unofficial and is not affiliated
with Spotify. It mutes Spotify's local audio stream during ads; it does not
block, skip, or remove ads, modify the Spotify client, or bypass DRM. Using it
may conflict with Spotify's Terms of Service. Explain this briefly and proceed
only if the user accepts.

Ask only when you need sudo consent, missing critical information, or a
destructive action. Otherwise work autonomously.

SAFETY RULES
- Work as the logged-in desktop user. Do not run the whole setup as root.
- Ask before any sudo/package-install command and show the exact command.
- Never download music, Spotify content, or anything copyrighted.
- Never modify or delete the user's music, Spotify files, or unrelated config.
- Never kill unrelated processes. Do not use "pkill -f spotify" or other broad
  pkill patterns; use systemctl --user for this project's services.
- Back up any existing config or systemd unit before changing it.
- Do not commit, push, publish, or create GitHub resources.
- Never ask for or handle Spotify passwords.
- If a required condition is missing (systemd user session, Spotify client,
  Python 3.11+, working audio), stop and report clearly.
- Do not claim success until the service is active and the startup log appears.

STEP 1 - INSPECT
  cat /etc/os-release
  printf '%s\n' "$XDG_CURRENT_DESKTOP" "$XDG_SESSION_TYPE"
  pactl info
  python3 --version
  command -v mpv git systemctl
  systemctl --user is-system-running || true
  pgrep -a -f '[s]potify' || true

Check: Linux desktop, PipeWire or PulseAudio responding, Python >= 3.11,
a working systemd --user session, and git. If Spotify is not running, ask the
user to start and sign in; do not handle credentials.

STEP 2 - INSTALL PREREQUISITES
First run "pactl info". If it already works, do not install or replace a sound
server; install only the missing tools (python3, venv, pip, mpv, pactl).

If pactl is missing or not connecting, ask before installing audio packages.
Use the matching package manager and adapt to whether the system runs PipeWire
or PulseAudio:
  Arch/Manjaro (PipeWire): sudo pacman -S --needed python mpv libpulse pipewire-pulse
  Arch/Manjaro (PulseAudio): sudo pacman -S --needed python mpv libpulse pulseaudio
  Debian/Ubuntu: sudo apt update && sudo apt install -y python3 python3-venv python3-pip mpv libpulse0 pulseaudio-utils
  Fedora: sudo dnf install -y python3 python3-pip mpv pulseaudio-libs pulseaudio-utils
Do not replace the user's audio stack. Re-run "pactl info" afterwards. If sudo
is not available and packages are missing, stop and report the missing packages.

STEP 3 - GET THE CODE
  mkdir -p ~/projects
  cd ~/projects
  if [ -d spotify-adbreak/.git ]; then
      cd spotify-adbreak
      git status --short
      # If dirty, stop and ask. Otherwise: git pull --ff-only
  else
      git clone https://github.com/gg686-jkl/spotify-adbreak.git
      cd spotify-adbreak
  fi
Do not clone into a directory that already contains unrelated files.

STEP 4 - INSTALL IN A VENV
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -e .
  .venv/bin/spotify-adbreak --help

STEP 5 - CONFIGURE
  mkdir -p ~/.config/spotify-adbreak
If ~/.config/spotify-adbreak/config.toml exists, back it up to
config.toml.bak-YYYYmmdd-HHMMSS before editing, and preserve the user's
existing values. Only add missing keys or change values the user asks for.

Set MUSIC_DIR to the user's music directory, defaulting to ~/Music. Create it
if missing. Search recursively for these extensions:
mp3 flac m4a ogg opus wav aac wma aiff alac oga mka

Write ~/.config/spotify-adbreak/config.toml with:
  ad_volume_percent = 0
  unmute_delay_ms = 500
  poll_interval_ms = 200
  premute_ms = 800
  log_level = "INFO"
  stream_match_mode = "relaxed"
  local_music_enabled = true|false
  music_dir = "/absolute/path/to/Music"
  music_volume_percent = 70
  music_player = "mpv"

If no playable audio files exist, set local_music_enabled = false and tell the
user to add music later. Do not download anything. Use an absolute music_dir
in the file. Do not install Python packages outside the venv and do not use
sudo for pip.

STEP 6 - HANDLE AN EXISTING INSTALLATION
  systemctl --user list-unit-files 'spotify-ad-muter.service' 'spotify-adbreak.service'

If an old spotify-ad-muter.service is active or enabled:
  systemctl --user disable --now spotify-ad-muter.service
Move its unit file to
~/.config/systemd/user/spotify-ad-muter.service.disabled-<timestamp>.
Preserve the old project and old config; do not delete them.

If spotify-adbreak.service already exists, back up its unit file and config,
then reinstall/restart. Never run two copies of the watcher at the same time.

STEP 7 - INSTALL THE SERVICE
  cd ~/projects/spotify-adbreak
  ./scripts/install.sh

The installer creates the venv if needed, preserves an existing config,
installs ~/.config/systemd/user/spotify-adbreak.service, and enables/starts it.
Then restart the unit so an existing process picks up the current code and
config:
  systemctl --user restart spotify-adbreak.service
If the script fails, do the equivalent steps manually and report the exact
error.

STEP 8 - VERIFY
  systemctl --user is-active spotify-adbreak.service
  systemctl --user is-enabled spotify-adbreak.service
  journalctl --user -u spotify-adbreak.service -n 30 --no-pager

Look for: "Watching Spotify ads; local ad-break music: ..."
Confirm there is no traceback or error. If Spotify is playing and no ad is
active, confirm its sink input is not muted with "pactl list sink-inputs". Do
not mute or unmute other applications.

Do not wait for a real ad. Tell the user the final test is to keep playing
Spotify until the next ad break. Optionally run:
  .venv/bin/python -m unittest discover -s tests -q

STEP 9 - REPORT
Report:
- repository path
- service status and enabled state
- config path and whether local music is enabled
- music directory and number of tracks found
- the exact log command:
  journalctl --user -u spotify-adbreak.service -f
- any warnings or skipped steps
- a short reminder: unofficial, mutes ads locally, does not block them, and
  may conflict with Spotify's Terms of Service.

If anything fails, stop and report the exact command and error. Do not hide
failures or claim the installation succeeded without verification.
```

</details>

## What it does

```text
Spotify ad starts
  -> mute only Spotify's PipeWire/PulseAudio stream
  -> start a shuffled mpv playlist from ~/Music
Spotify ad ends
  -> stop the local playlist
  -> unmute Spotify (after a short delay)
```

Before a track reaches its final ~0.8 s, the service mutes Spotify ahead of
time ("pre-mute guard"). If the next item is an ad, its very first sound is
already silent; if a normal song starts instead, the guard is released
immediately. This removes the short burst of ad audio caused by MPRIS metadata
arriving a fraction of a second after playback starts.

The rest of the system's audio is never muted, so notifications, videos, and
calls keep their sound.

## Disclaimer

This is an independent project and is not affiliated with, endorsed by, or
sponsored by Spotify AB or GNOME. It mutes the local Spotify audio stream; it
does not block, skip, or remove ads, modify the Spotify client, or bypass DRM.
Using it may conflict with Spotify's Terms of Service, and you are responsible
for complying with those terms and applicable law. Read the full
[DISCLAIMER.md](DISCLAIMER.md); it is not legal advice.

SPOTIFY and the Spotify logo are trademarks of Spotify AB. All other marks
belong to their respective owners. No trademark license is granted.

## Why this exists

The original GNOME Shell extension depends on GNOME Shell internals and can
break across GNOME releases. The upstream Python rewrite moved the runtime to
stable Linux interfaces:

- session D-Bus MPRIS metadata for ad detection
- PulseAudio or PipeWire's Pulse compatibility layer for per-app muting
- `mpv` for local ad-break playback

This project keeps that foundation and adds local ad-break music plus the
pre-mute guard that hides the first moment of an ad.

## Features

- detects ads from track IDs starting with `spotify:ad`, `/com/spotify/ad/`, or
  `https://open.spotify.com/ad/`, with an `Advertisement` title/URL fallback
- pre-mutes Spotify just before a track ends so the first ad sound cannot leak
- mutes only Spotify's stream, preserving every other application's audio
- plays a shuffled local playlist during the ad and stops it when the ad ends
- restores each Spotify stream to its previous mute/volume state
- keeps muting newly created Spotify streams while an ad is active
- restarts the local player if it exits before the ad finishes
- runs cleanly as a foreground CLI app or a systemd user service

## Requirements

- Linux with PipeWire or PulseAudio (`pactl`/`pulsectl` compatible)
- Python 3.11+
- `mpv` installed for local ad-break music
- the official Spotify client running and logged in
- at least one audio file in the configured music directory

## Project layout

```text
.
├── src/spotify_adbreak/
│   ├── audio.py      # Spotify stream mute/restore
│   ├── cli.py        # command-line entry point
│   ├── config.py     # config file and CLI merging
│   ├── mpris.py      # ad detection and track-end pre-mute guard
│   ├── music.py      # local ad-break player (mpv)
│   └── service.py    # coordination
├── tests/
├── systemd/
└── docs/
```

## Setup

```bash
git clone https://github.com/gg686-jkl/spotify-adbreak.git
cd spotify-adbreak
python3 -m venv .venv
.venv/bin/pip install -e .
```

### One-click install

For local installation with automatic virtualenv creation, config setup,
systemd user service install, and auto-start on login:

```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

This will:

- create `.venv`
- install the app into the virtualenv
- create `~/.config/spotify-adbreak/config.toml` if missing
- install `~/.config/systemd/user/spotify-adbreak.service`
- enable and start the user service

To remove only the installed user service:

```bash
chmod +x scripts/uninstall.sh
./scripts/uninstall.sh
```

## Local music

Put the songs you want to hear during ads under `~/Music` (subdirectories are
scanned recursively). Supported extensions: `.mp3`, `.flac`, `.m4a`, `.ogg`,
`.opus`, `.wav`, `.aac`, `.wma`, `.aiff`, `.alac`, `.oga`, `.mka`.

`mpv` receives the whole directory as a shuffled, looping playlist, so each ad
break starts a different track. Changing `music_dir` to another folder (for
example an external drive) is fully supported.

## Run

```bash
.venv/bin/spotify-adbreak --log-level INFO
```

Example with explicit flags:

```bash
.venv/bin/spotify-adbreak \
  --ad-volume-percent 0 \
  --unmute-delay-ms 500 \
  --poll-interval-ms 200 \
  --premute-ms 800 \
  --stream-match-mode relaxed \
  --music-dir "$HOME/Music" \
  --music-volume-percent 70 \
  --log-level INFO
```

Disable the local music and only mute ads:

```bash
.venv/bin/spotify-adbreak --no-local-music
```

## Config

Create `~/.config/spotify-adbreak/config.toml`:

```toml
# 0 = full mute during ads (the stream is muted, not merely turned down)
ad_volume_percent = 0
unmute_delay_ms = 500
poll_interval_ms = 200
premute_ms = 800
log_level = "INFO"
stream_match_mode = "relaxed"

local_music_enabled = true
music_dir = "~/Music"
music_volume_percent = 70
music_stop_mode = "finish"
music_fade_out_ms = 2000
music_player = "mpv"
```

CLI flags override config values.

| Key | Meaning |
| --- | --- |
| `local_music_enabled` | play local music during ads |
| `music_dir` | directory scanned recursively for audio files |
| `music_volume_percent` | mpv volume for the ad-break playlist |
| `music_stop_mode` | `fade` (default) fades local music out at ad end; `finish` lets the current local track play to its natural end before Spotify returns |
| `music_fade_out_ms` | fade local music out over this long when an ad ends; `0` stops immediately (default `2000`) |
| `music_player` | player executable (must support `--shuffle`/`--loop-playlist`; `mpv` also gives smooth IPC fade-out) |
| `poll_interval_ms` | how quickly ads are noticed (200 ms recommended) |
| `premute_ms` | mute this long before a track ends to catch a following ad; `0` disables the guard |
| `unmute_delay_ms` | delay before Spotify is unmuted at ad end |

## systemd user service

```bash
mkdir -p ~/.config/systemd/user
sed "s|@PROJECT_ROOT@|$(pwd)|g" systemd/spotify-adbreak.service > ~/.config/systemd/user/spotify-adbreak.service
systemctl --user daemon-reload
systemctl --user enable --now spotify-adbreak.service
```

Follow logs with:

```bash
journalctl --user -u spotify-adbreak.service -f
```

## Verify

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/spotify-adbreak --log-level DEBUG
```

Then start Spotify and watch for these log lines:

```text
Ad detected: spotify:ad:...
Playing local music during ad: N track(s) ...
Ad finished, restoring volume in 500ms
Stopped local ad-break music
Restored Spotify stream volume for ...
```

You can also verify the mute separately while Spotify is playing:

```bash
pactl list sink-inputs | grep -A3 -i spotify
```

## Limitations

- The pre-mute guard covers the normal "song ends, then an ad starts" case.
  If Spotify inserts an ad in the middle of a track, up to one polling interval
  of audio can still be heard.
- This software does not block, skip, or remove ads. It only mutes Spotify's
  local audio stream and plays different audio during the break.
- Ad detection depends on metadata exposed by the Spotify desktop client. A
  client update can change or remove that metadata.
- Local music must be obtained and used legally in your jurisdiction.

## Troubleshooting

- **Ads are heard but no mute/switch happens.** The Spotify client may not be
  exposing ad metadata over MPRIS. Run with `--log-level DEBUG`; ad detection
  relies on the track ID/title. Also make sure only one Spotify instance is
  running.
- **Spotify is muted but no music plays.** Check that `music_dir` contains
  playable files and that `mpv` is installed. `journalctl` reports an empty
  directory or a missing player once.
- **Local music keeps playing for a moment after the ad.** `mpv` is terminated
  with SIGTERM; a stuck process is killed after 2 seconds.
- **Songs get cut off slightly early.** That is the pre-mute guard. Lower
  `premute_ms` (for example `400`) if you prefer a shorter guard; raise it if a
  sliver of ad audio still gets through.
- **Wrong output device.** Ad-break music follows the default PipeWire sink,
  just like Spotify. Change the system default sink if needed.

## Attribution and license

This project is MIT-licensed. It is derived from
[spotify-ad-muter](https://github.com/Rishabh-Bajpai/spotify-ad-muter) and its
ad-detection approach was inspired by
[danigm/spotify-ad-blocker](https://github.com/danigm/spotify-ad-blocker).

- Original copyright: Copyright (c) 2026 Rishabh Bajpai
- Modifications: Copyright (c) 2026 Kadel and spotify-adbreak contributors

See [LICENSE](LICENSE) and [NOTICE](NOTICE).

## Docs

- `docs/architecture.md`
- `docs/migration.md`

## CI

GitHub Actions runs the unit test suite and compile checks on pushes and pull
requests for Python `3.11` through `3.14`.
