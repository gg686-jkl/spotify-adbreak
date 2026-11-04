from __future__ import annotations

import logging
import os
from pathlib import Path
import random
import shutil
import signal
import subprocess
import threading
import time

AUDIO_SUFFIXES = frozenset(
    {
        ".aac",
        ".aiff",
        ".alac",
        ".flac",
        ".m4a",
        ".mka",
        ".mp3",
        ".oga",
        ".ogg",
        ".opus",
        ".wav",
        ".wma",
    }
)

MAX_PLAYLIST_TRACKS = 1000


class LocalMusicPlayer:
    """Play a shuffled playlist from a local directory while Spotify is muted.

    One dedicated ``mpv`` process is started when an ad begins and terminated
    when the ad ends.  The process is deliberately isolated from any mpv
    instance the user may already be running.
    """

    def __init__(
        self,
        logger: logging.Logger,
        *,
        enabled: bool = True,
        directory: str | Path = "~/Music",
        volume_percent: int = 70,
        player: str = "mpv",
    ) -> None:
        self._logger = logger
        self._enabled = enabled
        self._directory = Path(directory).expanduser()
        self._volume_percent = max(0, min(100, volume_percent))
        self._player = player
        self._lock = threading.Lock()
        self._process: subprocess.Popen[bytes] | None = None
        self._empty_warned = False
        self._missing_player_warned = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def is_playing(self) -> bool:
        with self._lock:
            return self._is_running_locked()

    def start(self) -> bool:
        """Start ad-break music if it is not already running."""
        with self._lock:
            if not self._enabled:
                return False
            if self._is_running_locked():
                return True

            tracks = self._collect_tracks()
            if not tracks:
                if not self._empty_warned:
                    self._logger.warning(
                        "Local music enabled but no playable audio files found in %s",
                        self._directory,
                    )
                    self._empty_warned = True
                return False

            executable = shutil.which(self._player)
            if executable is None:
                if not self._missing_player_warned:
                    self._logger.warning(
                        "Local music player %r not found; install mpv or set music_player",
                        self._player,
                    )
                    self._missing_player_warned = True
                return False

            playlist = list(tracks)
            if len(playlist) > MAX_PLAYLIST_TRACKS:
                playlist = random.sample(playlist, MAX_PLAYLIST_TRACKS)

            command = [
                executable,
                "--no-config",
                "--no-video",
                "--no-terminal",
                "--really-quiet",
                "--audio-display=no",
                "--no-resume-playback",
                "--save-position-on-quit=no",
                "--audio-client-name=ad-break-music",
                f"--volume={self._volume_percent}",
                "--shuffle",
                "--loop-playlist=inf",
                *map(str, playlist),
            ]
            try:
                process = subprocess.Popen(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            except OSError as error:
                self._logger.warning("Failed to start local music: %s", error)
                return False

            # Catch immediate failures (missing codec, invalid audio device,
            # unreadable files) instead of reporting a false success.
            time.sleep(0.15)
            if process.poll() is not None:
                self._logger.warning(
                    "Local music player exited immediately with code %s",
                    process.returncode,
                )
                return False

            self._process = process
            self._logger.info(
                "Playing local music during ad: %d track(s) from %s at %d%% volume",
                len(playlist),
                self._directory,
                self._volume_percent,
            )
            return True

    def stop(self) -> bool:
        """Stop the ad-break music, if running."""
        with self._lock:
            process = self._process
            self._process = None

        if process is None or process.poll() is not None:
            return False

        self._terminate(process)
        self._logger.info("Stopped local ad-break music")
        return True

    def close(self) -> None:
        self.stop()

    def _collect_tracks(self) -> list[Path]:
        if not self._directory.is_dir():
            return []

        tracks: list[Path] = []
        for root, dirs, files in os.walk(self._directory, followlinks=False):
            dirs[:] = sorted(name for name in dirs if not name.startswith("."))
            for name in sorted(files):
                if name.startswith("."):
                    continue
                if Path(name).suffix.lower() in AUDIO_SUFFIXES:
                    tracks.append(Path(root) / name)
        return tracks

    def _is_running_locked(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def _terminate(self, process: subprocess.Popen[bytes]) -> None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        except OSError:
            process.terminate()

        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (ProcessLookupError, OSError):
                process.kill()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self._logger.warning("Local music process did not exit after SIGKILL")
