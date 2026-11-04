import importlib
import tempfile
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

music_module = importlib.import_module("spotify_adbreak.music")
LocalMusicPlayer = music_module.LocalMusicPlayer


class FakeProcess:
    def __init__(self) -> None:
        self.pid = 12345
        self.returncode = None
        self.terminated = False

    def poll(self):
        return None

    def wait(self, timeout=None):
        self.returncode = 0
        return 0

    def terminate(self) -> None:
        self.terminated = True


class LocalMusicPlayerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.logger = Mock()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.music_dir = Path(self.temp_dir.name)

    def make_player(self, **overrides):
        values = {
            "enabled": True,
            "directory": self.music_dir,
            "volume_percent": 65,
            "player": "mpv",
        }
        values.update(overrides)
        return LocalMusicPlayer(self.logger, **values)

    def test_disabled_player_does_not_start(self) -> None:
        player = self.make_player(enabled=False)

        self.assertFalse(player.start())
        self.assertIsNone(player._process)

    def test_start_without_audio_files_warns_and_returns_false(self) -> None:
        player = self.make_player()

        self.assertFalse(player.start())
        player.start()

        self.logger.warning.assert_called_once()
        self.assertIn("no playable audio files", self.logger.warning.call_args.args[0])

    def test_start_launches_mpv_with_shuffle_and_local_tracks(self) -> None:
        track = self.music_dir / "track.mp3"
        track.write_bytes(b"fake")
        process = FakeProcess()
        player = self.make_player()

        with (
            patch.object(music_module.shutil, "which", return_value="/usr/bin/mpv"),
            patch.object(
                music_module.subprocess, "Popen", return_value=process
            ) as popen,
            patch.object(music_module.time, "sleep"),
        ):
            self.assertTrue(player.start())

        command = popen.call_args.args[0]
        self.assertEqual(command[0], "/usr/bin/mpv")
        self.assertIn("--shuffle", command)
        self.assertIn("--loop-playlist=inf", command)
        self.assertIn("--volume=65", command)
        self.assertTrue(command[-1].endswith("track.mp3"))
        self.assertTrue(player.is_playing)

    def test_start_fails_cleanly_when_player_is_missing(self) -> None:
        (self.music_dir / "track.ogg").write_bytes(b"fake")
        player = self.make_player()

        with patch.object(music_module.shutil, "which", return_value=None):
            self.assertFalse(player.start())

        self.logger.warning.assert_called_once()
        self.assertIn("not found", self.logger.warning.call_args.args[0])

    def test_stop_terminates_running_process(self) -> None:
        player = self.make_player()
        process = FakeProcess()
        player._process = process  # type: ignore[assignment]

        with patch.object(music_module.os, "killpg") as killpg:
            self.assertTrue(player.stop())

        killpg.assert_called_once_with(process.pid, music_module.signal.SIGTERM)
        self.assertIsNone(player._process)

    def test_collect_tracks_is_recursive_and_ignores_hidden_files(self) -> None:
        nested = self.music_dir / "album"
        nested.mkdir()
        (nested / "song.FLAC").write_bytes(b"fake")
        (self.music_dir / ".hidden.mp3").write_bytes(b"fake")
        (self.music_dir / "notes.txt").write_text("nope")

        tracks = self.make_player()._collect_tracks()

        self.assertEqual(tracks, [nested / "song.FLAC"])
