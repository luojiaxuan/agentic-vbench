# Spec Card — asu-wsu-2024-baseball-run-scoring-timeline

```yaml
task: agentic_vbench_understanding/asu-wsu-2024-baseball-run-scoring-timeline

cognitive_level: understanding

modalities_required:
  video: the score bug only shows totals changing; naming WHO scored requires
    tracking the scoring runner from his earlier plate appearance (jersey number,
    roster mapping) to the moment he crosses home, and typing HOW the run scored
    requires reading the play action itself
  audio: not used (audio track stripped at bake time; the task is single-modality
    by construction, so commentary can never leak attributions)

question: Reconstruct every run scored in the game — inning, half, the runner who
  scored, the batter whose plate appearance was in progress, and how the run scored.
output_schema: >
  {"runs": [{"inning": 1-9, "half": "top"|"bottom", "scorer": "First Last",
  "batter": "First Last", "event": one of 18 closed-vocabulary strings}]}.
  No time tolerance needed: baseball has no clock; (inning, half) anchors each run
  and duplicates are handled by one-to-one multiset matching.

evidence:
  - each run's TP inherently spans two far-apart moments — the scoring runner's own
    earlier plate appearance (how he got on base, minutes before) and the plate
    crossing; the batter chyron/score bug alone never contains the answer
  - 15 runs spread across 9 innings of a ~3.2h broadcast (top 1st through top 9th);
    the 6-run bottom 5th requires untangling four scoring plays in one half-inning,
    including two 2-run homers back to back

ground_truth:
  source: official NCAA play-by-play, stats.ncaa.org contest 4532325
  tier: machine-truth
  verification: cross-checked against both schools' official box scores; the
    per-inning line score (ASU 210 002 001 = 7, WSU 000 060 02X = 8) and every
    player's individual R column reconcile exactly with the 15-run list

scorer:
  metric: two-tier F1 over runs — full credit (1.0) requires inning, half, scorer,
    batter, and event; partial credit (0.5) when only the event category differs
    (some labels are official-scorer rulings a flawless visual agent can miss, and
    wild_pitch/passed_ball are merged as one visually-identical class). Names
    normalized (unambiguous-lastname rule); greedy one-to-one matching with exact
    matches assigned first, so duplicate keys — the same runner scoring twice in
    one half-inning — are consumed at most once
  oracle_reward: 1.0
  null_reward: 0.0 (measured; empty list)

difficulty:
  strong_agent_reward: TBD (to be measured, target < 0.10)
  tool_call_turns: TBD (to be measured, target > 50)
  agent_model: Antigravity, Codex CLI, Claude Code CLI (per family requirements)

anti_shortcut:
  single_frame: ~0 expected — the line score shows per-inning totals at most, never
    scorers, batters, or event types (to be measured)
  video_only: n/a — the task ships video-only by construction
  audio_only: n/a — no audio track exists in the baked media
  no_media: ~0 expected — ordinary regular-season college game; the tuple
    (scorer, batter, event) per run is not recallable (to be measured)
  frame_dump_no_tools: ~0 expected — attribution needs targeted backward search
    around each score-bug change; uniform frames miss the earlier on-base events
    (to be measured)

input:
  url: https://www.youtube.com/watch?v=s-VS4Z1hEaA (official WSU Athletics upload;
    re-hosted processed copy pinned in environment/Dockerfile before merge)
  sha256: TBD (filled by environment/bake_media.sh after re-host)
  length_min: 192
  resolution: 720 (source stream is 1080p60; baked at 720p, audio stripped)
```
