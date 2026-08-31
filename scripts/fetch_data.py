#!/usr/bin/env python3
"""Fetch prices and fundamentals for every ticker in the coverage universe.

Writes:
  data/prices.csv        - 5 years of daily adjusted closes, one column per ticker
  data/fundamentals.csv  - one row per ticker with key valuation/quality metrics
"""

import csv
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
UNIVERSE_CSV = ROOT / "universe" / "universe.csv"
DATA_DIR = ROOT / "data"

# yfinance info keys -> output column names
FUNDAMENTAL_FIELDS = {
    "marketCap": "market_cap",
    "trailingPE": "pe_trailing",
    "forwardPE": "pe_forward",
    "enterpriseToEbitda": "ev_ebitda",
    "priceToBook": "price_to_book",
    "dividendYield": "dividend_yield",
    "returnOnEquity": "roe",
    "operatingMargins": "operating_margin",
    "revenueGrowth": "revenue_growth",
    "freeCashflow": "free_cash_flow",
    "totalDebt": "total_debt",
    "ebitda": "ebitda",
}


def load_universe() -> list[dict]:
    with open(UNIVERSE_CSV, newline="") as f:
        return list(csv.DictReader(f))


def fetch_prices(tickers: list[str]) -> pd.DataFrame:
    data = yf.download(tickers, period="5y", auto_adjust=True, progress=False)
    return data["Close"]


def fetch_fundamentals(universe: list[dict]) -> pd.DataFrame:
    rows = []
    for entry in universe:
        ticker = entry["ticker"]
        try:
            info = yf.Ticker(ticker).info
        except Exception as exc:  # network hiccups shouldn't kill the whole run
            print(f"  WARN {ticker}: {exc}")
            info = {}
        row = {"ticker": ticker, "name": entry["name"], "sub_industry": entry["sub_industry"]}
        for src, dst in FUNDAMENTAL_FIELDS.items():
            row[dst] = info.get(src)
        # FCF yield = free cash flow / market cap
        if row.get("free_cash_flow") and row.get("market_cap"):
            row["fcf_yield"] = row["free_cash_flow"] / row["market_cap"]
        else:
            row["fcf_yield"] = None
        rows.append(row)
        print(f"  fetched {ticker}")
    return pd.DataFrame(rows)


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    universe = load_universe()
    tickers = [e["ticker"] for e in universe]

    print(f"Fetching prices for {len(tickers)} tickers...")
    prices = fetch_prices(tickers)
    prices.to_csv(DATA_DIR / "prices.csv")

    print("Fetching fundamentals...")
    fundamentals = fetch_fundamentals(universe)
    fundamentals.to_csv(DATA_DIR / "fundamentals.csv", index=False)

    print(f"Done. Wrote {DATA_DIR / 'prices.csv'} and {DATA_DIR / 'fundamentals.csv'}")


if __name__ == "__main__":
    main()
