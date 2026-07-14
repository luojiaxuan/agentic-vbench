# Run-Scoring Timeline Reconstruction

You are given one video at `/workspace/materials/game.mp4`: the full broadcast of a
college baseball game (Arizona State at Washington State). The video has no audio
track. Reconstruct the complete timeline of every run scored in the game, by either
team.

For each run, report the inning, the half, the runner who scored, the batter whose
plate appearance was in progress when the run scored, and how the run scored. Use any
tools in the image (for example `ffmpeg` and `ffprobe`) to seek through and sample the
video. The on-screen score-and-inning graphic, the base-occupancy indicator, the
players' jersey numbers, and the play action are your evidence. The rosters below map
jersey numbers to names.

## What to submit

Write `/workspace/output/solution.json` in exactly this shape:

```json
{
  "runs": [
    {"inning": 3, "half": "top",    "scorer": "First Last", "batter": "First Last", "event": "home_run"},
    {"inning": 5, "half": "bottom", "scorer": "First Last", "batter": "First Last", "event": "sacrifice_fly"}
  ]
}
```

- One entry per run scored, in any order. A play that scores two runs produces two
  entries (one per scoring runner).
- `inning`: 1 to 9.
- `half`: `"top"` (Arizona State batting) or `"bottom"` (Washington State batting).
- `scorer`: the full name of the runner who crossed home plate.
- `batter`: the full name of the batter whose plate appearance was in progress when
  the run scored. For a home run, the batter is the scorer of his own run.
- `event`: how the run scored, one of exactly:
  `single, double, triple, home_run, sacrifice_fly, sacrifice_bunt, groundout,
  flyout, fielders_choice, error, wild_pitch, passed_ball, walk, hit_by_pitch,
  balk, stolen_base, double_play, other`.
  Use the category of the play on which the runner crossed home: e.g. a runner who
  scores from second on a single is `single`; a runner who scores when the batter
  grounds out is `groundout`; a runner who scores because a fielder misplays the
  ball (letting the run in on the miscue) is `error`; a runner who scores on a
  pitch that gets away with no batted ball is `wild_pitch` or `passed_ball`.

## Rosters (jersey number → name)

Arizona State (road, batting in the top half):

| # | Name | | # | Name |
|---|---|---|---|---|
| 2 | Ethan Mendoza | | 12 | Harris Williams |
| 3 | Nick McLain | | 15 | Thomas Burns |
| 4 | Jax Ryan | | 17 | Ryan Campos |
| 7 | Eamonn Lance | | 18 | Jacob Tobias |
| 8 | Steven Ondina | | 22 | Ben Jacobs |
| 11 | Kien Vu | | 24 | Isaiah Jackson |
| | | | 27 | Brandon Compton |
| | | | 54 | Ryan Schiefer |

Washington State (home, batting in the bottom half):

| # | Name | | # | Name |
|---|---|---|---|---|
| 1 | Kyle Russell | | 12 | Jacob Morrow |
| 2 | Ely Kennel | | 23 | Max Hartman |
| 4 | Logan Johnstone | | 25 | Casen Taggart |
| 6 | Joey Kramer | | 30 | Will Cresswell |
| 8 | Crew Parke | | 32 | Cole Cramer |
| 10 | Griffen Sotomayor | | 37 | Nate Swarts |
| | | | 41 | Chase Grillo |
| | | | 44 | Grant Taylor |
| | | | 46 | Carson Judd |
| | | | 49 | Duke Brotherton |

## Rules

- Stay inside this working directory. Do not read, write, or search outside it.
- Do not look anything up online, and do not rely on memory of this game; find every
  run in the video.
- Count only runs that scored: a runner reaching third, or a batter reaching base
  without a run crossing home, is not an entry.
