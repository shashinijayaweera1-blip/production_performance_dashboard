import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import html




# ============================================================
# MONTHLY MANAGEMENT REPORT PDF EXPORT
# ============================================================
def build_dashboard_pdf(factory_name, month_display, production_df,
                        downtime_df, size_df, machine_df):
    """Export the selected dashboard as a clean, chart-led monthly PDF."""
    import io
    import math
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Wedge
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle, Flowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    NAVY = "#17365D"
    BLUE = "#4472C4"
    TEAL = "#2F9E9E"
    ORANGE = "#ED7D31"
    RED = "#C00000"
    GREEN = "#70AD47"
    PURPLE = "#8064A2"

    def total(frame, col):
        if frame is None or frame.empty or col not in frame.columns:
            return 0.0
        return float(pd.to_numeric(frame[col], errors="coerce").fillna(0).sum())

    def find_col(frame, candidates):
        for name in candidates:
            if name in frame.columns:
                return name
        return None

    def classify(name):
        try:
            return classify_machine(name)
        except Exception:
            value = str(name).lower()
            if "wire" in value or "drawing" in value:
                return "Wire Drawing"
            if "rod" in value:
                return "Rod"
            if "nail" in value:
                return "Nail"
            return "Other"

    charts = []
    chart_group = "production"
    def save_chart(fig):
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=190, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        buf.seek(0)
        charts.append((buf, chart_group))

    def style_axes(ax, horizontal=False):
        ax.grid(axis="x" if horizontal else "y", linestyle="--", alpha=.22)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)

    def bar_chart(labels, values, title, ylabel, color=BLUE, horizontal=False,
                  decimals=1, rotate=0):
        if not labels:
            return
        fig, ax = plt.subplots(figsize=(11.8, 5.1))
        if horizontal:
            bars = ax.barh(labels, values, color=color, height=.62)
            ax.bar_label(bars, fmt=f"%.{decimals}f", padding=4, fontsize=11, color=NAVY, weight="bold")
            ax.invert_yaxis()
            ax.set_xlabel(ylabel)
        else:
            bars = ax.bar(labels, values, color=color, width=.62)
            ax.bar_label(bars, fmt=f"%.{decimals}f", padding=4, fontsize=11, color=NAVY, weight="bold")
            ax.set_ylabel(ylabel)
            if rotate:
                ax.tick_params(axis="x", rotation=rotate)
        ax.set_title(title, fontsize=15, color=NAVY, weight="bold", pad=15)
        style_axes(ax, horizontal)
        fig.tight_layout()
        save_chart(fig)

    # Production trend — shown directly below the KPI cards on page one.
    chart_group = "trend"
    if production_df is not None and not production_df.empty and "Date" in production_df.columns:
        cols = [c for c in ["Nail production(Ton)", "Rod Production (Ton)"] if c in production_df.columns]
        if factory_name != "D2 Factory":
            cols = [c for c in cols if c != "Rod Production (Ton)"]
        if cols:
            d = production_df.copy()
            d["Date"] = pd.to_datetime(d["Date"], errors="coerce")
            for c in cols:
                d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0)
            d = d.dropna(subset=["Date"]).groupby("Date", as_index=False)[cols].sum().sort_values("Date")
            if not d.empty:
                fig, ax = plt.subplots(figsize=(11.8, 5.1))
                if "Nail production(Ton)" in d:
                    y = d["Nail production(Ton)"].tolist()
                    ax.plot(d["Date"], y, marker="o", linewidth=2.5, color=BLUE, label="Nail Production")
                    for i, (x, v) in enumerate(zip(d["Date"], y)):
                        # Alternate label positions and use a light background so
                        # neighbouring values remain readable when the line is close.
                        offset = 15 if i % 2 == 0 else 25
                        ax.annotate(
                            f"{v:.1f}", (x, v), xytext=(0, offset),
                            textcoords="offset points", ha="center", va="bottom",
                            fontsize=12, fontweight="bold", color=NAVY,
                            bbox={"boxstyle": "round,pad=0.18", "fc": "white", "ec": "none", "alpha": .88}
                        )
                if "Rod Production (Ton)" in d:
                    rod_values = d["Rod Production (Ton)"].tolist()
                    ax.plot(d["Date"], rod_values, marker="o", linewidth=2.5, color=ORANGE, label="Rod Production")
                    for i, (x, v) in enumerate(zip(d["Date"], rod_values)):
                        offset = -19 if i % 2 == 0 else -29
                        ax.annotate(
                            f"{v:.1f}", (x, v), xytext=(0, offset),
                            textcoords="offset points", ha="center", va="top",
                            fontsize=12, fontweight="bold", color=ORANGE,
                            bbox={"boxstyle": "round,pad=0.18", "fc": "white", "ec": "none", "alpha": .88}
                        )
                ax.set_title("Production Trend", fontsize=15, color=NAVY, weight="bold", pad=15)
                ax.set_xlabel("Date"); ax.set_ylabel("Production (Ton)")
                ax.legend(frameon=False, ncol=2)
                ax.tick_params(axis="x", rotation=35)
                style_axes(ax)
                fig.tight_layout()
                save_chart(fig)

    chart_group = "production"
    # Size-wise production charts, matching the dashboard categories.
    if size_df is not None and not size_df.empty:
        nc = find_col(size_df, ["Nail Catogery", "Nail Category"])
        nq = find_col(size_df, ["Nail_Production", "Nail Production"])
        if nc and nq:
            x = size_df[[nc, nq]].copy(); x[nq] = pd.to_numeric(x[nq], errors="coerce").fillna(0)
            x[nc] = x[nc].fillna("").astype(str).str.strip(); x = x[x[nc] != ""]
            s = x.groupby(nc, as_index=False)[nq].sum().sort_values(nq, ascending=False)
            bar_chart(s[nc].tolist(), s[nq].tolist(), "Nail Production by Category", "Production (Ton)", BLUE, decimals=2, rotate=30)
        if factory_name == "D2 Factory":
            rc = find_col(size_df, ["Rod Catogery", "Rod Category"])
            rq = find_col(size_df, ["Rod_Production", "Rod Production"])
            if rc and rq:
                x = size_df[[rc, rq]].copy(); x[rq] = pd.to_numeric(x[rq], errors="coerce").fillna(0)
                x[rc] = x[rc].fillna("").astype(str).str.strip(); x = x[x[rc] != ""]
                s = x.groupby(rc, as_index=False)[rq].sum().sort_values(rq, ascending=False)
                bar_chart(s[rc].tolist(), s[rq].tolist(), "Rod Production by Category", "Production (Ton)", TEAL, decimals=2, rotate=30)

    # Machine-wise production — individual charts for each machine group.
    if machine_df is not None and not machine_df.empty and "Machine" in machine_df.columns and "Machine Production (ton)" in machine_df.columns:
        x = machine_df.copy(); x["Machine Production (ton)"] = pd.to_numeric(x["Machine Production (ton)"], errors="coerce").fillna(0)
        x["Machine"] = x["Machine"].fillna("").astype(str).str.strip(); x = x[x["Machine"] != ""]
        x["Machine Category"] = x["Machine"].apply(classify)
        groups = [("Wire Drawing", "Wire Drawing Machine Production", BLUE), ("Nail", "Nail Machine Production", TEAL)]
        if factory_name == "D2 Factory": groups.append(("Rod", "Rod Machine Production", ORANGE))
        for cat, title, color in groups:
            s = x[x["Machine Category"] == cat].groupby("Machine", as_index=False)["Machine Production (ton)"].sum().sort_values("Machine Production (ton)", ascending=False)
            bar_chart(s["Machine"].tolist(), s["Machine Production (ton)"].tolist(), title, "Production (Ton)", color, horizontal=True, decimals=1)

    # Daily downtime line chart — source is Production_data for each date.
    chart_group = "daily_downtime"
    if production_df is not None and not production_df.empty and "Date" in production_df.columns and "Total downtime (hours)" in production_df.columns:
        daily = production_df[["Date", "Total downtime (hours)"]].copy()
        daily["Date"] = pd.to_datetime(daily["Date"], errors="coerce")
        daily["Total downtime (hours)"] = pd.to_numeric(daily["Total downtime (hours)"], errors="coerce").fillna(0)
        daily = daily.dropna(subset=["Date"]).groupby("Date", as_index=False)["Total downtime (hours)"].sum().sort_values("Date")
        if not daily.empty:
            fig, ax = plt.subplots(figsize=(11.8, 5.1))
            values = daily["Total downtime (hours)"].tolist()
            ax.plot(daily["Date"], values, marker="o", markersize=7, linewidth=2.8, color=ORANGE)
            for i, (x, value) in enumerate(zip(daily["Date"], values)):
                offset = 15 if i % 2 == 0 else 25
                ax.annotate(
                    f"{value:.1f}", (x, value), xytext=(0, offset),
                    textcoords="offset points", ha="center", va="bottom",
                    fontsize=12, fontweight="bold", color=NAVY,
                    bbox={"boxstyle": "round,pad=0.18", "fc": "white", "ec": "none", "alpha": .9}
                )
            ax.set_title("Daily Downtime", fontsize=16, color=NAVY, weight="bold", pad=15)
            ax.set_xlabel("Date"); ax.set_ylabel("Downtime (Hours)")
            ax.tick_params(axis="x", rotation=35, labelsize=10)
            style_axes(ax)
            fig.tight_layout(); save_chart(fig)

    # Downtime by reason — grouped with utilization and shift-time indicators.
    chart_group = "downtime_summary"
    if downtime_df is not None and not downtime_df.empty and "Reason" in downtime_df.columns and "Downtime (hrs)" in downtime_df.columns:
        x = downtime_df[["Reason", "Downtime (hrs)"]].copy()
        x["Reason"] = x["Reason"].fillna("Unspecified").astype(str).str.strip()
        x["Downtime (hrs)"] = pd.to_numeric(x["Downtime (hrs)"], errors="coerce").fillna(0)
        s = x.groupby("Reason", as_index=False)["Downtime (hrs)"].sum().sort_values("Downtime (hrs)", ascending=False).head(10).sort_values("Downtime (hrs)")
        bar_chart(s["Reason"].tolist(), s["Downtime (hrs)"].tolist(), "Top 10 Downtime Reasons", "Downtime (Hours)", ORANGE, horizontal=True, decimals=1)

    # Downtime utilization gauge and its three key values.
    shift = total(production_df, "Machine shift time (hours)")
    downtime = total(production_df, "Total downtime (hours)")
    operating = max(shift - downtime, 0)
    if shift > 0:
        pct = min(max(downtime / shift * 100, 0), 100)
        fig, ax = plt.subplots(figsize=(11.8, 4.7))
        # Match the dashboard Plotly gauge: 0–100 scale, three colored zones,
        # orange value bar and a red threshold marker at 20%.
        gauge_zones = [(0, 10, "#E2F0D9"), (10, 20, "#FFF2CC"), (20, 100, "#FCE4D6")]
        for lower, upper, zone_color in gauge_zones:
            ax.add_patch(Wedge((0, 0), 1, 180 - upper * 1.8, 180 - lower * 1.8, width=.28, facecolor=zone_color, edgecolor="white", linewidth=1.5))
        if pct > 0:
            ax.add_patch(Wedge((0, 0), 1, 180 - pct * 1.8, 180, width=.28, facecolor=ORANGE, edgecolor="white", linewidth=.8))
        # Percentage scale labels make the gauge readable in the printed report.
        for tick in (0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100):
            angle = math.radians(180 - tick * 1.8)
            radius = 1.13
            tx, ty = radius * math.cos(angle), radius * math.sin(angle)
            ax.text(tx, ty, f"{tick}%", ha="center", va="center", fontsize=8.5,
                    color=RED if tick == 20 else NAVY,
                    fontweight="bold" if tick == 20 else "normal")
        threshold_angle = math.radians(180 - 20 * 1.8)
        ax.plot([.68 * math.cos(threshold_angle), 1.04 * math.cos(threshold_angle)], [.68 * math.sin(threshold_angle), 1.04 * math.sin(threshold_angle)], color=RED, linewidth=3.5, solid_capstyle="round")
        ax.text(0, .12, f"{pct:.1f}%", ha="center", va="center", fontsize=32, color=NAVY, weight="bold")
        ax.text(0, -.13, "Downtime % of Shift Time", ha="center", va="center", fontsize=12, color=NAVY)
        ax.set_title("Downtime Utilization", fontsize=16, color=NAVY, weight="bold", pad=12)
        ax.set_xlim(-1.32, 1.32); ax.set_ylim(-.30, 1.28); ax.set_aspect("equal"); ax.axis("off")
        fig.tight_layout(); save_chart(fig)
        # supporting values are presented as KPI cards, not as a data table
        fig, ax = plt.subplots(figsize=(11.8, 2.1)); ax.axis("off")
        items = [("Total Shift Time", shift, BLUE), ("Total Downtime", downtime, ORANGE), ("Operating Time", operating, GREEN)]
        for i, (label, value, color) in enumerate(items):
            left = .03 + i * .33
            ax.add_patch(plt.Rectangle((left, .15), .29, .7, facecolor="#F3F6FA", edgecolor="#D6DCE5", linewidth=1.2, transform=ax.transAxes))
            ax.add_patch(plt.Rectangle((left, .15), .012, .7, facecolor=color, edgecolor=color, transform=ax.transAxes))
            ax.text(left + .145, .62, label, ha="center", va="center", fontsize=10, color=NAVY, transform=ax.transAxes, weight="bold")
            ax.text(left + .145, .36, f"{value:,.1f} hrs", ha="center", va="center", fontsize=15, color="#1F2937", transform=ax.transAxes)
        fig.tight_layout(); save_chart(fig)

    chart_group = "rejection"
    # Rejection Analysis and Production vs Rejection share one report page.
    iron = total(production_df, "Iron Dust (Ton)")
    waste = total(production_df, "Waste(Ton)")
    nail_total = total(production_df, "Nail production(Ton)")
    rejection = total(production_df, "Total Rejection (Ton)")
    if production_df is not None and not production_df.empty:
        fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(11.8, 5.1))
        bars = ax_left.bar(["Iron Dust", "Waste"], [iron, waste], color=RED, width=.55)
        ax_left.bar_label(bars, fmt="%.1f", padding=5, fontsize=13, color=NAVY, weight="bold")
        ax_left.set_title("Rejection Analysis", fontsize=15, color=NAVY, weight="bold", pad=15)
        ax_left.set_ylabel("Quantity (Ton)"); style_axes(ax_left)
        if nail_total + rejection > 0:
            pie_values = [nail_total, rejection]
            pie_labels = ["Nail Production", "Rejection"]
            wedges, _, autotexts = ax_right.pie(
                pie_values,
                labels=None,
                colors=[BLUE, RED],
                startangle=90,
                autopct="%1.1f%%",
                pctdistance=0.78,
                radius=0.78,
                textprops={"fontsize": 9, "fontweight": "bold", "color": "white"},
                wedgeprops={"width": .38, "edgecolor": "white", "linewidth": 2},
            )
            # Keep chart labels away from the title: show percentages inside
            # the donut and place the production/rejection totals in a legend.
            ax_right.text(0, 0, "TOTAL\nOUTPUT", ha="center", va="center",
                          fontsize=9, color=NAVY, fontweight="bold")
            legend_labels = [
                f"Nail Production: {nail_total:,.1f} Ton",
                f"Rejection: {rejection:,.1f} Ton",
            ]
            ax_right.legend(
                wedges, legend_labels,
                loc="lower center", bbox_to_anchor=(0.5, -0.17),
                frameon=False, fontsize=8, ncol=1,
                handlelength=1.0, labelspacing=0.45,
            )
        else:
            ax_right.text(.5, .5, "No production or rejection data", ha="center", va="center", transform=ax_right.transAxes, color=NAVY)
        ax_right.set_title("Production vs Rejection", fontsize=15, color=NAVY, weight="bold", pad=22)
        ax_right.axis("equal")
        fig.subplots_adjust(top=0.82, bottom=0.18, wspace=0.28)
        save_chart(fig)

    # KPI values are the first page's opening content, retaining the dashboard KPIs.
    working_days = pd.to_datetime(production_df["Date"], errors="coerce").dt.date.nunique() if production_df is not None and not production_df.empty and "Date" in production_df.columns else 0
    raw = total(production_df, "Raw material (Ton)")
    wire = total(production_df, "Wire Drawing (Ton)")
    rod = total(production_df, "Rod Production (Ton)") if factory_name == "D2 Factory" else None
    packaging = total(production_df, "Packaging (Ton)")
    bags = total(production_df, "Packaging(25kg bags)")
    avg_nail = nail_total / working_days if working_days else 0
    kpis = [("Raw Material", f"{raw:,.1f} Ton"), ("Wire Drawing", f"{wire:,.1f} Ton"), ("Nail Production", f"{nail_total:,.1f} Ton")]
    if factory_name == "D2 Factory": kpis.append(("Rod Production", f"{(rod or 0):,.1f} Ton"))
    kpis += [("Total Rejection", f"{rejection:,.1f} Ton"), ("Packaging", f"{packaging:,.1f} Ton"), ("25 kg Bags", f"{bags:,.0f}"), ("Working Days", f"{working_days} Days")]

    class KPIGrid(Flowable):
        def __init__(self, items):
            super().__init__(); self.items = items; self.width = 277*mm; self.height = 38*mm
        def draw(self):
            c = self.canv; gap = 3*mm; cols = 4; card_w = (self.width - gap*(cols-1))/cols; card_h = 16*mm
            for idx, (label, value) in enumerate(self.items):
                row, col = divmod(idx, cols); x = col*(card_w+gap); y = self.height - (row+1)*card_h - row*2*mm
                c.setFillColor(colors.HexColor("#F2F5F9")); c.setStrokeColor(colors.HexColor("#D6DFEA")); c.roundRect(x, y, card_w, card_h, 2*mm, fill=1, stroke=1)
                c.setFillColor(colors.HexColor(NAVY)); c.setFont("Helvetica-Bold", 8); c.drawCentredString(x+card_w/2, y+10*mm, label)
                c.setFillColor(colors.HexColor("#263445")); c.setFont("Helvetica-Bold", 12); c.drawCentredString(x+card_w/2, y+4.5*mm, value)

    pdf_buffer = io.BytesIO()
    page_w, page_h = landscape(A4)
    doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(A4), rightMargin=10*mm, leftMargin=10*mm, topMargin=12*mm, bottomMargin=13*mm,
                            title=f"{factory_name} {month_display} Monthly Production Report", author="Production Performance Dashboard")
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ReportHeaderTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=19, leading=22, textColor=colors.HexColor(NAVY), alignment=TA_CENTER, spaceAfter=3)
    meta_style = ParagraphStyle("ReportHeaderMeta", parent=styles["Normal"], fontSize=10, leading=14, textColor=colors.HexColor("#475569"), alignment=TA_CENTER, spaceAfter=7)
    section_style = ParagraphStyle("ReportChartSection", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=colors.HexColor(NAVY), spaceAfter=5)

    def page_decor(canvas, document):
        canvas.saveState(); w, h = landscape(A4)
        canvas.setFillColor(colors.HexColor(NAVY)); canvas.rect(0, h-5*mm, w, 5*mm, fill=1, stroke=0)
        canvas.setStrokeColor(colors.HexColor("#D8E0EA")); canvas.line(10*mm, 9*mm, w-10*mm, 9*mm)
        canvas.setFont("Helvetica", 7.5); canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(10*mm, 5.5*mm, "MONTHLY PRODUCTION REPORT")
        canvas.drawRightString(w-10*mm, 5.5*mm, f"{factory_name}  |  {month_display}  |  Page {document.page}")
        canvas.restoreState()

    story = [Spacer(1, 3*mm), Paragraph("MONTHLY PRODUCTION REPORT", title_style),
             Paragraph(f"<b>{factory_name}</b> &nbsp;&nbsp; | &nbsp;&nbsp; {month_display}", meta_style),
             KPIGrid(kpis)]

    max_w = page_w - doc.leftMargin - doc.rightMargin
    max_h = page_h - doc.topMargin - doc.bottomMargin - 8*mm
    chart_groups = {}
    for chart, group in charts:
        chart_groups.setdefault(group, []).append(chart)

    # Page 1: report heading, all dashboard KPIs, then the production trend.
    trend_charts = chart_groups.pop("trend", [])
    if trend_charts:
        story.append(Spacer(1, 2*mm))
        trend_charts[0].seek(0)
        story.append(Image(trend_charts[0], width=max_w, height=92*mm, kind="proportional"))

    # Remaining production charts retain individual pages for readability.
    for group in ("production", "daily_downtime"):
        for chart in chart_groups.pop(group, []):
            story.append(PageBreak())
            chart.seek(0)
            story.append(Image(chart, width=max_w, height=max_h, kind="proportional"))

    # Downtime reasons, utilization gauge and the three time totals share one page.
    downtime_page = chart_groups.pop("downtime_summary", [])
    if downtime_page:
        story.append(PageBreak())
        for index, chart in enumerate(downtime_page):
            chart.seek(0)
            height = 76*mm if index == 0 else (67*mm if index == 1 else 32*mm)
            story.append(Image(chart, width=max_w, height=height, kind="proportional"))
            if index < len(downtime_page)-1:
                story.append(Spacer(1, 2*mm))

    for chart in chart_groups.pop("rejection", []):
        story.append(PageBreak())
        chart.seek(0)
        story.append(Image(chart, width=max_w, height=max_h, kind="proportional"))
    doc.build(story, onFirstPage=page_decor, onLaterPages=page_decor)
    return pdf_buffer.getvalue()


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




def _report_table(data, date_columns=None, max_rows=None):
    """Return a clean HTML table for the downloadable monthly report."""
    if data is None or data.empty:
        return '<p class="empty">No data available for this section.</p>'

    frame = data.copy()
    if max_rows is not None:
        frame = frame.head(max_rows)

    date_columns = date_columns or []
    for column in frame.columns:
        if column in date_columns:
            frame[column] = pd.to_datetime(
                frame[column], errors="coerce"
            ).dt.strftime("%d %b %Y").fillna("—")
        elif pd.api.types.is_numeric_dtype(frame[column]):
            frame[column] = frame[column].map(
                lambda value: "—" if pd.isna(value) else f"{value:,.2f}"
            )
        else:
            frame[column] = frame[column].fillna("—").astype(str)

    return frame.to_html(
        index=False,
        escape=True,
        border=0,
        classes="report-table",
        na_rep="—"
    )


def _report_bar_chart(data, label_col, value_col, title, color="#4472C4", limit=10):
    """Create a lightweight, printable horizontal bar chart using HTML/CSS."""
    if data is None or data.empty or label_col not in data.columns or value_col not in data.columns:
        return '<p class="empty">No chart data available for this section.</p>'
    chart = data[[label_col, value_col]].copy()
    chart[value_col] = pd.to_numeric(chart[value_col], errors="coerce").fillna(0)
    chart = chart.sort_values(value_col, ascending=False).head(limit)
    maximum = float(chart[value_col].max()) if not chart.empty else 0
    if maximum <= 0:
        return '<p class="empty">No positive values available to chart.</p>'
    rows = []
    for _, row in chart.iterrows():
        label = html.escape(str(row[label_col]))
        value = float(row[value_col])
        width = max(1.0, value / maximum * 100)
        rows.append(
            '<div class="bar-row">'
            f'<div class="bar-label" title="{label}">{label}</div>'
            '<div class="bar-track"><div class="bar-fill" '
            f'style="width:{width:.2f}%;background:{color};"></div></div>'
            f'<div class="bar-value">{value:,.2f}</div>'
            '</div>'
        )
    return '<div class="chart-card"><div class="chart-title">' + html.escape(title) + '</div>' + ''.join(rows) + '</div>'


def _report_trend_chart(trend_df):
    """Create an SVG daily production trend chart that prints without chart libraries."""
    if trend_df is None or trend_df.empty or "Date" not in trend_df.columns:
        return '<p class="empty">No daily production data available to chart.</p>'
    series = [
        (col, label, color) for col, label, color in [
            ("Nail Production (Ton)", "Nail Production", "#4472C4"),
            ("Rod Production (Ton)", "Rod Production", "#2F9E9E"),
        ] if col in trend_df.columns
    ]
    if not series:
        return '<p class="empty">No production columns available to chart.</p>'
    data = trend_df.copy().sort_values("Date")
    for col, _, _ in series:
        data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)
    n = len(data)
    if n == 0:
        return '<p class="empty">No daily production data available to chart.</p>'
    width, height = 900, 300
    left, right, top, bottom = 54, 20, 24, 52
    plot_w, plot_h = width-left-right, height-top-bottom
    max_val = max([float(data[col].max()) for col, _, _ in series] + [1.0])
    # Round the top axis to a readable interval.
    max_val = max_val * 1.12
    parts = [f'<svg class="trend-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Daily production trend">']
    for tick in range(5):
        val = max_val * tick / 4
        y = top + plot_h - (val / max_val * plot_h)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#E2E8F0" stroke-width="1"/>')
        parts.append(f'<text x="{left-9}" y="{y+4:.1f}" text-anchor="end" font-size="11" fill="#64748B">{val:.0f}</text>')
    for i in range(n):
        x = left + (plot_w * i / max(n-1, 1))
        if i == 0 or i == n-1 or (n > 10 and i % max(1, n//6) == 0):
            date_val = pd.to_datetime(data.iloc[i]["Date"], errors="coerce")
            label = date_val.strftime("%d %b") if not pd.isna(date_val) else str(data.iloc[i]["Date"])
            parts.append(f'<text x="{x:.1f}" y="{height-22}" text-anchor="middle" font-size="10" fill="#64748B">{html.escape(label)}</text>')
    for col, label, color in series:
        points = []
        for i, val in enumerate(data[col].tolist()):
            x = left + (plot_w * i / max(n-1, 1))
            y = top + plot_h - (float(val) / max_val * plot_h)
            points.append((x, y))
        point_string = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        parts.append(f'<polyline points="{point_string}" fill="none" stroke="{color}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>')
        for x, y in points:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{color}"/>')
    parts.append('</svg>')
    legend = ''.join(f'<span class="legend-item"><i style="background:{color}"></i>{html.escape(label)}</span>' for _, label, color in series)
    return '<div class="chart-card"><div class="chart-title">Daily Production Trend (Tonnes)</div>' + ''.join(parts) + f'<div class="chart-legend">{legend}</div></div>'


def build_monthly_report_html(
    factory_name,
    month_display,
    production_df,
    downtime_df,
    size_df,
    machine_df,
    kpis
):
    """Build a printable, self-contained HTML report without extra packages."""
    generated_on = pd.Timestamp.now().strftime("%d %B %Y, %I:%M %p")

    # Daily production detail
    daily_columns = [
        "Date",
        "Raw material (Ton)",
        "Wire Drawing (Ton)",
        "Nail production(Ton)",
    ]
    if factory_name == "D2 Factory":
        daily_columns.append("Rod Production (Ton)")
    daily_columns += [
        "Iron Dust (Ton)",
        "Waste(Ton)",
        "Total Rejection (Ton)",
        "Packaging (Ton)",
        "Packaging(25kg bags)",
        "Machine shift time (hours)",
        "Total downtime (hours)",
    ]
    available_daily_columns = [
        col for col in daily_columns if col in production_df.columns
    ]
    daily_detail = production_df[available_daily_columns].copy()
    daily_detail = daily_detail.rename(columns={
        "Date": "Date",
        "Raw material (Ton)": "Raw Material (Ton)",
        "Wire Drawing (Ton)": "Wire Drawing (Ton)",
        "Nail production(Ton)": "Nail Production (Ton)",
        "Rod Production (Ton)": "Rod Production (Ton)",
        "Iron Dust (Ton)": "Iron Dust (Ton)",
        "Waste(Ton)": "Waste (Ton)",
        "Total Rejection (Ton)": "Total Rejection (Ton)",
        "Packaging (Ton)": "Packaging (Ton)",
        "Packaging(25kg bags)": "25 kg Bags",
        "Machine shift time (hours)": "Shift Time (Hours)",
        "Total downtime (hours)": "Downtime (Hours)",
    })
    if "Date" in daily_detail.columns:
        daily_detail = daily_detail.sort_values("Date")

    # Daily production trend
    trend_columns = [
        col for col in ["Nail production(Ton)", "Rod Production (Ton)"]
        if col in production_df.columns
        and (col != "Rod Production (Ton)" or factory_name == "D2 Factory")
    ]
    if "Date" in production_df.columns and trend_columns:
        trend_df = production_df.groupby("Date", as_index=False)[trend_columns].sum()
        trend_df = trend_df.rename(columns={
            "Nail production(Ton)": "Nail Production (Ton)",
            "Rod Production (Ton)": "Rod Production (Ton)",
        }).sort_values("Date")
    else:
        trend_df = pd.DataFrame()

    # Size-wise production
    size_tables = []
    nail_category_col = find_column(size_df, ["Nail Catogery", "Nail Category"])
    nail_qty_col = find_column(size_df, ["Nail_Production", "Nail Production"])
    if nail_category_col and nail_qty_col:
        nail_size = size_df[[nail_category_col, nail_qty_col]].copy()
        nail_size[nail_qty_col] = pd.to_numeric(
            nail_size[nail_qty_col], errors="coerce"
        ).fillna(0)
        nail_size = nail_size[
            nail_size[nail_category_col].notna()
            & ~nail_size[nail_category_col].astype(str).str.strip().str.lower().isin(
                ["", "nan", "none"]
            )
        ]
        nail_size = nail_size.groupby(nail_category_col, as_index=False)[nail_qty_col].sum()
        nail_size = nail_size.sort_values(nail_qty_col, ascending=False).rename(
            columns={nail_category_col: "Nail Category", nail_qty_col: "Production (Ton)"}
        )
        size_tables.append(("Nail Production by Category", nail_size))

    if factory_name == "D2 Factory":
        rod_category_col = find_column(size_df, ["Rod Catogery", "Rod Category"])
        rod_qty_col = find_column(size_df, ["Rod_Production", "Rod Production"])
        if rod_category_col and rod_qty_col:
            rod_size = size_df[[rod_category_col, rod_qty_col]].copy()
            rod_size[rod_qty_col] = pd.to_numeric(
                rod_size[rod_qty_col], errors="coerce"
            ).fillna(0)
            rod_size = rod_size[
                rod_size[rod_category_col].notna()
                & ~rod_size[rod_category_col].astype(str).str.strip().str.lower().isin(
                    ["", "nan", "none"]
                )
            ]
            rod_size = rod_size.groupby(rod_category_col, as_index=False)[rod_qty_col].sum()
            rod_size = rod_size.sort_values(rod_qty_col, ascending=False).rename(
                columns={rod_category_col: "Rod Category", rod_qty_col: "Production (Ton)"}
            )
            size_tables.append(("Rod Production by Category", rod_size))

    # Machine-wise production summaries, separated by machine type
    machine_summaries = {}
    machine_chart_sections = []
    if (
        machine_df is not None
        and not machine_df.empty
        and "Machine" in machine_df.columns
        and "Machine Production (ton)" in machine_df.columns
    ):
        machine_work = machine_df[["Machine", "Machine Production (ton)"]].copy()
        machine_work["Machine"] = machine_work["Machine"].fillna("").astype(str).str.strip()
        machine_work["Machine Production (ton)"] = pd.to_numeric(
            machine_work["Machine Production (ton)"], errors="coerce"
        ).fillna(0)
        machine_work = machine_work[machine_work["Machine"] != ""]
        machine_work["Machine Category"] = machine_work["Machine"].apply(classify_machine)

        machine_types = [
            ("Wire Drawing", "Wire Drawing Machines", "#4472C4"),
            ("Nail", "Nail Machines", "#2F9E9E"),
        ]
        if factory_name == "D2 Factory":
            machine_types.append(("Rod", "Rod Machines", "#ED7D31"))

        for category, title, color in machine_types:
            summary = (
                machine_work[machine_work["Machine Category"] == category]
                .groupby("Machine", as_index=False)["Machine Production (ton)"]
                .sum()
                .sort_values("Machine Production (ton)", ascending=False)
                .rename(columns={"Machine Production (ton)": "Production (Ton)"})
            )
            machine_summaries[category] = summary
            machine_chart_sections.append(
                f'<section><h2>{html.escape(title)}</h2>'
                f'{_report_bar_chart(summary, "Machine", "Production (Ton)", title + " Production (Ton)", color, limit=30)}'
                f'{_report_table(summary)}</section>'
            )

    machine_chart_html = "".join(machine_chart_sections)

    # Downtime summary
    downtime_summary = pd.DataFrame()
    if "Reason" in downtime_df.columns and "Downtime (hrs)" in downtime_df.columns:
        dt = downtime_df[["Reason", "Downtime (hrs)"]].copy()
        dt["Downtime (hrs)"] = pd.to_numeric(
            dt["Downtime (hrs)"], errors="coerce"
        ).fillna(0)
        dt["Reason"] = dt["Reason"].fillna("Unspecified").astype(str).str.strip()
        downtime_summary = (
            dt.groupby("Reason", as_index=False)["Downtime (hrs)"]
            .sum()
            .sort_values("Downtime (hrs)", ascending=False)
            .head(10)
            .rename(columns={"Reason": "Downtime Reason", "Downtime (hrs)": "Downtime (Hours)"})
        )

    rejection_summary = pd.DataFrame([
        {"Rejection Type": "Iron Dust", "Quantity (Ton)": safe_sum(production_df, "Iron Dust (Ton)")},
        {"Rejection Type": "Waste", "Quantity (Ton)": safe_sum(production_df, "Waste(Ton)")},
        {"Rejection Type": "Total Rejection", "Quantity (Ton)": safe_sum(production_df, "Total Rejection (Ton)")},
    ])

    # Friendly chart components for the printable report
    trend_chart_html = _report_trend_chart(trend_df)
    size_chart_sections = []
    for title, table in size_tables:
        label_col = table.columns[0] if len(table.columns) else None
        value_col = table.columns[1] if len(table.columns) > 1 else None
        if label_col and value_col:
            chart_color = "#4472C4" if "Nail" in title else "#2F9E9E"
            size_chart_sections.append(
                f'<section><h2>{html.escape(title)} — Chart</h2>'
                f'{_report_bar_chart(table, label_col, value_col, title, chart_color, limit=12)}</section>'
            )
    size_chart_html = "".join(size_chart_sections)
    downtime_chart_html = _report_bar_chart(
        downtime_summary, "Downtime Reason", "Downtime (Hours)", "Top Downtime Reasons (Hours)", "#ED7D31", limit=10
    )
    rejection_chart_html = _report_bar_chart(
        rejection_summary, "Rejection Type", "Quantity (Ton)", "Rejection and Waste (Tonnes)", "#C00000", limit=5
    )

    kpi_cards = "".join(
        f'<div class="kpi"><div class="kpi-label">{html.escape(label)}</div>'
        f'<div class="kpi-value">{html.escape(value)}</div>'
        f'<div class="kpi-unit">{html.escape(unit)}</div></div>'
        for label, value, unit in kpis
    )
    size_sections = "".join(
        f'<section><h2>{html.escape(title)}</h2>{_report_table(table)}</section>'
        for title, table in size_tables
    )

    downtime_total = safe_sum(downtime_df, "Downtime (hrs)")
    shift_total = safe_sum(production_df, "Machine shift time (hours)")
    operating_total = max(shift_total - downtime_total, 0)
    downtime_pct = (downtime_total / shift_total * 100) if shift_total else 0
    report_working_days = (
        production_df["Date"].nunique()
        if "Date" in production_df.columns else 0
    )
    report_daily_avg_nail = (
        safe_sum(production_df, "Nail production(Ton)") / report_working_days
        if report_working_days else 0
    )

    factory_safe = html.escape(str(factory_name))
    month_safe = html.escape(str(month_display))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Production Report - {factory_safe} - {month_safe}</title>
<style>
:root {{ --navy:#17365D; --blue:#4472C4; --border:#D9E2EC; --muted:#64748B; }}
* {{ box-sizing:border-box; }}
body {{ font-family:Arial,Helvetica,sans-serif; color:#1F2937; margin:0;
       background:#F4F6F9; line-height:1.45; }}
.page {{ max-width:1100px; margin:24px auto; background:white; padding:34px 38px;
         box-shadow:0 2px 12px #00000012; }}
.header {{ background:linear-gradient(135deg,var(--navy),var(--blue)); color:white;
           padding:24px 28px; border-radius:8px; }}
.header h1 {{ margin:0 0 6px; font-size:25px; }}
.header p {{ margin:4px 0; color:#EAF1F8; }}
.meta {{ display:flex; flex-wrap:wrap; gap:18px; margin-top:16px; font-size:12px; }}
.actions {{ display:flex; gap:10px; margin:18px 0; }}
.actions button {{ border:0; border-radius:6px; padding:11px 16px; background:var(--navy);
                   color:white; font-size:14px; cursor:pointer; }}
.actions .secondary {{ background:#EAF1F8; color:var(--navy); }}
h2 {{ color:var(--navy); font-size:17px; border-bottom:2px solid #EAF1F8;
      padding-bottom:7px; margin:26px 0 12px; }}
.kpis {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin-top:18px; }}
.kpi {{ border:1px solid var(--border); border-radius:7px; padding:13px; }}
.kpi-label {{ color:var(--muted); text-transform:uppercase; font-size:10px; font-weight:bold; }}
.kpi-value {{ color:var(--navy); font-size:22px; font-weight:bold; margin-top:6px; }}
.kpi-unit {{ color:var(--muted); font-size:11px; }}
.report-table {{ width:100%; border-collapse:collapse; font-size:11px; margin:8px 0 20px; }}
.report-table th {{ background:var(--navy); color:white; text-align:left; padding:8px 7px; }}
.report-table td {{ padding:7px; border-bottom:1px solid var(--border); overflow-wrap:anywhere; }}
.report-table tr:nth-child(even) td {{ background:#F5F7FA; }}
.empty {{ color:var(--muted); font-style:italic; }}
.chart-card {{ border:1px solid var(--border); border-radius:8px; padding:16px; margin:10px 0 20px; background:#FFFFFF; break-inside:avoid; }}
.chart-title {{ color:var(--navy); font-size:13px; font-weight:bold; margin-bottom:14px; }}
.bar-row {{ display:grid; grid-template-columns:minmax(100px, 190px) minmax(100px, 1fr) 72px; gap:10px; align-items:center; margin:10px 0; }}
.bar-label {{ font-size:11px; overflow-wrap:anywhere; }}
.bar-track {{ height:15px; background:#EEF2F7; border-radius:4px; overflow:hidden; }}
.bar-fill {{ height:100%; border-radius:4px; }}
.bar-value {{ font-size:11px; font-weight:bold; text-align:right; font-variant-numeric:tabular-nums; }}
.trend-svg {{ width:100%; height:auto; display:block; }}
.chart-legend {{ display:flex; flex-wrap:wrap; gap:16px; justify-content:center; margin-top:6px; font-size:11px; }}
.legend-item {{ display:inline-flex; align-items:center; gap:6px; }}
.legend-item i {{ width:12px; height:12px; border-radius:50%; display:inline-block; }}
.note {{ color:var(--muted); font-size:11px; }}
.footer {{ margin-top:30px; border-top:1px solid var(--border); padding-top:10px;
           text-align:center; color:var(--muted); font-size:10px; }}
@page {{ size:A4 landscape; margin:12mm; }}
@media print {{
 body {{ background:white; font-size:10px; }}
 .page {{ max-width:none; margin:0; padding:0; box-shadow:none; }}
 .actions {{ display:none !important; }}
 .header,.report-table th,.kpi {{ print-color-adjust:exact; -webkit-print-color-adjust:exact; }}
 h2 {{ break-after:avoid; }} table {{ break-inside:auto; }} tr {{ break-inside:avoid; }}
}}
@media(max-width:700px) {{
 .page {{ margin:0; padding:16px; }} .kpis {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} .bar-row {{ grid-template-columns:100px minmax(70px,1fr) 58px; gap:6px; }}
}}
</style>
</head>
<body>
<div class="page">
<header class="header">
<h1>PRODUCTION PERFORMANCE DASHBOARD</h1>
<p>EKALA NAIL PLANT | MONTHLY PRODUCTION ANALYSIS</p>
<div class="meta">
<span><strong>Factory:</strong> {factory_safe}</span>
<span><strong>Reporting Month:</strong> {month_safe}</span>
<span><strong>Generated:</strong> {html.escape(generated_on)}</span>
</div>
</header>
<div class="actions">
<button onclick="window.print()">Print Report / Save as PDF</button>
<button class="secondary" onclick="window.close()">Close Report</button>
</div>
<section><h2>1. Monthly KPI Summary</h2><div class="kpis">{kpi_cards}</div></section>
<section><h2>2. Daily Average and Operating Time</h2>
{_report_table(pd.DataFrame([
    {"Indicator":"Working Days","Value":str(report_working_days),"Unit":"Days"},
    {"Indicator":"Average Daily Nail Production","Value":f"{report_daily_avg_nail:,.1f}","Unit":"Ton / Day"},
    {"Indicator":"Total Shift Time","Value":f"{shift_total:,.1f}","Unit":"Hours"},
    {"Indicator":"Total Downtime","Value":f"{downtime_total:,.1f}","Unit":"Hours"},
    {"Indicator":"Operating Time","Value":f"{operating_total:,.1f}","Unit":"Hours"},
    {"Indicator":"Downtime as % of Shift Time","Value":f"{downtime_pct:,.1f}%","Unit":""},
]))}
</section>
<section><h2>3. Daily Production Trend</h2>{trend_chart_html}{_report_table(trend_df,date_columns=["Date"])}</section>
{size_chart_html}
{size_sections}
<section><h2>4. Machine-wise Production</h2>{machine_chart_html}</section>
<section><h2>Downtime Analysis — Top 10 Reasons</h2>{downtime_chart_html}{_report_table(downtime_summary)}</section>
<section><h2>Rejection Analysis</h2>{rejection_chart_html}{_report_table(rejection_summary)}</section>
<section><h2>Daily Production Records</h2>{_report_table(daily_detail,date_columns=["Date"])}</section>
<p class="note">This report reflects the factory and month selected in the dashboard. Values are calculated from the loaded production workbook.</p>
<footer class="footer">Production Performance Dashboard · Monthly Production Report</footer>
</div>
</body>
</html>"""



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
    'Monthly Production Report'
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
# DOWNLOAD PDF — CHARTS ONLY
# ============================================================

pdf_bytes = build_dashboard_pdf(
    factory_name=selected_factory,
    month_display=selected_month_display,
    production_df=production_filtered,
    downtime_df=downtime_filtered,
    size_df=size_filtered,
    machine_df=machine_filtered,
)

pdf_filename_factory = selected_factory.lower().replace(" ", "_")
pdf_filename_month = pd.Timestamp(selected_month).strftime("%B_%Y").lower()

pdf_spacer, pdf_button_col = st.columns([7, 1.8])
with pdf_button_col:
    st.download_button(
        label="📄 Download Monthly Report PDF",
        data=pdf_bytes,
        file_name=f"{pdf_filename_factory}_{pdf_filename_month}_monthly_report.pdf",
        mime="application/pdf",
        use_container_width=True,
        key="download_monthly_report_pdf",
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
                mode="lines+markers+text",
                text=trend["Nail production(Ton)"].map(lambda v: f"{v:.1f}"),
                textposition="top center",
                textfont=dict(size=13, color=NAVY),
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
                    mode="lines+markers+text",
                    text=trend["Rod Production (Ton)"].map(lambda v: f"{v:.1f}"),
                    textposition="bottom center",
                    textfont=dict(size=13, color=ORANGE),
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

    # Daily downtime trend, positioned immediately above the Top 10 reasons.
    st.markdown("#### Daily Downtime")
    if (
        "Date" in production_filtered.columns
        and "Total downtime (hours)" in production_filtered.columns
    ):
        daily_dt_summary = production_filtered[["Date", "Total downtime (hours)"]].copy()
        daily_dt_summary["Date"] = pd.to_datetime(
            daily_dt_summary["Date"], errors="coerce"
        )
        daily_dt_summary["Total downtime (hours)"] = pd.to_numeric(
            daily_dt_summary["Total downtime (hours)"], errors="coerce"
        ).fillna(0)
        daily_dt_summary = (
            daily_dt_summary.dropna(subset=["Date"])
            .groupby("Date", as_index=False)["Total downtime (hours)"].sum()
            .sort_values("Date")
        )
        if not daily_dt_summary.empty:
            fig_daily_dt_summary = px.line(
                daily_dt_summary, x="Date", y="Total downtime (hours)",
                markers=True, text="Total downtime (hours)"
            )
            fig_daily_dt_summary.update_traces(
                line=dict(color=ORANGE, width=3), marker=dict(size=9),
                mode="lines+markers+text", texttemplate="%{y:.1f}",
                textposition="top center", textfont=dict(size=16, color=NAVY)
            )
            fig_daily_dt_summary.update_layout(
                height=320, margin=dict(l=10, r=35, t=15, b=10),
                paper_bgcolor="white", plot_bgcolor="white",
                xaxis_title="Date", yaxis_title="Downtime (Hours)"
            )
            st.plotly_chart(
                fig_daily_dt_summary, use_container_width=True,
                key="summary_daily_downtime"
            )
        else:
            st.info("Daily downtime data is unavailable.")
    else:
        st.info("Daily downtime data is unavailable.")

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


# Daily downtime trend is displayed immediately above the Top 10 reasons.
if "Date" in production_filtered.columns and "Total downtime (hours)" in production_filtered.columns:
    daily_downtime = production_filtered[["Date", "Total downtime (hours)"]].copy()
    daily_downtime["Date"] = pd.to_datetime(daily_downtime["Date"], errors="coerce")
    daily_downtime["Total downtime (hours)"] = pd.to_numeric(
        daily_downtime["Total downtime (hours)"], errors="coerce"
    ).fillna(0)
    daily_downtime = (
        daily_downtime.dropna(subset=["Date"])
        .groupby("Date", as_index=False)["Total downtime (hours)"].sum()
        .sort_values("Date")
    )
    st.markdown("#### Daily Downtime")
    if not daily_downtime.empty:
        fig_daily_dt = px.line(
            daily_downtime, x="Date", y="Total downtime (hours)",
            markers=True, text="Total downtime (hours)"
        )
        fig_daily_dt.update_traces(
            line=dict(color=ORANGE, width=3), marker=dict(size=9),
            mode="lines+markers+text", texttemplate="%{y:.1f}",
            textposition="top center", textfont=dict(size=16, color=NAVY)
        )
        fig_daily_dt.update_layout(
            height=360, margin=dict(l=20, r=35, t=20, b=20),
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis_title="Date", yaxis_title="Downtime (Hours)"
        )
        st.plotly_chart(fig_daily_dt, use_container_width=True, key="daily_downtime_trend")
    else:
        st.info("No daily downtime data available for the selected period.")

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
        # Keep percentages inside the donut; category names remain in legend.
        textinfo="percent",
        textposition="inside",
        insidetextorientation="horizontal",
        textfont=dict(size=13, color="white"),
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Quantity: %{value:.1f} Ton<br>"
            "Percentage: %{percent}"
            "<extra></extra>"
        )
    )

    fig_pie.update_layout(
        title=dict(
            text="Production vs Rejection",
            x=0.5,
            xanchor="center",
            y=0.98,
            yanchor="top",
            font=dict(size=16, color=NAVY)
        ),
        height=390,
        margin=dict(
            l=25,
            r=25,
            t=70,
            b=65
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.12,
            xanchor="center",
            x=0.5,
            font=dict(size=11)
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
