# Changelog

## 0.1.4 - 2026-11-05

- fix a race where the reconcile loop could start local ad-break music just
  after an ad ended, leaving mpv playing over the next Spotify track
- re-check the ad state after volume changes and stop local music if the ad
  ends while the player is starting

## 0.1.3 - 2026-11-05

- fix Spotify staying muted when it recreates its audio stream around ad
  boundaries; restore now recovers untracked Spotify streams that inherited
  the service's mute state

## 0.1.2 - 2026-11-04

- add a one-shot installation prompt for AI coding agents to both READMEs
- make the installer restart an existing service so it picks up new code and
  configuration

## 0.1.1 - 2026-11-04

- add a Simplified Chinese README
- expand the legal notice: unofficial status, trademark attribution, no ad
  blocking, ToS/account risk, local music rights, and liability limits
- add contribution licensing and legal-hygiene guidance
- include the disclaimer and docs in source distributions

## 0.1.0 - 2026-11-04

First independent release of `spotify-adbreak`, derived from
`spotify-ad-muter` 0.2.1 (MIT).

- detect Spotify ads over MPRIS, including track-ID, title, and URL fallbacks
- mute only Spotify's PipeWire/PulseAudio stream and restore its prior state
- play a shuffled local playlist through `mpv` during an ad
- stop local music and unmute Spotify when the ad ends
- pre-mute Spotify during the final `premute_ms` of a track so the first sound
  of a following ad cannot leak
- release the pre-mute guard on normal track changes, loop-one restarts, seeks,
  and a two-second safety timeout
- support config files, CLI overrides, a systemd user service, and an installer
- 42 automated tests across ad detection, muting, playback, config, and CLI

### Upstream history

The codebase started as a Python rewrite of the archived
`danigm/spotify-ad-blocker` GNOME Shell extension and was later developed as
`Rishabh-Bajpai/spotify-ad-muter`. See `NOTICE` for attribution.
