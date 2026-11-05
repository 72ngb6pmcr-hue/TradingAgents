# Event-driven market intelligence — operational playbook

Tracking: #15. Research-only; never an automatic trading instruction.
Reference: [GDELT DOC API 2.0](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/)
is a **discovery index**, not an authority verifying any reported event.

## Why this module exists
Price can react to new policy, shipping interruptions, sanctions, earnings,
weather, central-bank surprises and geopolitical developments. Twice-daily
technical scans may miss a fast catalyst. The hourly news watch records dated
headlines as **untrusted leads**; it does NOT infer that a report is true, nor
that a price move is still ahead. GitHub's scheduler and news feeds are
best-effort and not suitable for guaranteed second-by-second trading.

## Example: hypothetical shock affecting the Strait of Hormuz

Do **not** assume that a political leader ordered any strike merely because a
headline or user-provided example mentions it. A report of an attack, an actual
transit closure, a decline in physical oil deliveries and futures-price
reaction are different facts with different probabilities and lag.

| Question | Evidence to seek | What invalidates the conclusion? |
|---|---|---|
| What actually happened? | Government/port/maritime authority statements, original reporting with timestamps | Unconfirmed, recycled or misattributed claim |
| What physical impact? | Tanker traffic, exports, insurers' restrictions, shipping delays, producer outages | Shipments remain normal or interruption too brief |
| What is priced in? | Pre-event and post-event Brent/WTI futures, forward curve, FX, market trading hours | Oil already repriced, failed breakout or spread dominates |
| Could supply offset it? | Spare capacity, reserve releases, rerouting, OPEC output, demand | Offset eliminates shortage thesis |
| How to know thesis has changed? | Reopening, verified transit recovery, diplomatic settlement, changed supply/demand | Continuing confirmed shortages, no price follow-through |

### Entry discussion gate — **not** a buy signal
Requires a verified event, timestamped primary evidence, demonstrated
supply-impact scenario, time-aligned trading price, actual instrument exposure
(spot/futures/ETF/producer equity are **not interchangeable**), verified
trading costs and enough liquidity. Check which news was **already public**
when the hypothetical fill could occur. Unverified headlines always produce
**RESEARCH_ONLY**.

### Exit/stop discussion gate — **not** a sell signal
Predefine at time of simulated entry: maximum thesis horizon, downside
threshold, acceptable loss, take-profit protocol, trailing risk rule if any,
conditions for thesis invalidation (transit reopens; exports normalize; policy
reversed), and the effect of overnight price gaps or market closures. An
observed price reversal or offsetting supply can matter more than headline
counts. Do not repeatedly buy a rising price simply because the story
continues.

## Comparison and honest measurement
Archive each event's first-seen time and document URL, timestamp of
independent verification, eligible trade timestamp, market and FX prices,
hypothetical quantity, spreads/fees, transaction outcome and corresponding
benchmark. Evaluate false positives and missed events. Do not backfill
market-moving 'predictions' using facts learned after the decision date.

## Operational boundaries
- No guaranteed real-time news, no direct feed from a stock exchange and no
  position orders.
- No direct consultation with Claude/Gemini/DeepSeek has been performed.
  Actual model exchange requires configured access and recorded responses.
- Price direction is conditional, not certain; geopolitical shock may cause
  sharp reversals. No profit estimate is produced by keyword detection.
