import { DashboardShell } from "@/components/DashboardShell";
import { AnomalyDashboard } from "@/components/AnomalyDashboard";
export default function AnomaliesPage() {
  return (
    <DashboardShell title="Anomaly Detection" subtitle="Z-score rolling window · Correlated signals">
      <AnomalyDashboard />
    </DashboardShell>
  );
}
