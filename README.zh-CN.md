[English](README.md) | 简体中文

# Spotify Ad Break

[![CI](https://github.com/gg686-jkl/spotify-adbreak/actions/workflows/ci.yml/badge.svg)](https://github.com/gg686-jkl/spotify-adbreak/actions/workflows/ci.yml)

`spotify-adbreak` 是一个运行在 Linux 上的独立 Python 服务。它通过 MPRIS
检测 Spotify 广告，只静音 Spotify 自己的音频流，并在广告期间播放本地音乐；
广告结束后停止本地音乐并自动恢复 Spotify。

本项目是独立项目，派生自 Rishabh Bajpai 的
[spotify-ad-muter](https://github.com/Rishabh-Bajpai/spotify-ad-muter)（MIT），
后者的广告检测思路又受到
[danigm/spotify-ad-blocker](https://github.com/danigm/spotify-ad-blocker)
启发。原始版权声明保留在 `LICENSE` 中，完整署名见 `NOTICE`。

> **非官方项目，与 Spotify 没有关联。** 本工具只是静音 Spotify 的本地音频流，
> 不会屏蔽、跳过或移除广告。使用风险由你自行承担，并且可能违反 Spotify 的
> 服务条款。完整声明见 [DISCLAIMER.md](DISCLAIMER.md)；那不是法律建议。

## 给 AI Agent 的安装提示词

如果你是把本项目配置给用户的 AI agent，展开并复制下面这段提示词。提示词用英文
书写，兼容性更好；它会在执行 sudo 或破坏性操作前征求同意，并在最后验证服务状态。

<details>
<summary><strong>一键安装提示词（复制给 agent）</strong></summary>

```text
You are an installation and configuration agent for the open-source project
"spotify-adbreak". Your job is to install and configure it for the current
Linux desktop user, end to end, with minimal questions.

Repository: https://github.com/gg686-jkl/spotify-adbreak
License: MIT. Read README.md and DISCLAIMER.md before starting.

The user asked you to do this. This project is unofficial and is not affiliated
with Spotify. It mutes Spotify's local audio stream during ads; it does not
block, skip, or remove ads, modify the Spotify client, or bypass DRM. Using it
may conflict with Spotify's Terms of Service. Explain this briefly and proceed
only if the user accepts.

Ask only when you need sudo consent, missing critical information, or a
destructive action. Otherwise work autonomously.

SAFETY RULES
- Work as the logged-in desktop user. Do not run the whole setup as root.
- Ask before any sudo/package-install command and show the exact command.
- Never download music, Spotify content, or anything copyrighted.
- Never modify or delete the user's music, Spotify files, or unrelated config.
- Never kill unrelated processes. Do not use "pkill -f spotify" or other broad
  pkill patterns; use systemctl --user for this project's services.
- Back up any existing config or systemd unit before changing it.
- Do not commit, push, publish, or create GitHub resources.
- Never ask for or handle Spotify passwords.
- If a required condition is missing (systemd user session, Spotify client,
  Python 3.11+, working audio), stop and report clearly.
- Do not claim success until the service is active and the startup log appears.

STEP 1 - INSPECT
  cat /etc/os-release
  printf '%s\n' "$XDG_CURRENT_DESKTOP" "$XDG_SESSION_TYPE"
  pactl info
  python3 --version
  command -v mpv git systemctl
  systemctl --user is-system-running || true
  pgrep -a -f '[s]potify' || true

Check: Linux desktop, PipeWire or PulseAudio responding, Python >= 3.11,
a working systemd --user session, and git. If Spotify is not running, ask the
user to start and sign in; do not handle credentials.

STEP 2 - INSTALL PREREQUISITES
First run "pactl info". If it already works, do not install or replace a sound
server; install only the missing tools (python3, venv, pip, mpv, pactl).

If pactl is missing or not connecting, ask before installing audio packages.
Use the matching package manager and adapt to whether the system runs PipeWire
or PulseAudio:
  Arch/Manjaro (PipeWire): sudo pacman -S --needed python mpv libpulse pipewire-pulse
  Arch/Manjaro (PulseAudio): sudo pacman -S --needed python mpv libpulse pulseaudio
  Debian/Ubuntu: sudo apt update && sudo apt install -y python3 python3-venv python3-pip mpv libpulse0 pulseaudio-utils
  Fedora: sudo dnf install -y python3 python3-pip mpv pulseaudio-libs pulseaudio-utils
Do not replace the user's audio stack. Re-run "pactl info" afterwards. If sudo
is not available and packages are missing, stop and report the missing packages.

STEP 3 - GET THE CODE
  mkdir -p ~/projects
  cd ~/projects
  if [ -d spotify-adbreak/.git ]; then
      cd spotify-adbreak
      git status --short
      # If dirty, stop and ask. Otherwise: git pull --ff-only
  else
      git clone https://github.com/gg686-jkl/spotify-adbreak.git
      cd spotify-adbreak
  fi
Do not clone into a directory that already contains unrelated files.

STEP 4 - INSTALL IN A VENV
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -e .
  .venv/bin/spotify-adbreak --help

STEP 5 - CONFIGURE
  mkdir -p ~/.config/spotify-adbreak
If ~/.config/spotify-adbreak/config.toml exists, back it up to
config.toml.bak-YYYYmmdd-HHMMSS before editing, and preserve the user's
existing values. Only add missing keys or change values the user asks for.

Set MUSIC_DIR to the user's music directory, defaulting to ~/Music. Create it
if missing. Search recursively for these extensions:
mp3 flac m4a ogg opus wav aac wma aiff alac oga mka

Write ~/.config/spotify-adbreak/config.toml with:
  ad_volume_percent = 0
  unmute_delay_ms = 500
  poll_interval_ms = 200
  premute_ms = 800
  log_level = "INFO"
  stream_match_mode = "relaxed"
  local_music_enabled = true|false
  music_dir = "/absolute/path/to/Music"
  music_volume_percent = 70
  music_player = "mpv"

If no playable audio files exist, set local_music_enabled = false and tell the
user to add music later. Do not download anything. Use an absolute music_dir
in the file. Do not install Python packages outside the venv and do not use
sudo for pip.

STEP 6 - HANDLE AN EXISTING INSTALLATION
  systemctl --user list-unit-files 'spotify-ad-muter.service' 'spotify-adbreak.service'

If an old spotify-ad-muter.service is active or enabled:
  systemctl --user disable --now spotify-ad-muter.service
Move its unit file to
~/.config/systemd/user/spotify-ad-muter.service.disabled-<timestamp>.
Preserve the old project and old config; do not delete them.

If spotify-adbreak.service already exists, back up its unit file and config,
then reinstall/restart. Never run two copies of the watcher at the same time.

STEP 7 - INSTALL THE SERVICE
  cd ~/projects/spotify-adbreak
  ./scripts/install.sh

The installer creates the venv if needed, preserves an existing config,
installs ~/.config/systemd/user/spotify-adbreak.service, and enables/starts it.
Then restart the unit so an existing process picks up the current code and
config:
  systemctl --user restart spotify-adbreak.service
If the script fails, do the equivalent steps manually and report the exact
error.

STEP 8 - VERIFY
  systemctl --user is-active spotify-adbreak.service
  systemctl --user is-enabled spotify-adbreak.service
  journalctl --user -u spotify-adbreak.service -n 30 --no-pager

Look for: "Watching Spotify ads; local ad-break music: ..."
Confirm there is no traceback or error. If Spotify is playing and no ad is
active, confirm its sink input is not muted with "pactl list sink-inputs". Do
not mute or unmute other applications.

Do not wait for a real ad. Tell the user the final test is to keep playing
Spotify until the next ad break. Optionally run:
  .venv/bin/python -m unittest discover -s tests -q

STEP 9 - REPORT
Report:
- repository path
- service status and enabled state
- config path and whether local music is enabled
- music directory and number of tracks found
- the exact log command:
  journalctl --user -u spotify-adbreak.service -f
- any warnings or skipped steps
- a short reminder: unofficial, mutes ads locally, does not block them, and
  may conflict with Spotify's Terms of Service.

If anything fails, stop and report the exact command and error. Do not hide
failures or claim the installation succeeded without verification.
```

</details>

## 工作方式

```text
检测到 Spotify 广告
  -> 只静音 Spotify 的 PipeWire/PulseAudio 音频流
  -> 从 ~/Music 启动随机播放的 mpv 歌单
广告结束
  -> 停止本地歌单
  -> 延迟片刻后恢复 Spotify
```

在歌曲结束前约 0.8 秒，服务会提前静音 Spotify（“预静音保护”）。如果下一项是
广告，广告的第一声就已经是静音状态；如果下一项是普通歌曲，则立即恢复音量。
这解决了 MPRIS 元数据比声音晚一小段时间更新、导致广告开头漏音的问题。

系统其他应用的声音不会被静音，因此通知、视频和通话都不受影响。

## 功能

- 从 `spotify:ad`、`/com/spotify/ad/`、`https://open.spotify.com/ad/` 等
  track ID 检测广告，并用 `Advertisement` 标题/URL 作为兜底
- 歌曲结束前预静音，避免广告第一声漏出
- 只静音 Spotify 的音频流，不影响其他应用
- 广告期间随机播放本地歌单，广告结束后自动停止
- 恢复 Spotify 每个音频流原来的静音/音量状态
- 广告期间新出现的 Spotify 音频流也会继续被静音
- 本地播放器异常退出时自动重启
- 既可以前台运行，也可以作为 systemd 用户服务运行

## 系统要求

- Linux，使用 PipeWire 或 PulseAudio（兼容 `pactl`/`pulsectl`）
- Python 3.11+
- 安装 `mpv`（用于广告期间的本地音乐）
- 官方 Spotify 桌面客户端已启动并登录
- 配置的音乐目录中至少有一个音频文件

## 项目结构

```text
.
├── src/spotify_adbreak/
│   ├── audio.py      # Spotify 音频流静音/恢复
│   ├── cli.py        # 命令行入口
│   ├── config.py     # 配置文件和 CLI 合并
│   ├── mpris.py      # 广告检测和歌曲结束预静音
│   ├── music.py      # 本地广告歌单播放器（mpv）
│   └── service.py    # 整体协调
├── tests/
├── systemd/
└── docs/
```

## 安装

```bash
git clone https://github.com/gg686-jkl/spotify-adbreak.git
cd spotify-adbreak
python3 -m venv .venv
.venv/bin/pip install -e .
```

### 一键安装

以下脚本会自动创建虚拟环境、安装程序、生成配置、安装 systemd 用户服务并设置
登录自启：

```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

它会：

- 创建 `.venv`
- 把程序安装到虚拟环境
- 如果不存在，创建 `~/.config/spotify-adbreak/config.toml`
- 安装 `~/.config/systemd/user/spotify-adbreak.service`
- 启用并启动用户服务

只卸载 systemd 服务（保留项目文件和配置）：

```bash
chmod +x scripts/uninstall.sh
./scripts/uninstall.sh
```

## 本地音乐

把广告期间想听的歌曲放到 `~/Music`（会递归扫描子目录）。支持的扩展名：
`.mp3`、`.flac`、`.m4a`、`.ogg`、`.opus`、`.wav`、`.aac`、`.wma`、`.aiff`、
`.alac`、`.oga`、`.mka`。

`mpv` 会把整个目录作为随机、循环的歌单，因此每次广告会从不同曲目开始。也可以
把 `music_dir` 指向其他目录（例如外接硬盘）。

请只使用你有权使用的音乐文件，不要使用未经授权的版权内容。

## 运行

```bash
.venv/bin/spotify-adbreak --log-level INFO
```

带完整参数的示例：

```bash
.venv/bin/spotify-adbreak \
  --ad-volume-percent 0 \
  --unmute-delay-ms 500 \
  --poll-interval-ms 200 \
  --premute-ms 800 \
  --stream-match-mode relaxed \
  --music-dir "$HOME/Music" \
  --music-volume-percent 70 \
  --log-level INFO
```

只静音广告、不播放本地音乐：

```bash
.venv/bin/spotify-adbreak --no-local-music
```

## 配置

配置文件路径：`~/.config/spotify-adbreak/config.toml`

```toml
# 0 = 广告期间完全静音（静音音频流，而不是仅仅调低音量）
ad_volume_percent = 0
unmute_delay_ms = 500
poll_interval_ms = 200
premute_ms = 800
log_level = "INFO"
stream_match_mode = "relaxed"

local_music_enabled = true
music_dir = "~/Music"
music_volume_percent = 70
music_stop_mode = "finish"
music_fade_out_ms = 2000
music_player = "mpv"
```

命令行参数的优先级高于配置文件。

| 配置项 | 含义 |
| --- | --- |
| `ad_volume_percent` | 广告期间 Spotify 的音量；`0` 表示完全静音 |
| `unmute_delay_ms` | 广告结束后延迟多少毫秒恢复 Spotify |
| `poll_interval_ms` | 轮询 MPRIS 的间隔；默认 200ms |
| `premute_ms` | 歌曲结束前提前静音的时间；`0` 表示禁用预静音保护 |
| `stream_match_mode` | 匹配 Spotify 音频流的模式：`strict` 或 `relaxed` |
| `local_music_enabled` | 是否在广告期间播放本地音乐 |
| `music_dir` | 本地音乐目录，递归扫描 |
| `music_volume_percent` | 广告歌单的 mpv 音量 |
| `music_stop_mode` | `fade`（默认）广告结束时淡出本地音乐；`finish` 等当前本地歌曲完整播放后再恢复 Spotify |
| `music_fade_out_ms` | 广告结束时本地音乐淡出时长；`0` 表示立即停止（默认 `2000`） |
| `music_player` | 播放器可执行文件；需支持 `--shuffle`/`--loop-playlist`，`mpv` 还可通过 IPC 平滑淡出 |

## systemd 用户服务

```bash
mkdir -p ~/.config/systemd/user
sed "s|@PROJECT_ROOT@|$(pwd)|g" systemd/spotify-adbreak.service > ~/.config/systemd/user/spotify-adbreak.service
systemctl --user daemon-reload
systemctl --user enable --now spotify-adbreak.service
```

查看日志：

```bash
journalctl --user -u spotify-adbreak.service -f
```

## 验证

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/spotify-adbreak --log-level DEBUG
```

启动 Spotify 后，正常应看到类似日志：

```text
Ad detected: spotify:ad:...
Playing local music during ad: N track(s) ...
Ad finished, restoring volume in 500ms
Stopped local ad-break music
Restored Spotify stream volume for ...
```

也可以在 Spotify 播放时单独检查音频流：

```bash
pactl list sink-inputs | grep -A3 -i spotify
```

## 限制

- 预静音保护覆盖的是常见的“歌曲结束 → 广告开始”场景。如果 Spotify 在歌曲
  中途插入广告，仍可能在最多一个轮询间隔内听到一点广告声。
- 本软件不屏蔽、不跳过、也不移除广告，只是静音本地音频流并播放别的本地音乐。
- 广告检测依赖 Spotify 桌面客户端暴露的 MPRIS 元数据。客户端更新后可能失效。
- 本地音乐必须由你合法获取并在你所在地区合法使用。

## 常见问题

- **能听到广告，但没有静音/切换。** Spotify 客户端可能没有通过 MPRIS 暴露广告
  元数据。用 `--log-level DEBUG` 查看日志；广告检测依赖 track ID/标题。也请确认
  没有同时运行多个 Spotify 实例。
- **Spotify 静音了，但没有音乐。** 检查 `music_dir` 中是否有可播放文件，以及
  是否安装了 `mpv`。日志会提示目录为空或播放器缺失。
- **广告结束后本地音乐还响了一小会儿。** `mpv` 会先收到 SIGTERM；如果卡住，
  2 秒后会被强制结束。
- **歌曲结尾被切掉一点。** 这是预静音保护。可以把 `premute_ms` 调小（例如
  `400`）；如果仍漏出一点广告声，可以调大。
- **声音从错误的输出设备出来。** 广告音乐跟随系统默认 PipeWire sink，和
  Spotify 一样。需要时修改系统默认输出设备。

## 免责声明摘要

- 本项目是非官方项目，与 Spotify AB、GNOME 及其关联公司没有关联、赞助或背书。
- 本项目不修改 Spotify 客户端，不拦截网络请求，不跳过或移除广告，不绕过 DRM。
- 使用本软件可能违反 Spotify 的服务条款，可能导致账号受限或终止；请自行判断
  并遵守当地法律和服务条款。
- 软件按 MIT 许可证“原样”提供，不提供任何担保。
- SPOTIFY 及 Spotify 标志是 Spotify AB 的商标；其他商标归各自所有者。
- 本段不是法律建议。完整声明以 [DISCLAIMER.md](DISCLAIMER.md) 为准。

## 署名与许可

本项目使用 MIT 许可证，派生自
[spotify-ad-muter](https://github.com/Rishabh-Bajpai/spotify-ad-muter)，广告
检测思路受到
[danigm/spotify-ad-blocker](https://github.com/danigm/spotify-ad-blocker) 启发。

- 原始版权：Copyright (c) 2026 Rishabh Bajpai
- 修改部分：Copyright (c) 2026 Kadel and spotify-adbreak contributors

详见 [LICENSE](LICENSE) 和 [NOTICE](NOTICE)。

## 文档

- [docs/architecture.md](docs/architecture.md)
- [docs/migration.md](docs/migration.md)

## CI

GitHub Actions 会在 Python 3.11、3.12、3.13、3.14 上运行 42 个单元测试和编译检查。
