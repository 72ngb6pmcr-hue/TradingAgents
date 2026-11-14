"""Supply-chain scenario research, strictly read-only. No broker, LLM, or network."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

SECTORS = {
    "semiconductors": ["advanced_packaging", "hbm", "lithography", "specialty_gases"],
    "power_grids": ["transformers", "copper", "electrical_steel"],
    "batteries": ["lithium_refining", "graphite", "cathodes"],
    "aerospace": ["turbine_castings", "titanium", "certified_parts"],
    "pharma": ["active_ingredients", "sterile_capacity", "reagents"],
    "chemicals": ["natural_gas", "ammonia", "feedstocks"],
    "automotive": ["semiconductors", "rare_earth_magnets", "batteries"],
    "defense": ["energetic_materials", "semiconductors", "precision_parts"],
    "construction": ["cement", "steel", "copper"],
    "agriculture": ["fertilizers", "natural_gas", "water"],
}
# These edges are research hypotheses, NOT quantified supply-chain exposures.
# A shortage in an input can constrain the downstream output; the opposite
# direction (input demand falling) requires a separate model.
EDGES = [(part, product) for product, parts in SECTORS.items() for part in parts]


def validate_observation(item: dict) -> dict:
    """Require dated, attributable, quantitative evidence; never infer prices."""
    required = ("node", "date", "source_url", "metric", "unit", "value",
                "baseline", "direction")
    missing = [key for key in required if item.get(key) is None or item.get(key) == ""]
    if missing:
        raise ValueError("Missing observation fields: " + ", ".join(missing))
    if item["direction"] not in ("increase", "decrease"):
        raise ValueError("direction must be increase/decrease")
    if item["node"] not in set(SECTORS) | {p for parts in SECTORS.values() for p in parts}:
        raise ValueError("Unknown supply-chain node")
    datetime.fromisoformat(item["date"].replace("Z", "+00:00"))
    if not str(item["source_url"]).startswith(("https://", "http://")):
        raise ValueError("Source URL required")
    for key in ("value", "baseline"):
        if isinstance(item[key], bool) or not isinstance(item[key], (int, float)):
            raise ValueError(key + " must be numeric")
    return item


def analyze(observations: list[dict]) -> dict:
    validated = [validate_observation(o) for o in observations]
    scenarios = []
    for obs in validated:
        downstream = sorted({dst for src, dst in EDGES if src == obs["node"]})
        scenarios.append({
            "trigger": obs,
            "potential_downstream": downstream,
            "hypothesis": ("Potential input bottleneck; verify inventory, substitution, "
                           "spare capacity and supplier concentration before forecasting"
                           if obs["direction"] == "decrease" else
                           "Potential additional input availability; demand and contract "
                           "terms must be checked before inferring downstream benefits"),
            "status": "UNVERIFIED_CAUSAL_HYPOTHESIS",
            "price_prediction": None,
            "equity_signal": None,
            "invalidators": ["Substitute inputs available", "Sufficient inventory",
                             "Demand changes offset supply shock",
                             "Market prices already reflect event"],
        })
    return {
        "schema_version": 1,
        "mode": "RESEARCH_ONLY_NO_ORDERS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sectors": sorted(SECTORS),
        "graph_edges": len(EDGES),
        "observations_count": len(validated),
        "scenarios": scenarios,
        "data_limitations": [
            "Sector graph is a qualitative hypothesis map, not verified supplier exposure",
            "No live market prices, demand/supply forecasts, or verified company fundamentals",
            "No causality, lag, or correlation inferred from missing price histories",
            "An observed shortage does not establish an equity BUY/SELL signal",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations", type=Path, help="JSON list of externally verified observations")
    parser.add_argument("--output", type=Path, default=Path("scan-output/supply_chain_scenarios.json"))
    args = parser.parse_args()
    observations = json.loads(args.observations.read_text(encoding="utf-8")) if args.observations else []
    if not isinstance(observations, list):
        raise ValueError("Observations must be a JSON list")
    result = analyze(observations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Research graph: {result['graph_edges']} edges, {len(observations)} verified-format observations; no orders")


if __name__ == "__main__":
    main()
