# TradingAgents 2.0 — supply-chain research prototype

This is a **research-only, offline prototype**, not a validated forecasting strategy.

## Modules
- `tradingagents.agents.supply_chain_forecast`: 10 sector dependency maps and conditional, qualitative supply-shock hypotheses. The graph is a **taxonomy**, not verified supplier/customer exposure.
- `tradingagents.agents.structural_market`: matched-period reported demand/supply gaps and lagged Pearson correlations of dated log returns. No price predictions.

## Usage

```bash
python -m unittest discover -s tests -p 'test_supply_chain_forecast.py' -v
python -m unittest discover -s tests -p 'test_structural_market.py' -v
python -m tradingagents.agents.supply_chain_forecast
python -m tradingagents.agents.structural_market
```

Without supplied observations, reports deliberately contain **no empirical forecasts**.
The GitHub workflow uploads these two JSON reports as Actions artifacts; it does not modify `paper-game/`.

Supply-chain observations: JSON array, e.g.
```json
[{"node":"copper","date":"2026-11-11T10:00:00Z","source_url":"https://example.org/primary-disclosure","metric":"production","unit":"tonnes","value":90,"baseline":100,"direction":"decrease"}]
```
This is a **schema illustration**, not real market data. The URL is not fetched or verified by the tool. Use `--observations path.json` only with independently verified source material.

Structural market input: JSON object with `as_of`, `demand`, `supply`, `prices_a`, `prices_b`. Each demand/supply row needs `date`, `published_at` (timezone-aware), `source_url` (HTTPS), `unit`, `value`. Price rows replace `value` with `close`. Matching dates are required; only dates on/before `as_of` are used. Units must match for demand/supply. Run `--input path.json`.

**Cautions:** Supply/demand values must cover comparable periods and geographies; the code currently validates units but not geography, methodology, or publication revisions. Lag correlations use intersecting dates and session-index offsets; they do not establish predictive causality. Future improvements must add independent source verification, actual product-company links, inventories, elasticity, capacity lead times, out-of-sample evaluation and market reaction analysis.

**No brokerage access, no LLM calls, no order placement, no changes to the 100,000 PLN paper game.**
