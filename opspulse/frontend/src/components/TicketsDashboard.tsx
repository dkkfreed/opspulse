"use client";
import useSWR from "swr";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { MetricTile } from "@/components/ui/MetricTile";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { last30Days, fmtPct, fmtHours, fmtNum } from "@/lib/utils";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, LineChart, Line, PieChart, Pie, Cell
} from "recharts";

const { start, end } = last30Days();
const params = { start_date: start, end_date: end };

const PRIORITY_COLORS: Record<string, string> = {
  critical: "#ff4757", high: "#ffb340", medium: "#b085ff", low: "#8b91a8"
};

const CAT_COLORS = ["#00d4ff","#00e676","#b085ff","#ffb340","#ff4757","#8b91a8","#00d4ff88","#00e67688","#b085ff88"];

export function TicketsDashboard() {
  const { data: summary } = useSWR("tk-sum2", () => api.tickets.summary(params));
  const { data: trends } = useSWR("tk-tr2", () => api.tickets.trends(params));
  const { data: sla } = useSWR("tk-sla", () => api.tickets.slaReport(params));
  const { data: cats } = useSWR("tk-cat", () => api.tickets.byCategory(params));

  const trendData = (trends ?? []).slice(-21).map(t => ({
    date: t.date.slice(5),
    created: t.created_count,
    resolved: t.resolved_count,
    open: t.cumulative_open,
    sentiment: t.avg_sentiment,
  }));

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricTile label="Total Tickets" value={fmtNum(summary?.total ?? 0)} accent="cyan" />
        <MetricTile label="Open Tickets" value={fmtNum(summary?.open ?? 0)}
          sub={`${summary?.in_progress ?? 0} in progress`} accent="amber" />
        <MetricTile label="Avg Resolution" value={fmtHours(summary?.avg_resolution_hours ?? 0)} accent="purple" />
        <MetricTile label="SLA Breach Rate" value={fmtPct(summary?.sla_breach_rate_pct ?? 0)}
          sub={`${summary?.sla_breach_count ?? 0} breaches`}
          accent={(summary?.sla_breach_rate_pct ?? 0) > 20 ? "red" : "green"} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Volume trend */}
        <Card>
          <SectionHeader title="Daily Volume Trend" badge="21 days" />
          <ResponsiveContainer width="100%" height={190}>
            <BarChart data={trendData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }} barCategoryGap="40%">
              <CartesianGrid strokeDasharray="3 3" stroke="#252836" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#8b91a8", fontFamily: "IBM Plex Mono" }} tickLine={false} axisLine={false} interval={3} />
              <YAxis tick={{ fontSize: 10, fill: "#8b91a8", fontFamily: "IBM Plex Mono" }} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: "#1a1d27", border: "1px solid #252836", borderRadius: 8, fontFamily: "IBM Plex Mono", fontSize: 11 }} />
              <Bar dataKey="created" name="Created" fill="#00d4ff" opacity={0.8} radius={[3,3,0,0]} />
              <Bar dataKey="resolved" name="Resolved" fill="#00e676" opacity={0.7} radius={[3,3,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* Category breakdown */}
        <Card>
          <SectionHeader title="By Category" badge="30 days" />
          <div className="flex gap-4 items-center">
            <ResponsiveContainer width={150} height={150}>
              <PieChart>
                <Pie data={cats ?? []} dataKey="count" nameKey="category" cx="50%" cy="50%"
                  innerRadius={40} outerRadius={65} paddingAngle={2} strokeWidth={0}>
                  {(cats ?? []).map((_, i) => <Cell key={i} fill={CAT_COLORS[i % CAT_COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: "#1a1d27", border: "1px solid #252836", borderRadius: 8, fontFamily: "IBM Plex Mono", fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex flex-col gap-1.5 flex-1 min-w-0">
              {(cats ?? []).slice(0, 7).map((c, i) => (
                <div key={i} className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <div className="w-2 h-2 rounded-sm shrink-0" style={{ background: CAT_COLORS[i % CAT_COLORS.length] }} />
                    <span className="text-[10px] font-mono text-text-secondary truncate">{c.category}</span>
                  </div>
                  <span className="text-[10px] font-mono text-text-muted shrink-0">{c.pct_of_total}%</span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>

      {/* SLA report */}
      <Card glowColor={sla?.some(r => r.breach_rate_pct > 30) ? "red" : "none"}>
        <SectionHeader title="SLA Performance by Priority" />
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-bg-border">
                {["Priority","SLA Target","Total","Breached","Breach Rate","Avg Resolution","P95 Resolution"].map(h => (
                  <th key={h} className="text-left py-2 px-3 font-mono text-text-muted uppercase tracking-widest text-[10px]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(sla ?? []).map((r, i) => (
                <tr key={i} className="border-b border-bg-border/50 hover:bg-bg-elevated/40 transition-colors">
                  <td className="py-2.5 px-3">
                    <span className="font-mono text-[11px] px-2 py-0.5 rounded-full border"
                      style={{ color: PRIORITY_COLORS[r.priority] ?? "#8b91a8",
                               background: (PRIORITY_COLORS[r.priority] ?? "#8b91a8") + "20",
                               borderColor: (PRIORITY_COLORS[r.priority] ?? "#8b91a8") + "40" }}>
                      {r.priority}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 font-mono text-text-secondary">{fmtHours(r.sla_target_hours)}</td>
                  <td className="py-2.5 px-3 font-mono text-text-secondary">{fmtNum(r.total)}</td>
                  <td className="py-2.5 px-3 font-mono text-accent-red">{r.breached}</td>
                  <td className="py-2.5 px-3 font-mono" style={{ color: r.breach_rate_pct > 25 ? "#ff4757" : r.breach_rate_pct > 10 ? "#ffb340" : "#00e676" }}>
                    {fmtPct(r.breach_rate_pct)}
                  </td>
                  <td className="py-2.5 px-3 font-mono text-text-secondary">{fmtHours(r.avg_resolution_hours)}</td>
                  <td className="py-2.5 px-3 font-mono text-text-secondary">{fmtHours(r.p95_resolution_hours)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
