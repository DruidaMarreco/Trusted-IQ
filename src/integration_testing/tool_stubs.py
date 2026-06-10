"""Runnable CDT TextToSQL + ERDC Optimizer contract stubs.

Lets you exercise the **live** tool HTTP path before the real services exist.
The request bodies match ``app.tools.cdt.CDTQueryRequest`` /
``app.tools.erdc.OptimiseRequest`` and the responses match the shape
``app.tools`` expects. Synthetic data only; figures are deliberately distinctive
(and tagged ``live-*-stub``) so a live call is obvious in the answer.

Run the stub:
    uv run uvicorn integration_testing.tool_stubs:stub_app --port 8077

Then point the app at it (live tool path) and call the API normally:
    CDT_BASE_URL=http://127.0.0.1:8077  ERDC_BASE_URL=http://127.0.0.1:8077 \
        uv run python src/integration_testing/test.py
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import FastAPI

from app.tools.cdt import CDTQueryRequest
from app.tools.erdc import OptimiseRequest

logger = structlog.get_logger(__name__)

stub_app = FastAPI(title="CDT/ERDC contract stubs")


@stub_app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "service": "cdt-erdc-stubs"}


@stub_app.post("/query")
async def cdt_query(req: CDTQueryRequest) -> dict[str, Any]:
    """CDT TextToSQL contract — returns recommendation rows for the account."""
    logger.info("stub_cdt_query", **req.model_dump())
    account = req.account or "Tesco"
    return {
        "rows": [
            {
                "account": account,
                "sku": "KitKat 4-pack",
                "mechanic": "Easter display",
                "period": "April 2025",
                "rank": 1,
                "roi_predicted_pct": 188,  # distinctive vs the mock's 142
                "avg_planned_roi_pct": 120,
                "uplift_factor": 2.1,
                "guideline_min_uplift": 1.5,
                "incremental_volume_gbp": 2_600_000,
                "source": "live-cdt-stub",
            }
        ],
        "row_count": 1,
        "sql": f"SELECT * FROM recommendations WHERE account = '{account}' ORDER BY rank",
    }


@stub_app.post("/optimise")
async def erdc_optimise(req: OptimiseRequest) -> dict[str, Any]:
    """ERDC Optimizer contract — returns ranked options within the budget."""
    logger.info("stub_erdc_optimise", **req.model_dump())
    budget = req.budget_remaining
    used = min(45_000, budget)
    return {
        "currency": "GBP",
        "budget": budget,
        "objective": req.objective,
        "options": [
            {
                "rank": 1,
                "mechanic": "Gondola end",
                "sku": "Dairy Milk 110g",
                "cost_gbp": used,
                "roi_predicted_pct": 167,  # distinctive vs the mock's 142/131
                "uplift_factor": 1.9,
            }
        ],
        "selected_count": 1,
        "budget_used": used,
        "budget_utilisation_pct": round(used / budget * 100, 1) if budget else 0.0,
        "source": "live-erdc-stub",
    }
