from __future__ import annotations

import asyncio
import contextlib
import logging

from .audio import SpotifyAudioController
from .config import AppConfig
from .mpris import MprisWatcher
from .music import LocalMusicPlayer


class AdMuterService:
    def __init__(self, config: AppConfig, logger: logging.Logger | None = None) -> None:
        self._config = config
        self._logger = logger or logging.getLogger("spotify_adbreak")
        self._audio = SpotifyAudioController(
            self._logger, match_mode=config.stream_match_mode
        )
        self._watcher = MprisWatcher(
            self._logger,
            poll_interval_ms=config.poll_interval_ms,
            on_state_change=self._handle_state_change,
            premute_ms=config.premute_ms,
            on_track_ending=self._handle_track_ending,
            on_track_restart=self._handle_track_restart,
        )
        self._music = LocalMusicPlayer(
            self._logger,
            enabled=config.local_music_enabled,
            directory=config.music_dir,
            volume_percent=config.music_volume_percent,
            player=config.music_player,
        )
        self._ad_active = False
        self._guard_active = False
        self._guard_started_at = 0.0
        self._audio_lock = asyncio.Lock()
        self._last_muted_streams: set[int] = set()
        self._restore_task: asyncio.Task[None] | None = None
        self._shutdown = asyncio.Event()

    async def run(self) -> None:
        self._logger.info(
            "Watching Spotify ads; local ad-break music: %s (%s)",
            "enabled" if self._config.local_music_enabled else "disabled",
            self._config.music_dir,
        )
        await self._recover_stuck_streams()

        watcher_task = asyncio.create_task(self._watcher.run(), name="mpris-watcher")
        reconcile_task = asyncio.create_task(
            self._reconcile_loop(), name="audio-reconcile"
        )

        try:
            await self._shutdown.wait()
        finally:
            await self._watcher.stop()
            watcher_task.cancel()
            reconcile_task.cancel()
            self._guard_active = False
            if self._restore_task is not None:
                self._restore_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._restore_task
            with contextlib.suppress(asyncio.CancelledError):
                await watcher_task
            with contextlib.suppress(asyncio.CancelledError):
                await reconcile_task
            await self._stop_local_music()
            if self._ad_active or self._audio.has_saved_volumes:
                await self._restore_now()
            async with self._audio_lock:
                await asyncio.to_thread(self._audio.recover_stuck_streams)
            self._audio.close()

    async def stop(self) -> None:
        self._shutdown.set()

    async def _recover_stuck_streams(self) -> None:
        try:
            recovered = await asyncio.to_thread(self._audio.recover_stuck_streams)
            if recovered:
                self._logger.info(
                    "Recovered %d stuck Spotify stream(s) on startup: %s",
                    len(recovered),
                    recovered,
                )
        except Exception as error:
            self._logger.warning("Startup stream recovery failed: %s", error)

    async def _handle_state_change(self, is_ad: bool, track_id: str | None) -> None:
        if is_ad:
            if not self._ad_active:
                self._logger.info("Ad detected: %s", track_id or "unknown track")
            self._ad_active = True
            # A pre-mute guard already muted the stream; the ad lifecycle now
            # owns the saved state and will restore it when the ad ends.
            self._guard_active = False
            self._cancel_restore_task()
            await self._apply_ad_volume()
            await self._start_local_music()
            return

        if self._ad_active:
            self._logger.info(
                "Ad finished, restoring volume in %sms", self._config.unmute_delay_ms
            )
            self._ad_active = False
            self._last_muted_streams.clear()
            await self._fade_out_local_music()
            self._schedule_restore()
        elif self._guard_active:
            await self._release_guard("next track is not an ad")

    async def _reconcile_loop(self) -> None:
        interval = self._config.poll_interval_ms / 1000
        while True:
            await asyncio.sleep(interval)
            if self._ad_active:
                await self._apply_ad_volume()
                # The ad may have ended while apply_ad_volume() was running in
                # a worker thread; do not start music for a finished ad.
                if self._ad_active:
                    await self._ensure_local_music()
            elif self._guard_active:
                elapsed = asyncio.get_running_loop().time() - self._guard_started_at
                if elapsed > 2.0:
                    await self._release_guard("no track change after 2s")

    async def _handle_track_ending(self) -> None:
        """Pre-mute just before a track ends so a following ad cannot leak."""
        if self._ad_active or self._guard_active:
            return
        self._logger.debug(
            "Track nearly finished; pre-muting Spotify for up to %sms",
            self._config.premute_ms,
        )
        await self._apply_ad_volume()
        self._guard_active = True
        self._guard_started_at = asyncio.get_running_loop().time()

    async def _handle_track_restart(self) -> None:
        if self._guard_active:
            await self._release_guard("track restarted")

    async def _release_guard(self, reason: str) -> None:
        if not self._guard_active:
            return
        self._guard_active = False
        self._logger.debug("Releasing pre-mute guard: %s", reason)
        await self._restore_now(quiet=True)

    async def _apply_ad_volume(self) -> None:
        try:
            async with self._audio_lock:
                changed = await asyncio.to_thread(
                    self._audio.apply_ad_volume, self._config.ad_volume_percent
                )
            changed_set = set(changed)
            if changed and changed_set != self._last_muted_streams:
                self._logger.debug(
                    "Adjusted Spotify stream volume for %s",
                    ", ".join(map(str, changed)),
                )
            self._last_muted_streams = changed_set
        except Exception as error:
            self._logger.warning("Failed to change Spotify stream volume: %s", error)

    async def _start_local_music(self) -> None:
        if not self._config.local_music_enabled or not self._ad_active:
            return
        try:
            started = await asyncio.to_thread(self._music.start)
        except Exception as error:
            self._logger.warning("Failed to start local ad-break music: %s", error)
            return
        # Ad ended while the player was starting (startup takes ~150 ms);
        # stop it instead of leaving local music over the next Spotify track.
        if started and not self._ad_active:
            await self._stop_local_music()

    async def _ensure_local_music(self) -> None:
        if not self._config.local_music_enabled or not self._ad_active:
            return
        if self._music.is_playing:
            return
        await self._start_local_music()

    async def _fade_out_local_music(self) -> None:
        if not self._config.local_music_enabled:
            return
        try:
            await asyncio.to_thread(
                self._music.fade_out, self._config.music_fade_out_ms / 1000
            )
        except Exception as error:
            self._logger.warning("Failed to fade out local ad-break music: %s", error)

    async def _stop_local_music(self) -> None:
        try:
            await asyncio.to_thread(self._music.stop)
        except Exception as error:
            self._logger.warning("Failed to stop local ad-break music: %s", error)

    def _schedule_restore(self) -> None:
        self._cancel_restore_task()
        self._restore_task = asyncio.create_task(
            self._delayed_restore(), name="volume-restore"
        )

    def _cancel_restore_task(self) -> None:
        if self._restore_task is not None:
            self._restore_task.cancel()
            self._restore_task = None

    async def _delayed_restore(self) -> None:
        try:
            await asyncio.sleep(self._config.unmute_delay_ms / 1000)
            if not self._ad_active:
                await self._restore_now()
        except asyncio.CancelledError:
            raise
        finally:
            self._restore_task = None

    async def _restore_now(self, *, quiet: bool = False) -> None:
        try:
            async with self._audio_lock:
                restored = await asyncio.to_thread(self._audio.restore_volumes)
            if restored:
                log = self._logger.debug if quiet else self._logger.info
                log(
                    "Restored Spotify stream volume for %s",
                    ", ".join(map(str, restored)),
                )
            self._last_muted_streams.clear()
        except Exception as error:
            self._logger.warning("Failed to restore Spotify stream volume: %s", error)
