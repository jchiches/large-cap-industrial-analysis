#!/usr/bin/env python3
"""Rank the universe on a composite of valuation and quality factors.

Reads data/fundamentals.csv (produced by fetch_data.py) and writes
data/screen_results.csv sorted by composite score (best first).

Factors (equal-weighted z-scores within the universe):
  Valuation (cheaper is better): forward P/E, EV/EBITDA, FCF yield
  Quality  (higher is better):   ROE, operating margin, revenue growth
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

# column -> +1 if higher is better, -1 if lower is better
FACTORS = {
    "pe_forward": -1,
    "ev_ebitda": -1,
    "fcf_yield": 1,
    "roe": 1,
    "operating_margin": 1,
    "revenue_growth": 1,
}


def zscore(series: pd.Series) -> pd.Series:
    return (series - series.mean()) / series.std(ddof=0)


def main() -> None:
    fundamentals_path = DATA_DIR / "fundamentals.csv"
    if not fundamentals_path.exists():
        raise SystemExit("data/fundamentals.csv not found - run scripts/fetch_data.py first")

    df = pd.read_csv(fundamentals_path)

    score = pd.Series(0.0, index=df.index)
    used = pd.Series(0, index=df.index)
    for col, direction in FACTORS.items():
        if col not in df.columns:
            continue
        z = zscore(df[col]) * direction
        # winsorize extreme outliers so one bad print doesn't dominate
        z = z.clip(-3, 3)
        score = score.add(z, fill_value=0)
        used = used + z.notna().astype(int)

    df["composite_score"] = score / used.replace(0, pd.NA)
    df = df.sort_values("composite_score", ascending=False)

    out = DATA_DIR / "screen_results.csv"
    df.to_csv(out, index=False)

    cols = ["ticker", "name", "sub_industry", "composite_score"]
    print(df[cols].to_string(index=False))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
