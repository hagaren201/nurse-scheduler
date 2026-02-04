from collections import defaultdict
import pandas as pd

from engine.constants import DEFAULT_WEIGHTS
def penalty_consecutive_work(v_df, weight):
    if v_df.empty:
        return 0
    total = 0
    for _, r in v_df.iterrows():
        days = int(r["detail"].split()[0])
        excess = max(0, days - 6)
        total += excess * weight
    return total
def penalty_night_imbalance(v_df, weight):
    if v_df.empty:
        return 0
    return int((v_df["excess"] * weight).sum())
def penalty_off_request(v_df, weight):
    return len(v_df) * weight
def calc_total_penalty(violations, weights, unfilled_count=0):
    breakdown = {}

    breakdown["OFF_REQUEST"] = penalty_off_request(
        violations["off_request"],
        weights["OFF_REQUEST_VIOLATION"]
    )

    breakdown["CONSECUTIVE_WORK"] = penalty_consecutive_work(
        violations["consecutive_work"],
        weights["CONSECUTIVE_WORK_PER_DAY"]
    )

    breakdown["NIGHT_IMBALANCE"] = penalty_night_imbalance(
        violations["night_imbalance"],
        weights["NIGHT_EXCESS_PER_SHIFT"]
    )

    breakdown["UNFILLED"] = unfilled_count * weights["UNFILLED_SLOT"]

    total = sum(breakdown.values())
    return total, breakdown
def calc_consecutive_work_violations(schedule_df, max_consecutive=6):
    df = schedule_df[schedule_df["status"] == "ASSIGNED"].copy()
    df = df.sort_values(["nurse_id", "date"])

    violations = []

    for nurse_id, g in df.groupby("nurse_id"):
        dates = list(g["date"].unique())
        dates.sort()

        streak = 1
        for i in range(1, len(dates)):
            if (dates[i] - dates[i - 1]).days == 1:
                streak += 1
                if streak > max_consecutive:
                    violations.append({
                        "violation_type": "CONSECUTIVE_WORK",
                        "nurse_id": nurse_id,
                        "date": dates[i],
                        "detail": f"{streak} consecutive days"
                    })
            else:
                streak = 1

    return pd.DataFrame(violations)
def calc_night_imbalance(schedule_df):
    df = schedule_df[
        (schedule_df["status"] == "ASSIGNED") &
        (schedule_df["shift"] == "N")
    ]

    counts = df.groupby("nurse_id").size().reset_index(name="night_count")
    avg = counts["night_count"].mean() if not counts.empty else 0

    counts["avg_night"] = round(avg, 2)
    counts["excess"] = counts["night_count"] - avg
    counts["violation_type"] = "NIGHT_IMBALANCE"

    return counts[counts["excess"] > 0]
def calc_off_request_violations(schedule_df, requests_df):
    off_req = requests_df[requests_df["request_type"] == "OFF_REQUEST"].copy()
    assigned = schedule_df[schedule_df["status"] == "ASSIGNED"]

    merged = off_req.merge(
        assigned,
        on=["nurse_id", "date"],
        how="inner"
    )

    if merged.empty:
        return pd.DataFrame(columns=[
            "violation_type", "nurse_id", "date", "shift", "detail"
        ])

    merged["violation_type"] = "OFF_REQUEST_VIOLATION"
    merged["detail"] = "OFF request ignored"

    return merged[["violation_type", "nurse_id", "date", "shift", "detail"]]
def build_violation_summary(schedule_df, requests_df):
    return {
        "consecutive_work": calc_consecutive_work_violations(schedule_df),
        "night_imbalance": calc_night_imbalance(schedule_df),
        "off_request": calc_off_request_violations(schedule_df, requests_df)
    }
def build_top_n_summary(results_sorted, top_n=5):
    rows = []
    for rank, r in enumerate(results_sorted[:top_n], start=1):
        rows.append({
            "rank": rank,
            "seed": r["seed"],
            "total_penalty": r["penalty"]
        })
    return pd.DataFrame(rows)
def build_violation_overview_compare(results_sorted, top_n, weights=DEFAULT_WEIGHTS):
    rows = []

    for rank, r in enumerate(results_sorted[:top_n], start=1):
        violations = r["violations"]

        row = {
            "rank": rank,
            "seed": r["seed"],
            "total_penalty": r["penalty"]
        }

        row["OFF_REQUEST_VIOLATION_count"] = len(violations["off_request"])
        row["CONSECUTIVE_WORK_count"] = len(violations["consecutive_work"])
        row["NIGHT_IMBALANCE_count"] = len(violations["night_imbalance"])

        rows.append(row)

    return pd.DataFrame(rows)
