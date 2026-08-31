# Large Cap Industrial Stock Analysis

Research and analysis of large-capitalization industrial sector stocks (market cap ≥ $10B, GICS Industrials sector).

## Structure

```
large-cap-industrial-analysis/
├── README.md               # This file
├── universe/
│   └── universe.csv        # Coverage universe: tickers, names, sub-industries
├── data/                   # Raw and processed data (gitignored except samples)
├── scripts/
│   ├── fetch_data.py       # Pull prices + fundamentals for the universe
│   └── screen.py           # Rank the universe on valuation/quality metrics
├── analysis/
│   ├── TEMPLATE.md         # Single-stock analysis template
│   └── <TICKER>.md         # One writeup per company
├── requirements.txt
└── .gitignore
```

## Universe

The coverage universe (`universe/universe.csv`) spans the major GICS Industrials sub-industries:

- **Aerospace & Defense** — RTX, BA, LMT, NOC, GD, GE (Aerospace)
- **Machinery** — CAT, DE, CMI, PCAR, PH, ITW, DOV
- **Transportation (Rail/Freight/Logistics)** — UNP, CSX, NSC, UPS, FDX, ODFL
- **Electrical Equipment & Multi-Industry** — ETN, EMR, HON, MMM, ROK, AME
- **Building & HVAC** — TT, CARR, JCI, OTIS
- **Commercial Services & Waste** — WM, RSG, CTAS
- **Airlines** — DAL, UAL, LUV

## Methodology

Each company writeup (see `analysis/TEMPLATE.md`) covers:

1. **Business overview** — segments, revenue mix, competitive position / moat
2. **Fundamentals** — revenue growth, margins, ROIC, FCF conversion, balance sheet
3. **Valuation** — P/E, EV/EBITDA, FCF yield vs. history and peers
4. **Cycle positioning** — where the relevant end markets sit (capex cycle, freight cycle, defense budgets, aerospace aftermarket, construction)
5. **Thesis** — bull/bear cases, key catalysts and risks, verdict

The screening script (`scripts/screen.py`) produces a cross-sectional ranking of the universe on valuation and quality factors to prioritize which names to dig into.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/fetch_data.py     # pulls data for all tickers in universe.csv
python scripts/screen.py         # writes data/screen_results.csv
```

## Disclaimer

For research and educational purposes only. Nothing in this repository is investment advice.
