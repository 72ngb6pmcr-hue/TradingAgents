# Game 100k — official paper-only season (from 5 November 2026)

**No real money, no brokerage connectivity, no leverage or shorting.**
This is a *new* season; the older PLN 10k experiment is not backfilled
or silently included in this ledger.

**Source of truth**: `portfolio.json` is an append-only replay-verified
simulated journal. `strategy.json` is the immutable starting target and
research protocol. Each end-of-day run creates `receipts/YYYY-MM-DD.json`
with retrieved unadjusted *daily close* and dated NBP reference rate.
Do not interpret end-of-day proxy fills as quotes at which an investor
could actually transact, or as actual exchange executions.

## Target, chosen before first paper fill

| Instrument | Weight | Target PLN | Reason | Main caveat |
|---|---:|---:|---|---|
| VWCE.DE — Vanguard FTSE All-World UCITS Acc | 35% | 35,000 | Global equity core | Tech/US weight overlap |
| SXRV.DE — iShares Nasdaq 100 UCITS Acc | 15% | 15,000 | Growth innovation sleeve | High concentration and drawdowns |
| ETFBW20TR.WA — Beta ETF WIG20TR | 10% | 10,000 | Polish large-cap exposure | Country concentration |
| ETFBM40TR.WA — Beta ETF mWIG40TR | 10% | 10,000 | Polish mid-cap diversification | Liquidity/spreads |
| 4GLD.DE — Xetra Gold ETC | 10% | 10,000 | Gold defensive diversifier | ETC debt/security issuer risk, not UCITS |
| **PLN uninvested event reserve** | **20%** | **20,000** | React to *verified* catalysts | Cash drag |

Total initial targets 80,000 PLN plus 20,000 PLN cash. With integer units,
FX reference and 0.25% paper entry fees, actual invested allocation may
be below target; the remainder stays as cash. If a quote, volume or same-day
NBP rate is missing, instrument is PENDING. No forced trade.

## Timing and pricing

Decision entered **2026-11-05 15:00 Warsaw**. First eligible *modelled*
end-of-day fill **2026-11-05**, after 19:00 Warsaw, subject to every
instrument having a genuine unadjusted 2026-11-05 daily closing bar.
A quote from 4 November cannot fill a 5 November order.
New market/FX quotes are obtained from Yahoo daily prices and dated
official NBP tables. 0.25% per-side simulated fee. Actual broker FX spread,
bid/ask, market impact and taxes are not modelled; measured P&L is
optimistic if those costs are material.

The scheduler checks at **19:40 Warsaw weekdays** (GitHub Actions can be
late or skipped) and keeps transaction receipts in GitHub when write
permission allows. Idempotent trade IDs prevent duplicate initial buys.
The 08:00 and 20:00 ChatGPT summaries are readers, not another book of trades.

## Event-driven policy

Monitor public news about energy routes, geopolitics, central banks,
sanctions and public political/corporate transaction disclosures.
A news headline or a delayed STOCK Act filing is **not** by itself an
investment order. Each candidate must have primary-source corroboration,
market-response and risk / thesis-invalidation analysis. This season has
no automated headline-driven buys or sells; any new strategy orders
require documented decisions and testable rules.

## Risk and scoring

No instrument exceeds 35% of initial capital at first purchase.
Alarm if confirmed portfolio equity falls below **90,000 PLN**: freeze
new risk-taking pending review (this does not guarantee a 10% stop).
Score net return in PLN after modelled fees, max drawdown when enough
daily snapshots exist, and a fair comparison with VWCE bought on the
same eligibility date using identical pricing and cost assumptions.
Mark missing marks as UNVERIFIED, rather than reusing stale prices.
Historical or current returns are not guaranteed future performance.

## What the simulation still cannot do

- Quote true broker bid/ask or execute the exact close price.
- Promise new discovery every hour; news feeds and scheduled runs can lag.
- Confirm market events from GDELT headlines without independent checking.
- Consult third-party LLMs without real connected provider API credentials.
- Prove profitability from a day or two of results.
