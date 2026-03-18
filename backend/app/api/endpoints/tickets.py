from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date, timedelta, datetime
from typing import Optional
from app.database import get_db

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("/summary")
def get_ticket_summary(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    department_code: Optional[str] = None,
    db: Session = Depends(get_db),
):
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    query = text("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN ft.status = 'open' THEN 1 ELSE 0 END) as open_count,
            SUM(CASE WHEN ft.status = 'in_progress' THEN 1 ELSE 0 END) as in_progress_count,
            SUM(CASE WHEN ft.status = 'resolved' THEN 1 ELSE 0 END) as resolved_count,
            SUM(CASE WHEN ft.status = 'closed' THEN 1 ELSE 0 END) as closed_count,
            SUM(CASE WHEN ft.sla_breached THEN 1 ELSE 0 END) as breach_count,
            ROUND(CAST(AVG(ft.actual_resolution_hours) AS NUMERIC), 2) as avg_resolution_hours,
            SUM(CASE WHEN ft.priority = 'critical' AND ft.status IN ('open', 'in_progress') THEN 1 ELSE 0 END) as critical_open,
            SUM(CASE WHEN ft.escalated THEN 1 ELSE 0 END) as escalated_count
        FROM fact_ticket ft
        JOIN dim_date dd ON ft.created_date_id = dd.id
        LEFT JOIN dim_department dept ON ft.department_id = dept.id
        WHERE dd.date BETWEEN :start AND :end
        AND (:dept_code IS NULL OR dept.code = :dept_code)
    """)

    row = db.execute(query, {"start": start_date, "end": end_date, "dept_code": department_code}).fetchone()
    total = int(row.total or 0)
    breaches = int(row.breach_count or 0)

    return {
        "period_start": start_date,
        "period_end": end_date,
        "total": total,
        "open": int(row.open_count or 0),
        "in_progress": int(row.in_progress_count or 0),
        "resolved": int(row.resolved_count or 0),
        "closed": int(row.closed_count or 0),
        "sla_breach_count": breaches,
        "sla_breach_rate_pct": round(breaches / max(total, 1) * 100, 1),
        "avg_resolution_hours": float(row.avg_resolution_hours or 0),
        "critical_open": int(row.critical_open or 0),
        "escalated_count": int(row.escalated_count or 0),
    }


@router.get("/trends")
def get_ticket_trends(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    db: Session = Depends(get_db),
):
    """Daily ticket creation and resolution trends."""
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    query = text("""
        SELECT
            dd.date,
            COUNT(*) as created_count,
            SUM(CASE WHEN ft.status IN ('resolved', 'closed') THEN 1 ELSE 0 END) as resolved_count,
            AVG(ft.sentiment_score) as avg_sentiment
        FROM fact_ticket ft
        JOIN dim_date dd ON ft.created_date_id = dd.id
        WHERE dd.date BETWEEN :start AND :end
        GROUP BY dd.date
        ORDER BY dd.date
    """)

    rows = db.execute(query, {"start": start_date, "end": end_date}).fetchall()
    cumulative_open = 0
    results = []
    for r in rows:
        created = int(r.created_count or 0)
        resolved = int(r.resolved_count or 0)
        cumulative_open += created - resolved
        results.append({
            "date": str(r.date),
            "created_count": created,
            "resolved_count": resolved,
            "net_change": created - resolved,
            "cumulative_open": max(0, cumulative_open),
            "avg_sentiment": round(float(r.avg_sentiment), 2) if r.avg_sentiment else None,
        })
    return results


@router.get("/by-category")
def get_by_category(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    db: Session = Depends(get_db),
):
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    query = text("""
        SELECT
            ft.category,
            COUNT(*) as count,
            AVG(ft.actual_resolution_hours) as avg_hours,
            SUM(CASE WHEN ft.sla_breached THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*),0) * 100 as breach_rate
        FROM fact_ticket ft
        JOIN dim_date dd ON ft.created_date_id = dd.id
        WHERE dd.date BETWEEN :start AND :end
        GROUP BY ft.category
        ORDER BY count DESC
    """)

    rows = db.execute(query, {"start": start_date, "end": end_date}).fetchall()
    total = sum(int(r.count) for r in rows)
    return [
        {
            "category": r.category,
            "count": int(r.count),
            "pct_of_total": round(int(r.count) / max(total, 1) * 100, 1),
            "avg_resolution_hours": round(float(r.avg_hours or 0), 2),
            "breach_rate_pct": round(float(r.breach_rate or 0), 1),
        }
        for r in rows
    ]


@router.get("/sla-report")
def get_sla_report(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    db: Session = Depends(get_db),
):
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    query = text("""
        SELECT
            ft.priority,
            ft.sla_target_hours,
            COUNT(*) as total,
            SUM(CASE WHEN ft.sla_breached THEN 1 ELSE 0 END) as breaches,
            AVG(ft.actual_resolution_hours) as avg_hours,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ft.actual_resolution_hours) as p95_hours
        FROM fact_ticket ft
        JOIN dim_date dd ON ft.created_date_id = dd.id
        WHERE dd.date BETWEEN :start AND :end
        GROUP BY ft.priority, ft.sla_target_hours
        ORDER BY CASE ft.priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END
    """)

    rows = db.execute(query, {"start": start_date, "end": end_date}).fetchall()
    return [
        {
            "priority": r.priority,
            "sla_target_hours": float(r.sla_target_hours or 0),
            "total": int(r.total or 0),
            "breached": int(r.breaches or 0),
            "breach_rate_pct": round(int(r.breaches or 0) / max(int(r.total or 1), 1) * 100, 1),
            "avg_resolution_hours": round(float(r.avg_hours or 0), 2),
            "p95_resolution_hours": round(float(r.p95_hours or 0), 2),
        }
        for r in rows
    ]
