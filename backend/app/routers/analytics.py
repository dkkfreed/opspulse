"""
Analytics API Router
Provides aggregated metrics for all dashboard views.
Role-based: analyst | team_lead | executive
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Literal, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.narrative import NarrativeService

router = APIRouter(prefix="/analytics", tags=["Analytics"])
narrative_svc = NarrativeService()


# ---------------------------------------------------------------------------
# Workforce dashboard
# ---------------------------------------------------------------------------

@router.get("/workforce/overview")
async def workforce_overview(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    department_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    end_date = end_date or date.today()
    start_date = start_date or (end_date - timedelta(days=30))

    result = await db.execute(text("""
        SELECT
            COUNT(DISTINCT fo.employee_id)                         AS headcount,
            ROUND(AVG(fo.utilization_pct)::numeric, 1)             AS avg_utilization_pct,
            ROUND(SUM(fo.overtime_hours)::numeric, 1)              AS total_overtime_hours,
            ROUND(
                100.0 * SUM(CASE WHEN fo.is_absent THEN 1 ELSE 0 END)::numeric
                / NULLIF(COUNT(*), 0), 1
            )                                                       AS absence_rate_pct,
            SUM(fo.tasks_completed)                                 AS total_tasks,
            ROUND(AVG(fo.actual_hours)::numeric, 2)                AS avg_actual_hours
        FROM fact_operations fo
        JOIN dim_date dd ON fo.date_id = dd.id
        WHERE dd.date BETWEEN :start AND :end
        AND (:dept_id IS NULL OR fo.department_id = :dept_id)
    """), {"start": start_date, "end": end_date, "dept_id": department_id})
    row = result.mappings().one_or_none()

    # WoW comparison
    prev_start = start_date - (end_date - start_date)
    prev_result = await db.execute(text("""
        SELECT
            ROUND(AVG(fo.utilization_pct)::numeric, 1)  AS prev_utilization_pct,
            COUNT(DISTINCT fo.employee_id)               AS prev_headcount
        FROM fact_operations fo
        JOIN dim_date dd ON fo.date_id = dd.id
        WHERE dd.date BETWEEN :start AND :end
        AND (:dept_id IS NULL OR fo.department_id = :dept_id)
    """), {"start": prev_start, "end": start_date - timedelta(days=1), "dept_id": department_id})
    prev_row = prev_result.mappings().one_or_none()

    metrics = dict(row) if row else {}
    prev = dict(prev_row) if prev_row else {}

    # Compute WoW changes
    metrics["headcount_change"] = (
        int(metrics.get("headcount", 0) or 0) - int(prev.get("prev_headcount", 0) or 0)
    )
    prev_util = prev.get("prev_utilization_pct")
    curr_util = metrics.get("avg_utilization_pct")
    if prev_util and curr_util:
        metrics["utilization_change_pct"] = round(float(curr_util) - float(prev_util), 1)

    metrics["date_range"] = {"start": str(start_date), "end": str(end_date)}
    return metrics


@router.get("/workforce/daily-utilization")
async def workforce_daily_utilization(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    department_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    end_date = end_date or date.today()
    start_date = start_date or (end_date - timedelta(days=60))

    result = await db.execute(text("""
        SELECT
            dd.date,
            COUNT(DISTINCT fo.employee_id)              AS headcount,
            ROUND(AVG(fo.utilization_pct)::numeric, 1)  AS avg_utilization_pct,
            SUM(fo.overtime_hours)                       AS overtime_hours,
            SUM(CASE WHEN fo.is_absent THEN 1 ELSE 0 END) AS absent_count
        FROM fact_operations fo
        JOIN dim_date dd ON fo.date_id = dd.id
        WHERE dd.date BETWEEN :start AND :end
        AND (:dept_id IS NULL OR fo.department_id = :dept_id)
        GROUP BY dd.date
        ORDER BY dd.date
    """), {"start": start_date, "end": end_date, "dept_id": department_id})

    return [dict(r) for r in result.mappings().all()]


@router.get("/workforce/by-department")
async def workforce_by_department(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    end_date = end_date or date.today()
    start_date = start_date or (end_date - timedelta(days=30))

    result = await db.execute(text("""
        SELECT
            dd2.name                                     AS department,
            COUNT(DISTINCT fo.employee_id)               AS headcount,
            ROUND(AVG(fo.utilization_pct)::numeric, 1)   AS avg_utilization_pct,
            SUM(fo.tasks_completed)                      AS total_tasks,
            ROUND(
                100.0 * SUM(CASE WHEN fo.is_absent THEN 1 ELSE 0 END)::numeric
                / NULLIF(COUNT(*), 0), 1
            )                                            AS absence_rate_pct
        FROM fact_operations fo
        JOIN dim_date dd ON fo.date_id = dd.id
        JOIN dim_department dd2 ON fo.department_id = dd2.id
        WHERE dd.date BETWEEN :start AND :end
        GROUP BY dd2.name
        ORDER BY avg_utilization_pct DESC
    """), {"start": start_date, "end": end_date})

    return [dict(r) for r in result.mappings().all()]


# ---------------------------------------------------------------------------
# Tickets dashboard
# ---------------------------------------------------------------------------

@router.get("/tickets/overview")
async def tickets_overview(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    end_date = end_date or date.today()
    start_date = start_date or (end_date - timedelta(days=30))

    result = await db.execute(text("""
        SELECT
            COUNT(*)                                                     AS total_tickets,
            COUNT(*) FILTER (WHERE ft.status IN ('open', 'in_progress'))  AS open_tickets,
            COUNT(*) FILTER (WHERE ft.priority = 'critical')             AS critical_tickets,
            ROUND(
                100.0 * COUNT(*) FILTER (WHERE ft.sla_breached)::numeric
                / NULLIF(COUNT(*), 0), 1
            )                                                            AS sla_breach_pct,
            ROUND(AVG(ft.resolution_minutes) / 60.0, 1)                  AS avg_resolution_hours,
            ROUND(AVG(ft.first_response_minutes)::numeric, 0)            AS avg_first_response_min
        FROM fact_tickets ft
        JOIN dim_date dd ON ft.created_date_id = dd.id
        WHERE dd.date BETWEEN :start AND :end
    """), {"start": start_date, "end": end_date})
    row = result.mappings().one_or_none()
    metrics = dict(row) if row else {}
    metrics["date_range"] = {"start": str(start_date), "end": str(end_date)}
    return metrics


@router.get("/tickets/daily-volume")
async def tickets_daily_volume(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    end_date = end_date or date.today()
    start_date = start_date or (end_date - timedelta(days=60))

    result = await db.execute(text("""
        SELECT
            dd.date,
            COUNT(*)                                                    AS ticket_count,
            COUNT(*) FILTER (WHERE ft.priority = 'critical')           AS critical_count,
            COUNT(*) FILTER (WHERE ft.priority = 'high')               AS high_count,
            COUNT(*) FILTER (WHERE ft.sla_breached)                    AS sla_breaches,
            ROUND(AVG(ft.resolution_minutes)::numeric, 0)              AS avg_resolution_min
        FROM fact_tickets ft
        JOIN dim_date dd ON ft.created_date_id = dd.id
        WHERE dd.date BETWEEN :start AND :end
        GROUP BY dd.date
        ORDER BY dd.date
    """), {"start": start_date, "end": end_date})
    return [dict(r) for r in result.mappings().all()]


@router.get("/tickets/by-category")
async def tickets_by_category(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    end_date = end_date or date.today()
    start_date = start_date or (end_date - timedelta(days=30))

    result = await db.execute(text("""
        SELECT
            ft.category,
            COUNT(*)                                                    AS ticket_count,
            ROUND(
                100.0 * COUNT(*) FILTER (WHERE ft.sla_breached)::numeric
                / NULLIF(COUNT(*), 0), 1
            )                                                           AS sla_breach_pct,
            ROUND(AVG(ft.resolution_minutes) / 60.0, 1)                AS avg_resolution_hours
        FROM fact_tickets ft
        JOIN dim_date dd ON ft.created_date_id = dd.id
        WHERE dd.date BETWEEN :start AND :end
        GROUP BY ft.category
        ORDER BY ticket_count DESC
    """), {"start": start_date, "end": end_date})
    return [dict(r) for r in result.mappings().all()]


# ---------------------------------------------------------------------------
# Narrative insights
# ---------------------------------------------------------------------------

@router.get("/insights")
async def narrative_insights(
    role: Literal["analyst", "team_lead", "executive"] = Query(default="analyst"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    end = date.today()
    start = end - timedelta(days=7)
    prev_start = start - timedelta(days=7)

    # Workforce metrics
    wf_result = await db.execute(text("""
        SELECT
            ROUND(AVG(fo.utilization_pct)::numeric, 1) AS avg_utilization_pct,
            ROUND(100.0 * SUM(CASE WHEN fo.is_absent THEN 1 ELSE 0 END)::numeric / NULLIF(COUNT(*), 0), 1) AS absence_rate_pct,
            COUNT(DISTINCT fo.employee_id) AS headcount
        FROM fact_operations fo JOIN dim_date dd ON fo.date_id = dd.id
        WHERE dd.date BETWEEN :s AND :e
    """), {"s": start, "e": end})
    wf = dict(wf_result.mappings().one_or_none() or {})

    prev_wf = await db.execute(text("""
        SELECT COUNT(DISTINCT fo.employee_id) AS prev_headcount
        FROM fact_operations fo JOIN dim_date dd ON fo.date_id = dd.id
        WHERE dd.date BETWEEN :s AND :e
    """), {"s": prev_start, "e": start - timedelta(days=1)})
    prev_wf_row = dict(prev_wf.mappings().one_or_none() or {})

    # Staffing change %
    curr_hc = int(wf.get("headcount") or 0)
    prev_hc = int(prev_wf_row.get("prev_headcount") or 0)
    if prev_hc:
        wf["staffing_change_pct"] = round((curr_hc - prev_hc) / prev_hc * 100, 1)

    # Ticket metrics
    tk_result = await db.execute(text("""
        SELECT
            COUNT(*) AS total_tickets_this_week,
            ROUND(100.0 * SUM(CASE WHEN ft.sla_breached THEN 1 ELSE 0 END)::numeric / NULLIF(COUNT(*), 0), 1) AS sla_breach_pct,
            ROUND(AVG(ft.resolution_minutes) / 60.0, 1) AS avg_resolution_hours
        FROM fact_tickets ft JOIN dim_date dd ON ft.created_date_id = dd.id
        WHERE dd.date BETWEEN :s AND :e
    """), {"s": start, "e": end})
    tk = dict(tk_result.mappings().one_or_none() or {})

    prev_tk = await db.execute(text("""
        SELECT COUNT(*) AS prev_ticket_count
        FROM fact_tickets ft JOIN dim_date dd ON ft.created_date_id = dd.id
        WHERE dd.date BETWEEN :s AND :e
    """), {"s": prev_start, "e": start - timedelta(days=1)})
    prev_tk_row = dict(prev_tk.mappings().one_or_none() or {})

    curr_vol = int(tk.get("total_tickets_this_week") or 0)
    prev_vol = int(prev_tk_row.get("prev_ticket_count") or 0)
    if prev_vol:
        tk["volume_change_pct"] = round((curr_vol - prev_vol) / prev_vol * 100, 1)
        wf["demand_change_pct"] = tk["volume_change_pct"]

    wf_insights = narrative_svc.generate_workforce_narrative(wf)
    tk_insights = narrative_svc.generate_ticket_narrative(tk)

    if role == "executive":
        return {
            "role": role,
            "executive_summary": narrative_svc.generate_executive_summary(wf, tk, 0),
            "top_alerts": [
                i.__dict__ for i in (wf_insights + tk_insights)
                if i.severity == "alert"
            ][:5],
        }

    return {
        "role": role,
        "workforce_insights": [i.__dict__ for i in wf_insights],
        "ticket_insights": [i.__dict__ for i in tk_insights],
        "generated_at": str(end),
    }
