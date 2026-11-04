from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
from typing import Any, Awaitable, Callable, cast

from dbus_next.aio.message_bus import MessageBus
from dbus_next.constants import BusType
from dbus_next.errors import DBusError
from dbus_next.signature import Variant


MPRIS_SERVICE = "org.mpris.MediaPlayer2.spotify"
MPRIS_PATH = "/org/mpris/MediaPlayer2"
MPRIS_PLAYER_INTERFACE = "org.mpris.MediaPlayer2.Player"
AD_PREFIXES = (
    "spotify:ad",
    "/com/spotify/ad/",
    "https://open.spotify.com/ad/",
)
AD_TITLES = {"advertisement", "advertisements", "ad break", "广告"}


StateCallback = Callable[[bool, str | None], Awaitable[None]]
EndingCallback = Callable[[], Awaitable[None]]


@dataclass(slots=True)
class PlayerSnapshot:
    metadata: dict[str, Any] | None
    playback_status: str
    position_us: int
    remaining_us: int | None
    track_id: str | None
    is_ad: bool


def unwrap_variant(value: Any) -> Any:
    if isinstance(value, Variant):
        return unwrap_variant(value.value)
    if isinstance(value, dict):
        return {key: unwrap_variant(item) for key, item in value.items()}
    if isinstance(value, list):
        return [unwrap_variant(item) for item in value]
    return value


def is_ad_track(track_id: str | None) -> bool:
    if not track_id:
        return False
    normalized = str(track_id).strip().lower()
    return any(normalized.startswith(prefix) for prefix in AD_PREFIXES)


def is_ad_metadata(metadata: dict[str, Any] | None) -> bool:
    """Detect an ad from track id or, as a fallback, from its title/url.

    Recent Spotify clients occasionally expose an ad without the documented
    ``spotify:ad`` track id, but still label the metadata as an advertisement.
    """
    if not metadata:
        return False
    if is_ad_track(str(metadata.get("mpris:trackid") or "")):
        return True

    title = str(metadata.get("xesam:title") or "").strip().lower()
    if title in AD_TITLES:
        return True

    url = str(metadata.get("xesam:url") or "").strip().lower()
    return "/ad/" in url


class MprisWatcher:
    def __init__(
        self,
        logger: logging.Logger,
        *,
        poll_interval_ms: int,
        on_state_change: StateCallback,
        premute_ms: int = 0,
        on_track_ending: EndingCallback | None = None,
        on_track_restart: EndingCallback | None = None,
    ) -> None:
        self._logger = logger
        self._poll_interval = poll_interval_ms / 1000
        self._on_state_change = on_state_change
        self._premute_us = max(0, premute_ms) * 1000
        self._on_track_ending = on_track_ending
        self._on_track_restart = on_track_restart
        self._ending_signaled_for: str | None = None
        self._bus: MessageBus | None = None
        self._props = None
        self._last_state: bool | None = None
        self._last_track_id: str | None = None
        self._running = False

    async def run(self) -> None:
        self._running = True
        while self._running:
            snapshot = await self._fetch_snapshot()
            track_id = snapshot.track_id
            is_ad = snapshot.is_ad
            if track_id != self._last_track_id:
                self._ending_signaled_for = None
            if is_ad != self._last_state or track_id != self._last_track_id:
                self._last_state = is_ad
                self._last_track_id = track_id
                await self._on_state_change(is_ad, track_id)
            await self._maybe_premute(snapshot)
            await asyncio.sleep(self._poll_interval)

    async def stop(self) -> None:
        self._running = False
        if self._bus is not None:
            self._bus.disconnect()
            self._bus = None
        self._props = None

    @staticmethod
    def _track_id(metadata: dict[str, Any] | None) -> str | None:
        if not metadata:
            return None
        track_id = metadata.get("mpris:trackid")
        if track_id is None:
            return None
        return str(track_id)

    async def _fetch_track_id(self) -> str | None:
        return (await self._fetch_snapshot()).track_id

    async def _fetch_metadata(self) -> dict[str, Any] | None:
        return (await self._fetch_snapshot()).metadata

    async def _fetch_snapshot(self) -> PlayerSnapshot:
        try:
            props = await self._properties_interface()
            if props is None:
                return PlayerSnapshot(None, "", 0, None, None, False)
            values = await cast(Any, props).call_get_all(MPRIS_PLAYER_INTERFACE)
            values = unwrap_variant(values)
            if not isinstance(values, dict):
                return PlayerSnapshot(None, "", 0, None, None, False)

            metadata = values.get("Metadata")
            if not isinstance(metadata, dict):
                metadata = None
            playback_status = str(values.get("PlaybackStatus") or "")
            try:
                position_us = int(values.get("Position") or 0)
            except (TypeError, ValueError):
                position_us = 0

            remaining_us = self._remaining_us(metadata, position_us)
            return PlayerSnapshot(
                metadata=metadata,
                playback_status=playback_status,
                position_us=position_us,
                remaining_us=remaining_us,
                track_id=self._track_id(metadata),
                is_ad=is_ad_metadata(metadata),
            )
        except DBusError as error:
            if error.text not in {
                "The name is not activatable",
                "The name org.mpris.MediaPlayer2.spotify was not provided by any .service files",
            }:
                self._logger.debug("MPRIS query failed: %s", error)
            self._props = None
            return PlayerSnapshot(None, "", 0, None, None, False)
        except Exception as error:
            self._logger.debug("Unexpected MPRIS error: %s", error)
            self._props = None
            return PlayerSnapshot(None, "", 0, None, None, False)

    @staticmethod
    def _remaining_us(metadata: dict[str, Any] | None, position_us: int) -> int | None:
        if not metadata:
            return None
        try:
            length_us = int(metadata.get("mpris:length") or 0)
        except (TypeError, ValueError):
            return None
        if length_us <= 0:
            return None
        return length_us - position_us

    async def _maybe_premute(self, snapshot: PlayerSnapshot) -> None:
        """Mute just before a track ends, so an ad that follows never leaks audio."""
        if (
            self._premute_us <= 0
            or self._on_track_ending is None
            or snapshot.is_ad
            or snapshot.track_id is None
            or snapshot.remaining_us is None
        ):
            return

        if snapshot.playback_status != "Playing":
            # If the user pauses near the end and resumes later, allow the
            # guard to fire again for the same track.
            self._ending_signaled_for = None
            return

        if snapshot.remaining_us <= self._premute_us:
            if self._ending_signaled_for != snapshot.track_id:
                self._ending_signaled_for = snapshot.track_id
                await self._on_track_ending()
        elif (
            self._ending_signaled_for == snapshot.track_id
            and snapshot.remaining_us > self._premute_us + 250_000
        ):
            # Position moved back to the start (loop-one, seek, replay).
            self._ending_signaled_for = None
            if self._on_track_restart is not None:
                await self._on_track_restart()

    async def _properties_interface(self):
        if self._props is not None:
            return self._props
        if self._bus is None:
            self._bus = await MessageBus(bus_type=BusType.SESSION).connect()
        introspection = await self._bus.introspect(MPRIS_SERVICE, MPRIS_PATH)
        proxy_object = self._bus.get_proxy_object(
            MPRIS_SERVICE, MPRIS_PATH, introspection
        )
        self._props = proxy_object.get_interface("org.freedesktop.DBus.Properties")
        return self._props
