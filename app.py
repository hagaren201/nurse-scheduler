import streamlit as st
import pandas as pd
from pathlib import Path
from engine.loader import load_schedule_input
from engine.capacity import derive_monthly_max_shifts
from engine.greedy import multi_run_greedy
from engine.violations import build_top_n_summary, build_violation_overview_compare
from engine.calendar_view import build_nurse_calendar
from engine.constants import DEFAULT_WEIGHTS
from engine.export import export_schedule


# =========================================
# PAGE CONFIG
# =========================================
st.set_page_config(
    page_title="Nurse Scheduling Prototype",
    layout="wide"
)

st.title("🩺 Nurse Scheduling Prototype")
st.caption("Greedy-based nurse scheduling with violation-aware optimization")

if "results" not in st.session_state:
    st.session_state.results = None

if "mode" not in st.session_state:
    st.session_state.mode = None

# =========================================
# SIDEBAR – INPUT
# =========================================
from pathlib import Path

st.sidebar.header("1️⃣ Input")

BASE_DIR = Path(__file__).resolve().parent
SAMPLE_INPUT_PATH = BASE_DIR / "data" / "schedule_input_sample.xlsx"

uploaded_file = st.sidebar.file_uploader(
    "Upload schedule_input.xlsx",
    type=["xlsx"]
)

if uploaded_file is not None:
    input_source = uploaded_file
    st.sidebar.success("Using uploaded Excel file")
else:
    if not SAMPLE_INPUT_PATH.exists():
        st.error("Sample input file not found. Please upload an Excel file.")
        st.stop()

    input_source = SAMPLE_INPUT_PATH
    st.sidebar.info("Using sample schedule_input (default)")

st.sidebar.markdown(
    "📌 **Default behavior**  \n"
    "- No upload → sample data used  \n"
    "- Upload Excel → your data applied"
)

N_RUNS = st.sidebar.slider(
    "Number of greedy runs",
    min_value=10,
    max_value=300,
    value=100,
    step=10
)

st.sidebar.header("2️⃣ Penalty Weights")

weights = {
    "OFF_REQUEST_VIOLATION": st.sidebar.slider(
        "OFF request violation",
        0, 300, DEFAULT_WEIGHTS["OFF_REQUEST_VIOLATION"]
    ),
    "CONSECUTIVE_WORK_PER_DAY": st.sidebar.slider(
        "Consecutive work",
        0, 100, DEFAULT_WEIGHTS["CONSECUTIVE_WORK_PER_DAY"]
    ),
    "NIGHT_EXCESS_PER_SHIFT": st.sidebar.slider(
        "Night imbalance",
        0, 100, DEFAULT_WEIGHTS["NIGHT_EXCESS_PER_SHIFT"]
    ),
    "UNFILLED_SLOT": st.sidebar.slider(
        "Unfilled slot",
        0, 300, DEFAULT_WEIGHTS["UNFILLED_SLOT"]
    )
}

# =========================================
# MAIN – RUN
# =========================================
# LOAD INPUT
nurses, calendar, requirements, requests = load_schedule_input(input_source)
nurses = derive_monthly_max_shifts(calendar, nurses)

st.success(
    f"Loaded {len(nurses)} nurses | "
    f"Derived monthly_max_shifts = {nurses['monthly_max_shifts'].iloc[0]}"
)

# RUN BUTTON
if st.button("🚀 Run Scheduler"):
    with st.spinner("Running scheduler..."):
        results = multi_run_greedy(
            nurses, calendar, requirements, requests,
            n_runs=N_RUNS,
            weights=weights,
            allow_unfilled=False
        )

        mode = "STRICT"

        if len(results) == 0:
            results = multi_run_greedy(
                nurses, calendar, requirements, requests,
                n_runs=N_RUNS,
                weights=weights,
                allow_unfilled=True
            )
            mode = "RELAXED"

    # 🔥 핵심
    st.session_state.results = results
    st.session_state.mode = mode

if st.session_state.results is not None:
    results = st.session_state.results
    mode = st.session_state.mode
    st.success(f"Scheduler finished (mode = {mode})")

    # =====================================
    # TOP-N SUMMARY
    # =====================================
    st.subheader("📊 Top Candidate Schedules")
    TOP_N = min(5, len(results))
    top_n_df = build_top_n_summary(results, top_n=TOP_N)
    st.dataframe(top_n_df, use_container_width=True)

    overview_df = build_violation_overview_compare(
        results,
        top_n=TOP_N,
        weights=weights
    )
    st.dataframe(overview_df, use_container_width=True)

    # =====================================
    # SELECT FINAL
    # =====================================
    st.subheader("✅ Select Schedule")

    selected_rank = st.radio(
        "Choose candidate",
        options=top_n_df["rank"].tolist(),
        horizontal=True
    )

    chosen = results[selected_rank - 1]
    schedule_df = chosen["schedule"]

    st.markdown(
        f"""
        **Selected Result**
        - Rank: {selected_rank}
        - Seed: {chosen['seed']}
        - Total Penalty: {chosen['penalty']}
        - UNFILLED: {chosen['unfilled_count']}
        """
    )

    # =====================================
    # NURSE CALENDAR VIEW
    # =====================================
    st.subheader("🗓 Nurse Monthly Calendar")

    nurse_id = st.selectbox(
        "Select nurse",
        nurses["nurse_id"].tolist()
    )

    cal = build_nurse_calendar(schedule_df, nurse_id)
    st.dataframe(cal, use_container_width=True)

    # =====================================
    # EXPORT
    # =====================================
    st.subheader("⬇️ Export")

    if st.button("Download Excel"):
        output_path = "schedule_output.xlsx"
        export_schedule(schedule_df, requests, output_path)

        with open(output_path, "rb") as f:
            st.download_button(
                label="Download schedule_output.xlsx",
                data=f,
                file_name="schedule_output.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
