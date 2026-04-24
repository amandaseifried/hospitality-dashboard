"""Configuration for the Hospitality Earnings Dashboard."""

# Ordered by market capitalization (largest first)
COMPANIES = {
    "Marriott": {
        "ticker": "MAR",
        "color": "#A40034",  # Marriott red
        "description": "Largest hotel company by rooms globally",
        "hq": "Bethesda, MD",
        "segments": ["Luxury", "Premium", "Select", "Midscale"],
    },
    "Hilton": {
        "ticker": "HLT",
        "color": "#003B5C",  # Hilton blue
        "description": "Asset-light, fee-based model",
        "hq": "McLean, VA",
        "segments": ["Luxury", "Upper Upscale", "Upscale", "Upper Midscale"],
    },
    "IHG": {
        "ticker": "IHG",
        "color": "#E87722",  # IHG orange
        "description": "UK-headquartered, strong Americas presence",
        "hq": "Denham, UK",
        "segments": ["Luxury & Lifestyle", "Premium", "Essentials", "Suites"],
    },
    "Hyatt": {
        "ticker": "H",
        "color": "#6EB5D9",  # Hyatt light blue
        "description": "Luxury and upper-upscale focused",
        "hq": "Chicago, IL",
        "segments": ["Luxury", "Upper Upscale", "Upscale", "Inclusive Collection"],
    },
    "Accor": {
        "ticker": "ACCYY",
        "color": "#C4A962",  # Accor gold
        "description": "European leader, strong in luxury via Raffles/Fairmont",
        "hq": "Issy-les-Moulineaux, France",
        "segments": ["Luxury", "Premium", "Midscale", "Economy"],
    },
}

COMPANY_NAMES = list(COMPANIES.keys())
TICKERS = {name: info["ticker"] for name, info in COMPANIES.items()}
COLORS = {name: info["color"] for name, info in COMPANIES.items()}

# Quarters covered (trailing 4)
QUARTERS = ["Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025", "Q1 2026"]

# Currency formatting
def fmt_currency(val, decimals=0):
    if val is None:
        return "N/A"
    if abs(val) >= 1_000:
        return f"${val / 1_000:,.{decimals}f}B"
    return f"${val:,.{decimals}f}M"

def fmt_pct(val, decimals=1):
    if val is None:
        return "N/A"
    return f"{val:+.{decimals}f}%"
