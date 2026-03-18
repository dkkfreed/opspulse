"use client";
import useSWR from "swr";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { last30Days, fmtPct, fmtHours, fmtNum } from "@/lib/utils";

const { start, end } = last30Days();
const params = { start_date: start, end_date: end };

export function ExecutiveDashboard() {
  const { data: narrative } = useSWR("exec-narrative",
    () => api.analytics.narrative({ ...params, role_level: "executive" })
  );
  const { data: wf } = useSWR("exec-wf", () => api.workforce.summary(params));
  const { data: tk } = useSWR("exec-tk", () => api.tickets.summary(params));

  return (
    <div className="flex flex-col gap-6 max-w-4xl">
      {/* Top KPIs — large, clean */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Workforce Utilization", value: fmtPct(wf?.avg_utilization_pct ?? 0), color: (wf?.avg_utilization_pct ?? 0) > 90 ? "#ff4757" : "#00e676" },
          { label: "SLA Compliance", value: fmtPct(100 - (tk?.sla_breach_rate_pct ?? 0)), color: (tk?.sla_breach_rate_pct ?? 0) > 20 ? "#ff4757" : "#00e676" },
          { label: "Open Tickets", value: fmtNum(tk?.open ?? 0), color: (tk?.critical_open ?? 0) > 0 ? "#ff4757" : "#8b91a8" },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-bg-card rounded-xl border border-bg-border p-6 text-center">
            <div className="text-[11px] font-mono text-text-muted uppercase tracking-widest mb-2">{label}</div>
            <div className="text-4xl font-display font-bold" style={{ color }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Narrative */}
      {narrative && (
        <Card glowColor="cyan">
          <div className="mb-4 pb-4 border-b border-bg-border">
            <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-2">Executive Briefing · {narrative.period}</div>
            <h2 className="text-lg font-display font-bold text-text-primary leading-snug">{narrative.headline}</h2>
            <p className="text-sm text-text-secondary font-body mt-2 leading-relaxed">{narrative.summary}</p>
          </div>

          {narrative.alerts.length > 0 && (
            <div className="mb-4">
              <div className="text-[10px] font-mono text-accent-red uppercase tracking-widest mb-2">Action Required</div>
              <div className="flex flex-col gap-2">
                {narrative.alerts.map((a, i) => (
                  <div key={i} className="flex items-start gap-2 bg-accent-red-dim rounded-lg p-3 border border-accent-red/20">
                    <span className="text-accent-red font-mono text-sm shrink-0 mt-0.5">⚠</span>
                    <span className="text-sm text-text-primary font-body">{a}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="mb-4">
            <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-2">Key Findings</div>
            <div className="flex flex-col gap-2">
              {narrative.key_findings.map((f, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="text-accent-cyan font-mono text-sm shrink-0 mt-0.5">◆</span>
                  <span className="text-sm text-text-secondary font-body">{f}</span>
                </div>
              ))}
            </div>
          </div>

          {narrative.recommendations.length > 0 && (
            <div>
              <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-2">Recommendations</div>
              <div className="flex flex-col gap-2">
                {narrative.recommendations.map((r, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <span className="text-accent-green font-mono text-sm shrink-0 mt-0.5">→</span>
                    <span className="text-sm text-text-secondary font-body">{r}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Secondary metrics */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-bg-card rounded-xl border border-bg-border p-5">
          <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-4">Workforce Snapshot</div>
          {[
            ["Employees Tracked", fmtNum(wf?.total_employees ?? 0)],
            ["Scheduled Hours", fmtHours(wf?.total_scheduled_hours ?? 0)],
            ["Overtime Hours", fmtHours(wf?.total_overtime_hours ?? 0)],
            ["Absence Rate", fmtPct(wf?.absence_rate_pct ?? 0)],
            ["Demand Coverage", fmtPct(wf?.demand_coverage_pct ?? 0)],
          ].map(([label, value]) => (
            <div key={label} className="flex justify-between py-2 border-b border-bg-border/50 last:border-0">
              <span className="text-xs font-body text-text-secondary">{label}</span>
              <span className="text-xs font-mono font-medium text-text-primary">{value}</span>
            </div>
          ))}
        </div>
        <div className="bg-bg-card rounded-xl border border-bg-border p-5">
          <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-4">Support Snapshot</div>
          {[
            ["Total Tickets", fmtNum(tk?.total ?? 0)],
            ["Currently Open", fmtNum(tk?.open ?? 0)],
            ["Critical Open", String(tk?.critical_open ?? 0)],
            ["Avg Resolution", fmtHours(tk?.avg_resolution_hours ?? 0)],
            ["Escalated", String(tk?.escalated_count ?? 0)],
          ].map(([label, value]) => (
            <div key={label} className="flex justify-between py-2 border-b border-bg-border/50 last:border-0">
              <span className="text-xs font-body text-text-secondary">{label}</span>
              <span className="text-xs font-mono font-medium text-text-primary">{value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
