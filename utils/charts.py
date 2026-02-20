"""Reusable Plotly chart functions for the hospitality dashboard."""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from config import COLORS, COMPANY_NAMES

TEXT_COLOR = "#111111"
AXIS_COLOR = "#111111"
GRID_COLOR = "#ebebeb"
CHART_FONT = dict(family="Inter, Helvetica, Arial, sans-serif", size=13, color=TEXT_COLOR)


def _apply_theme(fig, height=None):
    """Apply clean, professional theme to all charts."""
    fig.update_layout(
        template="none",
        font=CHART_FONT,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=12, color=TEXT_COLOR),
        ),
        margin=dict(l=50, r=20, t=30, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(
            gridcolor=GRID_COLOR,
            showline=True,
            linecolor="#ccc",
            tickfont=dict(color=AXIS_COLOR, size=12),
            title_font=dict(color=AXIS_COLOR, size=13, family="Inter, Helvetica, Arial, sans-serif"),
        ),
        yaxis=dict(
            gridcolor=GRID_COLOR,
            showline=True,
            linecolor="#ccc",
            tickfont=dict(color=AXIS_COLOR, size=12),
            title_font=dict(color=AXIS_COLOR, size=13, family="Inter, Helvetica, Arial, sans-serif"),
        ),
        title_font=dict(color=TEXT_COLOR, size=14),
    )
    if height:
        fig.update_layout(height=height)
    return fig


def line_chart(df, x, y, color="Company", title="", y_label="", height=None):
    """Multi-company line chart using explicit go.Scatter traces per company."""
    fig = go.Figure()
    companies = [c for c in COMPANY_NAMES if c in df[color].values]
    # Fall back to whatever order is in the data
    if not companies:
        companies = [c for c in df[color].dropna().unique()]

    # Sort x values to ensure chronological order
    x_order = sorted(df[x].dropna().unique())

    for company in companies:
        cd = df[df[color] == company].dropna(subset=[y]).copy()
        cd["_ord"] = cd[x].map({v: i for i, v in enumerate(x_order)})
        cd = cd.sort_values("_ord")
        if cd.empty:
            continue
        fig.add_trace(go.Scatter(
            x=cd[x],
            y=cd[y],
            name=company,
            mode="lines+markers",
            line=dict(color=COLORS.get(company, "#888"), width=2.5),
            marker=dict(size=7, color=COLORS.get(company, "#888")),
        ))

    fig.update_layout(yaxis_title=y_label or y, xaxis_title="")
    if title:
        fig.update_layout(title=dict(text=title))
    return _apply_theme(fig, height=height)


def grouped_bar_chart(df, x, y, color="Company", title="", y_label="", height=None):
    fig = go.Figure()
    companies = [c for c in COMPANY_NAMES if c in df[color].values]
    if not companies:
        companies = list(df[color].dropna().unique())
    for company in companies:
        cd = df[df[color] == company]
        fig.add_trace(go.Bar(
            x=cd[x],
            y=cd[y],
            name=company,
            marker_color=COLORS.get(company, "#888"),
            opacity=0.85,
        ))
    fig.update_layout(barmode="group", yaxis_title=y_label or y, xaxis_title="")
    if title:
        fig.update_layout(title=dict(text=title))
    return _apply_theme(fig, height=height)


def horizontal_bar_chart(df, x, y, color="Company", title="", x_label="", height=None):
    """Horizontal bar chart — one explicit trace per row to avoid undefined labels."""
    fig = go.Figure()
    for _, row in df.iterrows():
        company = row[color]
        if pd.isna(company):
            continue
        fig.add_trace(go.Bar(
            x=[row[x]],
            y=[str(row[y])],
            name=str(company),
            orientation="h",
            marker_color=COLORS.get(str(company), "#888"),
            opacity=0.85,
            showlegend=False,
        ))
    fig.update_layout(showlegend=False, xaxis_title=x_label or x, yaxis_title="")
    if title:
        fig.update_layout(title=dict(text=title))
    return _apply_theme(fig, height=height)


def scatter_chart(df, x, y, color="Company", size=None, title="", x_label="", y_label="", height=None):
    """Scatter / bubble chart — one explicit trace per row to avoid undefined labels."""
    fig = go.Figure()
    max_size_val = df[size].max() if size and size in df.columns else 1
    for _, row in df.iterrows():
        company = row[color]
        if pd.isna(company):
            continue
        sz = 20
        if size and size in df.columns and pd.notna(row[size]):
            sz = max(12, int(row[size] / max_size_val * 52))
        fig.add_trace(go.Scatter(
            x=[row[x]],
            y=[row[y]],
            mode="markers+text",
            name=str(company),
            text=[str(company)],
            textposition="top center",
            textfont=dict(color=TEXT_COLOR, size=12),
            marker=dict(color=COLORS.get(str(company), "#888"), size=sz, opacity=0.85),
            showlegend=False,
        ))
    fig.update_layout(xaxis_title=x_label or x, yaxis_title=y_label or y)
    if title:
        fig.update_layout(title=dict(text=title))
    return _apply_theme(fig, height=height)


def normalized_stock_chart(stock_df, title="Relative Performance (Indexed to 100)", height=400):
    if stock_df.empty:
        return go.Figure()

    fig = go.Figure()
    for company in stock_df["Company"].unique():
        company_data = stock_df[stock_df["Company"] == company].sort_values("Date")
        if company_data.empty:
            continue
        base_price = company_data.iloc[0]["Close"]
        normalized = (company_data["Close"] / base_price) * 100
        fig.add_trace(go.Scatter(
            x=company_data["Date"],
            y=normalized,
            name=company,
            mode="lines",
            line=dict(color=COLORS.get(company, "#888"), width=2.5),
        ))

    fig.add_hline(y=100, line_dash="dash", line_color="#ccc", opacity=0.6)
    fig.update_layout(yaxis_title="Indexed Price (Start = 100)", xaxis_title="")
    if title:
        fig.update_layout(title=dict(text=title))
    return _apply_theme(fig, height=height)


def financial_combo_chart(
    df_display,
    metric,
    metric_label,
    period_col,
    period_order,
    df_prior=None,
    growth_label="YoY Growth (%)",
    height=380,
    show_growth=True,
):
    """
    Grouped bars (actual values, left y-axis) + optional dashed growth lines
    per company (right y-axis).

    show_growth=False  → bars only (quarterly view)
    show_growth=True   → bars + YoY growth lines (annual view)

    For quarterly YoY: pass df_prior (prior-year same quarters).
    For annual YoY:    pass df_prior=None; growth computed sequentially within df_display.
    """
    fig = go.Figure()
    companies = [c for c in COMPANY_NAMES if c in df_display["Company"].unique()]
    order_map = {p: i for i, p in enumerate(period_order)}

    # ── Compute growth rates (always, even if not shown, so layout stays clean) ──
    growth_by_company = {}
    for company in companies:
        curr_df = df_display[df_display["Company"] == company].copy()
        curr_df = curr_df[curr_df[period_col].isin(period_order)]
        curr = curr_df.set_index(period_col)[metric]

        growth = {}
        if df_prior is not None:
            # Quarterly YoY: Qn 2025 vs Qn 2024
            prev_df = df_prior[df_prior["Company"] == company].copy()
            prev = prev_df.set_index(period_col)[metric]
            for period in period_order:
                if period not in curr.index:
                    growth[period] = None
                    continue
                parts = period.split(" ")
                prior_period = f"{parts[0]} {int(parts[1]) - 1}" if len(parts) == 2 else None
                if prior_period and prior_period in prev.index:
                    cv, pv = curr[period], prev[prior_period]
                    growth[period] = round((cv - pv) / abs(pv) * 100, 1) if pd.notna(pv) and pv != 0 else None
                else:
                    growth[period] = None
        else:
            # Annual sequential YoY
            growth[period_order[0]] = None
            for i in range(1, len(period_order)):
                cp, pp = period_order[i], period_order[i - 1]
                if cp in curr.index and pp in curr.index:
                    cv, pv = curr[cp], curr[pp]
                    growth[cp] = round((cv - pv) / abs(pv) * 100, 1) if pd.notna(pv) and pv != 0 else None
                else:
                    growth[cp] = None
        growth_by_company[company] = growth

    # ── Bar traces ────────────────────────────────────────────────────────────
    for company in companies:
        cd = df_display[df_display["Company"] == company].copy()
        cd = cd[cd[period_col].isin(period_order)]
        cd["_ord"] = cd[period_col].map(order_map)
        cd = cd.sort_values("_ord")
        fig.add_trace(go.Bar(
            x=cd[period_col],
            y=cd[metric],
            name=company,
            marker_color=COLORS.get(company, "#888"),
            opacity=0.82,
            yaxis="y",
            legendgroup=company,
        ))

    # ── Growth line traces (annual only) ──────────────────────────────────────
    if show_growth:
        for company in companies:
            growth = growth_by_company.get(company, {})
            # Only plot positions where we have a real value
            valid_x = [p for p in period_order if growth.get(p) is not None]
            valid_y = [growth[p] for p in valid_x]
            if len(valid_x) >= 1:
                fig.add_trace(go.Scatter(
                    x=valid_x,
                    y=valid_y,
                    name=f"{company} YoY %",
                    mode="lines+markers",
                    line=dict(color=COLORS.get(company, "#888"), width=2, dash="dot"),
                    marker=dict(size=6, symbol="circle"),
                    yaxis="y2",
                    legendgroup=company,
                    showlegend=False,
                ))

    # ── Layout ───────────────────────────────────────────────────────────────
    right_margin = 70 if show_growth else 20
    layout = dict(
        barmode="group",
        template="none",
        font=CHART_FONT,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(size=11, color=TEXT_COLOR),
        ),
        margin=dict(l=60, r=right_margin, t=30, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=height,
        xaxis=dict(
            gridcolor=GRID_COLOR, showline=True, linecolor="#ccc",
            tickfont=dict(color=AXIS_COLOR, size=12),
            categoryorder="array", categoryarray=period_order,
        ),
        yaxis=dict(
            title=metric_label,
            gridcolor=GRID_COLOR, showline=True, linecolor="#ccc",
            tickfont=dict(color=AXIS_COLOR, size=12),
            title_font=dict(color=AXIS_COLOR, size=13, family="Inter, Helvetica, Arial, sans-serif"),
        ),
    )
    if show_growth:
        layout["yaxis2"] = dict(
            title=growth_label,
            overlaying="y", side="right",
            showgrid=False, showline=True, linecolor="#ddd",
            tickfont=dict(color="#777", size=11),
            title_font=dict(color="#777", size=12, family="Inter, Helvetica, Arial, sans-serif"),
            ticksuffix="%",
            zeroline=True, zerolinecolor="#ddd", zerolinewidth=1,
        )
    fig.update_layout(**layout)
    return fig
