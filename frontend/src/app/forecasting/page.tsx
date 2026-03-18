import { DashboardShell } from "@/components/DashboardShell";
import { ForecastingDashboard } from "@/components/ForecastingDashboard";
export default function ForecastingPage() {
  return (
    <DashboardShell title="Forecasting" subtitle="Ridge regression · 30-day horizon · 95% CI">
      <ForecastingDashboard />
    </DashboardShell>
  );
}
