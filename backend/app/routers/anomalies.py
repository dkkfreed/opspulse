"""Anomaly Detection API endpoints."""
from __future__ import annotations
from datetime import date, timedelta
from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd

from app.database import get_db
from app.services.anomaly_detection import AnomalyDetectionService

router = APIRouter(prefix="/anomalies", tags=["Anomaly Detection"])
svc = AnomalyDetectionService()


@router.get("/tickets")
async def ticket_anomalies(
    days: int = Query(default=90, ge=30, le=365),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    end = date.today()
    start = end - timedelta(days=days)

    result = await db.execute(text("""
        SELECT
            dd.date,
            COUNT(*)                                                     AS ticket_count,
            COUNT(*) FILTER (WHERE ft.priority = 'critical')            AS critical_count,
            COUNT(*) FILTER (WHERE ft.sla_breached)                     AS sla_breaches,
            ROUND(AVG(ft.resolution_minutes)::numeric, 0)               AS avg_resolution_min
        FROM fact_tickets ft
        JOIN dim_date dd ON ft.created_date_id = dd.id
        WHERE dd.date BETWEEN :start AND :end
        GROUP BY dd.date
        ORDER BY dd.date
    """), {"start": start, "end": end})
    rows = result.mappings().all()
    if not rows:
        return {"summary": "No data", "anomalies": []}

    df = pd.DataFrame([dict(r) for r in rows])
    report = svc.detect_ticket_anomalies(df)
    return {
        "summary": report.summary,
        "detection_method": report.detection_method,
        "total_points_analyzed": report.total_points_analyzed,
        "anomaly_rate": report.anomaly_rate,
        "anomalies": [a.__dict__ for a in report.anomalies],
    }


@router.get("/workforce")
async def workforce_anomalies(
    days: int = Query(default=90, ge=30, le=365),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    end = date.today()
    start = end - timedelta(days=days)

    result = await db.execute(text("""
        SELECT
            dd.date,
            ROUND(AVG(fo.utilization_pct)::numeric, 1)                   AS utilization_pct,
            SUM(CASE WHEN fo.is_absent THEN 1 ELSE 0 END)                 AS absent_count,
            SUM(fo.overtime_hours)                                         AS overtime_hours,
            COUNT(DISTINCT fo.employee_id)                                 AS headcount
        FROM fact_operations fo
        JOIN dim_date dd ON fo.date_id = dd.id
        WHERE dd.date BETWEEN :start AND :end
        GROUP BY dd.date
        ORDER BY dd.date
    """), {"start": start, "end": end})
    rows = result.mappings().all()
    if not rows:
        return {"summary": "No data", "anomalies": []}

    df = pd.DataFrame([dict(r) for r in rows])
    report = svc.detect_workforce_anomalies(df)
    return {
        "summary": report.summary,
        "detection_method": report.detection_method,
        "total_points_analyzed": report.total_points_analyzed,
        "anomaly_rate": report.anomaly_rate,
        "anomalies": [a.__dict__ for a in report.anomalies],
    }
