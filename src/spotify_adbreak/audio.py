from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

import pulsectl


@dataclass(slots=True)
class StreamMuteSnapshot:
    index: int
    muted: bool


class SpotifyAudioController:
    def __init__(self, logger: logging.Logger, *, match_mode: str = "relaxed") -> None:
        self._logger = logger
        self._match_mode = match_mode
        self._pulse: pulsectl.Pulse | None = None
        self._saved_mute_states: dict[int, StreamMuteSnapshot] = {}
        # Streams that existed before the current mute cycle. A stream that
        # appears later may inherit our mute state from module-stream-restore;
        # it must be treated as "was audible" so it gets unmuted afterwards.
        self._streams_at_cycle_start: set[int] | None = None

    @property
    def has_saved_volumes(self) -> bool:
        return bool(self._saved_mute_states)

    def close(self) -> None:
        if self._pulse is not None:
            self._pulse.close()
            self._pulse = None

    def apply_ad_volume(self, percent: int) -> list[int]:
        pulse = self._pulse_client()
        streams = self._spotify_streams(pulse)
        if self._streams_at_cycle_start is None:
            self._streams_at_cycle_start = {stream.index for stream in streams}

        changed: list[int] = []
        for stream in streams:
            if stream.index not in self._saved_mute_states:
                muted = bool(stream.mute)
                if stream.index not in self._streams_at_cycle_start:
                    # New stream during the mute cycle: this is our inherited
                    # mute, not a user preference, so restore it to audible.
                    muted = False
                self._saved_mute_states[stream.index] = StreamMuteSnapshot(
                    index=stream.index,
                    muted=muted,
                )
            if not stream.mute:
                pulse.sink_input_mute(stream.index, True)
                changed.append(stream.index)
        return changed

    def restore_volumes(self) -> list[int]:
        pulse = self._pulse_client()
        restored: list[int] = []
        tracked = set(self._saved_mute_states)
        for index, snapshot in list(self._saved_mute_states.items()):
            try:
                stream_info = pulse.sink_input_info(index)
            except (pulsectl.PulseIndexError, pulsectl.PulseOperationFailed):
                self._saved_mute_states.pop(index, None)
                continue
            if not snapshot.muted:
                pulse.sink_input_mute(index, False)
            pulse.sink_input_volume_set(index, stream_info.volume)
            restored.append(index)
            self._saved_mute_states.pop(index, None)

        # A stream can appear between the last ad-volume pass and this restore
        # (Spotify recreates its player around ad boundaries). If it inherited
        # our mute from module-stream-restore, it was never added to the
        # snapshot above; unmute it now rather than leaving Spotify silent.
        if self._streams_at_cycle_start is not None:
            for stream in self._spotify_streams(pulse):
                if stream.index not in tracked and stream.mute:
                    pulse.sink_input_mute(stream.index, False)
                    pulse.sink_input_volume_set(stream.index, stream.volume)
                    restored.append(stream.index)

        self._streams_at_cycle_start = None
        return restored

    def recover_stuck_streams(self) -> list[int]:
        pulse = self._pulse_client()
        recovered: list[int] = []
        for stream in self._spotify_streams(pulse):
            if stream.mute:
                pulse.sink_input_mute(stream.index, False)
                pulse.sink_input_volume_set(stream.index, stream.volume)
                recovered.append(stream.index)
        if recovered:
            self._logger.info("Recovered %d stuck stream(s): %s", len(recovered), recovered)
        return recovered

    def current_stream_indexes(self) -> list[int]:
        return [stream.index for stream in self._spotify_streams(self._pulse_client())]

    def _pulse_client(self) -> pulsectl.Pulse:
        if self._pulse is None:
            self._pulse = pulsectl.Pulse("spotify-adbreak")
        return self._pulse

    def _spotify_streams(self, pulse: pulsectl.Pulse) -> list[Any]:
        streams = pulse.sink_input_list()
        return [stream for stream in streams if self._is_spotify_stream(pulse, stream)]

    def _is_spotify_stream(self, pulse: pulsectl.Pulse, stream: Any) -> bool:
        stream_name = (getattr(stream, "name", "") or "").strip().lower()
        properties = {
            str(key).lower(): str(value).strip().lower()
            for key, value in dict(stream.proplist).items()
        }
        application_name = properties.get("application.name", "")
        binary_name = properties.get("application.process.binary", "")

        if application_name == "spotify" or stream_name == "spotify":
            return True
        if self._match_mode == "strict":
            return False
        if "spotify" in binary_name or "spotify" in application_name or "spotify" in stream_name:
            return True

        try:
            client_info = pulse.client_info(stream.client)
            client_props = {
                str(k).lower(): str(v).strip().lower()
                for k, v in dict(client_info.proplist).items()
            }
            client_name = (getattr(client_info, "name", "") or "").strip().lower()
            client_app = client_props.get("application.name", "")
            client_binary = client_props.get("application.process.binary", "")
            return (
                client_name == "spotify"
                or "spotify" in client_app
                or "spotify" in client_binary
            )
        except Exception:
            return False
