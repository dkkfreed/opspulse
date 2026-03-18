"use client";
import useSWR from "swr";
import { api } from "@/lib/api";
import { MetricTile } from "@/components/ui/MetricTile";
import { Card } from "@/components/ui/Card";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { last30Days, fmtPct, fmtHours, fmtNum, utilizationColor } from "@/lib/utils";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell
} from "recharts";
import { format, parseISO } from "date-fns";

const { start, end } = last30Days();
const params = { start_date: start, end_date: end };

function useSWRLoad<T>(key: string, fetcher: () => Promise<T>) {
  return useSWR<T>(key, fetcher, { refreshInterval: 60000 });
}

export function OverviewDashboard() {
  const { data: wf } = useSWRLoad("wf-summary", () => api.workforce.summary(params));
  const { data: tk } = useSWRLoad("tk-summary", () => api.tickets.summary(params));
  const { data: trends } = useSWRLoad("tk-trends", () => api.tickets.trends(params));
  const { data: depts } = useSWRLoad("wf-dept", () => api.workforce.byDepartment(params));
  const { data: narrative } = useSWRLoad("narrative", () =>
    api.analytics.narrative({ ...params, role_level: "analyst" })
  );

  const trendData = trends?.slice(-14).map(t => ({
    date: format(parseISO(t.date), "MMM d"),
    created: t.created_count,
    resolved: t.resolved_count,
    open: t.cumulative_open,
  })) ?? [];

  return (
    <div className="flex flex-col gap-6">
      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricTile
          label="Employees Active"
          value={fmtNum(wf?.total_employees ?? 0)}
          sub={`${fmtHours(wf?.total_actual_hours ?? 0)} actual`}
          accent="cyan"
        />
        <MetricTile
          label="Avg Utilization"
          value={fmtPct(wf?.avg_utilization_pct ?? 0)}
          sub={`${fmtHours(wf?.total_overtime_hours ?? 0)} OT`}
          accent={
            (wf?.avg_utilization_pct ?? 0) >= 95 ? "red" :
            (wf?.avg_utilization_pct ?? 0) >= 75 ? "green" : "amber"
          }
        />
        <MetricTile
          label="Open Tickets"
          value={fmtNum(tk?.open ?? 0)}
          sub={`${tk?.critical_open ?? 0} critical`}
          accent={(tk?.critical_open ?? 0) > 0 ? "red" : "cyan"}
        />
        <MetricTile
          label="SLA Breach Rate"
          value={fmtPct(tk?.sla_breach_rate_pct ?? 0)}
          sub={`${tk?.sla_breach_count ?? 0} breaches`}
          accent={(tk?.sla_breach_rate_pct ?? 0) > 20 ? "red" : "green"}
        />
      </div>

      {/* Narrative insight */}
      {narrative && (
        <Card glowColor="cyan">
          <div className="flex items-start gap-4">
            <div className="mt-0.5 w-8 h-8 rounded-lg bg-accent-cyan-dim border border-accent-cyan/20 flex items-center justify-center shrink-0">
              <span className="text-accent-cyan text-sm">◈</span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] font-mono text-text-muted uppercase tracking-widest">AI Narrative · Analyst View</span>
                {narrative.alerts.length > 0 && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-accent-red-dim text-accent-red border border-accent-red/30">
                    {narrative.alerts.length} Alert{narrative.alerts.length > 1 ? "s" : ""}
                  </span>
                )}
              </div>
              <p className="text-sm font-display font-semibold text-text-primary mb-1">{narrative.headline}</p>
              <p className="text-xs text-text-secondary font-body leading-relaxed mb-3">{narrative.summary}</p>
              {narrative.alerts.length > 0 && (
                <div className="flex flex-col gap-1">
                  {narrative.alerts.map((a, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs text-accent-amber font-mono">
                      <span className="shrink-0 mt-0.5">⚠</span><span>{a}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Ticket trend */}
        <Card>
          <SectionHeader title="Ticket Volume (14d)" badge="Daily" />
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={trendData} margin={{ top: 5, right: 10, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="createdGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00d4ff" stopOpacity={0.25}/>
                  <stop offset="95%" stopColor="#00d4ff" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="resolvedGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00e676" stopOpacity={0.2}/>
                  <stop offset="95%" stopColor="#00e676" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#252836" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#8b91a8", fontFamily: "IBM Plex Mono" }} tickLine={false} axisLine={false} interval={2} />
              <YAxis tick={{ fontSize: 10, fill: "#8b91a8", fontFamily: "IBM Plex Mono" }} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: "#1a1d27", border: "1px solid #252836", borderRadius: 8, fontFamily: "IBM Plex Mono", fontSize: 11 }} />
              <Area type="monotone" dataKey="created" stroke="#00d4ff" strokeWidth={1.5} fill="url(#createdGrad)" name="Created" dot={false} />
              <Area type="monotone" dataKey="resolved" stroke="#00e676" strokeWidth={1.5} fill="url(#resolvedGrad)" name="Resolved" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
          <div className="flex gap-4 mt-2">
            <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-accent-cyan"/><span className="text-[10px] font-mono text-text-muted">Created</span></div>
            <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-accent-green"/><span className="text-[10px] font-mono text-text-muted">Resolved</span></div>
          </div>
        </Card>

        {/* Dept utilization bars */}
        <Card>
          <SectionHeader title="Dept Utilization" badge="Avg %" />
          <ResponsiveContainer width="100%" height={180}>
            <BarChart
              data={(depts ?? []).slice(0, 6).map(d => ({
                dept: d.department_code,
                pct: d.utilization_pct,
              }))}
              margin={{ top: 5, right: 10, bottom: 0, left: -20 }}
              barCategoryGap="35%"
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#252836" vertical={false} />
              <XAxis dataKey="dept" tick={{ fontSize: 10, fill: "#8b91a8", fontFamily: "IBM Plex Mono" }} tickLine={false} axisLine={false} />
              <YAxis domain={[0, 120]} tick={{ fontSize: 10, fill: "#8b91a8", fontFamily: "IBM Plex Mono" }} tickLine={false} axisLine={false} unit="%" />
              <Tooltip contentStyle={{ background: "#1a1d27", border: "1px solid #252836", borderRadius: 8, fontFamily: "IBM Plex Mono", fontSize: 11 }} formatter={(v: number) => [`${v}%`, "Utilization"]} />
              <Bar dataKey="pct" radius={[3, 3, 0, 0]}>
                {(depts ?? []).slice(0, 6).map((d, i) => (
                  <Cell key={i} fill={utilizationColor(d.utilization_pct)} fillOpacity={0.85} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Department table */}
      <Card>
        <SectionHeader title="Department Summary" badge="30 days" />
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-bg-border">
                {["Department","Headcount","Utilization","OT Hours","Absences","Demand Cover","Status"].map(h => (
                  <th key={h} className="text-left py-2 px-3 font-mono text-text-muted uppercase tracking-widest text-[10px]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(depts ?? []).map((d, i) => (
                <tr key={i} className="border-b border-bg-border/50 hover:bg-bg-elevated/50 transition-colors">
                  <td className="py-2.5 px-3 font-display font-medium text-text-primary">{d.department_name}</td>
                  <td className="py-2.5 px-3 font-mono text-text-secondary">{d.headcount}</td>
                  <td className="py-2.5 px-3 font-mono" style={{ color: utilizationColor(d.utilization_pct) }}>
                    {fmtPct(d.utilization_pct)}
                  </td>
                  <td className="py-2.5 px-3 font-mono text-text-secondary">{fmtHours(d.overtime_hours)}</td>
                  <td className="py-2.5 px-3 font-mono text-text-secondary">{d.absence_count}</td>
                  <td className="py-2.5 px-3 font-mono text-text-secondary">{fmtPct(d.demand_coverage_pct)}</td>
                  <td className="py-2.5 px-3"><StatusBadge status={d.staffing_status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
