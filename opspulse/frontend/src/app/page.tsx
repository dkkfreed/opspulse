import { DashboardShell } from "@/components/DashboardShell";
import { OverviewDashboard } from "@/components/OverviewDashboard";

export default function HomePage() {
  return (
    <DashboardShell
      title="Operations Overview"
      subtitle="Last 30 days · All departments"
    >
      <OverviewDashboard />
    </DashboardShell>
  );
}
