from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import tomllib


DEFAULT_CONFIG_PATH = Path("~/.config/spotify-adbreak/config.toml").expanduser()


@dataclass(slots=True)
class AppConfig:
    ad_volume_percent: int = 0
    unmute_delay_ms: int = 500
    poll_interval_ms: int = 200
    premute_ms: int = 800
    log_level: str = "INFO"
    stream_match_mode: str = "relaxed"
    local_music_enabled: bool = True
    music_dir: str = "~/Music"
    music_volume_percent: int = 70
    music_stop_mode: str = "fade"
    music_fade_out_ms: int = 2000
    music_player: str = "mpv"

    @classmethod
    def from_sources(
        cls,
        *,
        cli_values: dict[str, Any] | None = None,
        config_path: Path | None = None,
    ) -> "AppConfig":
        data: dict[str, Any] = {}

        source_path = config_path or DEFAULT_CONFIG_PATH
        if source_path.exists():
            with source_path.open("rb") as handle:
                loaded = tomllib.load(handle)
            if isinstance(loaded, dict):
                data.update(loaded)

        if cli_values:
            for key, value in cli_values.items():
                if value is not None:
                    data[key] = value

        config = cls(**data)
        config.validate()
        return config

    def validate(self) -> None:
        if not 0 <= self.ad_volume_percent <= 100:
            raise ValueError("ad_volume_percent must be between 0 and 100")
        if self.unmute_delay_ms < 0:
            raise ValueError("unmute_delay_ms must be >= 0")
        if self.poll_interval_ms <= 0:
            raise ValueError("poll_interval_ms must be > 0")
        if not 0 <= self.premute_ms <= 10000:
            raise ValueError("premute_ms must be between 0 and 10000")
        if self.stream_match_mode not in {"strict", "relaxed"}:
            raise ValueError("stream_match_mode must be 'strict' or 'relaxed'")
        if not 0 <= self.music_volume_percent <= 100:
            raise ValueError("music_volume_percent must be between 0 and 100")
        if self.music_stop_mode not in {"fade", "finish"}:
            raise ValueError("music_stop_mode must be 'fade' or 'finish'")
        if not 0 <= self.music_fade_out_ms <= 10000:
            raise ValueError("music_fade_out_ms must be between 0 and 10000")
        if not str(self.music_dir).strip():
            raise ValueError("music_dir must not be empty")
        if not str(self.music_player).strip():
            raise ValueError("music_player must not be empty")
