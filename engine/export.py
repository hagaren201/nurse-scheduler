import pandas as pd

from engine.violations import build_violation_summary
def summarize_unfilled(schedule_df):
    uf = schedule_df[schedule_df["status"] == "UNFILLED"]
    if uf.empty:
        return pd.DataFrame(columns=["date", "shift", "count"])
    return (
        uf.groupby(["date", "shift"])
          .size()
          .reset_index(name="count")
          .sort_values(["date", "shift"])
    )
def export_schedule(df, requests_df, path):
    violations = build_violation_summary(df, requests_df)

    with pd.ExcelWriter(path, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="schedule_long", index=False)

        ok = df[df["status"] == "ASSIGNED"]
        pivot = (
            ok.groupby(["date", "shift"])["nurse_id"]
              .apply(lambda x: ", ".join(x))
              .reset_index()
        )
        pivot.to_excel(w, sheet_name="schedule_by_shift", index=False)

        for k, vdf in violations.items():
            if not vdf.empty:
                vdf.to_excel(w, sheet_name=f"violation_{k}", index=False)

        uf_summary = summarize_unfilled(df)
        if not uf_summary.empty:
            uf_summary.to_excel(w, sheet_name="unfilled_summary", index=False)
