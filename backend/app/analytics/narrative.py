from datetime import date, datetime
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


def generate_narrative(
    db: Session,
    period_start: date,
    period_end: date,
    role_level: str = "analyst",
) -> dict:
    """Generate a plain-English analytics summary from computed metrics."""
    from sqlalchemy import text

    # Workforce metrics
    ops_query = db.execute(text("""
        SELECT
            COUNT(DISTINCT fo.employee_id) as headcount,
            AVG(fo.utilization_rate) as avg_utilization,
            SUM(fo.absent::int) as total_absences,
            SUM(fo.overtime_hours) as total_overtime,
            AVG(fo.demand_units) as avg_demand,
            AVG(fo.capacity_units) as avg_capacity
        FROM fact_operations fo
        JOIN dim_date dd ON fo.date_id = dd.id
        WHERE dd.date BETWEEN :start AND :end
    """), {"start": period_start, "end": period_end}).fetchone()

    # Ticket metrics
    tkt_query = db.execute(text("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status IN ('open','in_progress') THEN 1 ELSE 0 END) as open_count,
            SUM(CASE WHEN sla_breached THEN 1 ELSE 0 END) as breaches,
            AVG(actual_resolution_hours) as avg_resolution,
            AVG(sentiment_score) as avg_sentiment
        FROM fact_ticket ft
        JOIN dim_date dd ON ft.created_date_id = dd.id
        WHERE dd.date BETWEEN :start AND :end
    """), {"start": period_start, "end": period_end}).fetchone()

    # Prior period for WoW/MoM comparison
    delta_days = (period_end - period_start).days
    prior_start = date.fromordinal(period_start.toordinal() - delta_days - 1)
    prior_end = date.fromordinal(period_start.toordinal() - 1)

    prior_tkt = db.execute(text("""
        SELECT COUNT(*) as total
        FROM fact_ticket ft
        JOIN dim_date dd ON ft.created_date_id = dd.id
        WHERE dd.date BETWEEN :start AND :end
    """), {"start": prior_start, "end": prior_end}).fetchone()

    # Build narrative
    utilization = float(ops_query.avg_utilization or 0) * 100
    demand_cov = 0
    if ops_query.avg_capacity and ops_query.avg_capacity > 0:
        demand_cov = (ops_query.avg_demand / ops_query.avg_capacity) * 100

    ticket_total = int(tkt_query.total or 0)
    prior_total = int(prior_tkt.total or 0)
    ticket_change_pct = 0
    if prior_total > 0:
        ticket_change_pct = ((ticket_total - prior_total) / prior_total) * 100

    sla_breach_rate = 0
    if ticket_total > 0:
        sla_breach_rate = (int(tkt_query.breaches or 0) / ticket_total) * 100

    avg_resolution = float(tkt_query.avg_resolution or 0)
    open_tickets = int(tkt_query.open_count or 0)

    key_findings = []
    alerts = []
    recommendations = []

    key_findings.append(
        f"Workforce utilization averaged {utilization:.1f}% over the period "
        f"({ops_query.headcount or 0} active employees tracked)."
    )

    if ticket_change_pct > 10:
        alerts.append(
            f"Support demand rose {ticket_change_pct:.0f}% period-over-period "
            f"({ticket_total} tickets vs {prior_total} prior)."
        )
        recommendations.append("Review staffing allocation to handle elevated support volume.")
    elif ticket_change_pct < -10:
        key_findings.append(
            f"Support demand decreased {abs(ticket_change_pct):.0f}% period-over-period."
        )

    if sla_breach_rate > 20:
        alerts.append(
            f"SLA breach rate reached {sla_breach_rate:.1f}% — exceeds the 20% warning threshold."
        )
        recommendations.append("Audit high-priority ticket queues and escalation paths.")
    elif sla_breach_rate > 0:
        key_findings.append(f"SLA compliance at {100 - sla_breach_rate:.1f}%.")

    if utilization > 95:
        alerts.append(
            f"Workforce is operating at {utilization:.1f}% utilization — over-capacity risk."
        )
        recommendations.append("Consider temporary staffing augmentation or workload redistribution.")
    elif utilization < 60:
        key_findings.append(
            f"Utilization at {utilization:.1f}% suggests available capacity — review scheduling efficiency."
        )

    if demand_cov > 100:
        alerts.append(
            f"Demand ({demand_cov:.0f}% of capacity) is outpacing available staff headcount."
        )

    if float(ops_query.total_overtime or 0) > 100:
        key_findings.append(
            f"Overtime hours totalled {ops_query.total_overtime:.0f}h — monitor for burnout signals."
        )

    # Role-level filtering
    if role_level == "executive":
        key_findings = key_findings[:3]
        alerts = alerts[:2]
        recommendations = recommendations[:2]

    headline = _generate_headline(utilization, ticket_change_pct, sla_breach_rate)
    period_label = f"{period_start.strftime('%b %d')} – {period_end.strftime('%b %d, %Y')}"

    summary = (
        f"For the period {period_label}, the organization tracked {ops_query.headcount or 0} employees "
        f"at {utilization:.1f}% utilization with {ticket_total} support tickets raised "
        f"({open_tickets} still open). "
        f"Average ticket resolution time was {avg_resolution:.1f} hours with a "
        f"{sla_breach_rate:.1f}% SLA breach rate."
    )

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "period": period_label,
        "role_level": role_level,
        "headline": headline,
        "summary": summary,
        "key_findings": key_findings,
        "alerts": alerts,
        "recommendations": recommendations,
    }


def _generate_headline(utilization: float, ticket_change_pct: float, breach_rate: float) -> str:
    if breach_rate > 25 and ticket_change_pct > 15:
        return "High demand surge with SLA risk — immediate attention recommended"
    elif breach_rate > 25:
        return "SLA performance below target — review ticket resolution capacity"
    elif ticket_change_pct > 15:
        return "Support volume trending up significantly — staffing alignment needed"
    elif utilization > 95:
        return "Workforce at near-maximum capacity — monitor for quality degradation"
    elif utilization < 60:
        return "Operational capacity is under-utilized — scheduling review recommended"
    else:
        return "Operations within normal parameters — minor optimizations available"
