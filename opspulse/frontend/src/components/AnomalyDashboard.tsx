"use client";
import { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { last30Days } from "@/lib/utils";

const METRICS = [
  { value: "ticket_volume", label: "Ticket Volume" },
  { value: "demand_units", label: "Demand Units" },
  { value: "absent", label: "Absenteeism" },
  { value: "utilization_rate", label: "Utilization Rate" },
];

const SEV_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };

export function AnomalyDashboard() {
  const [metric, setMetric] = useState("ticket_volume");
  const { start, end } = last30Days();
  const params = { metric, start_date: start, end_date: end };

  const { data: anomalies, isLoading } = useSWR(
    ["anomalies", metric],
    () => api.analytics.anomalies(params)
  );

  const sorted = [...(anomalies ?? [])].sort(
    (a, b) => (SEV_ORDER[a.severity] ?? 3) - (SEV_ORDER[b.severity] ?? 3)
  );

  const counts = { critical: 0, high: 0, medium: 0, low: 0 };
  sorted.forEach(a => { counts[a.severity as keyof typeof counts] = (counts[a.severity as keyof typeof counts] ?? 0) + 1; });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex gap-2 flex-wrap">
        {METRICS.map(m => (
          <button key={m.value} onClick={() => setMetric(m.value)}
            className={`px-4 py-2 rounded-lg text-xs font-mono transition-all border ${
              metric === m.value
                ? "bg-accent-amber-dim border-accent-amber/30 text-accent-amber"
                : "bg-bg-card border-bg-border text-text-secondary hover:text-text-primary"
            }`}>
            {m.label}
          </button>
        ))}
      </div>

      {/* Severity summary */}
      <div className="grid grid-cols-4 gap-3">
        {(["critical","high","medium","low"] as const).map(sev => {
          const colorMap = {
            critical: { text: "text-accent-red", bg: "bg-accent-red-dim", border: "border-accent-red/20" },
            high: { text: "text-accent-amber", bg: "bg-accent-amber-dim", border: "border-accent-amber/20" },
            medium: { text: "text-accent-purple", bg: "bg-accent-purple-dim", border: "border-accent-purple/20" },
            low: { text: "text-text-secondary", bg: "bg-bg-elevated", border: "border-bg-border" },
          };
          const c = colorMap[sev];
          return (
            <div key={sev} className={`rounded-xl border p-4 ${c.bg} ${c.border}`}>
              <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest mb-1">{sev}</div>
              <div className={`text-2xl font-display font-bold ${c.text}`}>{counts[sev]}</div>
              <div className="text-[10px] font-mono text-text-muted mt-1">anomalies</div>
            </div>
          );
        })}
      </div>

      {/* Alert feed */}
      <Card glowColor={counts.critical > 0 ? "red" : counts.high > 0 ? "amber" : "none"}>
        <SectionHeader
          title="Anomaly Feed"
          subtitle={`${metric.replace("_", " ")} · Last 30 days`}
          badge={`${sorted.length} detected`}
        />
        {isLoading ? (
          <div className="py-12 text-center text-text-muted font-mono text-sm animate-pulse">Scanning for anomalies...</div>
        ) : sorted.length === 0 ? (
          <div className="py-12 text-center">
            <div className="text-accent-green font-mono text-sm">✓ No anomalies detected</div>
            <div className="text-text-muted font-mono text-xs mt-1">All values within expected range</div>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {sorted.map((a, i) => (
              <div key={i} className="bg-bg-elevated rounded-lg p-4 border border-bg-border hover:border-bg-elevated transition-colors">
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={a.severity} />
                    <span className="text-xs font-mono text-text-secondary">{a.date}</span>
                    {a.department_code && (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-bg-card border border-bg-border text-text-muted">
                        {a.department_code}
                      </span>
                    )}
                  </div>
                  <span className="text-[10px] font-mono text-text-muted shrink-0">
                    Z={a.z_score.toFixed(2)}
                  </span>
                </div>
                <div className="flex gap-4 mb-2">
                  <div>
                    <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest">Observed</div>
                    <div className="text-sm font-display font-semibold text-accent-red">{a.observed_value.toFixed(1)}</div>
                  </div>
                  <div>
                    <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest">Expected</div>
                    <div className="text-sm font-display font-semibold text-text-secondary">{a.expected_value.toFixed(1)}</div>
                  </div>
                  <div>
                    <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest">Δ</div>
                    <div className="text-sm font-display font-semibold text-accent-amber">
                      {a.observed_value > a.expected_value ? "+" : ""}{(a.observed_value - a.expected_value).toFixed(1)}
                    </div>
                  </div>
                </div>
                {a.likely_cause && (
                  <p className="text-xs text-text-secondary font-body leading-relaxed">{a.likely_cause}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
