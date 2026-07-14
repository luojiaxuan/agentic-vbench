# Calibration — asu-wsu-2024-baseball-run-scoring-timeline

Deterministic F1 scorer (`steps/solve/tests/judge.py`). A task clears the bar when
**every real agent scores below 0.10** and a real attempt takes **more than 50
tool-call turns**. Oracle must be 1.0 and an empty attempt near 0.

| run | score | rollout (tool-call turns) |
|---|---|---|
| oracle | 1.0 | — |
| empty / null | 0.0 | — |
| 15-entry guess | 0.0 | — |
| Antigravity | _to run_ | _to run_ |
| Codex CLI | _to run_ | _to run_ |
| Claude Code CLI | _to run_ | _to run_ |

Raw transcripts are in `rollouts/` — one file per agent, so a reviewer can confirm
each score was earned honestly and count the tool-call turns.

Note on `no_media`: the official NCAA play-by-play for this game is public web
data. The container builds with `allow_internet = false` and the prompt forbids
lookups, so the no-media ablation measures pure model recall/guessing of that
public record; the measured row above verifies it is ≈ 0.
