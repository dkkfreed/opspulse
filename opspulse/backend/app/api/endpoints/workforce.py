from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, text
from datetime import date, timedelta
from typing import Optional, List
from app.database import get_db
from app.models.facts import FactOperations
from app.models.dimensions import DimDate, DimDepartment

router = APIRouter(prefix="/workforce", tags=["workforce"])


@router.get("/summary")
def get_workforce_summary(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    department_code: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Return aggregate workforce metrics for the selected period."""
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    query = text("""
        SELECT
            COUNT(DISTINCT fo.employee_id) as total_employees,
            ROUND(CAST(SUM(fo.scheduled_hours) AS NUMERIC), 2) as total_scheduled,
            ROUND(CAST(SUM(fo.actual_hours) AS NUMERIC), 2) as total_actual,
            ROUND(CAST(AVG(fo.utilization_rate) * 100 AS NUMERIC), 1) as avg_utilization_pct,
            ROUND(CAST(SUM(fo.overtime_hours) AS NUMERIC), 2) as total_overtime,
            SUM(fo.absent::int) as total_absences,
            ROUND(CAST(AVG(fo.demand_units) AS NUMERIC), 2) as avg_demand,
            ROUND(CAST(AVG(fo.capacity_units) AS NUMERIC), 2) as avg_capacity
        FROM fact_operations fo
        JOIN dim_date dd ON fo.date_id = dd.id
        JOIN dim_department dept ON fo.department_id = dept.id
        WHERE dd.date BETWEEN :start AND :end
        AND (:dept_code IS NULL OR dept.code = :dept_code)
    """)

    row = db.execute(query, {
        "start": start_date, "end": end_date, "dept_code": department_code
    }).fetchone()

    total_emp = int(row.total_employees or 0)
    total_absences = int(row.total_absences or 0)

    return {
        "period_start": start_date,
        "period_end": end_date,
        "total_employees": total_emp,
        "total_scheduled_hours": float(row.total_scheduled or 0),
        "total_actual_hours": float(row.total_actual or 0),
        "avg_utilization_pct": float(row.avg_utilization_pct or 0),
        "total_overtime_hours": float(row.total_overtime or 0),
        "total_absences": total_absences,
        "absence_rate_pct": round(total_absences / max(total_emp, 1) * 100, 1),
        "avg_demand": float(row.avg_demand or 0),
        "avg_capacity": float(row.avg_capacity or 0),
        "demand_coverage_pct": round(
            float(row.avg_demand or 0) / max(float(row.avg_capacity or 1), 0.01) * 100, 1
        ),
    }


@router.get("/by-department")
def get_by_department(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    db: Session = Depends(get_db),
):
    """Return workforce metrics broken down by department."""
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    query = text("""
        SELECT
            dept.code as department_code,
            dept.name as department_name,
            COUNT(DISTINCT fo.employee_id) as headcount,
            ROUND(CAST(SUM(fo.scheduled_hours) AS NUMERIC), 2) as scheduled_hours,
            ROUND(CAST(SUM(fo.actual_hours) AS NUMERIC), 2) as actual_hours,
            ROUND(CAST(AVG(fo.utilization_rate) * 100 AS NUMERIC), 1) as utilization_pct,
            ROUND(CAST(SUM(fo.overtime_hours) AS NUMERIC), 2) as overtime_hours,
            SUM(fo.absent::int) as absence_count,
            ROUND(CAST(SUM(fo.demand_units) AS NUMERIC), 2) as demand_units,
            ROUND(CAST(SUM(fo.capacity_units) AS NUMERIC), 2) as capacity_units
        FROM fact_operations fo
        JOIN dim_date dd ON fo.date_id = dd.id
        JOIN dim_department dept ON fo.department_id = dept.id
        WHERE dd.date BETWEEN :start AND :end
        GROUP BY dept.code, dept.name
        ORDER BY utilization_pct DESC
    """)

    rows = db.execute(query, {"start": start_date, "end": end_date}).fetchall()

    result = []
    for r in rows:
        demand = float(r.demand_units or 0)
        capacity = float(r.capacity_units or 0)
        result.append({
            "department_code": r.department_code,
            "department_name": r.department_name,
            "headcount": int(r.headcount or 0),
            "scheduled_hours": float(r.scheduled_hours or 0),
            "actual_hours": float(r.actual_hours or 0),
            "utilization_pct": float(r.utilization_pct or 0),
            "overtime_hours": float(r.overtime_hours or 0),
            "absence_count": int(r.absence_count or 0),
            "demand_units": demand,
            "capacity_units": capacity,
            "demand_coverage_pct": round(demand / max(capacity, 0.01) * 100, 1),
            "staffing_status": _classify_status(float(r.utilization_pct or 0)),
        })

    return result


@router.get("/utilization-heatmap")
def get_utilization_heatmap(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    db: Session = Depends(get_db),
):
    """Daily utilization by department — suitable for heatmap rendering."""
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    query = text("""
        SELECT
            dd.date,
            dept.code as department_code,
            dept.name as department_name,
            ROUND(CAST(AVG(fo.utilization_rate) * 100 AS NUMERIC), 1) as utilization_pct,
            COUNT(DISTINCT fo.employee_id) as headcount,
            SUM(fo.absent::int) as absences
        FROM fact_operations fo
        JOIN dim_date dd ON fo.date_id = dd.id
        JOIN dim_department dept ON fo.department_id = dept.id
        WHERE dd.date BETWEEN :start AND :end
        GROUP BY dd.date, dept.code, dept.name
        ORDER BY dd.date, dept.code
    """)

    rows = db.execute(query, {"start": start_date, "end": end_date}).fetchall()
    return [
        {
            "date": str(r.date),
            "department_code": r.department_code,
            "department_name": r.department_name,
            "utilization_pct": float(r.utilization_pct or 0),
            "headcount": int(r.headcount or 0),
            "absences": int(r.absences or 0),
        }
        for r in rows
    ]


@router.get("/staffing-gaps")
def get_staffing_gaps(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    db: Session = Depends(get_db),
):
    """Identify days and departments where demand exceeds capacity."""
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    query = text("""
        SELECT
            dd.date,
            dept.code as department_code,
            dept.name as department_name,
            SUM(fo.demand_units) as demand,
            SUM(fo.capacity_units) as capacity,
            SUM(fo.demand_units) - SUM(fo.capacity_units) as gap
        FROM fact_operations fo
        JOIN dim_date dd ON fo.date_id = dd.id
        JOIN dim_department dept ON fo.department_id = dept.id
        WHERE dd.date BETWEEN :start AND :end
        GROUP BY dd.date, dept.code, dept.name
        HAVING SUM(fo.demand_units) > SUM(fo.capacity_units) * 1.05
        ORDER BY gap DESC
        LIMIT 100
    """)

    rows = db.execute(query, {"start": start_date, "end": end_date}).fetchall()
    return [
        {
            "date": str(r.date),
            "department_code": r.department_code,
            "department_name": r.department_name,
            "demand": float(r.demand or 0),
            "capacity": float(r.capacity or 0),
            "gap": float(r.gap or 0),
            "gap_pct": round(float(r.gap or 0) / max(float(r.capacity or 1), 0.01) * 100, 1),
            "severity": _classify_gap(float(r.gap or 0), float(r.capacity or 1)),
        }
        for r in rows
    ]


def _classify_status(utilization_pct: float) -> str:
    if utilization_pct >= 95:
        return "over_capacity"
    elif utilization_pct >= 80:
        return "optimal"
    elif utilization_pct >= 60:
        return "underutilized"
    return "critical_underutilization"


def _classify_gap(gap: float, capacity: float) -> str:
    ratio = gap / max(capacity, 0.01)
    if ratio > 0.25:
        return "critical"
    elif ratio > 0.15:
        return "warning"
    return "low"
