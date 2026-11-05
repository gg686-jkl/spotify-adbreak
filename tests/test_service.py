import asyncio
import importlib
from pathlib import Path
import sys
import unittest
from unittest.mock import ANY, AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

config_module = importlib.import_module("spotify_adbreak.config")
service_module = importlib.import_module("spotify_adbreak.service")

AppConfig = config_module.AppConfig
AdMuterService = service_module.AdMuterService


class FakeWatcher:
    def __init__(self) -> None:
        self.run = AsyncMock()
        self.stop = AsyncMock()


class AdMuterServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.logger = Mock()
        self.audio = Mock()
        self.audio.has_saved_volumes = False
        self.watcher = FakeWatcher()
        self.music = Mock()
        self.music.is_playing = False
        self.music.start = Mock(return_value=True)
        self.music.stop = Mock(return_value=True)

        audio_patcher = patch.object(
            service_module, "SpotifyAudioController", return_value=self.audio
        )
        watcher_patcher = patch.object(
            service_module, "MprisWatcher", return_value=self.watcher
        )
        music_patcher = patch.object(
            service_module, "LocalMusicPlayer", return_value=self.music
        )
        self.addCleanup(audio_patcher.stop)
        self.addCleanup(watcher_patcher.stop)
        self.addCleanup(music_patcher.stop)
        audio_patcher.start()
        watcher_patcher.start()
        music_patcher.start()

    async def asyncTearDown(self) -> None:
        if hasattr(self, "service") and self.service._restore_task is not None:
            self.service._restore_task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await self.service._restore_task

    def make_service(self, **config_overrides: int) -> AdMuterService:
        config_values = {
            "ad_volume_percent": 0,
            "unmute_delay_ms": 10,
            "poll_interval_ms": 10,
        }
        config_values.update(config_overrides)
        config = AppConfig(**config_values)
        self.service = AdMuterService(config, self.logger)
        return self.service

    async def test_handle_state_change_tracks_ad_start_and_end_transitions(
        self,
    ) -> None:
        service = self.make_service()
        service._apply_ad_volume = AsyncMock()
        service._schedule_restore = Mock()
        service._last_muted_streams = {4, 5}

        await service._handle_state_change(True, "spotify:ad:123")
        await service._handle_state_change(False, "spotify:track:123")

        self.assertFalse(service._ad_active)
        service._apply_ad_volume.assert_awaited_once()
        self.music.start.assert_called_once_with()
        self.music.stop.assert_called_once_with()
        service._schedule_restore.assert_called_once_with()
        self.assertEqual(service._last_muted_streams, set())
        self.logger.info.assert_any_call("Ad detected: %s", "spotify:ad:123")
        self.logger.info.assert_any_call(
            "Ad finished, restoring volume in %sms", service._config.unmute_delay_ms
        )

    async def test_ad_start_does_not_restart_music_when_disabled(self) -> None:
        service = self.make_service(local_music_enabled=False)
        service._apply_ad_volume = AsyncMock()

        await service._handle_state_change(True, "spotify:ad:123")

        self.music.start.assert_not_called()

    async def test_ensure_local_music_restarts_after_player_exits(self) -> None:
        service = self.make_service()
        service._ad_active = True
        self.music.is_playing = False

        await service._ensure_local_music()

        self.music.start.assert_called_once_with()

    async def test_ensure_local_music_does_nothing_after_ad_ended(self) -> None:
        service = self.make_service()
        service._ad_active = False

        await service._ensure_local_music()

        self.music.start.assert_not_called()

    async def test_start_local_music_stops_if_ad_ends_during_start(self) -> None:
        service = self.make_service()
        service._ad_active = True

        def start_and_end_ad() -> bool:
            service._ad_active = False
            return True

        self.music.start = Mock(side_effect=start_and_end_ad)

        await service._start_local_music()

        self.music.stop.assert_called_once_with()

    async def test_track_end_guard_mutes_and_next_song_releases(self) -> None:
        service = self.make_service()
        service._apply_ad_volume = AsyncMock()
        service._restore_now = AsyncMock()

        await service._handle_track_ending()

        self.assertTrue(service._guard_active)
        service._apply_ad_volume.assert_awaited_once()

        await service._handle_state_change(False, "spotify:track:next")

        self.assertFalse(service._guard_active)
        service._restore_now.assert_awaited_once_with(quiet=True)

    async def test_track_restart_releases_guard(self) -> None:
        service = self.make_service()
        service._restore_now = AsyncMock()
        service._guard_active = True

        await service._handle_track_restart()

        self.assertFalse(service._guard_active)
        service._restore_now.assert_awaited_once_with(quiet=True)

    async def test_ad_start_absorbs_existing_guard_mute(self) -> None:
        service = self.make_service()
        service._apply_ad_volume = AsyncMock()
        service._guard_active = True

        await service._handle_state_change(True, "spotify:ad:1")

        self.assertFalse(service._guard_active)
        service._apply_ad_volume.assert_awaited_once()
        self.music.start.assert_called_once_with()

    async def test_schedule_restore_runs_restore_after_delay(self) -> None:
        service = self.make_service(unmute_delay_ms=1)
        service._restore_now = AsyncMock()

        service._schedule_restore()
        await asyncio.sleep(0.02)

        service._restore_now.assert_awaited_once()
        self.assertIsNone(service._restore_task)

    async def test_new_ad_cancels_pending_restore_task(self) -> None:
        service = self.make_service(unmute_delay_ms=100)
        service._apply_ad_volume = AsyncMock()
        service._schedule_restore()

        pending_task = service._restore_task
        self.assertIsNotNone(pending_task)

        await service._handle_state_change(True, "spotify:ad:next")
        await asyncio.sleep(0)

        self.assertIsNone(service._restore_task)
        self.assertTrue(pending_task.done())
        service._apply_ad_volume.assert_awaited_once()

    async def test_apply_ad_volume_logs_warning_on_audio_failure(self) -> None:
        service = self.make_service()
        self.audio.apply_ad_volume.side_effect = RuntimeError("boom")

        await service._apply_ad_volume()

        self.logger.warning.assert_called_once_with(
            "Failed to change Spotify stream volume: %s", ANY
        )

    async def test_restore_now_logs_warning_on_audio_failure(self) -> None:
        service = self.make_service()
        self.audio.restore_volumes.side_effect = RuntimeError("boom")
        service._last_muted_streams = {1}

        await service._restore_now()

        self.logger.warning.assert_called_once_with(
            "Failed to restore Spotify stream volume: %s", ANY
        )
        self.assertEqual(service._last_muted_streams, {1})
