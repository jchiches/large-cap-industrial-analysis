"""Compute 10-year rolling total shareholder return (TSR) ranks.

Fetches monthly dividend- and split-adjusted closes (yfinance auto_adjust)
for every ticker in universe/tsr_universe.csv, then for each year-end
2011..2025 computes the trailing 10-year TSR (cumulative and annualized)
and cross-sectional rank. Output feeds the bump chart.

Usage:
    python scripts/rolling_tsr.py

Writes:
    data/monthly_adj_close.csv   raw monthly adjusted closes
    data/rolling_tsr.json        per-year TSR + rank per ticker
"""

import json
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
UNIVERSE = ROOT / "universe" / "tsr_universe.csv"
DATA_DIR = ROOT / "data"

START = "2000-11-01"   # need Dec-2001 for the window ending Dec-2011
END = "2026-01-15"     # through Dec-2025 monthly bar
YEARS = range(2011, 2026)
WINDOW = 10


def fetch_monthly_closes(tickers: list[str]) -> pd.DataFrame:
    px = yf.download(
        tickers,
        start=START,
        end=END,
        interval="1mo",
        auto_adjust=True,
        progress=False,
        threads=True,
    )["Close"]
    if isinstance(px, pd.Series):
        px = px.to_frame(tickers[0])
    return px.dropna(how="all")


def year_end_series(px: pd.DataFrame) -> pd.DataFrame:
    """Last available monthly close per calendar year (normally the Dec bar)."""
    ye = px.groupby(px.index.year).last()
    ye.index.name = "year"
    return ye


def fetch_market_caps(tickers: list[str]) -> dict[str, float | None]:
    caps: dict[str, float | None] = {}
    for t in tickers:
        try:
            caps[t] = float(yf.Ticker(t).fast_info["marketCap"])
        except Exception as exc:
            print(f"WARNING: no market cap for {t}: {exc}")
            caps[t] = None
    return caps


def main() -> None:
    uni = pd.read_csv(UNIVERSE)
    tickers = uni["ticker"].tolist()
    meta = uni.set_index("ticker").to_dict("index")

    px = fetch_monthly_closes(tickers)
    missing = sorted(set(tickers) - set(px.columns))
    if missing:
        print(f"WARNING: no data at all for {missing}")

    DATA_DIR.mkdir(exist_ok=True)
    px.to_csv(DATA_DIR / "monthly_adj_close.csv")

    ye = year_end_series(px)

    records: dict[str, list[dict]] = {}
    for year in YEARS:
        start_year = year - WINDOW
        if start_year not in ye.index or year not in ye.index:
            continue
        p0, p1 = ye.loc[start_year], ye.loc[year]
        tsr = (p1 / p0 - 1.0).dropna()
        ann = (1.0 + tsr) ** (1.0 / WINDOW) - 1.0
        ranked = tsr.sort_values(ascending=False)
        records[str(year)] = [
            {
                "ticker": t,
                "name": meta[t]["name"],
                "group": meta[t]["group"],
                "rank": i + 1,
                "tsr_cum": round(float(tsr[t]), 4),
                "tsr_ann": round(float(ann[t]), 4),
            }
            for i, t in enumerate(ranked.index)
        ]
        print(f"{year}: {len(ranked)} tickers, "
              f"#1 {ranked.index[0]} ({ann[ranked.index[0]]:+.1%}/yr)")

    caps = fetch_market_caps([t for t in tickers if t in px.columns])
    companies = {
        t: {
            "name": m["name"],
            "short": m.get("short_name", m["name"]),
            "group": m["group"],
            "mkt_cap": caps.get(t),
        }
        for t, m in meta.items()
    }

    out = {
        "window_years": WINDOW,
        "as_of": pd.Timestamp.utcnow().strftime("%Y-%m-%d"),
        "companies": companies,
        "note": ("10-year TSR = change in dividend- and split-adjusted price "
                 "(dividends reinvested) between year-end Y-10 and year-end Y. "
                 "Source: Yahoo Finance monthly adjusted closes."),
        "years": records,
    }
    (DATA_DIR / "rolling_tsr.json").write_text(json.dumps(out, indent=1))
    print(f"Wrote {DATA_DIR / 'rolling_tsr.json'}")


if __name__ == "__main__":
    main()
