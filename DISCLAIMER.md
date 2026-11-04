# Disclaimer and Legal Notice

This document is not legal advice. It explains the project's intent and the
limits of what it does. Laws and contracts vary by country and by account, so
consult a qualified lawyer if you need legal advice.

## Unofficial project

Spotify Ad Break is an independent, non-commercial open-source project. It is
not affiliated with, endorsed by, sponsored by, approved by, or connected to
Spotify AB, GNOME, or any of their affiliates. The names "Spotify", "GNOME",
and other third-party names are used only to describe compatibility and the
problem the software addresses. They are not used as the project's own brand.

## What the software does

The software runs locally on your computer and:

- reads playback metadata exposed by the Spotify desktop client over MPRIS;
- mutes and unmutes the local PulseAudio/PipeWire audio stream belonging to
  Spotify;
- optionally plays audio files that you already own or are licensed to use.

## What the software does not do

This project is not an ad blocker. It does not:

- modify, patch, inject into, or reverse engineer the Spotify client;
- block, filter, or redirect network requests or ad delivery;
- skip, remove, prevent, or replace Spotify ads;
- bypass DRM, paid features, regional restrictions, or account limits;
- provide, download, or distribute Spotify content, code, or assets.

Spotify ads still play, and Spotify may still count them as played. The project
only changes what you hear locally during the ad and, optionally, plays
different local audio at the same time.

## Your responsibility

Using software that mutes ads may conflict with Spotify's Terms of Service or
other agreements, and could lead to account restrictions or termination. It may
also be restricted by local law or by your organization's policies.

You are solely responsible for:

- deciding whether to install and use this software;
- complying with Spotify's Terms of Service and all applicable laws;
- any effect on your Spotify account, devices, or data;
- the music you play and your rights to use it.

Do not use this software where it is prohibited. If you do not accept these
risks, do not install or use it.

## Trademarks

SPOTIFY and the Spotify logo are trademarks or registered trademarks of
Spotify AB. All other trademarks are the property of their respective owners.
This project does not grant any trademark license or imply any sponsorship,
endorsement, or affiliation. Any use of third-party marks is nominative and
descriptive only: it identifies the service this independent tool works with.

Do not use this project's name, repository, or contributors to suggest that
Spotify approves of or maintains it.

## Local music and copyright

No music is included in this repository. You are responsible for ensuring that
any audio files you use are legal for you to use and that playing them does not
infringe anyone's copyright or other rights.

## Privacy

The application runs locally and does not include telemetry, analytics, or a
remote service. It does not send your listening data to the project maintainers.
GitHub, as the hosting provider, has its own privacy policy for repository
traffic and interactions.

## No warranty and limitation of liability

This software is provided "AS IS", without warranties or conditions of any
kind, under the MIT License. To the fullest extent permitted by law, the
authors and contributors disclaim all liability for any claim, damage, loss, or
other liability arising from the software or its use. See `LICENSE` for the
controlling license text. Nothing here excludes liability that cannot be
excluded by applicable law.

## Third-party software

The project depends on third-party software such as `mpv`, PipeWire,
PulseAudio, `dbus-next`, and `pulsectl`. Those projects have their own licenses,
trademarks, and maintainers. This project is not affiliated with them.

## Rights-holder contact

If you are a rights holder and believe this repository infringes your rights,
please open an issue or use the repository's contact options on GitHub. We will
review good-faith notices and make reasonable changes, including removing
content where appropriate.
