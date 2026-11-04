# Architecture

The app has four core pieces:

- `mpris.py` polls Spotify's MPRIS metadata over the session D-Bus
- `audio.py` finds Spotify sink inputs and mutes only those streams through PulseAudio/PipeWire
- `music.py` owns the temporary `mpv` ad-break playlist
- `service.py` coordinates ad detection, music switching, delayed restore, and stream reconciliation

## Flow

1. Read `Metadata`, `PlaybackStatus`, and `Position` from
   `org.mpris.MediaPlayer2.spotify`
2. Treat IDs starting with `spotify:ad`, `/com/spotify/ad/`, or
   `https://open.spotify.com/ad/` as ads, with an `Advertisement` title/URL
   fallback
3. Snapshot current Spotify stream mute states
4. Mute every Spotify sink input
5. Start a shuffled `mpv` playlist from `music_dir`, restarting it if it exits
   while the ad is still active
6. When the ad ends, stop the local player, wait for the configured delay, and
   restore the saved mute states

## Pre-mute guard

MPRIS metadata is normally updated a fraction of a second after audio playback
switches, so polling alone can leak the first syllable of an ad. To avoid this,
the watcher reads `Position` and `mpris:length` and, during the final
`premute_ms` of a normal track, asks the service to mute Spotify ahead of time.
If the next metadata is an ad, the stream is already silent and the normal ad
flow takes over. If it is a normal song, the guard restores the stream right
away. A two-second safety timeout releases a guard if no track change arrives
(for example when the user pauses at the end of a song).

## Why polling

The service uses lightweight polling for both MPRIS state and active Spotify sink inputs. That keeps the implementation simple and robust across GNOME, PipeWire, and PulseAudio setups.
