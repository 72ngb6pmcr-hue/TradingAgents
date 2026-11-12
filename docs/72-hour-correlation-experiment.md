# Time-boxed correlation research: 12–15 November 2026

This is a **72-hour recurring experiment**, not 72 hours of uninterrupted
compute: GitHub Actions attempts one independent check per hour. GitHub may
delay or miss scheduled triggers. Missing runs are visible in the summary.

**Experiment period:** 2026-11-12 04:00 UTC (05:00 Warsaw CET) inclusive
through 2026-11-15 04:00 UTC (05:00 Warsaw CET) exclusive.
GitHub schedule is at 13 minutes after each UTC hour to reduce congestion.
The workflow attempts to disable itself after expiry. If the disable API fails,
later runs still skip research after the end time.

The GitHub workflow `.github/workflows/hourly-causal-72h.yml` checks out
`research/causal-72h-data` and saves each result under
`research-data/causal-72h/iteration-00.json` through
`iteration-71.json`. `summary.json` aggregates *all* observations and
missing data, not just correlations that look attractive.

### Predeclared historical analyses

- Daily Brent front-month continuous **proxy** (`BZ=F`) compared with
  exchange-listed energy and downstream proxies: `XLE`, `JETS`,
  `XOM`, `DAL`, and broad-market `SPY`.
- Each hour tests a **precommitted** combination in order, drawn from 5
  equity proxies × 4 leads (0, 1, 2, 5 trading sessions) × 4 lookbacks
  (180/365/730/1460 common sessions); first 72 of 80 combinations
  are selected by fixed order before seeing results. Some overlap heavily
  and thus are **not 72 independent events or probability estimates**.
- Correlations compare commodity return at session t with subsequent
  sector return at t+lag, split into first and second halves as a rough
  stability check. Daily EOD alignment cannot resolve intraday ordering.
- Known historical events from `historical_event_cases.json` receive
  a **retrospective** 1/5/20/60-session price path, explicitly not a
  tradeable event study. Their first public timestamps and properly adjusted
  benchmark-relative surprise returns are still not verified.
- Every result preserves its data source and errors. If Yahoo returns a
  blank history or a vendor error, the slot is recorded as `DATA_MISSING`.

### Interpretation limits

A large correlation is not causation and not a probability of profit.
Shared market factors, data revisions, futures contract rolls, market hours,
mixed sector exposure, hedging and adjustments may all drive observed
relationships. A sample of daily prices is **not** a dataset of confirmed
news-to-earnings causal effects. Neither event-specific effect size,
validated predictive precision, nor financial P&L is established.
The experiment intentionally produces `probability: null` and makes
**zero orders**. These hourly research results complement—not replace—the
longer-term supply-chain causal model in Issue #25.

### Final evaluation

At the first regular TradingAgents ChatGPT report after 2026-11-15
05:00 Warsaw, inspect the **actual** `research/causal-72h-data` branch
`research-data/causal-72h/summary.json` and all relevant evidence. Report:
number of attempted slots, valid vs failed historical tests, stable vs
unstable correlations by sector, counterexamples, whether any evidence
supports predictive probabilities (likely not yet), gaps, and next measured
experiment. Never substitute fabricated successful runs for missing results.
Use the dated sources; all profits and trades remain on separate paper ledger.
