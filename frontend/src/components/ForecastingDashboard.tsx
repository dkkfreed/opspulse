"use client";
import { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { last30Days, fmtNum } from "@/lib/utils";
import { format, parseISO } from "date-fns";
import {
  ResponsiveContainer, ComposedChart, Area, Line, XAxis,
  YAxis, CartesianGrid, Tooltip, ReferenceLine
} from "recharts";

const METRICS = [
  { value: "ticket_volume", label: "Ticket Volume" },
  { value: "demand_units", label: "Demand Units" },
  { value: "utilization_rate", label: "Utilization Rate" },
];

export function ForecastingDashboard() {
  const [metric, setMetric] = useState("ticket_volume");
  const { start } = last30Days();
  const params = { metric, start_date: start, horizon_days: "30" };

  const { data, isLoading } = useSWR(
    ["forecast", metric],
    () => api.analytics.forecast(params)
  );

  const chartData = (data?.points ?? []).map(p => ({
    date: format(parseISO(p.date), "MMM d"),
    actual: !p.is_forecast ? p.predicted : null,
    forecast: p.is_forecast ? p.predicted : null,
    lower: p.lower_bound,
    upper: p.upper_bound,
    isForecast: p.is_forecast,
  }));

  // Find where forecast starts
  const splitIdx = chartData.findIndex(d => d.isForecast);
  const splitDate = splitIdx > 0 ? chartData[splitIdx].date : undefined;

  return (
    <div className="flex flex-col gap-6">
      {/* Metric selector */}
      <div className="flex gap-2">
        {METRICS.map(m => (
          <button key={m.value} onClick={() => setMetric(m.value)}
            className={`px-4 py-2 rounded-lg text-xs font-mono transition-all border ${
              metric === m.value
                ? "bg-accent-cyan-dim border-accent-cyan/30 text-accent-cyan"
                : "bg-bg-card border-bg-border text-text-secondary hover:text-text-primary hover:border-bg-elevated"
            }`}>
            {m.label}
          </button>
        ))}
      </div>

      {/* Model info */}
      {data && (
        <div className="flex gap-4">
          {[
            { label: "Model", value: data.model_type.replace("_", " ") },
            { label: "Horizon", value: `${data.horizon_days} days` },
            { label: "MAE", value: data.mae != null ? fmtNum(Math.round(data.mae * 10) / 10) : "n/a" },
            { label: "RMSE", value: data.rmse != null ? fmtNum(Math.round(data.rmse * 10) / 10) : "n/a" },
            { label: "Confidence", value: `${(data.confidence_interval * 100).toFixed(0)}%` },
          ].map(({ label, value }) => (
            <div key={label} className="bg-bg-card border border-bg-border rounded-lg px-4 py-2.5">
              <div className="text-[10px] font-mono text-text-muted uppercase tracking-widest">{label}</div>
              <div className="text-sm font-display font-semibold text-accent-cyan mt-0.5">{value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Forecast chart */}
      <Card>
        <SectionHeader
          title={`${METRICS.find(m => m.value === metric)?.label} Forecast`}
          subtitle="Historical actuals + 30-day projection with 95% confidence band"
          badge="Ridge Regression"
        />
        {isLoading ? (
          <div className="h-64 flex items-center justify-center">
            <div className="text-text-muted font-mono text-sm animate-pulse">Computing forecast...</div>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="ciGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00d4ff" stopOpacity={0.12}/>
                  <stop offset="95%" stopColor="#00d4ff" stopOpacity={0.02}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#252836" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#8b91a8", fontFamily: "IBM Plex Mono" }} tickLine={false} axisLine={false} interval={6} />
              <YAxis tick={{ fontSize: 10, fill: "#8b91a8", fontFamily: "IBM Plex Mono" }} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: "#1a1d27", border: "1px solid #252836", borderRadius: 8, fontFamily: "IBM Plex Mono", fontSize: 11 }}
                formatter={(val: number, name: string) => [val?.toFixed(1), name]} />
              {splitDate && (
                <ReferenceLine x={splitDate} stroke="#00d4ff" strokeDasharray="4 4" strokeOpacity={0.5}
                  label={{ value: "Forecast →", position: "insideTopRight", fill: "#00d4ff", fontSize: 10, fontFamily: "IBM Plex Mono" }} />
              )}
              <Area type="monotone" dataKey="upper" fill="url(#ciGrad)" stroke="none" name="Upper CI" />
              <Area type="monotone" dataKey="lower" fill="transparent" stroke="none" name="Lower CI" />
              <Line type="monotone" dataKey="actual" stroke="#8b91a8" strokeWidth={1.5} dot={false} name="Actual" connectNulls={false} />
              <Line type="monotone" dataKey="forecast" stroke="#00d4ff" strokeWidth={2} dot={false} name="Forecast"
                strokeDasharray="5 3" connectNulls={false} />
            </ComposedChart>
          </ResponsiveContainer>
        )}
        <div className="flex gap-5 mt-3">
          {[["Actual","#8b91a8","solid"],["Forecast","#00d4ff","dashed"],["95% CI","#00d4ff33","area"]].map(([label, color, style]) => (
            <div key={label} className="flex items-center gap-2">
              <div className="w-6 h-0.5 rounded" style={{ background: color, borderTop: style === "dashed" ? `2px dashed ${color}` : "none" }} />
              <span className="text-[10px] font-mono text-text-muted">{label}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
