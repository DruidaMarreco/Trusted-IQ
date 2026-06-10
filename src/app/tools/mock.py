"""Deterministic mock TPO tools — used when the live CDT/ERDC services are not
configured (local dev, unit tests, model evaluation).

They return the same JSON shape the real SQL MI / optimizer output would have so
the Response Generator and the groundedness evaluation have concrete data to
work from. Synthetic data only — no client data.
"""

from __future__ import annotations

from typing import Any

# Synthetic recommendation rows — shape mirrors the Recommendation entity in the
# solution design (account, sku, roi_predicted, volume_predicted, uplift...).
_RECOMMENDATIONS: list[dict[str, Any]] = [
    {
        "account": "Tesco",
        "sku": "KitKat 4-pack",
        "mechanic": "Easter display",
        "period": "April 2025",
        "rank": 1,
        "roi_predicted_pct": 142,
        "avg_planned_roi_pct": 118,
        "uplift_factor": 1.8,
        "guideline_min_uplift": 1.5,
        "incremental_volume_gbp": 2_100_000,
    },
    {
        "account": "Tesco",
        "sku": "KitKat 4-pack",
        "mechanic": "25% price cut",
        "period": "April 2025",
        "rank": 2,
        "roi_predicted_pct": 108,
        "avg_planned_roi_pct": 118,
        "uplift_factor": 1.3,
        "guideline_min_uplift": 1.5,
        "incremental_volume_gbp": 1_200_000,
    },
    {
        "account": "Carrefour",
        "sku": "Oreo 154g",
        "mechanic": "Multibuy 3-for-2",
        "period": "Q1 2025",
        "rank": 1,
        "roi_predicted_pct": 131,
        "avg_planned_roi_pct": 120,
        "uplift_factor": 1.6,
        "guideline_min_uplift": 1.5,
        "incremental_volume_gbp": 1_750_000,
    },
]

# Synthetic optimizer candidate options, used by optimizer_run.
_OPTIMIZER_CANDIDATES: list[dict[str, Any]] = [
    {
        "mechanic": "Easter display",
        "sku": "KitKat 4-pack",
        "cost_gbp": 30_000,
        "roi_predicted_pct": 142,
        "uplift_factor": 1.8,
    },
    {
        "mechanic": "Multibuy 3-for-2",
        "sku": "Oreo 154g",
        "cost_gbp": 18_000,
        "roi_predicted_pct": 131,
        "uplift_factor": 1.6,
    },
    {
        "mechanic": "Gondola end",
        "sku": "Dairy Milk 110g",
        "cost_gbp": 22_000,
        "roi_predicted_pct": 124,
        "uplift_factor": 1.5,
    },
    {
        "mechanic": "25% price cut",
        "sku": "KitKat 4-pack",
        "cost_gbp": 15_000,
        "roi_predicted_pct": 108,
        "uplift_factor": 1.3,
    },
]


def text_to_sql_lookup(params: dict[str, Any]) -> dict[str, Any]:
    """Mock CDT TextToSQL agent — return recommendation rows for an account."""
    account = str(params.get("account") or "").lower()
    rows = [r for r in _RECOMMENDATIONS if not account or r["account"].lower() == account]
    if not rows:
        return {"rows": [], "row_count": 0, "note": "No matching recommendations found."}
    return {"rows": rows, "row_count": len(rows)}


def optimizer_run(params: dict[str, Any]) -> dict[str, Any]:
    """Mock ERDC Optimizer API — pick the best options within a budget."""
    budget = int(params.get("budget_remaining") or 100_000)
    chosen: list[dict[str, Any]] = []
    spent = 0
    for cand in sorted(_OPTIMIZER_CANDIDATES, key=lambda c: -c["roi_predicted_pct"]):
        if spent + cand["cost_gbp"] <= budget:
            chosen.append(cand)
            spent += cand["cost_gbp"]
    return {
        "currency": "GBP",
        "budget": budget,
        "objective": params.get("objective") or "maximise ROI",
        "options": [dict(c, rank=i + 1) for i, c in enumerate(chosen)],
        "selected_count": len(chosen),
        "budget_used": spent,
        "budget_utilisation_pct": round(spent / budget * 100, 1) if budget else 0.0,
    }
