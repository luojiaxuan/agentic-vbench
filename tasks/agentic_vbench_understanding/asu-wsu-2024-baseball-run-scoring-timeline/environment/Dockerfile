FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# The agent uses ffmpeg/ffprobe to seek and sample frames. The grader is pure
# stdlib (it only compares strings and integers), so it needs nothing extra.

# Bake the full-game broadcast at build time with a pinned URL and a SHA256
# verified at build, the same way the worked example does.
#
# Provenance and preparation (see environment/bake_media.sh):
#   Source: official WSU Athletics YouTube upload (1080p60),
#     https://www.youtube.com/watch?v=s-VS4Z1hEaA
#     "WSU Baseball: Arizona State at Washington State | Full Game | 3/22/24"
#   Prepared: downloaded at 720p, audio track stripped (ffmpeg -an) so the task is
#     single-modality video, then re-hosted at a stable URL so the bytes are pinned.
#   An archive.org mirror of the same upload exists (youtube-s-VS4Z1hEaA, 480p)
#     as a fallback provenance record.
#
ARG MATERIALS_URL=https://huggingface.co/datasets/gavinlaw/agentic-vbench-media/resolve/main/asu-wsu-2024-03-22-720p-noaudio.mp4
ARG MATERIALS_SHA256=ecef26a35713a10c453619fa42be1292715caf5815f46dbac03cde22297db43d
RUN mkdir -p /baked \
 && curl --fail --silent --show-error --location --retry 5 --retry-delay 3 \
      "$MATERIALS_URL" -o /baked/game.mp4 \
 && echo "${MATERIALS_SHA256}  /baked/game.mp4" | sha256sum -c - \
 && test -s /baked/game.mp4

WORKDIR /workspace
RUN mkdir -p /workspace/materials /workspace/output /workspace/work
