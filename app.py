import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Production Performance Dashboard",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# COLOR PALETTE
# ============================================================

NAVY = "#17365D"
STEEL_BLUE = "#4472C4"
TEAL = "#2F9E9E"
ORANGE = "#ED7D31"
RED = "#C00000"
GREEN = "#70AD47"
PURPLE = "#8064A2"

LIGHT_BLUE = "#EAF1F8"
LIGHT_GREY = "#F5F7FA"
MID_GREY = "#6B7280"
DARK = "#1F2937"
WHITE = "#FFFFFF"
BORDER = "#D9E2EC"


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    f"""
    <style>

    .stApp {{
        background-color: #F4F6F9;
    }}

    .block-container {{
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }}

    /* HEADER */

    .dashboard-header {{
        background: linear-gradient(
            135deg,
            {NAVY} 0%,
            #234F7D 55%,
            {STEEL_BLUE} 100%
        );
        padding: 25px 32px;
        border-radius: 14px;
        margin-bottom: 22px;
        box-shadow: 0 4px 14px rgba(23, 54, 93, 0.15);
    }}

    .header-title {{
        color: white;
        font-size: 30px;
        font-weight: 700;
        margin: 0;
    }}

    .header-subtitle {{
        color: #DCE8F5;
        font-size: 14px;
        margin-top: 6px;
    }}

    .header-line {{
        height: 3px;
        width: 55px;
        background-color: white;
        border-radius: 4px;
        margin-top: 14px;
    }}

    /* FILTER AREA */

    .filter-panel {{
        background-color: white;
        padding: 18px 22px 10px 22px;
        border: 1px solid {BORDER};
        border-radius: 12px;
        margin-bottom: 22px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }}

    .filter-title {{
        color: {NAVY};
        font-size: 13px;
        font-weight: 700;
        margin-bottom: 5px;
        letter-spacing: 0.5px;
    }}

    /* SECTION TITLES */

    .section-title {{
        color: {NAVY};
        font-size: 20px;
        font-weight: 700;
        margin-top: 15px;
        margin-bottom: 5px;
    }}

    .section-subtitle {{
        color: {MID_GREY};
        font-size: 13px;
        margin-bottom: 15px;
    }}

    .chart-title {{
        color: {NAVY};
        font-size: 16px;
        font-weight: 700;
        margin-top: 5px;
        margin-bottom: 8px;
    }}

    /* KPI */

    .kpi-card {{
        background-color: white;
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 17px 18px;
        min-height: 110px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }}

    .kpi-label {{
        color: {MID_GREY};
        font-size: 12px;
        font-weight: 700;
        margin-bottom: 7px;
        text-transform: uppercase;
    }}

    .kpi-value {{
        color: {NAVY};
        font-size: 25px;
        font-weight: 750;
        line-height: 1.15;
    }}

    .kpi-unit {{
        color: {MID_GREY};
        font-size: 12px;
        margin-top: 5px;
    }}

    /* FACTORY BADGE */

    .factory-badge {{
        display: inline-block;
        background-color: #EAF1F8;
        color: {NAVY};
        border-radius: 20px;
        padding: 5px 13px;
        font-size: 12px;
        font-weight: 700;
        margin-top: 5px;
    }}

    /* FOOTER */

    .dashboard-footer {{
        text-align: center;
        color: #8A94A6;
        font-size: 11px;
        margin-top: 30px;
        padding-top: 12px;
        border-top: 1px solid {BORDER};
    }}

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# FILE LOCATIONS
# ============================================================

DATA_FOLDER = Path("data")
LOGO_PATH = Path("assets/company_logo.")

FACTORY_FILES = {
    "D2 Factory": DATA_FOLDER / "D2_Factory.xlsx",
    "B2 Factory": DATA_FOLDER / "B2_Factory.xlsx"
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_column_names(df):
    """
    Clean Excel column names.

    Removes:
    - leading spaces
    - trailing spaces
    - non-breaking spaces
    """

    df = df.copy()

    df.columns = (
        df.columns
        .astype(str)
        .str.replace("\u00A0", " ", regex=False)
        .str.strip()
    )

    return df


def safe_sum(df, column):

    if column not in df.columns:
        return 0

    return pd.to_numeric(
        df[column],
        errors="coerce"
    ).fillna(0).sum()


def format_number(value):

    return f"{value:,.1f}"


def find_column(df, possible_names):
    """
    Find a column while ignoring:
    - leading/trailing spaces
    - non-breaking spaces
    - capitalization
    """

    column_map = {}

    for column in df.columns:

        cleaned_name = (
            str(column)
            .replace("\u00A0", " ")
            .strip()
            .lower()
        )

        column_map[cleaned_name] = column

    for name in possible_names:

        search_name = (
            str(name)
            .replace("\u00A0", " ")
            .strip()
            .lower()
        )

        if search_name in column_map:

            return column_map[search_name]

    return None


def classify_machine(machine_name):

    name = str(machine_name).strip().lower()

    if "wire" in name or "drawing" in name:

        return "Wire Drawing"

    elif "nail" in name:

        return "Nail"

    elif "rod" in name:

        return "Rod"

    else:

        return "Other"


def create_machine_chart(data, category, title, chart_color):

    if data.empty:

        st.info(
            f"No {category.lower()} machine data "
            f"available for the selected month."
        )

        return

    if "Machine" not in data.columns:

        st.info("Machine column is not available.")

        return

    if "Machine Production (ton)" not in data.columns:

        st.info(
            "Machine Production (ton) column is not available."
        )

        return

    category_data = data[
        data["Machine Category"] == category
    ].copy()

    if category_data.empty:

        st.info(
            f"No {category.lower()} machine data "
            f"available for the selected month."
        )

        return

    category_data["Machine Production (ton)"] = pd.to_numeric(
        category_data["Machine Production (ton)"],
        errors="coerce"
    ).fillna(0)

    machine_summary = (
        category_data
        .groupby(
            "Machine",
            as_index=False
        )["Machine Production (ton)"]
        .sum()
        .sort_values(
            "Machine Production (ton)",
            ascending=False
        )
    )

    if machine_summary.empty:

        st.info(
            f"No production data available for {title}."
        )

        return

    fig = px.bar(
        machine_summary,
        x="Machine",
        y="Machine Production (ton)",
        text="Machine Production (ton)"
    )

    fig.update_traces(
        marker_color=chart_color,
        texttemplate="%{text:.1f}",
        textposition="outside"
    )

    fig.update_layout(
        height=360,
        margin=dict(
            l=20,
            r=20,
            t=30,
            b=20
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis_title="Machine",
        yaxis_title="Production (Ton)",
        showlegend=False
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def load_factory_data(factory_name):

    file_path = FACTORY_FILES[factory_name]

    production = pd.read_excel(
        file_path,
        sheet_name="Production_data"
    )

    downtime = pd.read_excel(
        file_path,
        sheet_name="Downtime_data"
    )

    size_production = pd.read_excel(
        file_path,
        sheet_name="Size_vise_Production"
    )

    machine_production = pd.read_excel(
        file_path,
        sheet_name="Machine_vise_production"
    )

    # Clean all column names
    production = clean_column_names(production)
    downtime = clean_column_names(downtime)
    size_production = clean_column_names(size_production)
    machine_production = clean_column_names(machine_production)

    # Convert dates
    for df in [
        production,
        downtime,
        size_production,
        machine_production
    ]:

        if "Date" in df.columns:

            df["Date"] = pd.to_datetime(
                df["Date"],
                errors="coerce"
            )

    return (
        production,
        downtime,
        size_production,
        machine_production
    )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="dashboard-header">'
    '<div class="header-title">'
    'Production Performance Dashboard'
    '</div>'
    '<div class="header-subtitle">'
    'EKALA NAIL PLANT | PRODUCTION ANALYSIS'
    '</div>'
    '<div class="header-line"></div>'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# FILTER PANEL
# ============================================================

st.markdown(
    '<div class="filter-panel">',
    unsafe_allow_html=True
)

col_factory, col_month, col_info = st.columns(
    [1.4, 1.4, 3]
)


# ============================================================
# FACTORY SELECTOR
# ============================================================

with col_factory:

    st.markdown(
        '<div class="filter-title">FACTORY</div>',
        unsafe_allow_html=True
    )

    selected_factory = st.selectbox(
        "Factory",
        [
            "D2 Factory",
            "B2 Factory"
        ],
        label_visibility="collapsed"
    )


# ============================================================
# LOAD SELECTED FACTORY
# ============================================================

try:

    (
        production,
        downtime,
        size_production,
        machine_production
    ) = load_factory_data(selected_factory)

except Exception as e:

    st.error(
        f"Could not load {selected_factory} data."
    )

    st.exception(e)

    st.stop()


# ============================================================
# CREATE MONTH FIELD
# ============================================================

if "Date" not in production.columns:

    st.error(
        "The Production_data sheet must contain a 'Date' column."
    )

    st.stop()


production["Month_Start"] = (
    production["Date"]
    .dt.to_period("M")
    .dt.to_timestamp()
)

available_months = sorted(
    production["Month_Start"]
    .dropna()
    .unique()
)

if len(available_months) == 0:

    st.error(
        "No valid dates were found in Production_data."
    )

    st.stop()


# ============================================================
# MONTH SELECTOR
# ============================================================

with col_month:

    st.markdown(
        '<div class="filter-title">REPORTING MONTH</div>',
        unsafe_allow_html=True
    )

    selected_month = st.selectbox(
        "Month",
        available_months,
        format_func=lambda x: pd.Timestamp(x).strftime(
            "%B %Y"
        ),
        label_visibility="collapsed"
    )


# ============================================================
# INFORMATION
# ============================================================

selected_month_display = pd.Timestamp(
    selected_month
).strftime("%B %Y")


with col_info:

    st.markdown(
        f"""
        <div style="
            padding-top:20px;
            color:{MID_GREY};
            font-size:13px;
        ">

        Selected:
        <strong style="color:{NAVY};">
        {selected_factory}
        </strong>

        &nbsp;&nbsp;|&nbsp;&nbsp;

        <strong style="color:{NAVY};">
        {selected_month_display}
        </strong>

        </div>
        """,
        unsafe_allow_html=True
    )


st.markdown(
    "</div>",
    unsafe_allow_html=True
)


# ============================================================
# FILTER PRODUCTION DATA
# ============================================================

production_filtered = production[
    production["Month_Start"] == selected_month
].copy()


# ============================================================
# FILTER DOWNTIME DATA
# ============================================================

downtime_filtered = downtime.copy()

if "Date" in downtime_filtered.columns:

    downtime_filtered["Month_Start"] = (
        downtime_filtered["Date"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    downtime_filtered = downtime_filtered[
        downtime_filtered["Month_Start"] == selected_month
    ].copy()


# ============================================================
# FILTER SIZE-WISE PRODUCTION
# ============================================================

size_filtered = size_production.copy()

if "Date" in size_filtered.columns:

    size_filtered["Month_Start"] = (
        size_filtered["Date"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    size_filtered = size_filtered[
        size_filtered["Month_Start"] == selected_month
    ].copy()


# ============================================================
# FILTER MACHINE PRODUCTION
# ============================================================

machine_filtered = machine_production.copy()

if "Date" in machine_filtered.columns:

    machine_filtered["Month_Start"] = (
        machine_filtered["Date"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    machine_filtered = machine_filtered[
        machine_filtered["Month_Start"] == selected_month
    ].copy()


# ============================================================
# MACHINE CLASSIFICATION
# ============================================================

if "Machine" in machine_filtered.columns:

    machine_filtered["Machine Category"] = (
        machine_filtered["Machine"]
        .apply(classify_machine)
    )
st.markdown("### Dashboard View")

view_mode = st.radio(
    "Choose view",
    ["Summary View", "Detailed View"],
    horizontal=True,
    index=1,
    key="dashboard_view"
)

# ============================================================
# SELECTED PERIOD BADGE
# ============================================================

month_display = pd.Timestamp(
    selected_month
).strftime("%B %Y")


st.markdown(
    f"""
    <span class="factory-badge">
        {selected_factory}
    </span>

    <span style="
        color:#6B7280;
        font-size:13px;
        margin-left:8px;
    ">
        {month_display}
    </span>
    """,
    unsafe_allow_html=True
)


# ============================================================
# KPI VALUES
# ============================================================

raw_material = safe_sum(
    production_filtered,
    "Raw material (Ton)"
)

wire_drawing = safe_sum(
    production_filtered,
    "Wire Drawing (Ton)"
)

nail_production = safe_sum(
    production_filtered,
    "Nail production(Ton)"
)

rod_production = safe_sum(
    production_filtered,
    "Rod Production (Ton)"
)

rejection = safe_sum(
    production_filtered,
    "Total Rejection (Ton)"
)

packaging_ton = safe_sum(
    production_filtered,
    "Packaging (Ton)"
)

packaging_bags = safe_sum(
    production_filtered,
    "Packaging(25kg bags)"
)


# ============================================================
# WORKING DAYS
# ============================================================

working_days = (
    production_filtered["Date"]
    .dt.date
    .nunique()
)


# ============================================================
# DAILY AVERAGE PRODUCTION
# ============================================================

daily_avg_nail = (
    nail_production / working_days
    if working_days > 0
    else 0
)

daily_avg_rod = (
    rod_production / working_days
    if working_days > 0
    else 0
)


# ============================================================
# COMPACT MANAGEMENT SUMMARY
# ============================================================

if view_mode == "Summary View":

    st.markdown("## Production Summary")
    st.caption(
        f"{selected_factory} | {selected_month_display}"
    )

    # KPI cards
    if selected_factory == "D2 Factory":
        k1, k2, k3, k4 = st.columns(4)
        summary_kpis = [
            (k1, "Nail Production", nail_production, "Ton"),
            (k2, "Rod Production", rod_production, "Ton"),
            (k3, "Total Rejection", rejection, "Ton"),
            (k4, "Working Days", working_days, "Days"),
        ]
    else:
        k1, k2, k3, k4 = st.columns(4)
        summary_kpis = [
            (k1, "Nail Production", nail_production, "Ton"),
            (k2, "Wire Drawing", wire_drawing, "Ton"),
            (k3, "Total Rejection", rejection, "Ton"),
            (k4, "Working Days", working_days, "Days"),
        ]

    for col, label, value, unit in summary_kpis:
        with col:
            st.metric(label, f"{value:,.1f} {unit}")

    # Create two columns for compact charts
    left, right = st.columns(2)

    # 1. Daily production trend
    with left:
        st.markdown("#### Daily Production Trend")

        if not production_filtered.empty:
            trend = (
                production_filtered.groupby("Date", as_index=False)
                .agg({
                    "Nail production(Ton)": "sum",
                    **(
                        {"Rod Production (Ton)": "sum"}
                        if selected_factory == "D2 Factory"
                        and "Rod Production (Ton)" in production_filtered.columns
                        else {}
                    )
                })
            )

            fig_trend = go.Figure()

            fig_trend.add_trace(go.Scatter(
                x=trend["Date"],
                y=trend["Nail production(Ton)"],
                name="Nail",
                mode="lines+markers",
                line=dict(color=STEEL_BLUE, width=2)
            ))

            if (
                selected_factory == "D2 Factory"
                and "Rod Production (Ton)" in trend.columns
            ):
                fig_trend.add_trace(go.Scatter(
                    x=trend["Date"],
                    y=trend["Rod Production (Ton)"],
                    name="Rod",
                    mode="lines+markers",
                    line=dict(color=ORANGE, width=2)
                ))

            fig_trend.update_layout(
                height=280,
                margin=dict(l=10, r=10, t=20, b=10),
                paper_bgcolor="white",
                plot_bgcolor="white",
                legend=dict(orientation="h", y=1.12),
                xaxis_title=None,
                yaxis_title="Ton"
            )
            st.plotly_chart(
                fig_trend,
                use_container_width=True,
                key="summary_trend"
            )
        else:
            st.info("No production data available.")

    # 2. Machine performance
    with right:
        st.markdown("#### Machine Performance")

        if (
            not machine_filtered.empty
            and "Machine" in machine_filtered.columns
            and "Machine Production (ton)" in machine_filtered.columns
        ):
            machine_summary = machine_filtered.copy()
            machine_summary["Machine Production (ton)"] = pd.to_numeric(
                machine_summary["Machine Production (ton)"],
                errors="coerce"
            ).fillna(0)

            machine_summary["Category"] = (
                machine_summary["Machine"].apply(classify_machine)
            )

            machine_summary = (
                machine_summary[
                    machine_summary["Category"].isin(
                        ["Wire Drawing", "Nail", "Rod"]
                        if selected_factory == "D2 Factory"
                        else ["Wire Drawing", "Nail"]
                    )
                ]
                .groupby("Category", as_index=False)
                ["Machine Production (ton)"].sum()
            )

            fig_machine_summary = px.bar(
                machine_summary,
                x="Category",
                y="Machine Production (ton)",
                color="Category",
                text_auto=".1f",
                color_discrete_map={
                    "Wire Drawing": STEEL_BLUE,
                    "Nail": TEAL,
                    "Rod": ORANGE
                }
            )
            fig_machine_summary.update_layout(
                height=280,
                margin=dict(l=10, r=10, t=20, b=10),
                showlegend=False,
                paper_bgcolor="white",
                plot_bgcolor="white",
                xaxis_title=None,
                yaxis_title="Ton"
            )
            st.plotly_chart(
                fig_machine_summary,
                use_container_width=True,
                key="summary_machine"
            )
        else:
            st.info("Machine production data is unavailable.")

    # 3. Top downtime reasons
    left, right = st.columns(2)

    with left:
        st.markdown("#### Top 10 Downtime Reasons")

        if (
            "Reason" in downtime_filtered.columns
            and "Downtime (hrs)" in downtime_filtered.columns
        ):
            dt = downtime_filtered.copy()
            dt["Downtime (hrs)"] = pd.to_numeric(
                dt["Downtime (hrs)"], errors="coerce"
            ).fillna(0)

            dt_summary = (
                dt.groupby("Reason", as_index=False)["Downtime (hrs)"]
                .sum()
                .nlargest(10, "Downtime (hrs)")
                .sort_values("Downtime (hrs)")
            )

            fig_dt = px.bar(
                dt_summary,
                x="Downtime (hrs)",
                y="Reason",
                orientation="h",
                text_auto=".1f"
            )
            fig_dt.update_traces(marker_color=ORANGE)
            fig_dt.update_layout(
                height=320,
                margin=dict(l=10, r=15, t=15, b=10),
                paper_bgcolor="white",
                plot_bgcolor="white",
                xaxis_title="Hours",
                yaxis_title=None
            )
            st.plotly_chart(
                fig_dt,
                use_container_width=True,
                key="summary_downtime"
            )
        else:
            st.info("Downtime data is unavailable.")

    # 4. Rejection analysis
    with right:
        st.markdown("#### Rejection Analysis")

        rejection_types = pd.DataFrame({
            "Type": ["Iron Dust", "Waste"],
            "Quantity": [
                safe_sum(production_filtered, "Iron Dust (Ton)"),
                safe_sum(production_filtered, "Waste(Ton)")
            ]
        })

        fig_rejection_summary = px.bar(
            rejection_types,
            x="Type",
            y="Quantity",
            text_auto=".1f",
            color="Type",
            color_discrete_map={
                "Iron Dust": STEEL_BLUE,
                "Waste": RED
            }
        )
        fig_rejection_summary.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=15, b=10),
            showlegend=False,
            paper_bgcolor="white",
            plot_bgcolor="white",
            xaxis_title=None,
            yaxis_title="Ton"
        )
        st.plotly_chart(
            fig_rejection_summary,
            use_container_width=True,
            key="summary_rejection"
        )

    # Downtime utilization indicators
    total_downtime_summary = safe_sum(
        production_filtered, "Total downtime (hours)"
    )
    shift_time_summary = safe_sum(
        production_filtered, "Machine shift time (hours)"
    )
    operating_time_summary = max(
        shift_time_summary - total_downtime_summary, 0
    )

    st.markdown("#### Downtime Overview")
    a, b, c = st.columns(3)
    a.metric("Shift Time", f"{shift_time_summary:,.1f} hrs")
    b.metric("Downtime", f"{total_downtime_summary:,.1f} hrs")
    c.metric("Operating Time", f"{operating_time_summary:,.1f} hrs")

    st.caption(
        "Use Detailed View for size-wise production, individual machine "
        "charts, and the full downtime gauge."
    )

    st.stop()

# ============================================================
# PRODUCTION SUMMARY
# ============================================================

st.markdown(
    '<div class="section-title">Production Summary</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="section-subtitle">'
    'Key production indicators for the '
f"{selected_factory} in {selected_month_display}"
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# MAIN KPI CARDS
# ============================================================

if selected_factory == "D2 Factory":

    k1, k2, k3, k4, k5 = st.columns(5)

    kpi_data = [
        (
            k1,
            "Raw Material",
            format_number(raw_material),
            "Ton"
        ),
        (
            k2,
            "Wire Drawing",
            format_number(wire_drawing),
            "Ton"
        ),
        (
            k3,
            "Nail Production",
            format_number(nail_production),
            "Ton"
        ),
        (
            k4,
            "Rod Production",
            format_number(rod_production),
            "Ton"
        ),
        (
            k5,
            "Total Rejection",
            format_number(rejection),
            "Ton"
        )
    ]

else:

    k1, k2, k3, k4 = st.columns(4)

    kpi_data = [
        (
            k1,
            "Raw Material",
            format_number(raw_material),
            "Ton"
        ),
        (
            k2,
            "Wire Drawing",
            format_number(wire_drawing),
            "Ton"
        ),
        (
            k3,
            "Nail Production",
            format_number(nail_production),
            "Ton"
        ),
        (
            k4,
            "Total Rejection",
            format_number(rejection),
            "Ton"
        )
    ]


for column, label, value, unit in kpi_data:

    with column:

        st.markdown(
            f'<div class="kpi-card">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div>'
            f'<div class="kpi-unit">{unit}</div>'
            f'</div>',
            unsafe_allow_html=True
        )


st.write("")


# ============================================================
# PACKAGING / WORKING DAYS
# ============================================================

p1, p2, p3 = st.columns(3)


with p1:

    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">Nail Package</div>'
        f'<div class="kpi-value">'
        f'{packaging_ton:,.1f}'
        f'</div>'
        f'<div class="kpi-unit">Ton</div>'
        f'</div>',
        unsafe_allow_html=True
    )


with p2:

    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">25 KG Bags</div>'
        f'<div class="kpi-value">'
        f'{packaging_bags:,.0f}'
        f'</div>'
        f'<div class="kpi-unit">Bags</div>'
        f'</div>',
        unsafe_allow_html=True
    )


with p3:

    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">Working Days</div>'
        f'<div class="kpi-value">'
        f'{working_days}'
        f'</div>'
        f'<div class="kpi-unit">Days</div>'
        f'</div>',
        unsafe_allow_html=True
    )


# ============================================================
# DAILY PRODUCTION SUMMARY
# ============================================================

st.markdown(
    '<div class="section-title">Daily Production Summary</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="section-subtitle">'
    'Average production per working day for the '
f"{selected_factory} in {selected_month_display}"
    '</div>',
    unsafe_allow_html=True
)


if selected_factory == "D2 Factory":

    d1, d2 = st.columns(2)

else:

    d1, d2 = st.columns(2)


with d1:

    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">'
        f'Daily Avg. Nail Production'
        f'</div>'
        f'<div class="kpi-value">'
        f'{daily_avg_nail:,.1f}'
        f'</div>'
        f'<div class="kpi-unit">'
        f'Ton / Day'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )


if selected_factory == "D2 Factory":

    with d2:

        st.markdown(
            f'<div class="kpi-card">'
            f'<div class="kpi-label">'
            f'Daily Avg. Rod Production'
            f'</div>'
            f'<div class="kpi-value">'
            f'{daily_avg_rod:,.1f}'
            f'</div>'
            f'<div class="kpi-unit">'
            f'Ton / Day'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )


# ============================================================
# PRODUCTION TREND
# ============================================================

st.markdown(
    '<div class="section-title">Production Trend</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="section-subtitle">'
    'Daily production performance of '
     f"{selected_factory} in {selected_month_display}"
'</div>',
    unsafe_allow_html=True
)

if not production_filtered.empty:

    fig = go.Figure()

    # --------------------------------------------------------
    # NAIL PRODUCTION
    # --------------------------------------------------------

    if "Nail production(Ton)" in production_filtered.columns:

        daily_nail = (
            production_filtered
            .groupby(
                "Date",
                as_index=False
            )["Nail production(Ton)"]
            .sum()
        )

        fig.add_trace(
            go.Scatter(
                x=daily_nail["Date"],
                y=daily_nail["Nail production(Ton)"],
                mode="lines+markers",
                name="Nail Production",
                line=dict(
                    color=STEEL_BLUE,
                    width=3
                ),
                marker=dict(
                    size=6
                )
            )
        )

    # --------------------------------------------------------
    # ROD PRODUCTION - D2 ONLY
    # --------------------------------------------------------

    if selected_factory == "D2 Factory":

        if "Rod Production (Ton)" in production_filtered.columns:

            daily_rod = (
                production_filtered
                .groupby(
                    "Date",
                    as_index=False
                )["Rod Production (Ton)"]
                .sum()
            )

            fig.add_trace(
                go.Scatter(
                    x=daily_rod["Date"],
                    y=daily_rod["Rod Production (Ton)"],
                    mode="lines+markers",
                    name="Rod Production",
                    line=dict(
                        color=ORANGE,
                        width=3
                    ),
                    marker=dict(
                        size=6
                    )
                )
            )

    fig.update_layout(
        height=380,
        margin=dict(
            l=20,
            r=20,
            t=30,
            b=20
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis_title="Date",
        yaxis_title="Production (Ton)"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

else:

    st.info(
        "No production data available for the selected month."
    )


# ============================================================
# SIZE-WISE PRODUCTION
# ============================================================

st.markdown(
    '<div class="section-title">Size-Wise Production</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="section-subtitle">'
    'Production by category for the '
f"{selected_factory} in {selected_month_display}"
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# D2 FACTORY
# NAIL + ROD
# ============================================================

if selected_factory == "D2 Factory":

    size_col1, size_col2 = st.columns(2)

    # ========================================================
    # NAIL PRODUCTION BY CATEGORY
    # ========================================================

    with size_col1:

        st.markdown(
            '<div class="chart-title">'
            'Nail Production by Category'
            '</div>',
            unsafe_allow_html=True
        )

        nail_category = find_column(
            size_filtered,
            [
                "Nail Catogery",
                "Nail Category"
            ]
        )

        nail_production_column = find_column(
            size_filtered,
            [
                "Nail_Production",
                "Nail Production"
            ]
        )

        if nail_category and nail_production_column:

            nail_data = size_filtered[
                [
                    nail_category,
                    nail_production_column
                ]
            ].copy()

            nail_data[nail_category] = (
                nail_data[nail_category]
                .astype(str)
                .str.strip()
            )

            nail_data[nail_production_column] = pd.to_numeric(
                nail_data[nail_production_column],
                errors="coerce"
            ).fillna(0)

            nail_data = nail_data[
                ~nail_data[nail_category]
                .str.lower()
                .isin(
                    [
                        "",
                        "nan",
                        "none"
                    ]
                )
            ]

            nail_summary = (
                nail_data
                .groupby(
                    nail_category,
                    as_index=False
                )[nail_production_column]
                .sum()
                .sort_values(
                    nail_production_column,
                    ascending=False
                )
            )

            if not nail_summary.empty:

                fig_nail = px.bar(
                    nail_summary,
                    x=nail_category,
                    y=nail_production_column,
                    text=nail_production_column
                )

                fig_nail.update_traces(
                    marker_color=STEEL_BLUE,
                    texttemplate="%{text:.2f}",
                    textposition="outside"
                )

                fig_nail.update_layout(
                    height=430,
                    margin=dict(
                        l=20,
                        r=20,
                        t=30,
                        b=20
                    ),
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    xaxis_title="Nail Category",
                    yaxis_title="Production (Ton)",
                    showlegend=False
                )

                st.plotly_chart(
                    fig_nail,
                    use_container_width=True
                )

            else:

                st.info(
                    "No nail production values "
                    "for the selected month."
                )

        else:

            st.info(
                "Nail category data is not available."
            )


    # ========================================================
    # ROD PRODUCTION BY CATEGORY
    # ========================================================

    with size_col2:

        st.markdown(
            '<div class="chart-title">'
            'Rod Production by Category'
            '</div>',
            unsafe_allow_html=True
        )

        rod_category = find_column(
            size_filtered,
            [
                "Rod Catogery",
                "Rod Category"
            ]
        )

        rod_production_column = find_column(
            size_filtered,
            [
                "Rod_Production",
                "Rod Production"
            ]
        )

        if rod_category and rod_production_column:

            rod_data = size_filtered[
                [
                    rod_category,
                    rod_production_column
                ]
            ].copy()

            rod_data[rod_category] = (
                rod_data[rod_category]
                .astype(str)
                .str.strip()
            )

            rod_data[rod_production_column] = pd.to_numeric(
                rod_data[rod_production_column],
                errors="coerce"
            ).fillna(0)

            rod_data = rod_data[
                ~rod_data[rod_category]
                .str.lower()
                .isin(
                    [
                        "",
                        "nan",
                        "none"
                    ]
                )
            ]

            rod_summary = (
                rod_data
                .groupby(
                    rod_category,
                    as_index=False
                )[rod_production_column]
                .sum()
                .sort_values(
                    rod_production_column,
                    ascending=False
                )
            )

            if not rod_summary.empty:

                fig_rod = px.bar(
                    rod_summary,
                    x=rod_category,
                    y=rod_production_column,
                    text=rod_production_column
                )

                fig_rod.update_traces(
                    marker_color=TEAL,
                    texttemplate="%{text:.2f}",
                    textposition="outside"
                )

                fig_rod.update_layout(
                    height=430,
                    margin=dict(
                        l=20,
                        r=20,
                        t=30,
                        b=20
                    ),
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    xaxis_title="Rod Category",
                    yaxis_title="Production (Ton)",
                    showlegend=False
                )

                st.plotly_chart(
                    fig_rod,
                    use_container_width=True
                )

            else:

                st.info(
                    "No rod production values "
                    "for the selected month."
                )

        else:

            st.info(
                "Rod category data is not available."
            )


# ============================================================
# B2 FACTORY
# NAIL ONLY
# ============================================================

else:

    st.markdown(
        '<div class="chart-title">'
        'Nail Production by Category'
        '</div>',
        unsafe_allow_html=True
    )

    nail_category = find_column(
        size_filtered,
        [
            "Nail Catogery",
            "Nail Category"
        ]
    )

    nail_production_column = find_column(
        size_filtered,
        [
            "Nail_Production",
            "Nail Production"
        ]
    )

    if nail_category and nail_production_column:

        nail_data = size_filtered[
            [
                nail_category,
                nail_production_column
            ]
        ].copy()

        nail_data[nail_category] = (
            nail_data[nail_category]
            .astype(str)
            .str.strip()
        )

        nail_data[nail_production_column] = pd.to_numeric(
            nail_data[nail_production_column],
            errors="coerce"
        ).fillna(0)

        nail_data = nail_data[
            ~nail_data[nail_category]
            .str.lower()
            .isin(
                [
                    "",
                    "nan",
                    "none"
                ]
            )
        ]

        nail_summary = (
            nail_data
            .groupby(
                nail_category,
                as_index=False
            )[nail_production_column]
            .sum()
            .sort_values(
                nail_production_column,
                ascending=False
            )
        )

        if not nail_summary.empty:

            fig_nail = px.bar(
                nail_summary,
                x=nail_category,
                y=nail_production_column,
                text=nail_production_column
            )

            fig_nail.update_traces(
                marker_color=STEEL_BLUE,
                texttemplate="%{text:.2f}",
                textposition="outside"
            )

            fig_nail.update_layout(
                height=430,
                margin=dict(
                    l=20,
                    r=20,
                    t=30,
                    b=20
                ),
                plot_bgcolor="white",
                paper_bgcolor="white",
                xaxis_title="Nail Category",
                yaxis_title="Production (Ton)",
                showlegend=False
            )

            st.plotly_chart(
                fig_nail,
                use_container_width=True
            )

        else:

            st.info(
                "No nail production values "
                "for the selected month."
            )

    else:

        st.info(
            "Nail category data is not available."
        )


# ============================================================
# MACHINE PERFORMANCE
# ============================================================

st.markdown(
    '<div class="section-title">Machine Performance</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="section-subtitle">'
    'Machine-wise production performance for '
f"{selected_factory} in {selected_month_display}"
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# WIRE DRAWING MACHINES
# ============================================================

st.markdown(
    f'<div class="chart-title">'
    f'Wire Drawing Machines'
    f'</div>',
    unsafe_allow_html=True
)

create_machine_chart(
    machine_filtered,
    "Wire Drawing",
    "Wire Drawing Machine Production",
    STEEL_BLUE
)


# ============================================================
# NAIL MACHINES
# ============================================================

st.markdown(
    f'<div class="chart-title">'
    f'Nail Machines'
    f'</div>',
    unsafe_allow_html=True
)

create_machine_chart(
    machine_filtered,
    "Nail",
    "Nail Machine Production",
    TEAL
)


# ============================================================
# ROD MACHINES - D2 ONLY
# ============================================================

if selected_factory == "D2 Factory":

    st.markdown(
        f'<div class="chart-title">'
        f'Rod Machines'
        f'</div>',
        unsafe_allow_html=True
    )

    create_machine_chart(
        machine_filtered,
        "Rod",
        "Rod Machine Production",
        ORANGE
    )


# ============================================================
# DOWNTIME ANALYSIS - TOP 10
# ============================================================

st.markdown(
    '<div class="section-title">Downtime Analysis</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="section-subtitle">'
    'Top 10 downtime reasons for '
f"{selected_factory} in {selected_month_display}"
    '</div>',
    unsafe_allow_html=True
)


if (
    "Reason" in downtime_filtered.columns
    and
    "Downtime (hrs)" in downtime_filtered.columns
):

    downtime_chart_data = downtime_filtered.copy()

    downtime_chart_data["Downtime (hrs)"] = pd.to_numeric(
        downtime_chart_data["Downtime (hrs)"],
        errors="coerce"
    ).fillna(0)

    downtime_chart_data["Reason"] = (
        downtime_chart_data["Reason"]
        .astype(str)
        .str.strip()
    )

    downtime_summary = (
        downtime_chart_data
        .groupby(
            "Reason",
            as_index=False
        )["Downtime (hrs)"]
        .sum()
        .sort_values(
            "Downtime (hrs)",
            ascending=False
        )
        .head(10)
    )

    if not downtime_summary.empty:

        fig = px.bar(
            downtime_summary,
            x="Downtime (hrs)",
            y="Reason",
            orientation="h",
            text_auto=".1f"
        )

        fig.update_traces(
            marker_color=ORANGE,
            textposition="outside"
        )

        fig.update_layout(
            height=420,
            margin=dict(
                l=20,
                r=60,
                t=20,
                b=20
            ),
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis_title="Downtime (Hours)",
            yaxis_title="Downtime Reason",
            yaxis=dict(
                categoryorder="total ascending"
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    else:

        st.info(
            "No downtime data available for the selected period."
        )

else:

    st.info(
        "Downtime data is not available in the selected factory data."
    )


# ============================================================
# DOWNTIME VS SHIFT TIME GAUGE
# ============================================================

st.markdown(
    '<div class="section-title">Downtime Utilization</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="section-subtitle">'
    'Total downtime compared with total available machine shift time |'
f"{ selected_factory} | {selected_month_display}"
    '</div>',
    unsafe_allow_html=True
)


total_downtime = safe_sum(
    production_filtered,
    "Total downtime (hours)"
)

total_shift_time = safe_sum(
    production_filtered,
    "Machine shift time (hours)"
)


if total_shift_time > 0:

    downtime_percentage = (
        total_downtime / total_shift_time
    ) * 100

    gauge_value = min(
        max(downtime_percentage, 0),
        100
    )

    fig_gauge = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=gauge_value,
            number={
                "suffix": "%",
                "font": {
                    "size": 32
                }
            },
            title={
                "text": "Downtime % of Shift Time"
            },
            gauge={
                "axis": {
                    "range": [0, 100],
                    "ticksuffix": "%"
                },
                "bar": {
                    "color": ORANGE
                },
                "bgcolor": LIGHT_GREY,
                "borderwidth": 1,
                "bordercolor": BORDER,
                "steps": [
                    {
                        "range": [0, 10],
                        "color": "#E2F0D9"
                    },
                    {
                        "range": [10, 20],
                        "color": "#FFF2CC"
                    },
                    {
                        "range": [20, 100],
                        "color": "#FCE4D6"
                    }
                ],
                "threshold": {
                    "line": {
                        "color": RED,
                        "width": 4
                    },
                    "thickness": 0.75,
                    "value": 20
                }
            }
        )
    )

    fig_gauge.update_layout(
        height=350,
        margin=dict(
            l=30,
            r=30,
            t=60,
            b=20
        ),
        paper_bgcolor="white"
    )

    st.plotly_chart(
        fig_gauge,
        use_container_width=True
    )


    # --------------------------------------------------------
    # GAUGE SUPPORTING VALUES
    # --------------------------------------------------------

    gauge_col1, gauge_col2, gauge_col3 = st.columns(3)


    with gauge_col1:

        st.metric(
            "Total Shift Time",
            f"{total_shift_time:,.1f} hrs"
        )


    with gauge_col2:

        st.metric(
            "Total Downtime",
            f"{total_downtime:,.1f} hrs"
        )


    with gauge_col3:

        operating_time = max(
            total_shift_time - total_downtime,
            0
        )

        st.metric(
            "Operating Time",
            f"{operating_time:,.1f} hrs"
        )


else:

    st.info(
        "Shift time data is not available "
        "for the selected period."
    )


# ============================================================
# REJECTION ANALYSIS
# ============================================================

st.markdown(
    '<div class="section-title">Rejection Analysis</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="section-subtitle">'
    'Production rejection during'
f" {selected_month_display} for {selected_factory}"
    '</div>',
    unsafe_allow_html=True
)


if not production_filtered.empty:

    rejection_left, rejection_right = st.columns(2)


    # ========================================================
    # LEFT - REJECTION TYPE
    # ========================================================

    with rejection_left:

        rejection_data = []

        if "Iron Dust (Ton)" in production_filtered.columns:

            rejection_data.append(
                {
                    "Type": "Iron Dust",
                    "Quantity": safe_sum(
                        production_filtered,
                        "Iron Dust (Ton)"
                    )
                }
            )


        if "Waste(Ton)" in production_filtered.columns:

            rejection_data.append(
                {
                    "Type": "Waste",
                    "Quantity": safe_sum(
                        production_filtered,
                        "Waste(Ton)"
                    )
                }
            )


        if len(rejection_data) > 0:

            rejection_df = pd.DataFrame(
                rejection_data
            )

            fig_rejection = px.bar(
                rejection_df,
                x="Type",
                y="Quantity",
                text_auto=".1f"
            )

            fig_rejection.update_traces(
                marker_color=RED
            )

            fig_rejection.update_layout(
                height=330,
                margin=dict(
                    l=20,
                    r=20,
                    t=20,
                    b=20
                ),
                plot_bgcolor="white",
                paper_bgcolor="white",
                xaxis_title="Rejection Type",
                yaxis_title="Quantity (Ton)"
            )

            st.plotly_chart(
                fig_rejection,
                use_container_width=True
            )

        else:

            st.info(
                "Rejection data is not available."
            )


    # ========================================================
    # RIGHT - PRODUCTION VS REJECTION
    # ========================================================

    
with rejection_right:

    # Total nail production for both factories
    total_nail_production = safe_sum(
        production_filtered,
        "Nail production(Ton)"
    )

    # Total rejection
    total_rejection = safe_sum(
        production_filtered,
        "Total Rejection (Ton)"
    )

    # Pie chart data: Nail Production vs Rejection
    pie_df = pd.DataFrame(
        {
            "Type": [
                "Total Nail Production",
                "Total Rejection"
            ],
            "Quantity": [
                total_nail_production,
                total_rejection
            ]
        }
    )

    fig_pie = px.pie(
        pie_df,
        names="Type",
        values="Quantity",
        hole=0.35
    )

    fig_pie.update_traces(
        marker=dict(
            colors=[
                STEEL_BLUE,
                RED
            ]
        ),
        textinfo="label+percent",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Quantity: %{value:.1f} Ton<br>"
            "Percentage: %{percent}"
            "<extra></extra>"
        )
    )

    fig_pie.update_layout(
        height=350,
        margin=dict(
            l=20,
            r=20,
            t=30,
            b=20
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5
        )
    )

    st.plotly_chart(
        fig_pie,
        use_container_width=True
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div class="dashboard-footer">
        Production Performance Dashboard
        &nbsp;•&nbsp;
        Nail & Rod Production
    </div>
    """,
    unsafe_allow_html=True
)