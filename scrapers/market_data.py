"""Fetch market data via direct Yahoo Finance chart API requests.

Uses the v8/finance/chart endpoint which is reliably accessible from cloud
environments. Valuation metrics (P/E, EV/EBITDA, market cap) are loaded from
data/market_metrics.csv and updated manually each quarter from earnings reports,
since Yahoo's quoteSummary endpoint is rate-limited on cloud IPs.
"""

import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
import streamlit as st

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
}


def _chart(ticker: str, period: str = "1y", interval: str = "1d") -> dict | None:
    """Call Yahoo Finance v8 chart API. Returns result dict or None on failure."""
    try:
        r = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
            headers=_HEADERS,
            params={"interval": interval, "range": period},
            timeout=12,
        )
        if r.status_code == 200:
            result = r.json()["chart"]["result"]
            return result[0] if result else None
    except Exception:
        pass
    return None


def _price_from_yf(ticker: str) -> dict:
    """Fallback: get price/52W data from yfinance fast_info."""
    out = {"Price": None, "52W High": None, "52W Low": None}
    try:
        fi = yf.Ticker(ticker).fast_info
        if getattr(fi, "last_price", None):
            out["Price"]    = float(fi.last_price)
            out["52W High"] = float(fi.year_high) if getattr(fi, "year_high", None) else None
            out["52W Low"]  = float(fi.year_low)  if getattr(fi, "year_low",  None) else None
    except Exception:
        pass
    return out


@st.cache_data(ttl=3600)
def get_stock_data(tickers: dict, period: str = "1y") -> pd.DataFrame:
    """Fetch stock price history for all companies.

    Primary: Yahoo Finance v8 chart API (direct HTTP).
    Fallback: yfinance download().
    Returns DataFrame with columns: Date, Company, Ticker, Close, Volume
    """
    frames = []
    for company, ticker in tickers.items():
        df = None

        # Primary: chart API
        result = _chart(ticker, period=period)
        if result:
            timestamps = result.get("timestamp", [])
            quote = result.get("indicators", {}).get("quote", [{}])[0]
            closes = quote.get("close", [])
            volumes = quote.get("volume", [])
            if timestamps and closes:
                df = pd.DataFrame({
                    "Date": pd.to_datetime(timestamps, unit="s", utc=True).tz_localize(None),
                    "Close": closes,
                    "Volume": volumes if volumes else [None] * len(timestamps),
                })
                df = df.dropna(subset=["Close"])

        # Fallback: yfinance download
        if df is None or df.empty:
            try:
                hist = yf.download(ticker, period=period, progress=False, auto_adjust=True)
                if not hist.empty:
                    df = hist[["Close", "Volume"]].reset_index()
                    df.columns = ["Date", "Close", "Volume"]
                    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
            except Exception:
                pass

        if df is None or df.empty:
            continue
        df["Company"] = company
        df["Ticker"] = ticker
        frames.append(df)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


@st.cache_data(ttl=3600)
def get_company_info(tickers: dict) -> pd.DataFrame:
    """Return live price / 52W range merged with static valuation metrics.

    Live data (price, 52W high/low) comes from Yahoo Finance chart API.
    Market cap, P/E, Forward P/E, EV/EBITDA, Dividend Yield come from
    data/market_metrics.csv (updated each quarter).
    """
    fetch_time = datetime.now()

    # Load static valuation metrics
    try:
        static_df = pd.read_csv("data/market_metrics.csv")
    except Exception:
        static_df = pd.DataFrame()

    rows = []
    for company, ticker in tickers.items():
        row = {"Company": company, "Ticker": ticker,
               "Price": None, "52W High": None, "52W Low": None}

        # Primary: chart API
        result = _chart(ticker, period="5d")
        if result:
            meta = result.get("meta", {})
            price = meta.get("regularMarketPrice")
            hi    = meta.get("fiftyTwoWeekHigh")
            lo    = meta.get("fiftyTwoWeekLow")
            if price: row["Price"]    = float(price)
            if hi:    row["52W High"] = float(hi)
            if lo:    row["52W Low"]  = float(lo)

        # Fallback: yfinance fast_info
        if row["Price"] is None:
            fb = _price_from_yf(ticker)
            row.update({k: v for k, v in fb.items() if v is not None})

        rows.append(row)

    df = pd.DataFrame(rows)

    # Merge static metrics (Market Cap, P/E, Forward P/E, EV/EBITDA, Dividend Yield)
    if not static_df.empty and "Company" in static_df.columns:
        df = df.merge(static_df, on="Company", how="left")

    df["_fetched_at"] = fetch_time
    return df


def calculate_ytd_returns(stock_data: pd.DataFrame) -> dict:
    """Calculate YTD returns from stock price data."""
    if stock_data.empty:
        return {}
    returns = {}
    current_year = datetime.now().year
    for company in stock_data["Company"].unique():
        company_data = stock_data[stock_data["Company"] == company].sort_values("Date")
        ytd_data = company_data[company_data["Date"].dt.year == current_year]
        if ytd_data.empty:
            continue
        start_price = ytd_data.iloc[0]["Close"]
        end_price   = ytd_data.iloc[-1]["Close"]
        returns[company] = ((end_price - start_price) / start_price) * 100
    return returns


def calculate_period_returns(stock_data: pd.DataFrame) -> dict:
    """Calculate returns over the full period of the provided stock data."""
    if stock_data.empty:
        return {}
    returns = {}
    for company in stock_data["Company"].unique():
        company_data = stock_data[stock_data["Company"] == company].sort_values("Date")
        if len(company_data) < 2:
            continue
        start_price = company_data.iloc[0]["Close"]
        end_price   = company_data.iloc[-1]["Close"]
        returns[company] = ((end_price - start_price) / start_price) * 100
    return returns
