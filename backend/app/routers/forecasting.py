"""Forecasting API endpoints."""
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd

from app.database import get_db
from app.services.forecasting import ForecastingService

router = APIRouter(prefix="/forecasting", tags=["Forecasting"])
svc = ForecastingService()


@router.get("/ticket-volume")
async def forecast_ticket_volume(
    horizon: int = Query(default=30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(text("""
        SELECT dd.date, COUNT(*) AS ticket_count
        FROM fact_tickets ft
        JOIN dim_date dd ON ft.created_date_id = dd.id
        GROUP BY dd.date
        ORDER BY dd.date
    """))
    rows = result.mappings().all()
    if not rows:
        return {"error": "No ticket data available for forecasting."}

    series = pd.Series(
        {r["date"]: float(r["ticket_count"]) for r in rows},
        dtype=float
    )
    series.index = pd.to_datetime(series.index)
    result_obj = svc.forecast_ticket_volume(series, horizon)
    return {
        "metric": result_obj.metric,
        "horizon_days": result_obj.horizon_days,
        "methodology": result_obj.methodology,
        "mape": result_obj.mape,
        "trend_direction": result_obj.trend_direction,
        "summary": result_obj.summary,
        "points": [p.__dict__ for p in result_obj.points],
    }


@router.get("/workforce-demand")
async def forecast_workforce_demand(
    horizon: int = Query(default=30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(text("""
        SELECT dd.date, ROUND(AVG(fo.utilization_pct)::numeric, 2) AS utilization_pct
        FROM fact_operations fo
        JOIN dim_date dd ON fo.date_id = dd.id
        GROUP BY dd.date
        ORDER BY dd.date
    """))
    rows = result.mappings().all()
    if not rows:
        return {"error": "No operations data available for forecasting."}

    series = pd.Series(
        {r["date"]: float(r["utilization_pct"] or 0) for r in rows},
        dtype=float
    )
    series.index = pd.to_datetime(series.index)
    result_obj = svc.forecast_demand(series, horizon)
    return {
        "metric": result_obj.metric,
        "horizon_days": result_obj.horizon_days,
        "methodology": result_obj.methodology,
        "mape": result_obj.mape,
        "trend_direction": result_obj.trend_direction,
        "summary": result_obj.summary,
        "points": [p.__dict__ for p in result_obj.points],
    }
