import json
import glob
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from pyarrow.feather import read_feather

# ── Config ────────────────────────────────────────────────────────────────────


DATA_DIR = Path("./")

st.set_page_config(
    page_title="Polar Workout Dashboard",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Data loading ───────────────────────────────────────────────────────────────


def parse_duration_seconds(s: str | None) -> float:
    """Parse ISO 8601 duration PT<n>S → seconds."""
    if not s:
        return 0.0
    m = re.match(r"PT([\d.]+)S", str(s))
    return float(m.group(1)) if m else 0.0


def parse_zone_seconds(zones: list) -> dict:
    out = {}
    for z in zones:
        idx = z.get("zoneIndex", 0)
        out[f"z{idx}"] = parse_duration_seconds(z.get("inZone"))
    return out


@st.cache_data(show_spinner="Parsing Polar data (one-time)…")
def load_sessions():
    return pd.read_feather("sessions.feather")

# def parse_sessions_to_df(data_dir: str) -> pd.DataFrame:
#     files = sorted(glob.glob(os.path.join(data_dir, "training-session-*.json")))
#     rows = []
#     for fp in files:
#         try:
#             with open(fp) as f:
#                 d = json.load(f)
#         except Exception:
#             continue
#
#         ex_list = d.get("exercises", [])
#         sport = ex_list[0].get("sport", "UNKNOWN") if ex_list else "UNKNOWN"
#         # aggregate zone time across exercises
#         z_total = {f"z{i}": 0.0 for i in range(1, 6)}
#         dist_total = 0.0
#         ascent_total = 0.0
#         descent_total = 0.0
#         for ex in ex_list:
#             dist_total += ex.get("distance") or 0.0
#             ascent_total += ex.get("ascent") or 0.0
#             descent_total += ex.get("descent") or 0.0
#             hr_zones = ex.get("zones", {}).get("heart_rate", [])
#             for k, v in parse_zone_seconds(hr_zones).items():
#                 z_total[k] = z_total.get(k, 0.0) + v
#
#         # session-level distance fallback
#         if dist_total == 0.0:
#             dist_total = d.get("distance") or 0.0
#
#         row = {
#             "start": pd.to_datetime(d.get("startTime")),
#             "stop": pd.to_datetime(d.get("stopTime")),
#             "duration_s": parse_duration_seconds(d.get("duration")),
#             "sport": sport,
#             "avg_hr": d.get("averageHeartRate"),
#             "max_hr": d.get("maximumHeartRate"),
#             "kcal": d.get("kiloCalories"),
#             "feeling": float(d["feeling"]) if d.get("feeling") else None,
#             "distance_m": dist_total,
#             "ascent_m": ascent_total,
#             "descent_m": descent_total,
#             **z_total,
#         }
#         rows.append(row)
#
#     df = pd.DataFrame(rows)
#     df["duration_min"] = df["duration_s"] / 60
#     df["distance_km"] = df["distance_m"] / 1000
#     df["pace_min_km"] = np.where(
#         df["distance_km"] > 0,
#         df["duration_min"] / df["distance_km"],
#         np.nan,
#     )
#     df["speed_kmh"] = np.where(
#         df["duration_min"] > 0,
#         df["distance_km"] / (df["duration_min"] / 60),
#         np.nan,
#     )
#     df["week"] = df["start"].dt.to_period("W").apply(lambda p: p.start_time)
#     df["month"] = df["start"].dt.to_period("M").apply(lambda p: p.start_time)
#     df["year"] = df["start"].dt.year
#     df["dow"] = df["start"].dt.day_name()
#     df["hour"] = df["start"].dt.hour
#     return df
#
#
# @st.cache_data(show_spinner="Loading HR samples…")
# def load_hr_samples(data_dir: str, max_files: int = 500) -> pd.DataFrame:
#     """Load per-second HR traces for sessions that have them."""
#     files = sorted(glob.glob(os.path.join(data_dir, "training-session-*.json")))
#     rows = []
#     for fp in files[:max_files]:
#         try:
#             with open(fp) as f:
#                 d = json.load(f)
#         except Exception:
#             continue
#         sport = (d.get("exercises") or [{}])[0].get("sport", "?")
#         for ex in d.get("exercises", []):
#             samples = ex.get("samples", {}).get("heartRate", [])
#             for s in samples:
#                 rows.append(
#                     {
#                         "session": Path(fp).stem[:30],
#                         "sport": sport,
#                         "dt": pd.to_datetime(s["dateTime"]),
#                         "hr": s["value"],
#                     }
#                 )
#     return pd.DataFrame(rows)


# ── Sidebar ────────────────────────────────────────────────────────────────────

df = load_sessions()

with st.sidebar:
    st.title("🏃 Polar Dashboard")
    st.caption(f"Data: `{DATA_DIR}`")

    sports = sorted(df["sport"].unique())
    sel_sports = st.multiselect("Sport", sports, default=sports)

    year_min, year_max = int(df["year"].min()), int(df["year"].max())
    sel_years = st.slider("Year range", year_min, year_max, (year_min, year_max))

    st.divider()
    st.caption(f"{len(df):,} sessions loaded")

mask = df["sport"].isin(sel_sports) & df["year"].between(sel_years[0], sel_years[1])
dff = df[mask].copy()

# ── KPI row ────────────────────────────────────────────────────────────────────

st.header("Polar Workout Analytics", divider="gray")

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Sessions", f"{len(dff):,}")
k2.metric("Total hours", f"{dff['duration_min'].sum() / 60:,.0f}")
k3.metric("Total km", f"{dff['distance_km'].sum():,.0f}")
k4.metric("Total kcal", f"{dff['kcal'].sum():,.0f}")
k5.metric("Avg HR", f"{dff['avg_hr'].mean():.0f} bpm")
k6.metric("Years active", f"{sel_years[1] - sel_years[0] + 1}")

# ── Tabs ───────────────────────────────────────────────────────────────────────

tab_vol, tab_hr, tab_zones, tab_patterns, tab_speed, tab_corr, tab_session = st.tabs(
    [
        "📅 Volume",
        "❤️ Heart Rate",
        "🟢 HR Zones",
        "📆 Patterns",
        "⚡ Speed & Pace",
        "🔗 Correlations",
        "🔍 Session Deep-Dive",
    ]
)

SPORT_COLORS = {"RUNNING": "#EF553B", "CYCLING": "#636EFA", "SWIMMING": "#00CC96"}

# ── Tab 1: Volume ──────────────────────────────────────────────────────────────

with tab_vol:
    col_a, col_b = st.columns([3, 1])

    with col_a:
        resample = st.radio(
            "Aggregate by",
            ["Week", "Month", "Year"],
            horizontal=True,
            key="vol_resample",
        )

    agg_col = {"Week": "week", "Month": "month", "Year": "year"}[resample]

    vol = (
        dff.groupby([agg_col, "sport"])
        .agg(
            sessions=("duration_min", "count"),
            minutes=("duration_min", "sum"),
            km=("distance_km", "sum"),
        )
        .reset_index()
        .rename(columns={agg_col: "period"})
    )
    vol["period"] = vol["period"].astype(str)

    fig_vol = px.bar(
        vol,
        x="period",
        y="minutes",
        color="sport",
        color_discrete_map=SPORT_COLORS,
        title=f"Training Volume by {resample}",
        labels={"minutes": "Duration (min)", "period": resample},
        barmode="stack",
    )
    fig_vol.update_layout()
    st.plotly_chart(fig_vol)

    col1, col2 = st.columns(2)

    with col1:
        sport_summary = (
            dff.groupby("sport")
            .agg(
                sessions=("duration_min", "count"),
                hours=("duration_min", lambda x: x.sum() / 60),
                km=("distance_km", "sum"),
            )
            .reset_index()
        )
        fig_pie = px.pie(
            sport_summary,
            values="hours",
            names="sport",
            color="sport",
            color_discrete_map=SPORT_COLORS,
            title="Hours by Sport",
            hole=0.45,
        )
        fig_pie.update_traces(textinfo="label+percent")
        st.plotly_chart(fig_pie)

    with col2:
        yearly = (
            dff.groupby(["year", "sport"])
            .agg(sessions=("duration_min", "count"))
            .reset_index()
        )
        fig_yr = px.bar(
            yearly,
            x="year",
            y="sessions",
            color="sport",
            color_discrete_map=SPORT_COLORS,
            title="Sessions per Year",
            barmode="stack",
        )
        fig_yr.update_layout(height=320)
        st.plotly_chart(fig_yr)

    # Cumulative volume
    cum = dff.sort_values("start").assign(
        cum_hours=lambda d: d["duration_min"].cumsum() / 60
    )
    fig_cum = px.area(
        cum,
        x="start",
        y="cum_hours",
        color="sport",
        color_discrete_map=SPORT_COLORS,
        title="Cumulative Training Hours",
        labels={"cum_hours": "Hours", "start": "Date"},
    )
    fig_cum.update_layout(height=320)
    st.plotly_chart(fig_cum)

# ── Tab 2: Heart Rate ──────────────────────────────────────────────────────────

with tab_hr:
    col1, col2 = st.columns(2)

    with col1:
        fig_hr_dist = px.histogram(
            dff.dropna(subset=["avg_hr"]),
            x="avg_hr",
            color="sport",
            color_discrete_map=SPORT_COLORS,
            nbins=40,
            barmode="overlay",
            opacity=0.7,
            title="Average HR Distribution by Sport",
            labels={"avg_hr": "Avg HR (bpm)"},
        )
        fig_hr_dist.update_layout(height=360)
        st.plotly_chart(fig_hr_dist)

    with col2:
        fig_hr_box = px.box(
            dff.dropna(subset=["avg_hr"]),
            x="sport",
            y="avg_hr",
            color="sport",
            color_discrete_map=SPORT_COLORS,
            points="outliers",
            title="HR Distribution by Sport",
            labels={"avg_hr": "Avg HR (bpm)"},
        )
        fig_hr_box.update_layout(height=360, showlegend=False)
        st.plotly_chart(fig_hr_box)

    # HR trend over time (rolling 4w average)
    hr_time = (
        dff.dropna(subset=["avg_hr"])
        .sort_values("start")
        .set_index("start")
        .groupby("sport")["avg_hr"]
        .rolling("28D", min_periods=3)
        .mean()
        .reset_index()
    )
    fig_hr_trend = px.line(
        hr_time,
        x="start",
        y="avg_hr",
        color="sport",
        color_discrete_map=SPORT_COLORS,
        title="Average HR Trend (28-day rolling mean)",
        labels={"avg_hr": "Avg HR (bpm)", "start": "Date"},
    )
    fig_hr_trend.update_layout(height=340)
    st.plotly_chart(fig_hr_trend)

    # HR efficiency: avg HR vs duration
    fig_hr_dur = px.scatter(
        dff.dropna(subset=["avg_hr"]),
        x="duration_min",
        y="avg_hr",
        color="sport",
        color_discrete_map=SPORT_COLORS,
        opacity=0.5,
        trendline="lowess",
        title="Avg HR vs Session Duration",
        labels={"duration_min": "Duration (min)", "avg_hr": "Avg HR (bpm)"},
    )
    fig_hr_dur.update_layout(height=340)
    st.plotly_chart(fig_hr_dur)

# ── Tab 3: HR Zones ────────────────────────────────────────────────────────────

with tab_zones:
    zone_cols = ["z1", "z2", "z3", "z4", "z5"]
    zone_labels = {
        "z1": "Z1 Easy",
        "z2": "Z2 Aerobic",
        "z3": "Z3 Tempo",
        "z4": "Z4 Threshold",
        "z5": "Z5 VO2max",
    }
    zone_colors = ["#74B9FF", "#55EFC4", "#FDCB6E", "#E17055", "#D63031"]

    has_zones = dff[zone_cols].sum(axis=1) > 0
    dfz = dff[has_zones].copy()

    if dfz.empty:
        st.info("No HR zone data in current selection.")
    else:
        # Overall zone breakdown per sport
        zone_sport = dfz.groupby("sport")[zone_cols].sum().reset_index()
        zone_sport_long = zone_sport.melt(
            id_vars="sport", var_name="zone", value_name="seconds"
        )
        zone_sport_long["minutes"] = zone_sport_long["seconds"] / 60
        zone_sport_long["label"] = zone_sport_long["zone"].map(zone_labels)

        fig_zones = px.bar(
            zone_sport_long,
            x="sport",
            y="minutes",
            color="label",
            color_discrete_sequence=zone_colors,
            title="Total Time in HR Zones by Sport",
            labels={"minutes": "Time (min)"},
            barmode="stack",
        )
        st.plotly_chart(fig_zones)

        # Zone fractions per session over time
        for z in zone_cols:
            dfz[z + "_frac"] = dfz[z] / dfz[zone_cols].sum(axis=1).replace(0, np.nan)

        monthly_zones = (
            dfz.groupby("month")[[c + "_frac" for c in zone_cols]].mean().reset_index()
        )
        monthly_zones["month"] = monthly_zones["month"].astype(str)
        monthly_zones_long = monthly_zones.melt(
            id_vars="month", var_name="zone", value_name="fraction"
        )
        monthly_zones_long["label"] = (
            monthly_zones_long["zone"].str.replace("_frac", "").map(zone_labels)
        )

        fig_zone_time = px.area(
            monthly_zones_long,
            x="month",
            y="fraction",
            color="label",
            color_discrete_sequence=zone_colors,
            title="Monthly HR Zone Distribution (fraction)",
            labels={"fraction": "Fraction of zone time", "month": "Month"},
        )
        fig_zone_time.update_layout(height=340, xaxis_tickangle=-45)
        st.plotly_chart(fig_zone_time)

        # Polarization index: Z1+Z5 vs Z3
        dfz["polar_ratio"] = (dfz["z1"] + dfz["z5"]) / (dfz["z3"] + 1)
        pol_monthly = dfz.groupby("month")["polar_ratio"].median().reset_index()
        pol_monthly["month"] = pol_monthly["month"].astype(str)
        fig_pol = px.bar(
            pol_monthly,
            x="month",
            y="polar_ratio",
            title="Polarization Index by Month  (high = more polarized training)",
            labels={"polar_ratio": "(Z1+Z5) / Z3", "month": "Month"},
        )
        fig_pol.update_layout(height=300, xaxis_tickangle=-45)
        st.plotly_chart(fig_pol)

# ── Tab 4: Patterns ────────────────────────────────────────────────────────────

with tab_patterns:
    DOW_ORDER = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    col1, col2 = st.columns(2)

    with col1:
        dow_counts = dff.groupby(["dow", "sport"]).size().reset_index(name="count")
        dow_counts["dow"] = pd.Categorical(
            dow_counts["dow"], categories=DOW_ORDER, ordered=True
        )
        dow_counts = dow_counts.sort_values("dow")

        fig_dow = px.bar(
            dow_counts,
            x="dow",
            y="count",
            color="sport",
            color_discrete_map=SPORT_COLORS,
            title="Sessions by Day of Week",
            barmode="stack",
        )
        fig_dow.update_layout(height=340)
        st.plotly_chart(fig_dow)

    with col2:
        hour_counts = dff.groupby(["hour", "sport"]).size().reset_index(name="count")
        fig_hour = px.bar(
            hour_counts,
            x="hour",
            y="count",
            color="sport",
            color_discrete_map=SPORT_COLORS,
            title="Sessions by Hour of Day",
            barmode="stack",
            labels={"hour": "Hour (local time)"},
        )
        fig_hour.update_layout(height=340)
        st.plotly_chart(fig_hour)

    # Heatmap: day of week × hour
    heat = (
        dff.groupby(["dow", "hour"])
        .agg(sessions=("duration_min", "count"), avg_hr=("avg_hr", "mean"))
        .reset_index()
    )
    heat["dow"] = pd.Categorical(heat["dow"], categories=DOW_ORDER, ordered=True)
    heat_pivot = heat.pivot_table(
        index="dow", columns="hour", values="sessions", fill_value=0
    )
    heat_pivot = heat_pivot.reindex(DOW_ORDER)

    fig_heat = px.imshow(
        heat_pivot,
        color_continuous_scale="Blues",
        title="Session Frequency: Day × Hour",
        labels={"x": "Hour", "y": "Day", "color": "Sessions"},
        aspect="auto",
    )
    fig_heat.update_layout(height=320)
    st.plotly_chart(fig_heat)

    # Monthly kcal heatmap
    kcal_cal = (
        dff.dropna(subset=["kcal"])
        .groupby(["year", dff["start"].dt.month])["kcal"]
        .sum()
        .reset_index()
        .rename(columns={"start": "month_num"})
    )
    kcal_pivot = kcal_cal.pivot_table(
        index="year", columns="month_num", values="kcal", fill_value=0
    )
    month_names = {
        1: "Jan",
        2: "Feb",
        3: "Mar",
        4: "Apr",
        5: "May",
        6: "Jun",
        7: "Jul",
        8: "Aug",
        9: "Sep",
        10: "Oct",
        11: "Nov",
        12: "Dec",
    }
    kcal_pivot.columns = [month_names.get(c, c) for c in kcal_pivot.columns]

    fig_kcal = px.imshow(
        kcal_pivot,
        color_continuous_scale="YlOrRd",
        title="Total kcal: Year × Month",
        labels={"x": "Month", "y": "Year", "color": "kcal"},
        aspect="auto",
    )
    fig_kcal.update_layout(height=320)
    st.plotly_chart(fig_kcal)

# ── Tab 5: Speed & Pace ────────────────────────────────────────────────────────

with tab_speed:
    has_dist = dff["distance_km"] > 0
    dfd = dff[has_dist].copy()

    if dfd.empty:
        st.info("No sessions with distance data in current selection.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            fig_pace = px.histogram(
                dfd.dropna(subset=["pace_min_km"]).query("pace_min_km < 20"),
                x="pace_min_km",
                color="sport",
                color_discrete_map=SPORT_COLORS,
                nbins=40,
                opacity=0.75,
                barmode="overlay",
                title="Pace Distribution (min/km)",
                labels={"pace_min_km": "Pace (min/km)"},
            )
            fig_pace.update_layout(height=340)
            st.plotly_chart(fig_pace)

        with col2:
            fig_dist_box = px.box(
                dfd,
                x="sport",
                y="distance_km",
                color="sport",
                color_discrete_map=SPORT_COLORS,
                points="outliers",
                title="Session Distance Distribution",
                labels={"distance_km": "Distance (km)"},
            )
            fig_dist_box.update_layout(height=340, showlegend=False)
            st.plotly_chart(fig_dist_box)

        # Pace trend over time
        pace_trend = (
            dfd.dropna(subset=["pace_min_km"])
            .query("pace_min_km < 20")
            .sort_values("start")
            .set_index("start")
            .groupby("sport")["pace_min_km"]
            .rolling("90D", min_periods=5)
            .mean()
            .reset_index()
        )
        fig_pace_trend = px.line(
            pace_trend,
            x="start",
            y="pace_min_km",
            color="sport",
            color_discrete_map=SPORT_COLORS,
            title="Pace Trend (90-day rolling mean)",
            labels={"pace_min_km": "Pace (min/km)", "start": "Date"},
        )
        fig_pace_trend.update_layout(height=320, yaxis_autorange="reversed")
        st.plotly_chart(fig_pace_trend)

        # HR vs Pace scatter (aerobic efficiency proxy)
        fig_hr_pace = px.scatter(
            dfd.dropna(subset=["avg_hr", "pace_min_km"]).query("pace_min_km < 20"),
            x="pace_min_km",
            y="avg_hr",
            color="sport",
            color_discrete_map=SPORT_COLORS,
            opacity=0.5,
            size="distance_km",
            trendline="lowess",
            title="HR vs Pace  (size = distance — aerobic efficiency)",
            labels={"pace_min_km": "Pace (min/km)", "avg_hr": "Avg HR (bpm)"},
        )
        fig_hr_pace.update_layout(height=360)
        st.plotly_chart(fig_hr_pace)

# ── Tab 6: Correlations ────────────────────────────────────────────────────────

with tab_corr:
    num_cols = [
        "duration_min",
        "distance_km",
        "avg_hr",
        "max_hr",
        "kcal",
        "pace_min_km",
        "ascent_m",
        "z1",
        "z2",
        "z3",
        "z4",
        "z5",
    ]
    existing = [c for c in num_cols if c in dff.columns]

    corr_df = dff[existing].dropna(thresh=4).corr()

    fig_corr = px.imshow(
        corr_df,
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        title="Feature Correlation Matrix",
        text_auto=".2f",
        aspect="auto",
    )
    fig_corr.update_layout(height=520)
    st.plotly_chart(fig_corr)

    # Scatter matrix for key variables
    scatter_vars = [
        c
        for c in ["duration_min", "distance_km", "avg_hr", "pace_min_km"]
        if c in dff.columns
    ]
    fig_scatter = px.scatter_matrix(
        dff.dropna(subset=scatter_vars).sample(min(1, len(dff)), random_state=42),
        dimensions=scatter_vars,
        color="sport",
        color_discrete_map=SPORT_COLORS,
        opacity=0.5,
        title="Scatter Matrix (sampled ≤1000 sessions)",
    )
    fig_scatter.update_traces(diagonal_visible=False, marker_size=3)
    fig_scatter.update_layout(height=560)
    st.plotly_chart(fig_scatter)

# ── Tab 7: Session Deep-Dive ───────────────────────────────────────────────────

with tab_session:
    st.subheader("Per-session HR trace")

    # Pick sessions that have HR samples #TODO: change to pandas df
    files = read_feather("sessions.feather")
    sessions_with_hr = []
    for fp in files:
        try:
            with open(fp) as f:
                d = json.load(f)
        except Exception:
            continue
        for ex in d.get("exercises", []):
            if ex.get("samples", {}).get("heartRate"):
                start = d.get("startTime", "")[:10]
                sport = ex.get("sport", "?")
                sessions_with_hr.append((start, sport, fp))
                break

    if not sessions_with_hr:
        st.info("No sessions with HR samples found.")
    else:
        # Apply same sport filter
        sessions_with_hr = [
            (s, sp, fp) for s, sp, fp in sessions_with_hr if sp in sel_sports
        ]
        options = {f"{s}  {sp}": fp for s, sp, fp in sessions_with_hr[-200:]}

        sel_label = st.selectbox(
            "Select a session (most recent 200 with HR data)",
            list(options.keys()),
            index=len(options) - 1,
        )
        sel_fp = options[sel_label]

        with open(sel_fp) as f:
            raw = json.load(f)

        for ex in raw.get("exercises", []):
            hr_samp = ex.get("samples", {}).get("heartRate", [])
            spd_samp = ex.get("samples", {}).get("speed", [])

            if not hr_samp:
                continue

            hr_df = pd.DataFrame(hr_samp)
            hr_df["dt"] = pd.to_datetime(hr_df["dateTime"])
            hr_df["elapsed_min"] = (
                hr_df["dt"] - hr_df["dt"].iloc[0]
            ).dt.total_seconds() / 60

            fig_trace = make_subplots(specs=[[{"secondary_y": True}]])

            fig_trace.add_trace(
                go.Scatter(
                    x=hr_df["elapsed_min"],
                    y=hr_df["value"],
                    name="HR (bpm)",
                    line=dict(color="#E17055", width=1.5),
                    fill="tozeroy",
                    fillcolor="rgba(225,112,85,0.15)",
                ),
                secondary_y=False,
            )

            if spd_samp:
                spd_df = pd.DataFrame(spd_samp)
                spd_df["dt"] = pd.to_datetime(spd_df["dateTime"])
                spd_df["elapsed_min"] = (
                    spd_df["dt"] - hr_df["dt"].iloc[0]
                ).dt.total_seconds() / 60
                fig_trace.add_trace(
                    go.Scatter(
                        x=spd_df["elapsed_min"],
                        y=spd_df["value"],
                        name="Speed (km/h)",
                        line=dict(color="#636EFA", width=1.5),
                    ),
                    secondary_y=True,
                )

            # HR zone bands from this exercise
            zones = ex.get("zones", {}).get("heart_rate", [])
            zone_clrs = [
                "#74B9FF55",
                "#55EFC455",
                "#FDCB6E55",
                "#E1705555",
                "#D6303155",
            ]
            for z in zones:
                lo = z.get("lowerLimit", 0)
                hi = z.get("higherLimit", 999)
                zi = z.get("zoneIndex", 1) - 1
                fig_trace.add_hrect(
                    y0=lo,
                    y1=hi,
                    fillcolor=zone_clrs[zi % len(zone_clrs)],
                    line_width=0,
                    secondary_y=False,
                )

            fig_trace.update_layout(
                title=f"HR Trace — {sel_label}",
                xaxis_title="Elapsed (min)",
                height=400,
                legend=dict(x=0.01, y=0.99),
            )
            fig_trace.update_yaxes(title_text="HR (bpm)", secondary_y=False)
            fig_trace.update_yaxes(title_text="Speed (km/h)", secondary_y=True)
            st.plotly_chart(fig_trace)

        # Session metadata table
        meta_cols = [
            "start",
            "sport",
            "duration_min",
            "distance_km",
            "avg_hr",
            "max_hr",
            "kcal",
        ]
        existing_meta = [c for c in meta_cols if c in dff.columns]
        st.dataframe(
            dff[existing_meta]
            .sort_values("start", ascending=False)
            .head(50)
            .reset_index(drop=True),
            use_container_width=True,
        )
