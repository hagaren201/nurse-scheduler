import random
from datetime import timedelta
from collections import defaultdict

import pandas as pd

from engine.constants import SHIFT_ORDER
from engine.violations import build_violation_summary, calc_total_penalty
def parse_requests(requests_df):
    off_requests = set()
    shift_avoid = defaultdict(set)

    for _, r in requests_df.iterrows():
        nid = r["nurse_id"]
        d = r["date"]
        typ = r["request_type"]

        if typ == "OFF_REQUEST":
            off_requests.add((nid, d))

        elif typ == "SHIFT_AVOID" and isinstance(r.get("shift"), str):
            shift_avoid[(nid, d)].add(r["shift"].upper().strip())

    return off_requests, shift_avoid
def can_assign(
    nid, date, shift,
    assigned_today,
    last_shift,
    month_count,
    nurse_meta
):
    if nid in assigned_today:
        return False

    if month_count[nid] >= nurse_meta[nid]["monthly_max_shifts"]:
        return False

    if shift == "N" and not nurse_meta[nid]["night_ok"]:
        return False

    prev_day = date - timedelta(days=1)
    if shift == "D" and last_shift.get((nid, prev_day)) == "N":
        return False

    return True
def greedy_schedule(nurses, calendar, requirements, requests, seed=42):
    random.seed(seed)

    nurse_meta = {
        r["nurse_id"]: {
            "night_ok": r["night_ok"],
            "monthly_max_shifts": r["monthly_max_shifts"]
        }
        for _, r in nurses.iterrows()
    }

    nurse_ids = list(nurse_meta.keys())
    dates = sorted(calendar["date"].unique())

    off_requests, shift_avoid = parse_requests(requests)

    required = {
        (r["date"], r["shift"]): int(r["required"])
        for _, r in requirements.iterrows()
    }

    assigned_today = {d: set() for d in dates}
    last_shift = {}
    month_count = defaultdict(int)

    rows = []

    for d in dates:
        for shift in SHIFT_ORDER:
            need = required.get((d, shift), 0)

            for _ in range(need):
                candidates = []

                for nid in nurse_ids:
                    if not can_assign(
                        nid, d, shift,
                        assigned_today[d],
                        last_shift,
                        month_count,
                        nurse_meta
                    ):
                        continue

                    score = 0
                    if (nid, d) in off_requests:
                        score += 1000
                    if shift in shift_avoid.get((nid, d), set()):
                        score += 50
                    score += month_count[nid]

                    candidates.append((score, random.random(), nid))

                if not candidates:
                    rows.append({
                        "date": d,
                        "shift": shift,
                        "nurse_id": None,
                        "status": "UNFILLED"
                    })
                    continue

                _, _, chosen = min(candidates)
                assigned_today[d].add(chosen)
                last_shift[(chosen, d)] = shift
                month_count[chosen] += 1

                rows.append({
                    "date": d,
                    "shift": shift,
                    "nurse_id": chosen,
                    "status": "ASSIGNED"
                })

    return pd.DataFrame(rows)
def multi_run_greedy(
    nurses, calendar, requirements, requests,
    n_runs=100,
    weights=None,
    allow_unfilled=False
):
    results = []

    for seed in range(n_runs):
        schedule = greedy_schedule(
            nurses, calendar, requirements, requests, seed=seed
        )

        unfilled_count = len(schedule[schedule["status"] == "UNFILLED"])

        if not allow_unfilled and unfilled_count > 0:
            continue

        violations = build_violation_summary(schedule, requests)

        penalty, breakdown = calc_total_penalty(
            violations,
            weights,
            unfilled_count=unfilled_count if allow_unfilled else 0
        )

        results.append({
            "seed": seed,
            "penalty": penalty,
            "penalty_breakdown": breakdown,
            "unfilled_count": unfilled_count,
            "schedule": schedule,
            "violations": violations
        })

    return sorted(results, key=lambda x: x["penalty"])
