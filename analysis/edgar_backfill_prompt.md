# Prompt: backfill 2011–2014 market caps from SEC EDGAR

Paste the prompt below into a Claude Code session running **locally** (your
machine, normal residential internet). It will not work from GitHub Actions
or most cloud sandboxes — SEC and several data hosts block datacenter IPs,
which is why these years are missing in the first place.

---

Work in my repo `jchiches/large-cap-industrial-analysis` (clone it from
GitHub if you don't have it), on branch `main`.

Context: `scripts/rolling_tsr.py` builds rolling-TSR datasets
(`data/basket_tsr.json`, `data/rolling_tsr.json`) for an interactive bump
chart (`analysis/rolling_tsr_bump.html`). Each dataset's `companies` map
carries year-end market caps under `caps`, computed as year-end share count
x year-end close. Yahoo's share-count history only reaches back to ~2015,
so caps for 2011–2014 are missing. The script already contains a
`caps_from_edgar()` fallback that fills missing years from SEC XBRL
cover-page share counts (`dei:EntityCommonStockSharesOutstanding`) — it
just can't run from CI because SEC 403s datacenter IPs. Your job is to run
it locally and improve its coverage.

Steps:

1. `pip install yfinance pandas requests`, then confirm SEC access works
   from this machine:
   `python -c "import requests; print(requests.get('https://data.sec.gov/api/xbrl/companyconcept/CIK0000018230/dei/EntityCommonStockSharesOutstanding.json', headers={'User-Agent':'large-cap-industrial-analysis research'}).status_code)"`
   — expect 200. If 403, stop and report; don't try to evade the block.
2. In `scripts/rolling_tsr.py`, the hardcoded `CIK` dict only covers the
   21-name basket's US filers. Extend coverage to every US ticker in
   `universe/tsr_universe.csv` by fetching
   `https://www.sec.gov/files/company_tickers.json` at runtime (works
   locally) to build the ticker→CIK map, keeping the hardcoded dict as a
   fallback. Leave `ADR_TICKERS` excluded as they are now.
3. Known gap to fix while you're in there: `caps_from_edgar()` only matches
   filings whose period end is `-12-31`, so companies with non-December
   fiscal years (Deere ends in October; check for others) get no fill.
   Widen the matching so an observation whose end date falls within
   October–January maps to the nearest December 31 (Oct–Dec of year Y and
   January of Y+1 both count as year-end Y).
4. Run both datasets:
   - `python scripts/rolling_tsr.py universe/basket_universe.csv data/basket_tsr.json data/basket_monthly_adj_close.csv`
   - `python scripts/rolling_tsr.py`
   Respect SEC fair-access rules: keep the identifying User-Agent that's
   already in the script and stay well under 10 requests/second.
5. Verify before committing (all in the produced JSONs):
   - Basket: CAT, XOM, UNP, LUV caps now start at 2011. Spot-check
     magnitudes: XOM 2011 ≈ $400B, CAT 2011 ≈ $59B, UNP 2011 ≈ $51B
     (within ~10% is fine — these are share-count × close approximations).
   - Values for 2015+ should be unchanged or nearly unchanged from what's
     already committed.
   - No `NaN` anywhere in either JSON (`grep -c NaN` should be 0).
6. Commit the script change and the regenerated
   `data/basket_tsr.json`, `data/rolling_tsr.json`,
   `data/basket_monthly_adj_close.csv`, `data/monthly_adj_close.csv`
   (data files are force-added; `data/*.csv` is gitignored) with a clear
   message, and push to `main`.
7. Do NOT edit `analysis/rolling_tsr_bump.html` — the chart is maintained
   in a separate session and will pick up the new data on its next
   rebuild. Report which tickers/years you were able to fill and any that
   remain missing.
