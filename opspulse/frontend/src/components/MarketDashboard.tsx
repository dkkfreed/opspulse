"use client";
import useSWR from "swr";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { last30Days } from "@/lib/utils";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";

const { start, end } = last30Days();

export function MarketDashboard() {
  const { data: signals } = useSWR("market-all", () =>
    api.analytics.marketSignals({ start_date: start, end_date: end })
  );

  // Group by category
  const catGroups: Record<string, typeof signals> = {};
  (signals ?? []).forEach(s => {
    if (!catGroups[s.category]) catGroups[s.category] = [];
    catGroups[s.category]!.push(s);
  });

  // By industry: avg change_pct
  const industryMap: Record<string, number[]> = {};
  (signals ?? []).forEach(s => {
    if (s.industry) {
      if (!industryMap[s.industry]) industryMap[s.industry] = [];
      industryMap[s.industry].push(s.change_pct);
    }
  });
  const industryData = Object.entries(industryMap).map(([k, v]) => ({
    industry: k,
    avg_change: parseFloat((v.reduce((a, b) => a + b, 0) / v.length).toFixed(2)),
  })).sort((a, b) => b.avg_change - a.avg_change);

  return (
    <div className="flex flex-col gap-6">
      {/* Industry trend chart */}
      <Card>
        <SectionHeader title="Avg Change % by Industry" subtitle="30-day period" badge="Market Intelligence" />
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={industryData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }} barCategoryGap="40%">
            <CartesianGrid strokeDasharray="3 3" stroke="#252836" vertical={false} />
            <XAxis dataKey="industry" tick={{ fontSize: 10, fill: "#8b91a8", fontFamily: "IBM Plex Mono" }} tickLine={false} axisLine={false} />
            <YAxis tick={{ fontSize: 10, fill: "#8b91a8", fontFamily: "IBM Plex Mono" }} tickLine={false} axisLine={false} unit="%" />
            <Tooltip contentStyle={{ background: "#1a1d27", border: "1px solid #252836", borderRadius: 8, fontFamily: "IBM Plex Mono", fontSize: 11 }}
              formatter={(v: number) => [`${v}%`, "Avg Change"]} />
            <Bar dataKey="avg_change" radius={[3,3,0,0]}>
              {industryData.map((d, i) => (
                <Cell key={i} fill={d.avg_change >= 0 ? "#00e676" : "#ff4757"} opacity={0.8} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>

      {/* Raw signals table */}
      <Card>
        <SectionHeader title="Recent Signals" badge={`${signals?.length ?? 0} records`} />
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-bg-border">
                {["Date","Source","Category","Industry","Region","Value","Change %","Notes"].map(h => (
                  <th key={h} className="text-left py-2 px-3 font-mono text-text-muted uppercase tracking-widest text-[10px]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(signals ?? []).slice(0, 30).map((s, i) => (
                <tr key={i} className="border-b border-bg-border/50 hover:bg-bg-elevated/40 transition-colors">
                  <td className="py-2 px-3 font-mono text-text-muted">{s.signal_date}</td>
                  <td className="py-2 px-3 font-mono text-text-secondary">{s.source}</td>
                  <td className="py-2 px-3 font-mono text-accent-cyan">{s.category}</td>
                  <td className="py-2 px-3 font-mono text-text-secondary">{s.industry ?? "–"}</td>
                  <td className="py-2 px-3 font-mono text-text-secondary">{s.region ?? "–"}</td>
                  <td className="py-2 px-3 font-mono text-text-secondary">{s.value.toFixed(1)}</td>
                  <td className="py-2 px-3 font-mono" style={{ color: s.change_pct >= 0 ? "#00e676" : "#ff4757" }}>
                    {s.change_pct >= 0 ? "+" : ""}{s.change_pct.toFixed(1)}%
                  </td>
                  <td className="py-2 px-3 font-mono text-text-muted truncate max-w-[200px]">{s.notes ?? "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
