"""Load and merge data from CSVs and live sources."""

import pandas as pd
import os
import streamlit as st
from config import QUARTERS

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

_HOTEL_KPI_NUMS = [
    "Revenue ($M)", "Fee Revenue ($M)", "Adj. EBITDA ($M)", "Adj. EPS",
    "Net Income ($M)", "RevPAR", "ADR", "Occupancy %", "Properties",
    "System-wide Rooms", "Pipeline Rooms", "Net Unit Growth %", "Loyalty Members (M)",
]

_FINANCIALS_NUMS = [
    "Year", "Revenue ($M)", "Fee Revenue ($M)", "Adj. EBITDA ($M)",
    "Adj. EPS", "Net Income ($M)",
]

_DIGITAL_NUMS = [
    "Loyalty Members (M)", "Mobile App Rating", "Digital Check-in %",
    "Direct Booking %",
]

_LOYALTY_NUMS = ["Year", "Loyalty Members (M)"]


def _coerce(df, cols):
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(ttl=600)
def load_hotel_kpis() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "hotel_kpis.csv")
    df = pd.read_csv(path, encoding="utf-8").dropna(how="all")
    return _coerce(df, _HOTEL_KPI_NUMS)


@st.cache_data(ttl=600)
def load_hotel_financials_annual() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "hotel_financials_annual.csv")
    df = pd.read_csv(path, encoding="utf-8").dropna(how="all")
    return _coerce(df, _FINANCIALS_NUMS)


@st.cache_data(ttl=600)
def load_strategic_intel() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "strategic_intel.csv")
    return pd.read_csv(path, encoding="utf-8").dropna(how="all")


@st.cache_data(ttl=600)
def load_luxury_news() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "luxury_news.csv")
    return pd.read_csv(path, encoding="utf-8").dropna(how="all")


@st.cache_data(ttl=600)
def load_luxury_brands() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "luxury_brands.csv")
    df = pd.read_csv(path, encoding="utf-8").dropna(how="all")
    for col in ("Properties", "Rooms"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    return df


@st.cache_data(ttl=600)
def load_digital_trends() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "digital_trends.csv")
    df = pd.read_csv(path, encoding="utf-8").dropna(how="all")
    return _coerce(df, _DIGITAL_NUMS)


@st.cache_data(ttl=600)
def load_loyalty_historical() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "loyalty_historical.csv")
    df = pd.read_csv(path, encoding="utf-8").dropna(how="all")
    return _coerce(df, _LOYALTY_NUMS)


@st.cache_data(ttl=600)
def load_digital_news() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "digital_news.csv")
    return pd.read_csv(path, encoding="utf-8").dropna(how="all")


def get_latest_quarter(df: pd.DataFrame) -> pd.DataFrame:
    available = [q for q in QUARTERS if q in df["Quarter"].values]
    if not available:
        return df
    return df[df["Quarter"] == available[-1]]


def get_latest_per_company(df: pd.DataFrame) -> pd.DataFrame:
    """Return each company's most recent quarter that has actual data.

    Used during earnings season when not all companies have reported yet —
    shows each company at its own latest reported quarter rather than forcing
    all companies to Q1 2026 when only some have filed.
    """
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    result = []
    for company in df["Company"].unique():
        co = df[df["Company"] == company]
        for q in reversed(QUARTERS):
            qrow = co[co["Quarter"] == q]
            if not qrow.empty and qrow[numeric_cols].notna().any(axis=None):
                result.append(qrow)
                break
    return pd.concat(result) if result else df


def get_logo_path(company: str) -> str:
    return os.path.join(DATA_DIR, "logos", f"{company.lower()}.png")
