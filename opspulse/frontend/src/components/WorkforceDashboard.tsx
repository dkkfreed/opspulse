"use client";
import useSWR from "swr";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { MetricTile } from "@/components/ui/MetricTile";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { last30Days, fmtPct, fmtHours, fmtNum, utilizationColor } from "@/lib/utils";
import { format, parseISO } from "date-fns";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, ScatterChart, Scatter, ZAxis
} from "recharts";

const { start, end } = last30Days();
const params = { start_date: start, end_date: end };

export function WorkforceDashboard() {
  const { data: summary } = useSWR("wf-sum", () => api.workforce.summary(params));
  const { data: depts } = useSWR("wf-depts", () => api.workforce.byDepartment(params));
  const { data: heatmap } = useSWR("wf-heat", () => api.workforce.heatmap(params));
  const { data: gaps } = useSWR("wf-gaps", () => api.workforce.gaps(params));

  // Heatmap: group by date
  const heatDates = Array.from(new Set((heatmap ?? []).map(h => h.date))).slice(-14);
  const heatDepts = Array.from(new Set((heatmap ?? []).map(h => h.department_code)));

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricTile label="Employees" value={fmtNum(summary?.total_employees ?? 0)} accent="cyan" />
        <MetricTile label="Avg Utilization" value={fmtPct(summary?.avg_utilization_pct ?? 0)}
          accent={(summary?.avg_utilization_pct ?? 0) > 90 ? "red" : "green"} />
        <MetricTile label="Total Overtime" value={fmtHours(summary?.total_overtime_hours ?? 0)}
          accent={(summary?.total_overtime_hours ?? 0) > 200 ? "amber" : "cyan"} />
        <MetricTile label="Absence Rate" value={fmtPct(summary?.absence_rate_pct ?? 0)} accent="purple" />
      </div>

      {/* Utilization heatmap grid */}
      <Card>
        <SectionHeader title="Utilization Heatmap" subtitle="By department · Last 14 days" badge="Heatmap" />
        <div className="overflow-x-auto">
          <table className="text-[10px] font-mono border-separate border-spacing-0.5">
            <thead>
              <tr>
                <th className="text-text-muted text-left pr-3 py-1 font-normal uppercase tracking-widest">Dept</th>
                {heatDates.map(d => (
                  <th key={d} className="text-text-muted font-normal w-8 text-center">
                    {format(parseISO(d), "d")}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {heatDepts.map(dept => (
                <tr key={dept}>
                  <td className="text-text-secondary pr-3 py-0.5 whitespace-nowrap">{dept}</td>
                  {heatDates.map(d => {
                    const cell = heatmap?.find(h => h.date === d && h.department_code === dept);
                    const pct = cell?.utilization_pct ?? 0;
                    const bg = pct >= 95 ? "rgba(255,71,87,0.7)" :
                               pct >= 80 ? "rgba(0,230,118,0.6)" :
                               pct >= 60 ? "rgba(255,179,64,0.5)" :
                               "rgba(74,80,104,0.3)";
                    return (
                      <td key={d} className="w-8 h-6 rounded text-center text-[9px]"
                        style={{ background: bg, color: pct > 0 ? "#e8eaf0" : "#4a5068" }}
                        title={`${dept} · ${d} · ${pct}%`}>
                        {pct > 0 ? Math.round(pct) : "–"}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex items-center gap-4 mt-3">
            {[["≥95% Over", "#ff4757"], ["80-94% Optimal","#00e676"], ["60-79% Low","#ffb340"], ["<60% Critical","#4a5068"]].map(([label, color]) => (
              <div key={label} className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-sm" style={{ background: color + "99" }} />
                <span className="text-text-muted text-[10px] font-mono">{label}</span>
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* Dept table */}
      <Card>
        <SectionHeader title="Department Breakdown" />
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-bg-border">
                {["Department","Headcount","Sched Hours","Actual Hours","Util %","OT Hours","Absences","Demand Cov","Status"].map(h => (
                  <th key={h} className="text-left py-2 px-3 font-mono text-text-muted uppercase tracking-widest text-[10px]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(depts ?? []).map((d, i) => (
                <tr key={i} className="border-b border-bg-border/50 hover:bg-bg-elevated/40 transition-colors">
                  <td className="py-2.5 px-3 font-display font-medium text-text-primary">{d.department_name}</td>
                  <td className="py-2.5 px-3 font-mono text-text-secondary">{d.headcount}</td>
                  <td className="py-2.5 px-3 font-mono text-text-secondary">{fmtHours(d.scheduled_hours)}</td>
                  <td className="py-2.5 px-3 font-mono text-text-secondary">{fmtHours(d.actual_hours)}</td>
                  <td className="py-2.5 px-3 font-mono font-semibold" style={{ color: utilizationColor(d.utilization_pct) }}>
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

      {/* Staffing gaps */}
      {(gaps ?? []).length > 0 && (
        <Card glowColor="amber">
          <SectionHeader title="Staffing Gaps" subtitle="Days where demand exceeds capacity by >5%" badge={`${gaps?.length} gaps`} />
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-bg-border">
                  {["Date","Department","Demand","Capacity","Gap","Gap %","Severity"].map(h => (
                    <th key={h} className="text-left py-2 px-3 font-mono text-text-muted uppercase tracking-widest text-[10px]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(gaps ?? []).slice(0, 15).map((g, i) => (
                  <tr key={i} className="border-b border-bg-border/50 hover:bg-bg-elevated/40 transition-colors">
                    <td className="py-2 px-3 font-mono text-text-secondary">{g.date}</td>
                    <td className="py-2 px-3 font-display text-text-primary">{g.department_name}</td>
                    <td className="py-2 px-3 font-mono text-text-secondary">{g.demand.toFixed(1)}</td>
                    <td className="py-2 px-3 font-mono text-text-secondary">{g.capacity.toFixed(1)}</td>
                    <td className="py-2 px-3 font-mono text-accent-amber">+{g.gap.toFixed(1)}</td>
                    <td className="py-2 px-3 font-mono text-accent-amber">{fmtPct(g.gap_pct)}</td>
                    <td className="py-2 px-3"><StatusBadge status={g.severity} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
