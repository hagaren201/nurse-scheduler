import pandas as pd


def derive_monthly_max_shifts(calendar_df, nurses_df):
    days_in_month = calendar_df["date"].nunique()

    is_off = (
        calendar_df["is_weekend"].astype(bool)
        | calendar_df["is_holiday"].astype(bool)
    )

    base_off_days = calendar_df.loc[is_off, "date"].nunique()
    base_working_days = days_in_month - base_off_days

    nurses_df = nurses_df.copy()
    nurses_df["monthly_max_shifts"] = base_working_days

    return nurses_df
