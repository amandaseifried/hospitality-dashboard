"""Fetch live market and financial data via yfinance."""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_stock_data(tickers: dict, period: str = "1y") -> pd.DataFrame:
    """Fetch stock price history for all companies.

    Args:
        tickers: dict mapping company name to ticker symbol
        period: yfinance period string (e.g., '1y', '6mo')

    Returns:
        DataFrame with columns: Date, Company, Close, Volume
    """
    frames = []
    for company, ticker in tickers.items():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            if hist.empty:
                continue
            df = hist[["Close", "Volume"]].reset_index()
            df["Company"] = company
            df["Ticker"] = ticker
            frames.append(df)
        except Exception:
            continue

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


@st.cache_data(ttl=3600)
def get_company_info(tickers: dict) -> pd.DataFrame:
    """Fetch current company info (market cap, P/E, etc.).

    Returns:
        DataFrame with one row per company.
    """
    rows = []
    for company, ticker in tickers.items():
        row = {
            "Company": company, "Ticker": ticker,
            "Price": None, "Market Cap ($B)": None,
            "P/E Ratio": None, "Forward P/E": None,
            "EV/EBITDA": None, "52W High": None,
            "52W Low": None, "Dividend Yield (%)": None,
            "YTD Return (%)": None,
        }
        try:
            stock = yf.Ticker(ticker)
            # fast_info is more reliable than stock.info in cloud environments
            fi = stock.fast_info
            price = getattr(fi, "last_price", None)
            mcap = getattr(fi, "market_cap", None)
            if price:
                row["Price"] = float(price)
            if mcap:
                row["Market Cap ($B)"] = float(mcap) / 1e9
            yh = getattr(fi, "year_high", None)
            yl = getattr(fi, "year_low", None)
            if yh:
                row["52W High"] = float(yh)
            if yl:
                row["52W Low"] = float(yl)
        except Exception:
            pass
        try:
            info = stock.info or {}
            if info and len(info) > 5:  # non-empty info dict
                pe = info.get("trailingPE")
                fpe = info.get("forwardPE")
                ev = info.get("enterpriseToEbitda")
                div = info.get("dividendYield")
                if pe:
                    row["P/E Ratio"] = float(pe)
                if fpe:
                    row["Forward P/E"] = float(fpe)
                if ev:
                    row["EV/EBITDA"] = float(ev)
                if div:
                    row["Dividend Yield (%)"] = float(div) * 100
                # Fallback price from info if fast_info missed it
                if row["Price"] is None:
                    p = info.get("currentPrice") or info.get("regularMarketPrice")
                    if p:
                        row["Price"] = float(p)
                if row["Market Cap ($B)"] is None:
                    mc = info.get("marketCap")
                    if mc:
                        row["Market Cap ($B)"] = float(mc) / 1e9
        except Exception:
            pass
        rows.append(row)

    return pd.DataFrame(rows)


@st.cache_data(ttl=3600)
def get_quarterly_financials(tickers: dict) -> pd.DataFrame:
    """Fetch quarterly income statement data via yfinance.

    Returns:
        DataFrame with quarterly revenue, net income, EPS per company.
    """
    rows = []
    for company, ticker in tickers.items():
        try:
            stock = yf.Ticker(ticker)
            # Quarterly income statement
            q_financials = stock.quarterly_income_stmt
            if q_financials is None or q_financials.empty:
                continue

            for col in q_financials.columns:
                quarter_date = col
                revenue = q_financials.loc["Total Revenue", col] if "Total Revenue" in q_financials.index else None
                net_income = q_financials.loc["Net Income", col] if "Net Income" in q_financials.index else None
                ebitda = q_financials.loc["EBITDA", col] if "EBITDA" in q_financials.index else None
                diluted_eps = q_financials.loc["Diluted EPS", col] if "Diluted EPS" in q_financials.index else None

                rows.append({
                    "Company": company,
                    "Date": quarter_date,
                    "Revenue ($M)": (revenue or 0) / 1e6 if revenue else None,
                    "Net Income ($M)": (net_income or 0) / 1e6 if net_income else None,
                    "EBITDA ($M)": (ebitda or 0) / 1e6 if ebitda else None,
                    "Diluted EPS": diluted_eps,
                })
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values(["Company", "Date"])
    return df


def calculate_ytd_returns(stock_data: pd.DataFrame) -> dict:
    """Calculate YTD returns from stock price data."""
    if stock_data.empty:
        return {}

    returns = {}
    current_year = datetime.now().year

    for company in stock_data["Company"].unique():
        company_data = stock_data[stock_data["Company"] == company].sort_values("Date")

        # Get first trading day of current year
        ytd_data = company_data[company_data["Date"].dt.year == current_year]
        if ytd_data.empty:
            continue

        start_price = ytd_data.iloc[0]["Close"]
        end_price = ytd_data.iloc[-1]["Close"]
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
        end_price = company_data.iloc[-1]["Close"]
        returns[company] = ((end_price - start_price) / start_price) * 100

    return returns
