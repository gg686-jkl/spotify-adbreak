import importlib
from unittest.mock import AsyncMock, Mock
from pathlib import Path
import sys
import unittest

from dbus_next.errors import DBusError
from dbus_next.signature import Variant

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

mpris_module = importlib.import_module("spotify_adbreak.mpris")
MprisWatcher = mpris_module.MprisWatcher
PlayerSnapshot = mpris_module.PlayerSnapshot
is_ad_track = mpris_module.is_ad_track
is_ad_metadata = mpris_module.is_ad_metadata
unwrap_variant = mpris_module.unwrap_variant


class MprisTests(unittest.TestCase):
    def test_is_ad_track_matches_known_prefixes(self) -> None:
        self.assertTrue(is_ad_track("spotify:ad:123"))
        self.assertTrue(is_ad_track("/com/spotify/ad/123"))
        self.assertFalse(is_ad_track("spotify:track:123"))
        self.assertFalse(is_ad_track(None))
        self.assertTrue(is_ad_track("SPOTIFY:AD:123"))

    def test_is_ad_metadata_uses_title_and_url_fallbacks(self) -> None:
        self.assertTrue(
            is_ad_metadata(
                {
                    "mpris:trackid": "/com/spotify/track/123",
                    "xesam:title": "Advertisement",
                }
            )
        )
        self.assertTrue(
            is_ad_metadata(
                {
                    "mpris:trackid": "/com/spotify/track/123",
                    "xesam:url": "https://open.spotify.com/ad/123",
                }
            )
        )
        self.assertFalse(
            is_ad_metadata(
                {
                    "mpris:trackid": "/com/spotify/track/123",
                    "xesam:title": "Normal song",
                }
            )
        )
        self.assertFalse(is_ad_metadata(None))

    def test_unwrap_variant_handles_nested_structures(self) -> None:
        wrapped = Variant(
            "a{sv}",
            {
                "mpris:trackid": Variant("s", "spotify:ad:123"),
                "artists": Variant("as", ["one", "two"]),
                "nested": Variant("av", [Variant("s", "value")]),
            },
        )

        self.assertEqual(
            unwrap_variant(wrapped),
            {
                "mpris:trackid": "spotify:ad:123",
                "artists": ["one", "two"],
                "nested": ["value"],
            },
        )


class MprisWatcherTests(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_track_id_reads_metadata(self) -> None:
        logger = Mock()
        watcher = MprisWatcher(logger, poll_interval_ms=1, on_state_change=AsyncMock())
        props = Mock()
        props.call_get_all = AsyncMock(
            return_value={
                "Metadata": Variant(
                    "a{sv}", {"mpris:trackid": Variant("s", "spotify:track:123")}
                ),
                "PlaybackStatus": Variant("s", "Playing"),
                "Position": Variant("x", 0),
            }
        )
        watcher._properties_interface = AsyncMock(return_value=props)

        track_id = await watcher._fetch_track_id()

        self.assertEqual(track_id, "spotify:track:123")

    async def test_fetch_track_id_resets_cached_properties_on_dbus_error(self) -> None:
        logger = Mock()
        watcher = MprisWatcher(logger, poll_interval_ms=1, on_state_change=AsyncMock())
        props = Mock()
        props.call_get_all = AsyncMock(
            side_effect=DBusError("org.test.Error", "something broke")
        )
        watcher._props = object()
        watcher._properties_interface = AsyncMock(return_value=props)

        track_id = await watcher._fetch_track_id()

        self.assertIsNone(track_id)
        self.assertIsNone(watcher._props)
        logger.debug.assert_called_once()

    async def test_run_deduplicates_repeated_state_changes(self) -> None:
        logger = Mock()
        callback = AsyncMock()
        watcher = MprisWatcher(logger, poll_interval_ms=1, on_state_change=callback)
        track_ids = iter(
            [
                "spotify:track:1",
                "spotify:track:1",
                "spotify:ad:2",
                "spotify:ad:2",
            ]
        )

        async def fake_fetch() -> PlayerSnapshot:
            value = next(track_ids)
            if value == "spotify:ad:2" and callback.await_count == 1:
                watcher._running = False
            return PlayerSnapshot(
                metadata={"mpris:trackid": value},
                playback_status="Playing",
                position_us=0,
                remaining_us=180_000_000,
                track_id=value,
                is_ad=value.startswith("spotify:ad"),
            )

        watcher._fetch_snapshot = fake_fetch  # type: ignore[method-assign]

        await watcher.run()

        self.assertEqual(callback.await_count, 2)
        self.assertEqual(callback.await_args_list[0].args, (False, "spotify:track:1"))
        self.assertEqual(callback.await_args_list[1].args, (True, "spotify:ad:2"))

    async def test_premute_fires_once_near_the_end_of_a_track(self) -> None:
        logger = Mock()
        ending = AsyncMock()
        watcher = MprisWatcher(
            logger,
            poll_interval_ms=1,
            on_state_change=AsyncMock(),
            premute_ms=800,
            on_track_ending=ending,
        )
        snapshot = PlayerSnapshot(
            metadata={
                "mpris:trackid": "spotify:track:1",
                "mpris:length": 180_000_000,
            },
            playback_status="Playing",
            position_us=179_500_000,
            remaining_us=500_000,
            track_id="spotify:track:1",
            is_ad=False,
        )

        await watcher._maybe_premute(snapshot)
        await watcher._maybe_premute(snapshot)

        ending.assert_awaited_once()

    async def test_premute_callback_can_fire_again_after_track_restarts(self) -> None:
        logger = Mock()
        ending = AsyncMock()
        restart = AsyncMock()
        watcher = MprisWatcher(
            logger,
            poll_interval_ms=1,
            on_state_change=AsyncMock(),
            premute_ms=800,
            on_track_ending=ending,
            on_track_restart=restart,
        )
        metadata = {"mpris:trackid": "spotify:track:1", "mpris:length": 180_000_000}
        near_end = PlayerSnapshot(
            metadata=metadata,
            playback_status="Playing",
            position_us=179_500_000,
            remaining_us=500_000,
            track_id="spotify:track:1",
            is_ad=False,
        )
        restarted = PlayerSnapshot(
            metadata=metadata,
            playback_status="Playing",
            position_us=1_000_000,
            remaining_us=179_000_000,
            track_id="spotify:track:1",
            is_ad=False,
        )

        await watcher._maybe_premute(near_end)
        await watcher._maybe_premute(restarted)
        await watcher._maybe_premute(near_end)

        self.assertEqual(ending.await_count, 2)
        restart.assert_awaited_once()

    async def test_premute_ignores_ads_and_paused_tracks(self) -> None:
        logger = Mock()
        ending = AsyncMock()
        watcher = MprisWatcher(
            logger,
            poll_interval_ms=1,
            on_state_change=AsyncMock(),
            premute_ms=800,
            on_track_ending=ending,
        )
        base = dict(
            metadata={"mpris:trackid": "spotify:track:1", "mpris:length": 30_000_000},
            position_us=29_900_000,
            remaining_us=100_000,
            track_id="spotify:track:1",
        )

        await watcher._maybe_premute(
            PlayerSnapshot(playback_status="Playing", is_ad=True, **base)
        )
        await watcher._maybe_premute(
            PlayerSnapshot(playback_status="Paused", is_ad=False, **base)
        )

        ending.assert_not_awaited()
