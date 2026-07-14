#!/bin/bash
# Oracle: write the verified run-scoring timeline as solution.json.
#
# The reference answer is the official play-by-play (NCAA statistics, contest
# 4532325, cross-checked against both schools' box scores): every run with inning,
# half, scoring runner, batter at the plate, and event type. This is the verified
# answer key, not an echo of the input. The agent never sees this file.
set -euo pipefail

mkdir -p /workspace/output

python3 - <<'PY'
import json
from pathlib import Path

RUNS = [
  {"inning": 1, "half": "top",    "scorer": "Brandon Compton",  "batter": "Ryan Campos",     "event": "double"},
  {"inning": 1, "half": "top",    "scorer": "Ryan Campos",      "batter": "Jacob Tobias",    "event": "single"},
  {"inning": 2, "half": "top",    "scorer": "Harris Williams",  "batter": "Brandon Compton", "event": "double"},
  {"inning": 3, "half": "top",    "scorer": "Nick McLain",      "batter": "Steven Ondina",   "event": "single"},
  {"inning": 5, "half": "bottom", "scorer": "Logan Johnstone",  "batter": "Nate Swarts",     "event": "double"},
  {"inning": 5, "half": "bottom", "scorer": "Nate Swarts",      "batter": "Crew Parke",      "event": "sacrifice_fly"},
  {"inning": 5, "half": "bottom", "scorer": "Kyle Russell",     "batter": "Casen Taggart",   "event": "home_run"},
  {"inning": 5, "half": "bottom", "scorer": "Casen Taggart",    "batter": "Casen Taggart",   "event": "home_run"},
  {"inning": 5, "half": "bottom", "scorer": "Joey Kramer",      "batter": "Jacob Morrow",    "event": "home_run"},
  {"inning": 5, "half": "bottom", "scorer": "Jacob Morrow",     "batter": "Jacob Morrow",    "event": "home_run"},
  {"inning": 6, "half": "top",    "scorer": "Jacob Tobias",     "batter": "Nick McLain",     "event": "triple"},
  {"inning": 6, "half": "top",    "scorer": "Ryan Campos",      "batter": "Nick McLain",     "event": "triple"},
  {"inning": 8, "half": "bottom", "scorer": "Cole Cramer",      "batter": "Max Hartman",     "event": "single"},
  {"inning": 8, "half": "bottom", "scorer": "Nate Swarts",      "batter": "Kyle Russell",    "event": "error"},
  {"inning": 9, "half": "top",    "scorer": "Isaiah Jackson",   "batter": "Harris Williams", "event": "groundout"},
]

Path("/workspace/output/solution.json").write_text(json.dumps({"runs": RUNS}, indent=2))
PY

echo "oracle: wrote /workspace/output/solution.json (15 runs)"
