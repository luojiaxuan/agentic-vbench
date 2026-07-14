#!/usr/bin/env python3
"""Grade a run-scoring-timeline reconstruction. Pure Python stdlib, deterministic.

The agent must list every run scored with inning, half, the runner who scored, the
batter at the plate, and the event type. Scoring is two-tier:

  * full credit (1.0)    — inning, half, scorer, batter, AND event all match;
  * partial credit (0.5) — inning, half, scorer, and batter match but the event
    category differs.

The partial tier exists because some event labels are official-scorer rulings a
perfect visual agent can legitimately miss (a ball misplayed by a fielder is a hit
or an error by ruling, not by sight). For the same reason wild_pitch and passed_ball
— visually identical, split only by the scorer's fault assignment — are merged into
one equivalence class. reward = F1 over summed credit (misses and false positives
both hurt).

Why this task and metric: a full game has ~15 runs scattered across 3 hours. The
score bug shows only the totals changing — it never names the runner who crossed the
plate. Attributing each run means tracking the scoring runner from his own earlier
plate appearance to the moment he touches home, so only genuinely reconstructing the
game off the video scores. The oracle (exact list) -> 1.0; an empty or guessed
list -> ~0.

Baseball has no game clock, so there is no time tolerance; the (inning, half) pair
anchors each run. Duplicate keys — the same runner scoring twice in one half-inning,
or two runs on one swing — are handled by greedy one-to-one multiset matching (each
ground-truth run can be consumed by at most one prediction). Exact (full-credit)
matches are assigned in a first pass so a partial match can never steal a slot from
an exact one.
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

PARTIAL_CREDIT = 0.5  # identity right, event category wrong (official-ruling ceiling)

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

# Official-scorer equivalence classes: labels a flawless visual agent cannot be
# expected to separate. wild_pitch vs passed_ball is a fault ruling (pitcher vs
# catcher) over the same visual play.
EVENT_GROUPS = {"passed_ball": "wild_pitch"}


def norm(s):
    return re.sub(r"[^a-z]", "", str(s).lower())


def norm_event(s):
    key = str(s).strip().lower()
    key = EVENT_ALIASES.get(key, key)
    key = re.sub(r"[^a-z_]", "", key)
    return EVENT_GROUPS.get(key, key)


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


def parse_pred(pr):
    if not isinstance(pr, dict):
        return None
    try:
        inning = int(pr.get("inning"))
    except (TypeError, ValueError):
        return None
    return {
        "inning": inning,
        "half": norm_half(pr.get("half", "")),
        "scorer": pr.get("scorer", ""),
        "batter": pr.get("batter", ""),
        "event": norm_event(pr.get("event", "")),
    }


def identity_match(p, gt):
    return p["inning"] == gt["inning"] and p["half"] == gt["half"] \
        and name_match(p["scorer"], gt["scorer"]) \
        and name_match(p["batter"], gt["batter"])


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

    parsed = [parse_pred(pr) for pr in preds]

    used = [False] * len(GROUND_TRUTH)
    consumed = [False] * len(parsed)
    full = 0
    # pass 1: exact matches (identity + event) so partials never steal exact slots
    for j, p in enumerate(parsed):
        if p is None:
            continue
        for i, gt in enumerate(GROUND_TRUTH):
            if not used[i] and identity_match(p, gt) \
                    and p["event"] == norm_event(gt["event"]):
                used[i] = True
                consumed[j] = True
                full += 1
                break
    # pass 2: identity-only matches at partial credit
    partial = 0
    for j, p in enumerate(parsed):
        if p is None or consumed[j]:
            continue
        for i, gt in enumerate(GROUND_TRUTH):
            if not used[i] and identity_match(p, gt):
                used[i] = True
                consumed[j] = True
                partial += 1
                break

    # diagnostic: right scorer in the right half-inning, batter/event aside
    used_loose = [False] * len(GROUND_TRUTH)
    scorer_inning_only = 0
    for p in parsed:
        if p is None:
            continue
        for i, gt in enumerate(GROUND_TRUTH):
            if not used_loose[i] and p["inning"] == gt["inning"] \
                    and p["half"] == gt["half"] \
                    and name_match(p["scorer"], gt["scorer"]):
                used_loose[i] = True
                scorer_inning_only += 1
                break

    credit = full + PARTIAL_CREDIT * partial
    n_pred, n_gt = len(preds), len(GROUND_TRUTH)
    precision = credit / n_pred if n_pred else 0.0
    recall = credit / n_gt if n_gt else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    details = {
        "reason": reason,
        "n_ground_truth": n_gt,
        "n_predicted": n_pred,
        "full_matches": full,
        "partial_matches_event_off": partial,
        "credit": round(credit, 4),
        "scorer_inning_only_matches": scorer_inning_only,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "partial_credit": PARTIAL_CREDIT,
    }
    args.reward_json.parent.mkdir(parents=True, exist_ok=True)
    args.reward_json.write_text(json.dumps({"reward": round(f1, 4), "details": details}, indent=2))
    args.reward_txt.write_text(f"{round(f1, 4)}\n")


if __name__ == "__main__":
    main()
