# Design Notes and History

This project is a continuation of
[spotify-ad-muter](https://github.com/Rishabh-Bajpai/spotify-ad-muter), which
started as a standalone Python rewrite of the
[danigm/spotify-ad-blocker](https://github.com/danigm/spotify-ad-blocker)
GNOME Shell extension.

The extension muted Spotify by watching MPRIS metadata, but it depended on
GNOME Shell extension APIs. The Python service keeps the same ad-detection
approach while using stable Linux interfaces:

- session D-Bus MPRIS for metadata
- PulseAudio/PipeWire for per-stream muting
- `mpv` for local ad-break playback

## Differences from the GNOME extension

- no GNOME panel button or preferences UI
- no dependency on GNOME Shell version compatibility
- restores the previous per-stream state instead of forcing one volume
- runs as a regular CLI app or a systemd user service
- can play local music and pre-mute before a track ends

## Why the archived extension is not bundled

The GNOME extension is GPL-3.0, while this project is MIT. To keep the
licensing of this repository unambiguous, the extension source is not included.
It remains available at its original repository:
<https://github.com/danigm/spotify-ad-blocker>.
