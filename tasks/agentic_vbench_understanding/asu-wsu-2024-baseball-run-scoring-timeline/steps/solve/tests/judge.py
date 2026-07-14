#!/usr/bin/env python3
"""Grade a run-scoring-timeline reconstruction. Pure Python stdlib, deterministic.

The agent must list every run scored with inning, half, the runner who scored, the
batter at the plate, and the event type. A predicted run is a true positive only when
it FULLY reconstructs the run: same inning, same half, same scorer, same batter, and
same event category. We then score by F1 (misses and false positives both hurt).
reward = F1.

Why this task and metric: a full game has ~15 runs scattered across 3 hours. The
score bug shows only the totals changing — it never names the runner who crossed the
plate. Attributing each run means tracking the scoring runner from his own earlier
plate appearance to the moment he touches home, so only genuinely reconstructing the
game off the video scores. The oracle (exact list) -> 1.0; an empty or guessed
list -> ~0.

Baseball has no game clock, so there is no time tolerance; the (inning, half) pair
anchors each run and duplicate events (the same runner scoring twice in a game, or
two runs on one swing) are handled by greedy one-to-one multiset matching.
"""
import argparse
import json
import re
from pathlib import Path

# Official record: 15 runs (ASU 7, WSU 8), 2024-03-22, Arizona State at Washington
# State. Cross-checked against three independent official records (NCAA play-by-play,
# both schools' box scores); the per-inning line score and each player's R column
# reconcile exactly with this list.
GROUND_TRUTH = [
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

# Deterministic aliases for common spelling variants of the closed vocabulary.
EVENT_ALIASES = {
    "homerun": "home_run", "home run": "home_run", "hr": "home_run",
    "sac_fly": "sacrifice_fly", "sac fly": "sacrifice_fly", "sacfly": "sacrifice_fly",
    "sac_bunt": "sacrifice_bunt", "sac bunt": "sacrifice_bunt",
    "fielder's_choice": "fielders_choice", "fielders choice": "fielders_choice",
    "fielder's choice": "fielders_choice",
    "ground_out": "groundout", "ground out": "groundout",
    "fly_out": "flyout", "fly out": "flyout",
    "wild pitch": "wild_pitch", "passed ball": "passed_ball",
    "hit by pitch": "hit_by_pitch", "hbp": "hit_by_pitch",
    "stolen base": "stolen_base", "double play": "double_play",
}


def norm(s):
    return re.sub(r"[^a-z]", "", str(s).lower())


def norm_event(s):
    key = str(s).strip().lower()
    key = EVENT_ALIASES.get(key, key)
    return re.sub(r"[^a-z_]", "", key)


def norm_half(s):
    h = norm(s)
    if h in ("top", "t", "tophalf"):
        return "top"
    if h in ("bottom", "bot", "b", "bottomhalf"):
        return "bottom"
    return h


# Lastnames that are unique among GT players can be matched on lastname alone;
# ambiguous ones would require the full name (here every lastname is unique --
# note Kramer and Cramer are different players and stay distinct under norm()).
def _lastname(name):
    return norm(name.split()[-1]) if str(name).split() else norm(name)


_GT_NAMES = [g["scorer"] for g in GROUND_TRUTH] + [g["batter"] for g in GROUND_TRUTH]
_GT_LASTS = [_lastname(n) for n in set(_GT_NAMES)]
_UNIQUE_LASTS = {ln for ln in _GT_LASTS if _GT_LASTS.count(ln) == 1}


def name_match(pred, gt_full):
    p, g = norm(pred), norm(gt_full)
    if not p:
        return False
    if p == g:
        return True
    gl = _lastname(gt_full)
    return gl in _UNIQUE_LASTS and p == gl  # lastname only if unambiguous


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solution", required=True, type=Path)
    ap.add_argument("--reward-json", required=True, type=Path)
    ap.add_argument("--reward-txt", required=True, type=Path)
    args = ap.parse_args()

    reason = "ok"
    preds = []
    try:
        sol = json.loads(args.solution.read_text())
        preds = sol.get("runs", [])
        if not isinstance(preds, list):
            raise ValueError("runs is not a list")
    except Exception as exc:  # noqa: BLE001 - malformed output scores 0
        reason, preds = f"unreadable solution.json: {exc}", []

    used = [False] * len(GROUND_TRUTH)        # strict (full-run) TPs
    used_loose = [False] * len(GROUND_TRUTH)  # scorer+inning+half only, diagnostics
    tp = 0
    scorer_inning_only = 0
    for pr in preds:
        if not isinstance(pr, dict):
            continue
        try:
            pi = int(pr.get("inning"))
        except (TypeError, ValueError):
            continue
        ph = norm_half(pr.get("half", ""))
        # diagnostic: did it at least place the right scorer in the right half-inning?
        for i, gt in enumerate(GROUND_TRUTH):
            if not used_loose[i] and pi == gt["inning"] and ph == gt["half"] \
                    and name_match(pr.get("scorer", ""), gt["scorer"]):
                used_loose[i] = True
                scorer_inning_only += 1
                break
        # scored: full-run reconstruction (also requires batter and event)
        for i, gt in enumerate(GROUND_TRUTH):
            if not used[i] and pi == gt["inning"] and ph == gt["half"] \
                    and name_match(pr.get("scorer", ""), gt["scorer"]) \
                    and name_match(pr.get("batter", ""), gt["batter"]) \
                    and norm_event(pr.get("event", "")) == gt["event"]:
                used[i] = True
                tp += 1
                break

    n_pred, n_gt = len(preds), len(GROUND_TRUTH)
    precision = tp / n_pred if n_pred else 0.0
    recall = tp / n_gt if n_gt else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    details = {
        "reason": reason,
        "n_ground_truth": n_gt,
        "n_predicted": n_pred,
        "true_positives_full_run": tp,
        "scorer_inning_only_matches": scorer_inning_only,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }
    args.reward_json.parent.mkdir(parents=True, exist_ok=True)
    args.reward_json.write_text(json.dumps({"reward": round(f1, 4), "details": details}, indent=2))
    args.reward_txt.write_text(f"{round(f1, 4)}\n")


if __name__ == "__main__":
    main()
