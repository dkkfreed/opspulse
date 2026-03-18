from pydantic import BaseModel
from typing import Optional, List
from datetime import date


class DepartmentBreakdown(BaseModel):
    department_code: str
    department_name: str
    headcount: int
    scheduled_hours: float
    actual_hours: float
    utilization_rate: float
    overtime_hours: float
    absence_count: int
    demand_units: float
    capacity_units: float
    demand_coverage_pct: float


class WorkforceMetrics(BaseModel):
    period_start: date
    period_end: date
    total_employees: int
    total_scheduled_hours: float
    total_actual_hours: float
    avg_utilization_rate: float
    total_overtime_hours: float
    total_absences: int
    absence_rate: float
    demand_coverage_pct: float
    departments: List[DepartmentBreakdown]


class UtilizationSummary(BaseModel):
    date: date
    department_code: str
    department_name: str
    utilization_rate: float
    headcount_present: int
    headcount_scheduled: int


class StaffingGap(BaseModel):
    date: date
    department_code: str
    department_name: str
    demand_units: float
    capacity_units: float
    gap: float
    gap_pct: float
    severity: str
