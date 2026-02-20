"""Load and merge data from CSVs and live sources."""

import pandas as pd
import os
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


@st.cache_data(ttl=600)
def load_hotel_kpis() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "hotel_kpis.csv")
    return pd.read_csv(path)


@st.cache_data(ttl=600)
def load_hotel_financials_annual() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "hotel_financials_annual.csv")
    return pd.read_csv(path)


@st.cache_data(ttl=600)
def load_strategic_intel() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "strategic_intel.csv")
    return pd.read_csv(path)


@st.cache_data(ttl=600)
def load_luxury_news() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "luxury_news.csv")
    return pd.read_csv(path)


@st.cache_data(ttl=600)
def load_luxury_brands() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "luxury_brands.csv")
    return pd.read_csv(path)


@st.cache_data(ttl=600)
def load_digital_trends() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "digital_trends.csv")
    return pd.read_csv(path)


@st.cache_data(ttl=600)
def load_loyalty_historical() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "loyalty_historical.csv")
    return pd.read_csv(path)


@st.cache_data(ttl=600)
def load_digital_news() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "digital_news.csv")
    return pd.read_csv(path)


def get_latest_quarter(df: pd.DataFrame) -> pd.DataFrame:
    quarters_order = ["Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025"]
    available = [q for q in quarters_order if q in df["Quarter"].values]
    if not available:
        return df
    return df[df["Quarter"] == available[-1]]


def get_logo_path(company: str) -> str:
    return os.path.join(DATA_DIR, "logos", f"{company.lower()}.png")
