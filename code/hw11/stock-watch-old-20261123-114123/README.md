# DATA 260 HW11 corrected Stock Watch kit

This kit is the corrected HW11 submission source. It is not the classroom demo.

## Live watchlist

- MRNA - Moderna, SEC CIK 0001682852
- REGN - Regeneron Pharmaceuticals, SEC CIK 0000872589
- GILD - Gilead Sciences, SEC CIK 0000882095

The watchlist matches Domain 1 Clinical Trials. The CIK values were checked in SEC EDGAR.

## Graded evaluation files

- `policy.md`: notify, digest, ask, and quiet rules with different thresholds for MRNA, REGN, and GILD
- `sources.json`: live sources, CIKs, approved-host list, and fictional fixture sources
- `fixtures/hw11/`: original fictional QXZA-QXZL test data
- `golden/gold_hw11_prerun.json`: 12 labels finalized before the Muse run
- `watch.py`: persistent state, deduplication, restart, injection guard, trace, metrics, and run timing
- `calibrate_volatility.py`: measures 60 recent daily moves for the live watchlist
- `demo_test.sh`: static validation only; it does not run graded fixtures or create state
- `HW11_RUN_GUIDE.md`: exact order for pre-run commit, live run, failure tests, screenshots, and metrics

## Important properties

- All graded fixture companies, tickers, prices, filings, and news are fictional.
- The 12 golden cases map to 11 unique retrieved effects plus one intentionally missing-price case.
- The near-duplicate case has two source sightings but one effect.
- The retry case uses its own separate effect.
- The injection item's own URL is outside the allowlist and must be blocked.
- No exact token count is invented when Muse shows only a weekly usage percentage.

Run `bash demo_test.sh` for a static check. Then follow `HW11_RUN_GUIDE.md`.
