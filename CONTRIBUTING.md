# Contributing

Thanks for considering a contribution.

## Development setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

## Test before opening a PR

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m compileall src tests
```

GitHub Actions runs the same checks on pushes and pull requests.

## Guidelines

- keep changes focused and small when possible
- follow the existing project structure in `src/spotify_adbreak/`
- add or update tests for behavior changes
- update docs when commands, setup, or behavior changes

## Reporting bugs

Include:

- your Linux desktop environment and version
- whether you use PulseAudio or PipeWire
- relevant command output or service logs
- steps to reproduce

## Contribution license and legal hygiene

By submitting a pull request or patch, you agree that your contribution is
licensed under the project's MIT License and that you have the right to submit
it.

Please do not contribute:

- code copied from the Spotify client or other proprietary software;
- code copied from the GPL-3.0 GNOME extension referenced in the project history;
- DRM-circumvention code or instructions;
- Spotify logos, screenshots containing third-party artwork, or music files.

Keep the project focused on local audio-stream muting and local playback. Do not
describe it as an ad blocker or imply that Spotify endorses it.

## Security and legal concerns

For security issues, follow `SECURITY.md`. For trademark, copyright, or other
legal concerns, open an issue or use the repository's contact options rather
than starting a public dispute.
