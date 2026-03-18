"""
Narrative Insights Service
Generates plain-English summaries from computed metrics.
No LLM required — rule-based template engine driven by real data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class NarrativeInsight:
    title: str
    body: str
    severity: str  # "info" | "warning" | "alert"
    metric_key: str
    value: float | None = None
    change_pct: float | None = None


class NarrativeService:

    def generate_workforce_narrative(self, metrics: dict[str, Any]) -> list[NarrativeInsight]:
        insights = []

        # Staffing vs demand
        staff_change = metrics.get("staffing_change_pct")
        demand_change = metrics.get("demand_change_pct")
        if staff_change is not None and demand_change is not None:
            gap = demand_change - staff_change
            if gap > 10:
                insights.append(NarrativeInsight(
                    title="Staffing Gap Widening",
                    body=(
                        f"Demand rose {demand_change:.1f}% week-over-week while staffing "
                        f"rose only {staff_change:.1f}%. A {gap:.1f}pp gap may strain "
                        f"capacity and increase SLA risk."
                    ),
                    severity="alert",
                    metric_key="staffing_gap",
                    change_pct=gap,
                ))
            elif gap < -10:
                insights.append(NarrativeInsight(
                    title="Over-Staffing Signal",
                    body=(
                        f"Staffing grew {staff_change:.1f}% while demand grew only "
                        f"{demand_change:.1f}%. Consider reviewing shift allocations."
                    ),
                    severity="warning",
                    metric_key="staffing_overage",
                    change_pct=gap,
                ))

        # Utilization
        util = metrics.get("avg_utilization_pct")
        if util is not None:
            if util < 60:
                insights.append(NarrativeInsight(
                    title="Low Workforce Utilization",
                    body=f"Average utilization is {util:.1f}% — below the 75% operational target.",
                    severity="warning",
                    metric_key="utilization",
                    value=util,
                ))
            elif util > 95:
                insights.append(NarrativeInsight(
                    title="Near-Capacity Utilization",
                    body=f"Average utilization at {util:.1f}%. Risk of burnout and quality degradation.",
                    severity="alert",
                    metric_key="utilization",
                    value=util,
                ))
            else:
                insights.append(NarrativeInsight(
                    title="Utilization On Target",
                    body=f"Workforce utilization is {util:.1f}% — within healthy operating range.",
                    severity="info",
                    metric_key="utilization",
                    value=util,
                ))

        # Absence rate
        absence_rate = metrics.get("absence_rate_pct")
        if absence_rate is not None and absence_rate > 10:
            insights.append(NarrativeInsight(
                title="Elevated Absence Rate",
                body=f"Absence rate is {absence_rate:.1f}% — above the 8% benchmark. Review coverage plans.",
                severity="warning",
                metric_key="absence_rate",
                value=absence_rate,
            ))

        return insights

    def generate_ticket_narrative(self, metrics: dict[str, Any]) -> list[NarrativeInsight]:
        insights = []

        # Volume trend
        vol_change = metrics.get("volume_change_pct")
        if vol_change is not None:
            if vol_change > 20:
                insights.append(NarrativeInsight(
                    title="Ticket Volume Spike",
                    body=f"Support demand rose {vol_change:.1f}% week-over-week. Investigate root cause.",
                    severity="alert",
                    metric_key="ticket_volume",
                    change_pct=vol_change,
                ))
            elif vol_change < -15:
                insights.append(NarrativeInsight(
                    title="Ticket Volume Declining",
                    body=f"Ticket volume dropped {abs(vol_change):.1f}% week-over-week.",
                    severity="info",
                    metric_key="ticket_volume",
                    change_pct=vol_change,
                ))

        # SLA breach rate
        sla_breach = metrics.get("sla_breach_pct")
        if sla_breach is not None:
            if sla_breach > 15:
                insights.append(NarrativeInsight(
                    title="SLA Compliance At Risk",
                    body=(
                        f"{sla_breach:.1f}% of tickets breached SLA targets. "
                        f"Review critical and high priority response times."
                    ),
                    severity="alert",
                    metric_key="sla_breach",
                    value=sla_breach,
                ))

        # Avg resolution time
        avg_res = metrics.get("avg_resolution_hours")
        if avg_res is not None and avg_res > 48:
            insights.append(NarrativeInsight(
                title="Slow Resolution Times",
                body=f"Average resolution time is {avg_res:.1f} hours. Consider triaging backlog.",
                severity="warning",
                metric_key="resolution_time",
                value=avg_res,
            ))

        return insights

    def generate_executive_summary(
        self,
        workforce_metrics: dict[str, Any],
        ticket_metrics: dict[str, Any],
        anomaly_count: int,
    ) -> str:
        parts = ["**Operations Summary**\n"]

        util = workforce_metrics.get("avg_utilization_pct")
        if util:
            parts.append(f"- Workforce utilization: **{util:.1f}%**")

        vol = ticket_metrics.get("total_tickets_this_week")
        vol_change = ticket_metrics.get("volume_change_pct")
        if vol:
            change_str = f" ({'+' if vol_change and vol_change >= 0 else ''}{vol_change:.1f}% WoW)" if vol_change else ""
            parts.append(f"- Ticket volume this week: **{vol}**{change_str}")

        sla = ticket_metrics.get("sla_breach_pct")
        if sla is not None:
            parts.append(f"- SLA compliance: **{100 - sla:.1f}%**")

        if anomaly_count:
            parts.append(f"- Active anomalies flagged: **{anomaly_count}** — review recommended")

        return "\n".join(parts)
