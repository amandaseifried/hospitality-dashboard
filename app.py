"""Hospitality Earnings & Competitive Intelligence Dashboard."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from config import COMPANIES, COMPANY_NAMES, TICKERS, COLORS, QUARTERS
from scrapers.market_data import (
    get_stock_data, get_company_info,
    calculate_ytd_returns, calculate_period_returns
)
from utils.data_loader import (
    load_hotel_kpis, load_hotel_financials_annual,
    load_luxury_brands, load_luxury_news, load_digital_trends,
    load_loyalty_historical, load_digital_news,
    get_latest_quarter, get_latest_per_company, get_logo_path
)
import calendar as _calendar
from utils.charts import (
    line_chart, grouped_bar_chart, horizontal_bar_chart,
    scatter_chart, normalized_stock_chart, financial_combo_chart
)
import base64

def _logo_base64(path):
    """Read a logo image file and return its base64 encoding."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# ── Sources ──────────────────────────────────────────────────────────────────
SOURCES = {
    "company_overview": [
        ("Yahoo Finance", "https://finance.yahoo.com/"),
        ("Marriott Investor Relations", "https://marriott.gcs-web.com/"),
        ("Hilton Investor Relations", "https://ir.hilton.com/"),
        ("Hyatt Investor Relations", "https://investors.hyatt.com/"),
        ("IHG Investor Relations", "https://www.ihgplc.com/en/investors"),
        ("Accor Finance", "https://group.accor.com/en/finance"),
    ],
    "financial_overview": [
        ("Marriott Q4 & FY 2025 Earnings Release", "https://marriott.gcs-web.com/news-releases/news-release-details/marriott-international-reports-fourth-quarter-and-full-year-2025"),
        ("Hilton Q4 & FY 2025 Earnings Release", "https://stories.hilton.com/releases/hilton-reports-2025-fourth-quarter-and-full-year-results"),
        ("Hyatt Q4 & FY 2025 Earnings Release", "https://newsroom.hyatt.com/Q4-FullYear-2025-Earnings"),
        ("IHG FY 2025 Full Year Results", "https://www.ihgplc.com/en/investors/results-reports-and-presentations/2026/full-year-results-for-the-year-to-31-dec-2025"),
        ("Accor H1 2025 Results (FY2025 est.)", "https://press.accor.com/first-half-2025-solid-activity-in-a-complex-macroeconomic-environment"),
    ],
    "luxury_overview": [
        ("Marriott Brands", "https://www.marriott.com/marriott-brands.mi"),
        ("Hilton Brands", "https://www.hilton.com/en/brands/"),
        ("Hyatt Brands", "https://world.hyatt.com/content/gp/en/brands.html"),
        ("IHG Brands", "https://www.ihg.com/content/us/en/about/brands"),
        ("Accor Brands", "https://group.accor.com/en/brands"),
    ],
    "operational_overview": [
        ("Marriott Q4 & FY 2025 Earnings Release", "https://marriott.gcs-web.com/news-releases/news-release-details/marriott-international-reports-fourth-quarter-and-full-year-2025"),
        ("Hilton Q4 & FY 2025 Earnings Release", "https://stories.hilton.com/releases/hilton-reports-2025-fourth-quarter-and-full-year-results"),
        ("Hyatt Q4 & FY 2025 Earnings Release", "https://newsroom.hyatt.com/Q4-FullYear-2025-Earnings"),
        ("IHG FY 2025 Full Year Results", "https://www.ihgplc.com/en/investors/results-reports-and-presentations/2026/full-year-results-for-the-year-to-31-dec-2025"),
        ("Accor H1 2025 Results", "https://press.accor.com/first-half-2025-solid-activity-in-a-complex-macroeconomic-environment"),
    ],
    "digital_trends": [
        ("Marriott Bonvoy", "https://www.marriott.com/loyalty.mi"),
        ("Hilton Honors", "https://www.hilton.com/en/hilton-honors/"),
        ("World of Hyatt", "https://world.hyatt.com/content/gp/en/rewards.html"),
        ("IHG One Rewards", "https://www.ihg.com/one-rewards/content/us/en/home"),
        ("ALL - Accor Live Limitless", "https://all.accor.com/"),
        ("Company Earnings Releases & 10-Q/10-K SEC Filings", "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"),
    ],
}

def render_sources(key):
    """Render a sources section at the bottom of a tab."""
    sources = SOURCES.get(key, [])
    if not sources:
        return
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    links = " &nbsp;|&nbsp; ".join(
        f'<a href="{url}" target="_blank" style="color: #666; text-decoration: none;">{name}</a>'
        for name, url in sources
    )
    st.markdown(
        f'<div style="padding: 12px 0;">'
        f'<p style="font-size: 0.72rem; font-weight: 600; color: #999; '
        f'text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px;">Sources</p>'
        f'<p style="font-size: 0.75rem; line-height: 1.8;">{links}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── News table helpers — global scope so Tab 3 and Tab 5 both have access ─────
_month_abbr = {m: i for i, m in enumerate(_calendar.month_abbr) if m}


def _date_key(d):
    parts = str(d).split()
    if len(parts) == 2:
        try:
            return int(parts[1]) * 100 + _month_abbr.get(parts[0], 0)
        except Exception:
            pass
    return 0


def _year_from_date(d):
    parts = str(d).split()
    if len(parts) == 2:
        try:
            return int(parts[1])
        except Exception:
            pass
    return 0


def _is_direct_quote(news):
    if not pd.notna(news):
        return False
    return str(news).strip().startswith(('"', '\u201c', '\u2018'))


def _news_table_html(df, table_class, col3_header):
    # Sort newest first
    df = df.copy()
    df["_sort"] = df["Date"].apply(_date_key)
    df = df.sort_values("_sort", ascending=False)

    # Company chip filter bar (only companies present in this dataset)
    companies = [c for c in ["Marriott", "Hilton", "Hyatt", "IHG", "Accor"]
                 if c in df["Company"].values]
    chips_html = (
        '<div style="display:flex; flex-wrap:wrap; gap:8px; margin-bottom:14px; align-items:center;">'
        '<span style="font-size:0.72rem; font-weight:700; color:#aaa; text-transform:uppercase; '
        'letter-spacing:0.06em; margin-right:2px;">Filter:</span>'
    )
    for company in companies:
        color = COLORS.get(company, "#888")
        chips_html += (
            f'<button class="nchip" data-company="{company}" data-table="{table_class}" '
            f'data-color="{color}" '
            f'style="padding:4px 14px; border-radius:20px; border:1.5px solid {color}; '
            f'background:transparent; color:{color}; cursor:pointer; font-size:0.82rem; '
            f'font-weight:600; font-family:Inter,Helvetica,Arial,sans-serif; '
            f'transition:all 0.15s;" onclick="newsChipToggle(this)">{company}</button>'
        )
    chips_html += '</div>'

    rows_html = ""
    for _, row in df.iterrows():
        company  = str(row["Company"]) if pd.notna(row["Company"]) else ""
        brand    = row["Brand"] if str(row["Brand"]) not in ("N/A", "nan", "") else "N/A"
        news     = row["News"]
        date     = str(row["Date"]) if pd.notna(row["Date"]) else ""
        src_name = str(row["SourceName"]) if pd.notna(row["SourceName"]) else ""
        src_url  = str(row["SourceURL"]) if pd.notna(row["SourceURL"]) else "#"
        color    = COLORS.get(company, "#888")
        news_safe = str(news).replace("&", "&amp;") if pd.notna(news) else ""
        # All rows in the table are direct quotes — render in italics
        news_display = f'<em style="color:#333;">{news_safe}</em>'
        brand_safe = str(brand).replace("&", "&amp;")
        brand_badge = (
            f'<span style="font-size:0.78rem; color:#fff; background:{color}; '
            f'border-radius:4px; padding:2px 7px; white-space:nowrap;">{brand_safe}</span>'
            if brand != "N/A"
            else '<span style="color:#bbb; font-size:0.82rem;">—</span>'
        )
        company_safe = company.replace("&", "&amp;")
        src_name_safe = src_name.replace("&", "&amp;")
        rows_html += (
            f'<tr data-company="{company}">'
            f'<td style="font-weight:600; color:{color}; white-space:nowrap;">{company_safe}</td>'
            f'<td style="text-align:center;">{brand_badge}</td>'
            f'<td style="font-size:0.84rem; line-height:1.6;">{news_display}</td>'
            f'<td style="white-space:nowrap; color:#888; font-size:0.82rem;">{date}</td>'
            f'<td style="white-space:nowrap; font-size:0.82rem;">'
            f'<a href="{src_url}" target="_blank" '
            f'style="color:#555; text-decoration:underline; text-underline-offset:2px;">'
            f'{src_name_safe}</a></td>'
            f'</tr>'
        )

    script = """
    <script>
    if (!window._newsChipReady) {
      window._newsChipReady = true;
      window.newsChipToggle = function(btn) {
        var color = btn.getAttribute('data-color');
        var tclass = btn.getAttribute('data-table');
        var isActive = btn.classList.toggle('nchip-on');
        btn.style.background = isActive ? color : 'transparent';
        btn.style.color = isActive ? '#fff' : color;
        var active = [];
        document.querySelectorAll('.nchip[data-table="' + tclass + '"]').forEach(function(c) {
          if (c.classList.contains('nchip-on')) active.push(c.getAttribute('data-company'));
        });
        document.querySelectorAll('.' + tclass + ' tbody tr').forEach(function(r) {
          r.style.display = (active.length === 0 || active.indexOf(r.getAttribute('data-company')) !== -1) ? '' : 'none';
        });
      };
    }
    </script>
    """

    return f"""
    <style>
      .{table_class} {{
        width: 100%; border-collapse: collapse;
        font-family: Inter, Helvetica, Arial, sans-serif;
        font-size: 0.85rem; color: #111;
      }}
      .{table_class} th {{
        background: #f5f5f5; color: #444; font-weight: 600;
        font-size: 0.76rem; text-transform: uppercase; letter-spacing: 0.05em;
        padding: 10px 14px; text-align: left; border-bottom: 2px solid #e0e0e0;
        white-space: nowrap;
      }}
      .{table_class} td {{
        padding: 11px 14px; border-bottom: 1px solid #f0f0f0;
        vertical-align: top; background: #fff;
      }}
      .{table_class} tr:hover td {{ background: #fafafa; }}
    </style>
    <div style="overflow-x:auto; border:1px solid #eeeeee; border-radius:8px;
                margin-top:8px; padding:14px 16px 0 16px; background:#fff;">
      {chips_html}
      <table class="{table_class}">
        <thead>
          <tr>
            <th style="width:9%;">Company</th>
            <th style="width:11%; text-align:center;">Brand</th>
            <th style="width:54%;">{col3_header}</th>
            <th style="width:9%;">Date</th>
            <th style="width:17%;">Source</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
    {script}
    """

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Hospitality Competitive Intelligence",
    page_icon="H",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global */
    .stApp { background-color: #ffffff; }
    .block-container { padding: 1.5rem 2rem 2rem 2rem; max-width: 1200px; }
    html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; }

    /* Header */
    h1 { font-size: 1.6rem !important; font-weight: 600 !important; color: #1a1a1a !important;
         letter-spacing: -0.02em; margin-bottom: 0.2rem !important; }
    h2 { font-size: 1.15rem !important; font-weight: 600 !important; color: #333 !important;
         margin-top: 1.5rem !important; margin-bottom: 0.5rem !important; }
    h3 { font-size: 0.95rem !important; font-weight: 500 !important; color: #555 !important; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px;
        border-bottom: 2px solid #f0f0f0;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 0.85rem;
        font-weight: 500;
        color: #888;
        padding: 0.6rem 1.2rem;
        border-bottom: 2px solid transparent;
        background: transparent;
    }
    .stTabs [aria-selected="true"] {
        color: #1a1a1a !important;
        border-bottom: 2px solid #1a1a1a !important;
        background: transparent !important;
    }

    /* Metrics */
    [data-testid="stMetric"] {
        background: #fafafa;
        padding: 14px 16px;
        border-radius: 8px;
        border: 1px solid #f0f0f0;
    }
    [data-testid="stMetricLabel"] { font-size: 0.75rem; color: #888; font-weight: 500; }
    [data-testid="stMetricValue"] { font-size: 1.2rem; font-weight: 600; color: #1a1a1a; }

    /* Cards */
    .company-card {
        background: #fafafa;
        border-radius: 10px;
        padding: 20px;
        border: 1px solid #f0f0f0;
        text-align: center;
        margin-bottom: 12px;
    }
    .company-card img { height: 32px; margin-bottom: 8px; }
    .section-divider { border-top: 1px solid #f0f0f0; margin: 1.5rem 0; }

    /* Luxury brand cards */
    .brand-card {
        background: #fafafa;
        border-radius: 8px;
        padding: 12px 16px;
        border: 1px solid #f0f0f0;
        margin-bottom: 8px;
    }
    .brand-name { font-weight: 600; font-size: 0.9rem; color: #1a1a1a; }
    .brand-detail { font-size: 0.78rem; color: #888; margin-top: 2px; }

    /* Hide Streamlit extras */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stDeployButton { display: none; }

    /* Dataframes */
    .stDataFrame { border: 1px solid #f0f0f0; border-radius: 8px; }

    /* Selectbox styling */
    [data-baseweb="select"] > div {
        background-color: #f5f5f5 !important;
        border-color: #e0e0e0 !important;
        color: #111 !important;
    }
    [data-baseweb="select"] [data-testid="stMarkdownContainer"] {
        color: #111 !important;
    }

    /* ── Financial period toggle buttons ── */
    div[data-testid="stButton"] button[data-testid="baseButton-primary"] {
        background-color: #1a1a1a !important;
        border-color: #1a1a1a !important;
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    div[data-testid="stButton"] button[data-testid="baseButton-secondary"] {
        background-color: #f5f5f5 !important;
        border-color: #e0e0e0 !important;
        color: #444 !important;
        font-weight: 500 !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("# Hospitality Competitive Intelligence")

# ── Load Data ────────────────────────────────────────────────────────────────
hotel_kpis = load_hotel_kpis()
hotel_financials_annual = load_hotel_financials_annual()
luxury_brands = load_luxury_brands()
luxury_news = load_luxury_news()
digital_trends = load_digital_trends()
loyalty_historical = load_loyalty_historical()
digital_news = load_digital_news()

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Company Overview",
    "Financial Overview",
    "Luxury Overview",
    "Operational Overview",
    "Guest & Digital Trends",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: COMPANY OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    # Company logos — uniform height
    cols = st.columns(5)
    for i, company in enumerate(COMPANY_NAMES):
        with cols[i]:
            logo_path = get_logo_path(company)
            if os.path.exists(logo_path):
                logo_height = "38px" if company == "Hyatt" else "50px"
                st.markdown(
                    f'<div style="display:flex; align-items:center; justify-content:center; height:60px; margin-bottom:4px;">'
                    f'<img src="data:image/png;base64,{_logo_base64(logo_path)}" style="max-height:{logo_height}; max-width:100%; object-fit:contain;" />'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            info = COMPANIES[company]
            st.markdown(
                f'<p style="text-align:center; font-size:0.78rem; color:#888; margin-top:0px;">'
                f'{info["hq"]}</p>',
                unsafe_allow_html=True,
            )

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # Portfolio Scale chart — dual axes: Properties (left) and Rooms (right)
    st.markdown("## Portfolio Scale")
    latest = hotel_kpis[hotel_kpis["Quarter"] == "Q4 2025"]
    if not latest.empty:
        # Sort by market cap order
        latest = latest.set_index("Company").loc[
            [c for c in COMPANY_NAMES if c in latest["Company"].values]
        ].reset_index()

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=latest["Company"],
            y=latest["Properties"],
            name="# of Properties",
            marker_color=[COLORS.get(c, "#888") for c in latest["Company"]],
            opacity=0.85,
            text=latest["Properties"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else ""),
            textposition="outside",
            yaxis="y",
            offsetgroup=0,
        ))
        fig.add_trace(go.Bar(
            x=latest["Company"],
            y=latest["System-wide Rooms"],
            name="# of Rooms",
            marker_color=[COLORS.get(c, "#888") for c in latest["Company"]],
            opacity=0.4,
            text=latest["System-wide Rooms"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else ""),
            textposition="outside",
            yaxis="y2",
            offsetgroup=1,
        ))

        fig.update_layout(
            template="none",
            font=dict(family="Inter, sans-serif", size=13, color="#111111"),
            barmode="group",
            yaxis=dict(
                title="# of Properties",
                gridcolor="#f0f0f0", showline=True, linecolor="#e0e0e0",
                title_font=dict(color="#111111"), tickfont=dict(color="#111111"),
            ),
            yaxis2=dict(
                title="# of Rooms",
                overlaying="y", side="right",
                gridcolor="#f0f0f0", showline=True, linecolor="#e0e0e0",
                title_font=dict(color="#111111"), tickfont=dict(color="#111111"),
                range=[0, latest["System-wide Rooms"].max() * 1.25],
            ),
            margin=dict(l=60, r=60, t=30, b=40),
            height=420,
            plot_bgcolor="white",
            paper_bgcolor="white",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                font=dict(color="#111111"),
            ),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # Market data section
    st.markdown("## Market Performance")
    with st.spinner("Loading market data..."):
        company_info = get_company_info(TICKERS)

    if not company_info.empty:
        # Stock price row with title
        st.markdown("### Current Stock Price")
        price_cols = st.columns(5)
        for i, company in enumerate(COMPANY_NAMES):
            with price_cols[i]:
                row = company_info[company_info["Company"] == company]
                if not row.empty:
                    price = row.iloc[0].get("Price")
                    ticker = TICKERS.get(company, "")
                    currency = "€" if ticker.endswith(".PA") else "$"
                    st.metric(company, f"{currency}{price:,.2f}" if pd.notna(price) else "N/A")
        if "_fetched_at" in company_info.columns:
            _ft = company_info.iloc[0]["_fetched_at"]
            st.caption(f"Last updated: {_ft.strftime('%b %d, %Y %I:%M %p')}")

        # Market cap row with title
        st.markdown("### Market Capitalization")
        mcap_cols = st.columns(5)
        for i, company in enumerate(COMPANY_NAMES):
            with mcap_cols[i]:
                row = company_info[company_info["Company"] == company]
                if not row.empty:
                    mcap = row.iloc[0].get("Market Cap ($B)")
                    st.metric(company, f"${mcap:,.1f}B" if (pd.notna(mcap) and mcap > 0) else "N/A")

    # Stock chart with time horizon selector
    st.markdown("### Stock Performance")
    period_options = {"YTD": "ytd", "1 Year": "1y", "3 Years": "3y", "5 Years": "5y"}
    selected_period = st.selectbox(
        "Time Horizon", list(period_options.keys()), index=1, label_visibility="collapsed",
        key="stock_period",
    )
    period_value = period_options[selected_period]

    with st.spinner("Loading stock data..."):
        stock_data = get_stock_data(TICKERS, period=period_value)

    if not stock_data.empty:
        fig = normalized_stock_chart(
            stock_data,
            title=f"{selected_period} Relative Performance (Indexed to 100)",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Returns matching the selected period
        period_returns = calculate_period_returns(stock_data)
        if period_returns:
            ret_cols = st.columns(5)
            for i, company in enumerate(COMPANY_NAMES):
                with ret_cols[i]:
                    ret = period_returns.get(company)
                    if ret is not None:
                        st.metric(f"{company} ({selected_period})", f"{ret:+.1f}%")

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # Valuation metrics table
    st.markdown("## Valuation Metrics")
    if not company_info.empty:
        val_cols = ["Company", "P/E Ratio", "Forward P/E", "EV/EBITDA", "Dividend Yield (%)", "52W High", "52W Low"]
        available = [c for c in val_cols if c in company_info.columns]
        # Order by market cap
        display_df = company_info[available].copy()
        display_df["Company"] = pd.Categorical(display_df["Company"], categories=COMPANY_NAMES, ordered=True)
        display_df = display_df.sort_values("Company").set_index("Company")

        for col in display_df.columns:
            if col != display_df.index.name:
                display_df[col] = pd.to_numeric(display_df[col], errors='coerce')

        # Render as styled HTML table
        table_html = display_df.to_html(
            float_format=lambda x: f"{x:.2f}" if pd.notna(x) else "N/A",
            na_rep="N/A",
        )
        st.markdown(
            f'<div style="overflow-x:auto;">'
            f'<style>'
            f'.val-table {{ width:100%; border-collapse:collapse; font-size:0.85rem; font-family:Inter,sans-serif; }}'
            f'.val-table th {{ background:#f5f5f5; color:#111; font-weight:600; padding:10px 14px; text-align:left; border-bottom:2px solid #e0e0e0; }}'
            f'.val-table td {{ background:#fafafa; color:#111; padding:9px 14px; border-bottom:1px solid #eee; }}'
            f'.val-table tr:hover td {{ background:#f0f0f0; }}'
            f'</style>'
            f'{table_html.replace("<table", "<table class=val-table")}'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.caption("P/E, Forward P/E, EV/EBITDA, Dividend Yield as of FY2025. 52W High/Low and stock prices are live. Accor price and 52W range in EUR (Paris: AC.PA).")

    render_sources("company_overview")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: FINANCIAL OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    # ── Period toggle — explicit buttons (reliable cross-browser) ──
    if "fin_view_mode" not in st.session_state:
        st.session_state["fin_view_mode"] = "Quarterly"

    _is_qtr_now = (st.session_state["fin_view_mode"] == "Quarterly")
    _tc1, _tc2, _trest = st.columns([0.13, 0.13, 0.74])
    with _tc1:
        if st.button(
            "Quarterly",
            type="primary" if _is_qtr_now else "secondary",
            key="btn_qtr",
            use_container_width=True,
        ):
            st.session_state["fin_view_mode"] = "Quarterly"
            st.rerun()
    with _tc2:
        if st.button(
            "Annually",
            type="primary" if not _is_qtr_now else "secondary",
            key="btn_ann",
            use_container_width=True,
        ):
            st.session_state["fin_view_mode"] = "Annually"
            st.rerun()

    view_mode = st.session_state["fin_view_mode"]

    CURR_QUARTERS = QUARTERS[-4:]
    PREV_QUARTERS = [f"{q.split()[0]} {int(q.split()[1]) - 1}" for q in CURR_QUARTERS]
    ANNUAL_YEARS  = [2022, 2023, 2024, 2025]

    is_quarterly = (view_mode == "Quarterly")

    if is_quarterly:
        df_curr      = hotel_kpis[hotel_kpis["Quarter"].isin(CURR_QUARTERS)].copy()
        df_prev      = hotel_kpis[hotel_kpis["Quarter"].isin(PREV_QUARTERS)].copy()
        period_col   = "Quarter"
        period_order = CURR_QUARTERS
        chart_prefix = "Quarterly"
    else:
        df_curr      = hotel_financials_annual[
            hotel_financials_annual["Year"].isin(ANNUAL_YEARS)
        ].copy()
        df_curr["Year"] = df_curr["Year"].astype(str)
        df_prev      = None
        period_col   = "Year"
        period_order = [str(y) for y in ANNUAL_YEARS]
        chart_prefix = "Annual"

    # ── Four combo charts (growth lines on annual only) ───────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"## {chart_prefix} Revenue")
        fig = financial_combo_chart(
            df_curr, "Revenue ($M)", "Revenue ($M)",
            period_col, period_order, df_prev,
            growth_label="YoY Growth (%)", height=340,
            show_growth=not is_quarterly,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown(f"## {chart_prefix} Adjusted EPS")
        fig = financial_combo_chart(
            df_curr, "Adj. EPS", "Adjusted EPS ($)",
            period_col, period_order, df_prev,
            growth_label="YoY Growth (%)", height=340,
            show_growth=not is_quarterly,
        )
        st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"## {chart_prefix} Fee Revenue")
        fig = financial_combo_chart(
            df_curr, "Fee Revenue ($M)", "Fee Revenue ($M)",
            period_col, period_order, df_prev,
            growth_label="YoY Growth (%)", height=340,
            show_growth=not is_quarterly,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown(f"## {chart_prefix} Adj. EBITDA")
        fig = financial_combo_chart(
            df_curr, "Adj. EBITDA ($M)", "Adj. EBITDA ($M)",
            period_col, period_order, df_prev,
            growth_label="YoY Growth (%)", height=340,
            show_growth=not is_quarterly,
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # ── Financial Summary ─────────────────────────────────────────────────────
    st.markdown("## Financial Summary")

    _avail_years = sorted(hotel_financials_annual["Year"].unique(), reverse=True)
    _sel_col, _ = st.columns([1, 3])
    with _sel_col:
        selected_year = st.selectbox(
            "Fiscal Year", options=_avail_years, index=0, key="fin_summary_year",
        )

    _yr   = hotel_financials_annual[hotel_financials_annual["Year"] == selected_year]
    _prev = hotel_financials_annual[hotel_financials_annual["Year"] == selected_year - 1]

    _metrics = [
        ("Revenue ($M)",    "Revenue",  "{:,.0f}"),
        ("Fee Revenue ($M)","Fee Rev.", "{:,.0f}"),
        ("Adj. EBITDA ($M)","EBITDA",   "{:,.0f}"),
        ("Adj. EPS",        "EPS",      "{:.2f}"),
        ("Net Income ($M)", "Net Inc.", "{:,.0f}"),
    ]

    def _fmt_yoy(curr_val, prior_df, company, col):
        if not pd.notna(curr_val):
            return '<span style="color:#bbb;">—</span>'
        row = prior_df[prior_df["Company"] == company]
        if row.empty:
            return '<span style="color:#bbb;">—</span>'
        pv = row.iloc[0][col]
        if not pd.notna(pv) or pv == 0:
            return '<span style="color:#bbb;">—</span>'
        g = (curr_val - pv) / abs(pv) * 100
        color = "#2a7a50" if g >= 0 else "#b03030"
        sign  = "+" if g >= 0 else ""
        return f'<span style="color:{color}; font-weight:600;">{sign}{g:.1f}%</span>'

    # Header
    _th = "".join(
        f'<th style="text-align:right;">{lbl}</th>'
        f'<th style="text-align:center; color:#999; font-weight:500; font-size:0.74rem;">YoY</th>'
        for _, lbl, _ in _metrics
    )
    _header = f'<tr><th style="text-align:left;">Company</th>{_th}</tr>'

    # Rows
    _rows = ""
    for company in COMPANY_NAMES:
        crow = _yr[_yr["Company"] == company]
        if crow.empty:
            continue
        color = COLORS.get(company, "#888")
        _td = ""
        for col, _, fmt in _metrics:
            val = crow.iloc[0][col]
            fmt_val = fmt.format(val) if pd.notna(val) else "N/A"
            _td += (
                f'<td style="text-align:right; font-variant-numeric:tabular-nums;">'
                f'{fmt_val}</td>'
                f'<td style="text-align:center;">{_fmt_yoy(val, _prev, company, col)}</td>'
            )
        _rows += (
            f'<tr>'
            f'<td style="font-weight:600; color:{color}; white-space:nowrap;">{company}</td>'
            f'{_td}'
            f'</tr>'
        )

    _summary_html = f"""
    <style>
      .fin-summary {{
        width: 100%;
        border-collapse: collapse;
        font-family: Inter, Helvetica, Arial, sans-serif;
        font-size: 0.85rem;
        color: #111;
      }}
      .fin-summary th {{
        background: #f2f2f2;
        color: #555;
        font-weight: 600;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        padding: 10px 14px;
        border-bottom: 2px solid #e0e0e0;
        white-space: nowrap;
      }}
      .fin-summary td {{
        background: #f9f9f9;
        padding: 10px 14px;
        border-bottom: 1px solid #eeeeee;
        vertical-align: middle;
      }}
      .fin-summary tr:last-child td {{ border-bottom: none; }}
      .fin-summary tr:hover td {{ background: #f2f2f2; }}
    </style>
    <div style="border: 1px solid #e8e8e8; border-radius: 10px; overflow: hidden; margin-top: 6px;">
      <div style="background:#f2f2f2; padding:10px 14px; border-bottom:1px solid #e0e0e0;">
        <span style="font-size:0.8rem; font-weight:600; color:#555; text-transform:uppercase;
                     letter-spacing:0.05em;">FY {selected_year}</span>
        {'<span style="font-size:0.78rem; color:#aaa; margin-left:10px;">YoY vs FY ' + str(selected_year - 1) + '</span>' if selected_year > min(_avail_years) else '<span style="font-size:0.78rem; color:#aaa; margin-left:10px;">No prior year for comparison</span>'}
      </div>
      <table class="fin-summary">
        <thead>{_header}</thead>
        <tbody>{_rows}</tbody>
      </table>
    </div>
    """
    st.markdown(_summary_html, unsafe_allow_html=True)

    render_sources("financial_overview")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: LUXURY OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    # ── Disclaimer note ───────────────────────────────────────────────────────
    st.markdown(
        '<div style="background:#fffbf0; border:1px solid #f0e6c8; border-radius:8px; '
        'padding:10px 16px; margin-bottom:20px; font-size:0.82rem; color:#7a6a3a;">'
        '<em>* Luxury brands listed are self-identified by each company in their '
        'public filings, investor presentations, and brand portfolios. Brand tier '
        'classifications reflect each company\'s own segmentation and may differ '
        'from third-party definitions of luxury.</em>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Brand cards by company ────────────────────────────────────────────────
    for company in COMPANY_NAMES:
        color = COLORS[company]
        company_brands = luxury_brands[luxury_brands["Company"] == company]
        if company_brands.empty:
            continue

        total_props = company_brands["Properties"].sum()
        total_rooms = company_brands["Rooms"].sum()

        st.markdown(
            f'<div style="border-left: 4px solid {color}; padding: 8px 16px; '
            f'margin: 20px 0 12px 0; background: #fafafa; border-radius: 0 8px 8px 0;">'
            f'<span style="font-weight: 600; font-size: 1.05rem; color: {color};">{company}</span>'
            f'<span style="color: #888; font-size: 0.82rem; margin-left: 16px;">'
            f'{total_props} luxury properties &middot; {total_rooms:,} rooms</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        n_brands = len(company_brands)
        cols_per_row = min(4, n_brands)
        brand_cols = st.columns(cols_per_row)

        for j, (_, brand) in enumerate(company_brands.iterrows()):
            with brand_cols[j % cols_per_row]:
                st.markdown(
                    f'<div class="brand-card">'
                    f'<div class="brand-name">{brand["Brand"]}</div>'
                    f'<div class="brand-detail">{brand["Properties"]} properties &middot; '
                    f'{brand["Rooms"]:,} rooms</div>'
                    f'<div class="brand-detail" style="margin-top:4px; font-style:italic;">'
                    f'{brand["Description"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # ── Luxury News & Earnings Tracker ────────────────────────────────────────
    st.markdown("## Luxury News & Earnings Tracker")

    # ── 2025–2026 direct quotes only ───────────────────────────────────────────
    _lux_display = luxury_news[
        luxury_news["Date"].apply(lambda d: _year_from_date(d) >= 2025) &
        luxury_news["News"].apply(_is_direct_quote)
    ]

    st.markdown(
        _news_table_html(_lux_display, "lux-news-table", "Earnings / Press Release Quote"),
        unsafe_allow_html=True,
    )

    render_sources("luxury_overview")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: OPERATIONAL OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    _Q25 = QUARTERS[-4:]
    _Q24 = [f"{q.split()[0]} {int(q.split()[1]) - 1}" for q in _Q25]
    _q4  = get_latest_per_company(hotel_kpis).copy()

    _OP_THEME = dict(
        template="none",
        font=dict(family="Inter, Helvetica, Arial, sans-serif", size=13, color="#111"),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=60, r=70, t=30, b=40),
    )
    _AXIS = dict(gridcolor="#ebebeb", showline=True, linecolor="#ccc",
                 tickfont=dict(color="#111", size=12))

    # ── Full-width RevPAR combo chart (rolling 4Q avg vs prior 4Q avg) ───────
    _revpar_label = f"{_Q25[0]}–{_Q25[-1]}"
    st.markdown(f"## RevPAR — Rolling 4 Quarters ({_revpar_label})")

    _fy25 = hotel_kpis[hotel_kpis["Quarter"].isin(_Q25)]
    _fy24 = hotel_kpis[hotel_kpis["Quarter"].isin(_Q24)]
    _rp25 = _fy25.groupby("Company")["RevPAR"].mean()
    _rp24 = _fy24.groupby("Company")["RevPAR"].mean()
    _rp_yoy = ((_rp25 - _rp24) / _rp24 * 100).round(1)
    _cos = [c for c in COMPANY_NAMES if c in _rp25.index]

    fig_revpar = go.Figure()
    fig_revpar.add_trace(go.Bar(
        x=_cos, y=[float(_rp25[c]) for c in _cos],
        name=f"Avg RevPAR ({_revpar_label})",
        marker_color=[COLORS.get(c, "#888") for c in _cos],
        opacity=0.85, yaxis="y",
    ))
    _g = [float(_rp_yoy[c]) if c in _rp_yoy.index else None for c in _cos]
    fig_revpar.add_trace(go.Scatter(
        x=_cos, y=_g, name="YoY Growth %",
        mode="lines+markers+text",
        line=dict(color="#555", width=2.5, dash="dot"),
        marker=dict(size=11, color=[COLORS.get(c, "#888") for c in _cos],
                    line=dict(color="#333", width=1.5)),
        text=[f"{v:+.1f}%" if (v is not None and v == v) else "" for v in _g],
        textposition="top center", textfont=dict(size=11, color="#333"),
        yaxis="y2",
    ))
    fig_revpar.update_layout(
        **_OP_THEME, height=440, barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=12, color="#111")),
        xaxis={**_AXIS, "tickfont": dict(color="#111", size=13)},
        yaxis=dict(**_AXIS, title="Avg RevPAR ($)",
                   title_font=dict(color="#111", size=13,
                                   family="Inter, Helvetica, Arial, sans-serif")),
        yaxis2=dict(title="YoY Growth (%)", overlaying="y", side="right",
                    showgrid=False, showline=True, linecolor="#ddd",
                    tickfont=dict(color="#888", size=11), ticksuffix="%",
                    title_font=dict(color="#888", size=12,
                                    family="Inter, Helvetica, Arial, sans-serif"),
                    zeroline=True, zerolinecolor="#ddd", zerolinewidth=1),
    )
    st.plotly_chart(fig_revpar, use_container_width=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # ── ADR & Occupancy (inline horizontal bars) ──────────────────────────────
    col1, col2 = st.columns(2)

    def _horiz_bar(df_sorted, x_col, height=280):
        fig = go.Figure()
        for _, r in df_sorted.iterrows():
            co = str(r["Company"])
            fig.add_trace(go.Bar(
                x=[float(r[x_col])], y=[co],
                name=co, orientation="h",
                marker_color=COLORS.get(co, "#888"), opacity=0.85,
                showlegend=False,
            ))
        fig.update_layout(
            **_OP_THEME, height=height, showlegend=False,
            xaxis=dict(**_AXIS), yaxis=dict(**_AXIS, showgrid=False),
        )
        return fig

    with col1:
        st.markdown("## ADR — Q4 2025")
        if not _q4.empty:
            st.plotly_chart(
                _horiz_bar(_q4.sort_values("ADR"), "ADR"),
                use_container_width=True,
            )

    with col2:
        st.markdown("## Occupancy — Q4 2025")
        if not _q4.empty:
            st.plotly_chart(
                _horiz_bar(_q4.sort_values("Occupancy %"), "Occupancy %"),
                use_container_width=True,
            )

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # ── ADR vs Occupancy scatter (inline) ─────────────────────────────────────
    st.markdown("## ADR vs Occupancy — Q4 2025")
    if not _q4.empty:
        _max_rooms = float(_q4["System-wide Rooms"].max())
        if not pd.notna(_max_rooms) or _max_rooms == 0:
            _max_rooms = 1
        fig_sc = go.Figure()
        for _, r in _q4.iterrows():
            co = str(r["Company"])
            _sz_raw = float(r["System-wide Rooms"]) / _max_rooms * 55 if pd.notna(r["System-wide Rooms"]) else 0
            sz = max(14, int(_sz_raw) if pd.notna(_sz_raw) and _sz_raw == _sz_raw else 20)
            fig_sc.add_trace(go.Scatter(
                x=[float(r["Occupancy %"])], y=[float(r["ADR"])],
                mode="markers+text", name=co,
                text=[co], textposition="top center",
                textfont=dict(color="#111", size=12),
                marker=dict(color=COLORS.get(co, "#888"), size=sz, opacity=0.82,
                            line=dict(color="#555", width=1)),
                showlegend=False,
            ))
        fig_sc.update_layout(
            **_OP_THEME, height=400,
            xaxis=dict(**_AXIS, title="Occupancy (%)",
                       title_font=dict(color="#111", size=13)),
            yaxis=dict(**_AXIS, title="ADR ($)",
                       title_font=dict(color="#111", size=13)),
        )
        st.plotly_chart(fig_sc, use_container_width=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # ── Pipeline & Net Unit Growth ────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("## Development Pipeline — Q4 2025")
        if not _q4.empty:
            st.plotly_chart(
                _horiz_bar(_q4.sort_values("Pipeline Rooms"), "Pipeline Rooms"),
                use_container_width=True,
            )

    with col2:
        st.markdown("## Net Unit Growth — FY 2025")
        _kpis_q25 = hotel_kpis[hotel_kpis["Quarter"].isin(_Q25)]
        fig_nug = go.Figure()
        _x_ord = {q: i for i, q in enumerate(_Q25)}
        for co in COMPANY_NAMES:
            _cd = _kpis_q25[_kpis_q25["Company"] == co].copy()
            _cd["_o"] = _cd["Quarter"].map(_x_ord)
            _cd = _cd.sort_values("_o")
            if _cd.empty:
                continue
            fig_nug.add_trace(go.Scatter(
                x=_cd["Quarter"].tolist(), y=_cd["Net Unit Growth %"].tolist(),
                name=co, mode="lines+markers",
                line=dict(color=COLORS.get(co, "#888"), width=2.5),
                marker=dict(size=7, color=COLORS.get(co, "#888")),
            ))
        fig_nug.update_layout(
            **_OP_THEME, height=280,
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="right", x=1, font=dict(size=11)),
            xaxis=dict(**_AXIS), yaxis=dict(**_AXIS, title="Net Unit Growth (%)"),
        )
        st.plotly_chart(fig_nug, use_container_width=True)

    render_sources("operational_overview")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5: GUEST & DIGITAL TRENDS
# ═══════════════════════════════════════════════════════════════════════════════
with tab5:
    # ── Loyalty Membership — Annual Line Chart (2022–2025) ────────────────────
    st.markdown("## Loyalty Membership Growth (2022–2025)")

    _DIG_THEME = dict(
        template="none",
        font=dict(family="Inter, Helvetica, Arial, sans-serif", size=13, color="#111"),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=60, r=20, t=30, b=40),
    )
    _DIG_AXIS = dict(gridcolor="#ebebeb", showline=True, linecolor="#ccc",
                     tickfont=dict(color="#111", size=12))

    fig_loyalty = go.Figure()
    for _co in COMPANY_NAMES:
        _lh = loyalty_historical[loyalty_historical["Company"] == _co].sort_values("Year")
        if _lh.empty:
            continue
        fig_loyalty.add_trace(go.Scatter(
            x=_lh["Year"].astype(str).tolist(),
            y=_lh["Loyalty Members (M)"].tolist(),
            name=_co, mode="lines+markers",
            line=dict(color=COLORS.get(_co, "#888"), width=2.5),
            marker=dict(size=9, color=COLORS.get(_co, "#888")),
        ))
    fig_loyalty.update_layout(
        **_DIG_THEME, height=360,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1, font=dict(size=12, color="#111")),
        xaxis=dict(**_DIG_AXIS),
        yaxis=dict(**_DIG_AXIS, title="Members (Millions)",
                   title_font=dict(color="#111", size=13,
                                   family="Inter, Helvetica, Arial, sans-serif")),
    )
    st.plotly_chart(fig_loyalty, use_container_width=True)

    # ── FY 2025 Loyalty metric boxes ──────────────────────────────────────────
    st.markdown("### FY 2025 Loyalty Members")
    _loy_mcols = st.columns(5)
    for _i, _co in enumerate(COMPANY_NAMES):
        with _loy_mcols[_i]:
            _r25 = loyalty_historical[
                (loyalty_historical["Company"] == _co) & (loyalty_historical["Year"] == 2025)
            ]
            _r24 = loyalty_historical[
                (loyalty_historical["Company"] == _co) & (loyalty_historical["Year"] == 2024)
            ]
            if not _r25.empty:
                _m25 = float(_r25.iloc[0]["Loyalty Members (M)"])
                _delta = None
                if not _r24.empty:
                    _m24 = float(_r24.iloc[0]["Loyalty Members (M)"])
                    _pct = (_m25 - _m24) / _m24 * 100
                    sign = "+" if _pct >= 0 else ""
                    _delta = f"{sign}{_pct:.1f}% YoY"
                st.metric(_co, f"{_m25:.0f}M", delta=_delta)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # ── Digital Engagement — Q4 2025 ─────────────────────────────────────────
    st.markdown("## Digital Engagement — Q4 2025")

    st.markdown(
        '<div style="background:#f5f7fa; border:1px solid #dde4ef; border-radius:8px; '
        'padding:12px 18px; margin-bottom:18px; font-size:0.82rem; color:#555; line-height:1.75;">'
        '<strong>Metric Definitions &amp; Notes</strong><br>'
        '<strong>Digital Check-in %</strong> — Estimated share of check-ins completed via '
        'mobile app or digital kiosk, bypassing the traditional front desk. '
        'Figures are management estimates disclosed in earnings calls and investor presentations.<br>'
        '<strong>Direct Booking %</strong> — Estimated share of room nights booked directly '
        'through the company\'s own website or app (excluding OTAs and third-party channels). '
        'Definitions vary slightly by company; some report channel mix for loyalty members only.<br>'
        '<em>Exact disclosure methodologies differ across companies; figures are indicative '
        'and not directly comparable across brands.</em>'
        '</div>',
        unsafe_allow_html=True,
    )

    _q4_dig = digital_trends[digital_trends["Quarter"] == "Q4 2025"]
    if not _q4_dig.empty:
        for _, _row in _q4_dig.iterrows():
            _co = _row["Company"]
            _col = COLORS.get(_co, "#888")
            st.markdown(
                f'<div style="border-left: 4px solid {_col}; padding: 10px 16px; '
                f'margin: 8px 0; background: #fafafa; border-radius: 0 8px 8px 0;">'
                f'<span style="font-weight: 600; color: {_col};">{_co}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            _mc = st.columns(4)
            with _mc[0]:
                st.metric("App Rating", f"{_row['Mobile App Rating']}/5.0")
            with _mc[1]:
                st.metric("Digital Check-in", f"{_row['Digital Check-in %']}%")
            with _mc[2]:
                st.metric("Direct Booking", f"{_row['Direct Booking %']}%")
            with _mc[3]:
                st.caption("Key Initiative")
                st.markdown(f"*{_row['Key Initiative']}*")

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # ── Digital, Personalization & AI News ───────────────────────────────────
    st.markdown("## Digital, Personalization & AI News")

    # ── 2025–2026 direct quotes only ───────────────────────────────────────────
    _dig_display = digital_news[
        digital_news["Date"].apply(lambda d: _year_from_date(d) >= 2025) &
        digital_news["News"].apply(_is_direct_quote)
    ]

    st.markdown(
        _news_table_html(_dig_display, "dig-news-table", "Digital / AI Quote"),
        unsafe_allow_html=True,
    )

    render_sources("digital_trends")
