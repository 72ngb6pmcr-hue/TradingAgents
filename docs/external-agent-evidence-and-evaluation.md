# Decision note — reusing external trading-agent evidence

Date: 2026-11-05. Tracking: #15. Research only; not a profitability claim.

## Executive decision

**Do not add more bespoke agents now.** First use the existing TradingAgents
backtest/memory framework, a reliable paper portfolio journal, and published
benchmarks to identify whether independent model consultations produce
incremental, risk-adjusted gains over simple baselines. No broker orders.

## External projects: what is reusable?

| Reference | Observed capability / finding | Adopt (not copy blindly) |
|---|---|---|
| [TradingAgents upstream](https://github.com/TauricResearch/TradingAgents) | Already supports separated bull/bear deliberation, model-provider choice per tier, point-in-time controls, saved decision memory, settled alpha and backtesting; Apache-2.0. | **Reuse** built-in graph, `backtest.py` and settlement instead of implementing another conversation framework. Examine existing subscription/remote model providers before introducing a new API adapter. |
| [FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) | Separates language-model reasoning from deterministic valuation and verification; supports financial tooling and debate. | **Borrow the architecture principle** and evidence provenance, not its entire application or dependencies. Verify license for any code before copying. |
| [StockBench](https://arxiv.org/abs/2510.02209) | Sequential trading evaluation reports that most tested LLM agents struggle to beat buy-and-hold. | **Evaluate against buy-and-hold** and report return, drawdown and risk metrics. Avoid cherry-picked examples. |
| [AI-Trader](https://github.com/HKUDS/AI-Trader) | Public multi-model trading experiments; useful as design/evaluation evidence but results are specific to dataset, market, dates and costs. | **Compare measurement methodology**, never transfer reported gains to a new portfolio. |

Sources checked 2026-11-05, subject to upstream changes. Research papers and
README claims are not independently audited brokerage records.

## Audit of this repository (current main)

Already implemented:
- `tradingagents/backtest.py`: runs graph on a grid, settles ratings against
  regional benchmark; explicitly **not a portfolio P&L simulator**.
- `tradingagents/agents/strategy_baselines.py`: deterministic PLN 20/50 MA
  versus buy-and-hold, adjusted-close proxy, explicitly hypothetical.
- `tradingagents/agents/independent_agent_review.py`: three **rule-based**
  independent critiques, **not consultations with external LLMs**.
- `tradingagents/agents/paper_portfolio.py`: standalone journal with replay;
  no evidence it is synchronized to the separately scheduled ChatGPT portfolio
  experiment.
- `tradingagents/agents/four_analyst_review.py`: manual full LLM-run
  entrypoint. Historical OpenRouter free model 429 blocked a previous run.
- `.github/workflows/twice-daily-market-scan.yml`: scheduled read-only
  market scanner; passing CI checks do **not** prove scheduled scan completed,
  nor that any strategy generated net returns.

**Important unresolved inconsistency:** our GitHub market scan and our ChatGPT
virtual PLN 10,000 portfolio are separate processes. Without verified, shared,
immutable holdings and fills, portfolio performance must be labelled
UNVERIFIED. Never reset capital or invent trades to fill missing records.

## Experiment: external models talking to our coordinator

**Stage A — no paid API calls:** freeze a dated, versioned research packet
(ticker, completed OHLCV bars, corporate actions, fundamentals with publication
dates, costs, market timezone, current paper holdings). Ask identical questions
in a model-blind format. Define before running: sample universe, holding
period, baseline, fill-price assumptions, transaction fees, maximum permitted
drawdown, minimum observations and a separate out-of-sample period.

**Stage B — requires actual access:** configure at least two distinct providers
from the existing upstream provider registry with explicit user authorization
for any paid API usage, retaining each raw response, provider/model identity,
parameters, timestamps, rates and costs. Do not claim any consultation occurred
without those artifacts. Models review each other's claims only **after**
their first independent outputs are frozen. A common coordinator then
compares substantive disagreements with verified data. If a provider fails,
record PROVIDER_UNAVAILABLE rather than synthesizing its opinion.

**Stage C — falsifiable evaluation:** compare (1) baseline strategy, (2)
existing TradingAgents, (3) independent-model consultation added to the same
TradingAgents pipeline, on an identical predeclared date grid. Score net
portfolio P&L *when genuine paper fills exist*, total return, maximum
drawdown, turnover, trading costs, alpha vs corresponding market benchmark,
fraction of rejected invalid decisions and model cost per reviewed idea.
Check survivorship/look-ahead leakage and reproducibility. Stop the added
model expense unless it provides convincing net incremental value.

## Near-term decision gates

1. **Resolve reliable portfolio persistence and quote provenance first**;
   no financial claims from a missing journal.
2. **Reuse existing TradingAgents provider registry** rather than build
   Claude/Gemini/DeepSeek integrations unless a documented gap exists.
3. **No automated real trades**; external-model requests and costs require
   permission and traceable credentials; never commit API keys.
4. Communicate plainly to the user: source, tests actually executed,
   confirmed net result or UNVERIFIED, next decision; GitHub is only the
   engineering record.

### What this note does *not* do
No third-party models were invoked, no external collaborators were contacted,
no backtest was run in this document, and no gains or losses were measured.
