from pydantic import BaseModel
from typing import Optional
from datetime import date


class TicketSummary(BaseModel):
    total_open: int
    total_in_progress: int
    total_resolved: int
    total_closed: int
    sla_breach_count: int
    sla_breach_rate: float
    avg_resolution_hours: float
    critical_open: int
    escalated_count: int


class TicketTrend(BaseModel):
    date: date
    created_count: int
    resolved_count: int
    net_change: int
    cumulative_open: int
    avg_sentiment: Optional[float] = None


class SLAReport(BaseModel):
    priority: str
    sla_target_hours: float
    total_tickets: int
    breached_count: int
    breach_rate: float
    avg_resolution_hours: float
    p95_resolution_hours: float


class TicketCategoryBreakdown(BaseModel):
    category: str
    count: int
    pct_of_total: float
    avg_resolution_hours: float
    breach_rate: float
