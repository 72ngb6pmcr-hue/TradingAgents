# Historical event → production network → market effects (Issue #25)

## Goal

For each **publicly known** event, estimate what can change in a physical
production network and which listed instruments *might* be affected. Rank
conditional scenarios only after acquiring **independent, timestamped market
outcomes**. This is not a deterministic mapping from a headline to a BUY.

## What the initial implementation actually does

1. `tradingagents/knowledge/historical_event_cases.json` records dated
   examples and sources. The first entries are:
   - 14 September 2019: damage to Saudi Abqaiq/Khurais facilities and temporary
     physical supply outage.
   - 2 January 2020: geopolitical escalation in Iraq, involving an oil-supply
     *risk premium* but no direct physical oil outage.
   - 24 February 2022: invasion of Ukraine and the broader oil-market
     repricing, which also depended on inventories, sanctions and demand.
2. `tradingagents/knowledge/supply_chain_graph.json` defines hypotheses:
   supply → crude prices → fuel/feedstock prices → producers, airlines and
   petrochemicals. The sign of an effect depends on hedging, offsetting supply,
   demand, geography, contractual prices and the firm's exposure.
3. `tradingagents/agents/causal_event_library.py` traverses that graph,
   enumerating effects in either direction **without inventing numerical
   probabilities**. Example:
   `python -m tradingagents.agents.causal_event_library --as-of 2026-11-12T04:00:00+01:00 --event-type PHYSICAL_OIL_OUTAGE --changed-node crude_supply --direction -1`
4. The `empirical_probability()` helper requires at least **20 independent
   timestamped, settled event outcomes** for the exact event type, instrument
   and horizon. Even then it reports a *historical hit frequency and Wilson
   interval*, not a calibrated prediction or a causal proof. This 20-case
   threshold is an engineering guard, **not** a statistical guarantee.
   Current initial casebook has **zero** verified per-security outcome rows
   with reproducible first-public timestamps. Hence no numeric estimate.

## What must be added to turn this into a working predictive model

- A historical universe of event-specific records with timestamp of first
  public knowledge and a **separately timestamped** verification date.
  Distinguish events that actually restricted barrels from threats alone.
- Point-in-time series: Brent/WTI (contract and roll specification), jet fuel,
  feedstocks, inventory and freight costs, GPW/US/ETF security prices, FX,
  dividend/corporate-action adjustments and market trading hours.
- Links between companies and products from audited filings, segment
  exposure and input-output tables (Eurostat/OECD), including geography,
  price-pass-through and whether producers hedge their costs.
- Event studies comparing price changes *after the first public news time*
  with prior expected returns and a matched benchmark. Score horizons
  1/5/20/60 sessions, net of executable spreads/fees/FX; avoid hindsight.
- Cross-sectional / lead-lag tests separating a commodity's first move from
  delayed supplier/customer repricing. Use a purged rolling training/evaluation
  split; cluster correlated events so a war lasting months is not counted as
  hundreds of independent cases.
- Fit probabilities only on historically available settled events; calibrate
  and test Brier score, reliability curves, conditional hit rates, tail losses,
  drawdown and strategy net P&L **out of sample**. Compare to always-hold,
  no-trade and price-only baselines.
- Run a blinded forecast journal for future news: source + first-seen time,
  proposed exposure and sign, horizon, confidence, invalidation condition,
  actual future outcome. Capture mistakes, too, to prevent cherry-picking.

## Historical evidence — important counterexample

The EIA described why the September 2019 Saudi production outage and January
2020 Iraq military escalation initially produced similar positive oil-price
reactions but diverged on physical supply consequences. Brent then retraced
part of its initial gains. A *negative supply shock* can be a robust economic
mechanism without ensuring that buying a producer's stock **after publication**
will be profitable. Source:
https://www.eia.gov/TODAYinENERGY/detail.php?id=42675

World Bank described Brent's return toward pre-attack levels by late
September 2019 as production returned and spare supply and demand conditions
changed. Source:
https://documents1.worldbank.org/curated/en/697771572367279523/pdf/Commodity-Markets-Outlook.pdf

A study of production networks and monetary policy documented important
network effects in US stock reactions, supporting the *research direction*,
not proving that our proposed stock selections have predictive power:
https://doi.org/10.1093/rfs/hhaf106

## Non-negotiable constraints

- Never use the **date of an event** as the date its details became known to
  investors. Retrospective EIA descriptions are excellent for understanding
  history but cannot be passed off as contemporary news.
- Correlation does not equal causation. An oil company's share price also
  depends on hedging, production volume, taxes, reserves, management,
  leverage, valuation and market expectations.
- No 'sure bets'; always allow 'insufficient evidence / no trade'.
- External model opinions are independent *only if models were genuinely
  called* and their original replies recorded. None were called here.
- No actual broker orders, financial profit claim or unsupported precision.
