import pandas as pd
def build_nurse_calendar(schedule_df, nurse_id):
    df = schedule_df.copy()
    df["date"] = pd.to_datetime(df["date"])

    month_start = df["date"].min().replace(day=1)
    month_end = df["date"].max()

    nurse_df = df[
        (df["nurse_id"] == nurse_id) &
        (df["status"] == "ASSIGNED")
    ]

    daily = (
        nurse_df.groupby("date")["shift"]
        .first()
        .to_dict()
        if not nurse_df.empty
        else {}
    )

    all_dates = pd.date_range(month_start, month_end, freq="D")

    rows = []
    for d in all_dates:
        rows.append({
            "week": d.isocalendar().week,
            "weekday": d.weekday(),
            "shift": daily.get(d.normalize(), "OFF")
        })

    cal_df = pd.DataFrame(rows)

    cal = cal_df.pivot_table(
        index="week",
        columns="weekday",
        values="shift",
        aggfunc="first"
    )

    cal.columns = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    cal = cal.fillna("")

    return cal
