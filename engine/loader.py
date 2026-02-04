import pandas as pd


def load_schedule_input(path):
    xl = pd.ExcelFile(path)

    nurses = xl.parse("nurses")
    calendar = xl.parse("calendar")
    requirements = xl.parse("requirements")
    requests = xl.parse("requests")

    # 날짜 타입 통일
    for df in [calendar, requirements, requests]:
        df["date"] = pd.to_datetime(df["date"]).dt.date

    nurses["night_ok"] = (
        nurses["night_ok"]
        .astype(str)
        .str.upper()
        .map({"Y": True, "N": False})
    )

    requirements["shift"] = requirements["shift"].str.upper().str.strip()

    return nurses, calendar, requirements, requests
