from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date, timedelta
from typing import Optional
from app.database import get_db
from app.analytics.forecasting import forecast_metric
from app.analytics.anomaly_detection import detect_zscore_anomalies
from app.analytics.narrative import generate_narrative

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/forecast")
def get_forecast(
    metric: str = Query(default="ticket_volume", description="ticket_volume | demand_units | utilization_rate"),
    department_code: Optional[str] = None,
    horizon_days: int = Query(default=30, ge=7, le=90),
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    db: Session = Depends(get_db),
):
    """Time-series forecast using Ridge regression with engineered time features."""
    if not start_date:
        start_date = date.today() - timedelta(days=90)
    if not end_date:
        end_date = date.today()

    if metric == "ticket_volume":
        query = text("""
            SELECT dd.date, COUNT(*) as value
            FROM fact_ticket ft
            JOIN dim_date dd ON ft.created_date_id = dd.id
            LEFT JOIN dim_department dept ON ft.department_id = dept.id
            WHERE dd.date BETWEEN :start AND :end
            AND (:dept IS NULL OR dept.code = :dept)
            GROUP BY dd.date ORDER BY dd.date
        """)
    elif metric == "demand_units":
        query = text("""
            SELECT dd.date, SUM(fo.demand_units) as value
            FROM fact_operations fo
            JOIN dim_date dd ON fo.date_id = dd.id
            LEFT JOIN dim_department dept ON fo.department_id = dept.id
            WHERE dd.date BETWEEN :start AND :end
            AND (:dept IS NULL OR dept.code = :dept)
            GROUP BY dd.date ORDER BY dd.date
        """)
    elif metric == "utilization_rate":
        query = text("""
            SELECT dd.date, AVG(fo.utilization_rate) * 100 as value
            FROM fact_operations fo
            JOIN dim_date dd ON fo.date_id = dd.id
            LEFT JOIN dim_department dept ON fo.department_id = dept.id
            WHERE dd.date BETWEEN :start AND :end
            AND (:dept IS NULL OR dept.code = :dept)
            GROUP BY dd.date ORDER BY dd.date
        """)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown metric: {metric}")

    rows = db.execute(query, {"start": start_date, "end": end_date, "dept": department_code}).fetchall()

    if len(rows) < 7:
        raise HTTPException(status_code=422, detail="Insufficient data for forecasting (need 7+ days)")

    dates = [r.date for r in rows]
    values = [float(r.value or 0) for r in rows]

    result = forecast_metric(dates, values, horizon_days=horizon_days)
    result["metric"] = metric
    result["department_code"] = department_code
    return result


@router.get("/anomalies")
def get_anomalies(
    metric: str = Query(default="ticket_volume"),
    department_code: Optional[str] = None,
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    db: Session = Depends(get_db),
):
    """Detect anomalies using rolling Z-score method."""
    if not start_date:
        start_date = date.today() - timedelta(days=60)
    if not end_date:
        end_date = date.today()

    if metric == "ticket_volume":
        query = text("""
            SELECT dd.date, COUNT(*) as value
            FROM fact_ticket ft
            JOIN dim_date dd ON ft.created_date_id = dd.id
            LEFT JOIN dim_department dept ON ft.department_id = dept.id
            WHERE dd.date BETWEEN :start AND :end
            AND (:dept IS NULL OR dept.code = :dept)
            GROUP BY dd.date ORDER BY dd.date
        """)
    elif metric in ("demand_units", "utilization_rate", "absent"):
        col = "SUM(fo.demand_units)" if metric == "demand_units" else (
            "AVG(fo.utilization_rate)*100" if metric == "utilization_rate" else "SUM(fo.absent::int)"
        )
        query = text(f"""
            SELECT dd.date, {col} as value
            FROM fact_operations fo
            JOIN dim_date dd ON fo.date_id = dd.id
            LEFT JOIN dim_department dept ON fo.department_id = dept.id
            WHERE dd.date BETWEEN :start AND :end
            AND (:dept IS NULL OR dept.code = :dept)
            GROUP BY dd.date ORDER BY dd.date
        """)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown metric: {metric}")

    rows = db.execute(query, {"start": start_date, "end": end_date, "dept": department_code}).fetchall()
    if not rows:
        return []

    dates = [r.date for r in rows]
    values = [float(r.value or 0) for r in rows]

    return detect_zscore_anomalies(dates, values, metric=metric, department_code=department_code)


@router.get("/narrative")
def get_narrative(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    role_level: str = Query(default="analyst", description="analyst | lead | executive"),
    db: Session = Depends(get_db),
):
    """Generate a plain-English operations summary for the selected period."""
    if not start_date:
        start_date = date.today() - timedelta(days=7)
    if not end_date:
        end_date = date.today()

    if role_level not in ("analyst", "lead", "executive"):
        raise HTTPException(status_code=400, detail="role_level must be analyst, lead, or executive")

    return generate_narrative(db, start_date, end_date, role_level)


@router.get("/market-signals")
def get_market_signals(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    query = text("""
        SELECT
            fms.signal_date,
            fms.source,
            fms.category,
            fms.subcategory,
            fms.region,
            fms.industry,
            fms.value,
            fms.value_label,
            fms.change_pct,
            fms.notes
        FROM fact_market_signal fms
        WHERE fms.signal_date BETWEEN :start AND :end
        AND (:cat IS NULL OR fms.category = :cat)
        ORDER BY fms.signal_date DESC
        LIMIT 200
    """)

    rows = db.execute(query, {"start": start_date, "end": end_date, "cat": category}).fetchall()
    return [dict(r._mapping) for r in rows]
