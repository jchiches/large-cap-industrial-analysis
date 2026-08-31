"""Compute 10-year rolling total shareholder return (TSR) ranks.

Fetches monthly dividend- and split-adjusted closes (yfinance auto_adjust)
for every ticker in universe/tsr_universe.csv, then for each year-end
2011..2025 computes the trailing 10-year TSR (cumulative and annualized)
and cross-sectional rank. Output feeds the bump chart.

Usage:
    python scripts/rolling_tsr.py [universe_csv] [out_json] [out_prices_csv]

Defaults to the full chart universe:
    python scripts/rolling_tsr.py universe/tsr_universe.csv \
        data/rolling_tsr.json data/monthly_adj_close.csv
"""

import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
UNIVERSE = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "universe" / "tsr_universe.csv"
OUT_JSON = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "data" / "rolling_tsr.json"
OUT_PRICES = Path(sys.argv[3]) if len(sys.argv) > 3 else ROOT / "data" / "monthly_adj_close.csv"

START = "2000-11-01"   # need Dec-2001 for the window ending Dec-2011
END = "2026-01-15"     # through Dec-2025 monthly bar
YEARS = range(2011, 2026)
WINDOW = 10           # headline window; WINDOWS are all emitted under "windows"
WINDOWS = (10, 5)


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


CAP_SUFFIX = {"T": 1e12, "B": 1e9, "M": 1e6}


def fetch_cap_history(tickers: list[str]) -> dict[str, dict[int, float]]:
    """Year-end market caps from Macrotrends' annual market-cap tables.

    Macrotrends aggregates dual-listed structures (BHP, Rio Tinto) and ADRs
    into one company-level cap, which EDGAR share counts do not.
    """
    headers = {"User-Agent": "Mozilla/5.0 (research script)"}
    out: dict[str, dict[int, float]] = {}
    for t in tickers:
        url = f"https://www.macrotrends.net/stocks/charts/{t}/x/market-cap"
        try:
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            rows = re.findall(
                r"<td[^>]*>(20\d{2})</td>\s*<td[^>]*>\$([\d.,]+)\s*([TBM])</td>",
                r.text,
            )
            caps = {int(y): float(v.replace(",", "")) * CAP_SUFFIX[sfx]
                    for y, v, sfx in rows}
            if caps:
                out[t] = caps
            print(f"{t}: {len(caps)} years of market cap"
                  + (f" ({min(caps)}-{max(caps)})" if caps else ""))
        except Exception as exc:
            print(f"WARNING: no cap history for {t}: {exc}")
        time.sleep(1)
    return out


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

    OUT_PRICES.parent.mkdir(exist_ok=True)
    px.to_csv(OUT_PRICES)

    ye = year_end_series(px)

    def window_records(window: int) -> dict[str, list[dict]]:
        recs: dict[str, list[dict]] = {}
        for year in YEARS:
            start_year = year - window
            if start_year not in ye.index or year not in ye.index:
                continue
            p0, p1 = ye.loc[start_year], ye.loc[year]
            tsr = (p1 / p0 - 1.0).dropna()
            ann = (1.0 + tsr) ** (1.0 / window) - 1.0
            ranked = tsr.sort_values(ascending=False)
            recs[str(year)] = [
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
            print(f"{window}y {year}: {len(ranked)} tickers, "
                  f"#1 {ranked.index[0]} ({ann[ranked.index[0]]:+.1%}/yr)")
        return recs

    windows = {str(w): window_records(w) for w in WINDOWS}
    records = windows[str(WINDOW)]

    live = [t for t in tickers if t in px.columns]
    caps = fetch_market_caps(live)
    cap_hist = fetch_cap_history(live)
    companies = {
        t: {
            "name": m["name"],
            "short": m.get("short_name", m["name"]),
            "group": m["group"],
            "mkt_cap": caps.get(t),
            "caps": {y: c for y, c in cap_hist.get(t, {}).items()
                     if min(YEARS) <= y <= max(YEARS)},
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
        "windows": windows,
    }
    OUT_JSON.write_text(json.dumps(out, indent=1))
    print(f"Wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
